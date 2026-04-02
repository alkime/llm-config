# Build Team

Execute implementation work from an epic using coordinated agents in isolated worktrees. One builder per work stream, parallel execution, validation after each task.

## Inputs

The user provides one of:
1. **An epic ID** (e.g., `pla-oiet`) — the `tk` epic that defines work streams and tasks
2. **A design package directory** (e.g., `docs/chat/`) + instruction to create the epic first
3. **The base branch** to cut worktrees from (defaults to current branch)

If the user provides a design package but no epic exists yet, create the epic and tasks first using `tk create` (see "Epic Creation" below).

## How It Works

The project uses the `tk` CLI for ticket management. Epics define **work streams** — groups of tasks that share a worktree branch. Each work stream is safe to develop in parallel with other streams. Dependencies within and across streams are tracked via `tk dep`.

The Build Team reads the epic, spawns one builder agent per ready work stream, and coordinates through task completion → validation → next task cycles.

## Team Roster

| Role | Agent Name | Responsibility |
|------|------------|----------------|
| Builder(s) | `builder-{stream-name}` | One per work stream. Works in a dedicated worktree. Implements tasks sequentially within its stream. |
| Validator | `validator` | Spawned per completed task. Runs `make check` in the worktree. Reports pass/fail. |
| Team Lead | (you) | Reads epic, sets up worktrees, spawns builders, handles cross-stream deps, creates PRs, reports progress. |

### Builder count

One builder per **currently ready** work stream. The epic's `## Work Streams` section defines what's safe to parallelize. Don't spawn more builders than there are independent streams.

Typical counts:
- Small epic (1-2 streams): 1-2 builders
- Medium epic (3-4 streams): 2-3 builders (some streams may be single-task)
- Large epic (5+ streams): 3-4 builders max (diminishing returns, merge complexity)

## Workflow

### Phase 1: Read the Epic

1. **Read the epic ticket** — `tk show {epic-id}` or read `.tickets/{epic-id}.md`
2. **Parse the work streams** — identify branch names, task chains, and the dependency graph
3. **Check current state** — `tk ready` to see which tasks are unblocked, `tk blocked` to see what's waiting
4. **Read referenced design docs** — architecture briefs, implementation plans, etc.
5. **Identify the first wave** — streams with no cross-stream dependencies that can start immediately

### Phase 2: Setup

1. **Create the team** — `TeamCreate` with name derived from the epic (e.g., `build-chat-mvp`)
2. **Create worktrees** for each stream that can start now:
   ```bash
   git worktree add .worktrees/{stream-branch} -b {stream-branch} {base-branch}
   ```
   Follow AGENTS.md conventions: always in `.worktrees/`, descriptive kebab-case branch names.
3. **Create tasks** in the team task list — one per `tk` ticket that's ready or in the first wave. Set up `addBlockedBy` to mirror the `tk dep` graph.

### Phase 3: Parallel Execution

For each ready work stream, spawn a builder:

```
Agent(
  name: "builder-{stream-name}",
  team_name: "{team-name}",
  mode: "bypassPermissions",
  prompt: <see Builder Prompt Template below>
)
```

**Builder lifecycle within a stream:**
1. Builder reads the task ticket (`.tickets/{id}.md`) — Design section is the implementation blueprint
2. Builder reads referenced design docs and codebase patterns
3. Builder runs `tk start {id}` to claim the task
4. Builder implements the task, following the Design section and style guides
5. Builder verifies against Acceptance Criteria (runs tests, checks specific conditions)
6. Builder commits with a descriptive message
7. Builder runs `tk close {id}`
8. Builder messages team lead: "Task {id} done, stream {name}"

**Team lead on task completion:**
1. Mark the team task as completed
2. Spawn a validator agent in the worktree (see Validation below)
3. If validation passes:
   - Check if the stream has more tasks: `tk ready` filtered to this stream's children
   - If yes: send the builder the next task via `SendMessage`
   - If no: the stream is done. Shut down the builder.
4. If validation fails: send the builder the failure output, builder fixes and re-commits

**Cross-stream dependencies:**
When a task in stream B depends on a completed task in stream A:
1. Team lead waits for stream A's task to complete and validate
2. Team lead rebases stream B's worktree onto stream A's branch (or the base branch if A was merged):
   ```bash
   cd .worktrees/{stream-b-branch}
   git fetch origin
   git rebase {stream-a-branch-or-base}
   ```
3. Then spawn (or message) the builder for stream B with the newly unblocked task

### Phase 4: Validation

After each task completion, spawn a validator:

```
Agent(
  name: "validator",
  team_name: "{team-name}",
  mode: "bypassPermissions",
  prompt: "You are a code validator. Your job is to verify that the recent changes
    in the worktree at {worktree-path} pass all checks.

    Run these commands in order:
    1. cd {worktree-path} && make generate  (regenerate code if schemas/proto changed)
    2. cd {worktree-path} && make check     (runs tests + lint + proto-lint)

    If any step fails, report the exact error output.
    If all pass, report SUCCESS.

    Also review the git diff for obvious issues:
    - Does the code follow the project's Go style guide?
    - Are errors wrapped with context (fmt.Errorf with %w)?
    - Any TODO/FIXME comments that should be addressed?

    Message the team lead with your result: PASS or FAIL with details."
)
```

The validator is short-lived — spawned, runs checks, reports, shuts down. Don't keep it running between tasks.

### Phase 5: Integration

After all streams complete:

1. **Create PRs** — one per work stream, targeting the project branch (or main):
   ```bash
   cd .worktrees/{stream-branch}
   git push -u origin {stream-branch}
   gh pr create --base {target-branch} --title "{stream title}" --body "..."
   ```
2. **Report completion** — summary table of what was built, PRs created, any issues found during validation
3. **Clean up** — shut down all agents, note any remaining tasks

## Builder Prompt Template

Each builder agent receives a prompt structured like this:

```
You are a senior engineer implementing a task from the {epic-title} epic.

## Your Task
- **Ticket:** {task-id} — {task-title}
- **Work stream:** {stream-name} (branch: {branch-name})
- **Worktree path:** .worktrees/{branch-name}

## Context
Read these files before starting:
1. `.tickets/{task-id}.md` — your task. The Design section is your implementation blueprint.
   The Acceptance Criteria define what "done" looks like.
2. `.tickets/{epic-id}.md` — the epic for overall context.
3. {design-doc-paths} — referenced design documents.
4. `AGENTS.md` — project conventions and build commands.
5. `docs/guides/go-style-guide.md` — Go coding patterns (if backend work).

## Working Directory
You are working in the worktree at `.worktrees/{branch-name}`.
All file edits and git operations should happen in this directory.

## Workflow
1. Run `tk start {task-id}` to claim the task
2. Read your task ticket's Design section carefully
3. Implement the changes described
4. Verify the Acceptance Criteria are met
5. Commit your changes with a descriptive message
6. Run `tk close {task-id}`
7. Message the team lead: "Task {task-id} complete"

If your stream has more tasks after this one, the team lead will
send you the next task. Stay available.

## Important
- Follow the project's style guides strictly
- Run `make generate` if you modify Ent schemas or proto files
- Run `make test` and `make lint` before committing
- Wrap all errors with context (fmt.Errorf with %w)
- Don't modify files outside the scope of your task
```

## Epic Creation (When No Epic Exists)

If the user has a design package (e.g., from a Design Team run) but no `tk` epic, create one:

1. **Read the implementation plan** — specifically the "Work Items" section with milestones and dependencies
2. **Create the epic:**
   ```bash
   tk create "Epic Title" -t epic -p 2
   ```
3. **Create tasks** for each work item:
   ```bash
   tk create "Task Title" -t task --parent {epic-id} --tags backend,database
   ```
4. **Set dependencies:**
   ```bash
   tk dep {task-id} {dep-task-id}
   ```
5. **Edit the epic** to add `## Work Streams` and `## Parallel Execution` sections, following the established format:
   ```markdown
   ## Work Streams

   ### stream-name (branch: branch-name)
   task-id-1 Description → task-id-2 Description
   (blocking notes if applicable)

   ## Parallel Execution
   Streams that can run concurrently: ...
   After X completes: Y can start ...
   ```
6. **Edit each task** to add `## Design` and `## Acceptance Criteria` sections, pulling from the implementation plan

## Coordination Rules

- **Use `tk` for all task state.** `tk start` when beginning, `tk close` when done, `tk ready` for next task. Don't rely solely on the team task list — `tk` is the canonical source.
- **One builder per stream.** Don't split a stream across multiple agents — tasks within a stream often have implicit ordering and shared context.
- **Shut down completed builders.** When a stream finishes, shut down its builder immediately.
- **Rebase, don't merge.** When updating worktrees from the base branch, use `git rebase` to keep PR diffs clean (per AGENTS.md conventions).
- **Validate before advancing.** Don't send the next task to a builder until validation passes on the current one.
- **Status updates after each wave.** Show the user a table of completed/in-progress/blocked streams.

## Failure Handling

| Failure | Response |
|---------|----------|
| Validation fails (test/lint) | Send failure output to builder, builder fixes and re-commits |
| Builder gets stuck (no progress for extended time) | Message the builder asking for status. If blocked, help resolve or reassign. |
| Cross-stream merge conflict | Team lead resolves manually, or serializes the conflicting tasks |
| Task Design section is ambiguous | Builder messages team lead, who reads the design docs and provides clarification |
| `make generate` changes unexpected files | Builder commits generated code separately, validator re-checks |

## Key Differences from Artificer

| Aspect | Artificer | Build Team |
|--------|-----------|------------|
| Parallelism | Sequential (one task at a time) | Parallel (one builder per stream) |
| Isolation | Single worktree per agent | Dedicated worktree per stream |
| Validation | Self-validated | Separate validator agent |
| Task source | Picks any ready task from epic | Team lead assigns based on stream membership |
| Coordination | Autonomous | Team lead orchestrates waves and cross-stream deps |
| Scope | Single session, single task | Multi-task, multi-stream, full epic execution |
