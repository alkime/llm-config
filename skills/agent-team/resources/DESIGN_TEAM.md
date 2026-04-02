# Architecture Design Team

Orchestrate a team of specialized agents to produce a complete technical design package from an architecture brief or feature specification.

## Inputs

The user provides:
1. **A brief or spec document** — the source of truth for the design work
2. **An output directory** — where deliverables go (e.g., `docs/chat/`)
3. **Optionally, a team composition override** — which roles to include, custom roles, or roles to skip

If the user doesn't specify these, ask.

## Default Team Composition

6 specialists + the team lead (you). Adapt this roster based on the project — not every design needs all roles.

| Role | Agent Name | Deliverable | Depends On |
|------|------------|-------------|------------|
| Systems Architect | `systems-architect` | `01_systems_design.md` | (none) |
| Protocol Designer | `protocol-designer` | `02_api_design.md` | systems-architect |
| Backend Engineer | `backend-engineer` | `03_implementation_plan.md` | systems-architect, protocol-designer |
| Client Engineer | `client-engineer` | `04_client_architecture.md` | protocol-designer |
| Domain Specialist | `domain-specialist` | `05_domain_design.md` | systems-architect |
| Reviewer | `reviewer` | `06_design_review.md` | ALL others |

The team lead (you) writes `00_executive_summary.md` after the reviewer finishes.

**The domain specialist role is flexible.** It adapts to the project:
- AI/agent system → agent-designer (persona, prompts, tools, trust model)
- Data pipeline → data-engineer (schemas, ETL, validation, monitoring)
- Security-sensitive → security-architect (threat model, auth flows, encryption)
- Integrations-heavy → integration-designer (API contracts, webhooks, sync protocols)

Name the agent and tailor its prompt to the domain.

### When to modify the roster

- **No domain-specific complexity?** Drop the domain specialist.
- **API-only project?** Drop client-engineer.
- **Backend-only?** Drop client-engineer, simplify protocol-designer scope.
- **Need extra review depth?** Add a `security-reviewer` alongside the reviewer.
- **Simple feature?** Drop to 3 agents: architect + engineer + reviewer.

## Workflow

### Phase 1: Setup

1. **Read the brief** — understand scope, decisions, constraints, technology stack
2. **Identify the team roster** — which roles are needed for this project
3. **Create the team** — `TeamCreate` with a descriptive name (e.g., `chat-design`)
4. **Create tasks** — one per deliverable, with `addBlockedBy` for the dependency chain
5. **Create the output directory** if it doesn't exist

### Phase 2: Pipeline Execution

Launch agents in dependency waves — maximize parallelism within each wave.

```
Wave 1: systems-architect (no dependencies)
Wave 2: protocol-designer + domain-specialist (depend on Wave 1)
Wave 3: backend-engineer + client-engineer (depend on Waves 1-2)
Wave 4: reviewer (depends on all)
```

For each agent in a wave:
1. **Assign the task** — `TaskUpdate` with owner and `in_progress`
2. **Spawn the agent** — `Agent` tool with `team_name`, `mode: bypassPermissions`
3. **Wait for completion** — agent messages the team lead when done
4. **Mark task complete** — `TaskUpdate` with `completed`
5. **Shut down the agent** — `SendMessage` with `shutdown_request`
6. **Launch the next wave** — spawn all newly-unblocked agents in parallel

### Phase 3: Synthesis

After the reviewer finishes:
1. Read the review document thoroughly
2. Read key sections from all other documents (at minimum: data model, API surface, work items, critical findings)
3. Write `00_executive_summary.md` covering:
   - Architecture at a glance (1 paragraph + key decisions table)
   - Critical findings from the review (each with proposed fix)
   - Key cross-cutting concerns that span multiple documents
   - Recommended implementation sequence (milestones with parallelism opportunities)
   - Top 5 risks (with mitigations)
4. Report completion to the user

### Phase 4: Epic Creation (Optional — for Build Team handoff)

If the user wants to proceed to implementation, create a `tk` epic from the design's work items. This is the handoff artifact that the Build Team consumes.

1. **Create the epic:**
   ```bash
   tk create "Epic Title" -t epic -p 2
   ```

2. **Create tasks** for each work item from the implementation plan's Work Items section:
   ```bash
   tk create "Task Title" -t task --parent {epic-id} --tags backend,database
   ```

3. **Set dependencies** between tasks:
   ```bash
   tk dep {task-id} {dep-task-id}
   ```

4. **Edit the epic** (`.tickets/{epic-id}.md`) to add the standard sections:
   ```markdown
   ## Work Streams

   ### stream-name (branch: branch-name)
   {task-id} Description → {task-id} Description
   (blocking notes where applicable)

   ### another-stream (branch: branch-name)
   {task-id} Description
   (independent — can start immediately)

   ## Parallel Execution

   Streams that can run concurrently right now:
   - stream-a
   - stream-b

   After stream-a completes {task-id}:
   - stream-c can start
   ```

5. **Edit each task** (`.tickets/{task-id}.md`) to add:
   - `## Design` — pull the implementation details from the relevant design document section. Include file paths, code patterns, and key decisions.
   - `## Acceptance Criteria` — concrete, verifiable conditions (e.g., "make test passes", "make lint passes", specific behavioral checks)

**Guidelines for work stream design:**
- Group tasks that touch the same files or packages into the same stream
- Each stream gets its own branch name (descriptive kebab-case, not ticket IDs)
- Streams should be independent enough to develop in parallel without merge conflicts
- Cross-stream dependencies are explicit: noted in the stream description and tracked via `tk dep`
- Branch names come from the implementation plan's milestone groupings or natural code boundaries

**Tip:** The implementation plan (doc 03) and client architecture (doc 04) already have Work Items sections organized by milestone. These map naturally to work streams.

## Agent Prompt Structure

Each agent prompt must include these sections:

### 1. Role
Who they are and what expertise they bring. This frames their perspective.

### 2. Deliverable
Exact file path. E.g., "Write `docs/chat/01_systems_design.md`."

### 3. Context to Read
Ordered list of files to read before starting:
- The architecture brief (always first)
- Project conventions (AGENTS.md, CLAUDE.md, style guides)
- Predecessor documents (e.g., protocol-designer reads systems design first)
- Relevant existing code (e.g., existing Ent schemas, proto files, handlers)

### 4. Sections to Cover
A detailed outline with enough specificity that the agent can write each section without ambiguity. Don't just say "cover the data model" — say which entities, which fields, which relationships, which indexes, and what trade-offs to address.

### 5. Codebase Exploration
Which existing code to examine for patterns. E.g., "Look at `api/schema/` for Ent schema conventions, `api/internal/handlers/` for ConnectRPC handler patterns."

### 6. Notification
Who to message when done. Always include the team lead. Include downstream agents if they're waiting.

### Key Principles
- **Include product context in every prompt.** Agents don't see the original user message. Embed or reference the product vision, tech stack, and domain context.
- **Tell agents to read predecessors BEFORE starting.** Not after, not in parallel with their own work.
- **Be specific about "done."** Each section outline should describe what a complete section looks like.
- **Reference style guides.** Tell agents to follow existing codebase conventions.

## Reviewer Prompt Structure

The reviewer is special — their prompt must include:

1. **All document paths** to read (list every single one)
2. **Specific adversarial angles** to investigate:
   - Race conditions (with specific flows to trace)
   - Data loss scenarios (crash between steps X and Y)
   - Security issues (authentication, authorization, injection, impersonation)
   - Consent/permission violations (especially for sensitive domains)
   - Performance under load (specific numbers to reason about)
   - Document drift (do documents agree on names, types, flows?)
3. **Finding format**: problem → affected documents → concrete scenario → proposed fix
4. **Severity levels**: CRITICAL (must fix before implementation), IMPORTANT (significant risk), MINOR (nice to fix)
5. **Design coherence section**: does the system deliver on the product promise? What's the biggest risk?

## Coordination Rules

- **One task per agent.** Don't assign multiple deliverables to one agent.
- **Shut down completed agents.** Send `shutdown_request` once their work is done and no downstream agent needs them as a message target.
- **Wait for real completion.** Don't launch the next wave until you receive the completion message — not just "started" or "idle."
- **Status updates.** After each wave, update the user with a progress table showing completed/in-progress/blocked tasks.
- **The reviewer reads EVERYTHING.** No shortcuts. List every document in the reviewer prompt.

## Example: Typical Dependency Graph

```
Task #1: Systems Design (systems-architect)       ← Wave 1
  ├→ Task #2: API Design (protocol-designer)      ← Wave 2
  │    ├→ Task #3: Implementation Plan (backend)  ← Wave 3
  │    └→ Task #4: Client Architecture (client)   ← Wave 3
  └→ Task #5: Domain Design (domain-specialist)   ← Wave 2
       ↓
Task #6: Design Review (reviewer)                 ← Wave 4
  ↓
Task #7: Executive Summary (team-lead)            ← Phase 3
```
