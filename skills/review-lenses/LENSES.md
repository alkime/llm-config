# Review Lens Catalog

Shared by the `code-reviewer` agent (rates a diff) and the `plan-reviewer` agent (rates a plan's sections).
One lens = one focused review pass. A reviewer runs each *applicable* lens independently, then a judge merges.

Lenses are generic. They point at the repo's own standards instead of copying them, so the standards stay the single
source of truth. **Before running a lens, read the "Read first" sources for it that exist in the repo under review.**
If a source does not exist, skip it; never invent a standard.

## Shared severity scale

Every finding is rated `L`, `M`, or `H` (plan-reviewer also uses `0` = no concern in this section for this lens).
The scale is defined by **consequence and reversibility**, not by how strongly a reviewer feels.

| Sev | Meaning | What happens to it |
|-----|---------|--------------------|
| H | Hard or impossible to undo once it ships, or it harms people/data/security, or it breaks other in-flight work (a stacked-upon PR, a shared fixture, an applied migration). | Fixed before merge. Goes on the ledger. Interrupts the human if the PR is stacked upon. |
| M | Violates a documented repo standard or James's recorded feedback, or will cause bugs/rework later, but is cheap to undo today. | Fixed (or deferred with a reason). Goes on the ledger. |
| L | Local, cosmetic, or a judgment call with no lasting consequence. | Fixed silently. Never on the ledger. |

**Tie-break rules (apply in order):**
1. Irreversible beats reversible (code review only; a plan is rated as it would ship, so rule 1's drop never applies to plans): if the same flaw is H when shipped to staging/prod, rate it H only when the diff
   actually reaches an environment that cannot cheaply roll it back (applied/pushed migration, proto field on `main`,
   public API). Inside a branch that has not reached `main` and has no applied side effects (a PR merged into a project branch
   counts as unreached until the project->main PR merges; an applied migration or deployed environment does not), drop
   one level (H -> M).
2. A violation of a *written* standard (style guide, AGENTS.md, a `feedback_*` memory) is at least M. An *unwritten*
   preference is at most M, and is L when it is only taste.
3. Count the blast radius, not the lines. One-line flaws in a shared helper outrank sprawling flaws in a leaf.
4. If two levels both fit, choose the higher one only when rule 1 says irreversible; otherwise choose the lower one.
5. One root cause appearing in several places or plan sections is one finding at its owning location; mark the rest
   "same root as ..." and do not re-rate them.
6. Never rate on tone ("ugly", "confusing") alone. A finding must name the concrete failure or the written rule.
7. "Deferred" means deferred in the epic/plan text. A rule recorded only in a memory/sweep note (e.g. the
   provider-agnostic rename sweep) does not exempt a finding: rate it M with `disp=deferred`.

## How to read a lens

- **Applies when:** diff/plan signals that make the lens relevant. If none match, the lens is skipped (recorded as
  `skipped` with the reason, not run).
- **Check:** what to look for.
- **Rubric:** concrete H/M/L triggers. Two reviewers given the same issue should land on the same row.
- **Read first:** repo sources to consult.
- **Plan mode:** how the lens reads when the artifact is a plan section rather than code.

---

## 1. ownership-dry

**Applies when:** the diff adds types, helpers, constants, or converters; adds a second implementation of something;
or the plan introduces a new component/table/service/struct.

**Check:**
- Parallel copies of a type or helper that already exists elsewhere, plus a field-by-field converter between them.
- A concept with more than one owner (two packages each deciding the same rule; two call sites that must be kept in
  sync by hand).
- New abstraction with a single caller and no second caller in sight (premature), or copy-paste with 3+ copies
  (missing abstraction).
- Config/wiring constructed in several places that must stay symmetric.

**Rubric:**
- H: two owners of a rule that guards money, auth, or data integrity, and they already disagree.
- M: duplicated domain type with a mechanical converter; wiring that must be edited in N places and the diff edits
  fewer than N; a rule duplicated across layers where drift would change behaviour.
- L: small duplicated helper (<10 lines) within one package; extraction that is merely optional.

**Read first:** `docs/guides/go-style-guide.md` (don't duplicate domain types; typed JSON fields), repo `AGENTS.md`,
memory `feedback_two_storage_clients`, `feedback_one_to_one_json_embed`.

**Plan mode:** flag sections that introduce a second owner of an existing concept, or a new table/service where the
repo's established pattern embeds or reuses.

## 2. coupling-boundaries

**Applies when:** the diff crosses layers (handler -> biz -> data, client -> API), adds imports between packages,
adds dependencies, or the plan changes who calls whom.

**Check:**
- Layer violations (handler doing business logic, biz importing transport types, UI doing data shaping the API should).
- Import direction and cycles; a low-level package gaining a dependency on a higher-level one.
- Functions that take too many parameters/return too many values (repo limits), god structs.
- Side effects hidden in constructors, init-time global state, migrations run implicitly at startup.
- Shared mutable state between features; one feature reaching into another's internals.
- Error handling that loses context at a boundary (unwrapped errors, swallowed errors).

**Rubric:**
- H: a boundary violation that makes a later split/rollback impossible without a rewrite (e.g. business rule only
  enforceable in a client; implicit startup migration).
- M: layer leak; wrong dependency direction; breached parameter/return-count rule in the style guide; unwrapped errors
  across a package boundary; one mode's behaviour leaking into another where the repo says they are disjoint.
- L: naming/placement within the right layer; minor over-exposure of exported symbols.

**Read first:** `docs/guides/go-style-guide.md`, `docs/guides/react-typescript-style-guide.md`, repo `AGENTS.md`
architecture section; memory `feedback_voice_text_split_strict`, `feedback_mobile_compose_decoupled`.

**Plan mode:** flag sections whose design needs cross-layer calls the architecture section doesn't allow, or that
create new coupling between streams.

## 3. data-model-migrations

**Applies when:** the diff touches schema definitions, `migrations/`, generated-schema inputs, SQL, JSON column shapes,
proto messages/enums/fields, or the plan describes new entities, columns, or backfills.

**Check:**
- Is each migration additive? (new nullable/defaulted column, new table, new index). Destructive changes (drop, rename,
  type change, NOT NULL on existing data) need an explicit rollout story.
- **Cross-project additive compatibility:** other in-flight branches/projects share the same database. A migration
  must not break code on `main` or other project branches that have not yet merged it.
- **Migrations-first:** known schema work belongs in the epic's first task. Schema changes appearing mid-project in a
  non-foundation task are a smell; rewrites of an already-applied migration are a human-blocker (schema rewind).
- Data movement (backfills, legacy copies) must be an out-of-band, dry-run-default, idempotent CLI, never a SQL
  function in a migration or a startup job. Cleanup of old tables/columns must be safe if done many releases later. Rebuilding *derived* data (embeddings,
  search indexes, caches) that can always be regenerated is not a data copy and is exempt from the out-of-band rule.
- Privileges/grants for API roles must not be in tracked migrations (local-only fixes go in the seed file).
- Typed structs for JSON fields, not `map[string]any`; strict 1:1 config embedded as JSON rather than a unique-FK table.
- Constraints enforced by the DB (unique/FK) instead of pre-check queries.
- Enum zero values: real `UNSPECIFIED = 0`; a rollout default does not own the zero value.
- Proto: removed/retyped fields are `reserved` (number and name); no field-number reuse.
- Derived temporal state (expired, overdue) computed from timestamps, not stored.

**Rubric:**
- H: destructive/rewriting migration that reaches shared or hosted databases; field-number reuse or retype without
  `reserved` on a shipped proto; data copy that runs at deploy time; GRANT to API roles in a tracked migration;
  migration that breaks `main`'s code against the shared DB.
- M: non-additive change without a rollout story inside an unmerged project; mid-project schema change that belongs in
  the foundation task; `map[string]any` JSON field; pre-check query racing a constraint; stored derived state;
  1:1 config in its own table; enum zero value that encodes a rollout default.
- L: index naming; column ordering; missing comment on a column.

**Read first:** `docs/guides/go-style-guide.md` (items 11, 13, 17, 19, 20), `docs/guides/infra-style-guide.md`
(item 5, proto reserved); memory `feedback_data_migrations_out_of_band`, `feedback_data_api_grants_local_only`,
`feedback_one_to_one_json_embed`, `feedback_no_supabase_reset`.

**Plan mode:** rate the section H if it sequences schema work after dependent code, leaves a destructive step
unscheduled as a human-blocker, or proposes deploy-time data movement.

## 4. security-auth

**Applies when:** the diff touches handlers/RPCs, auth/JWT/RBAC code, protos exposed to clients, queries over
user-authored content, secrets/env/config, storage/signed URLs, logging, or the plan adds an endpoint or role.

**Check:**
- External APIs identify users by `auth_id` (UUID string), never internal numeric IDs.
- Every new RPC declares its auth posture; public RPCs use the repo's explicit `unauthenticated` proto option, and
  anything without it is authenticated and authorized (role/permission or ownership check, not just "logged in").
- Authorization on object access: caller must belong to the circle/owner of the object, checked server-side.
- Secrets never in code, `.env` files, or logs; non-secret config in tracked config, secrets in the secret store.
- User message content never appears in diagnostics: lengths and metadata, not previews. This includes logs, admin
  tooling, SQL examples in PR text.
- Signed URL / host handling; trust of client-supplied IDs; injection (SQL, prompt, path).
- Agent/LLM tools that take IDs from the model: they are endpoints. The model's input is untrusted (prompt injection),
  so each needs the same ownership check as an RPC.
- Test fixtures that grant themselves privileges that production would not.

**Rubric:**
- H: missing authorization on an object-level read/write; numeric user ID exposed in a client-facing proto/response;
  secret committed or logged; user message content in logs/diagnostics; unauthenticated RPC without the explicit
  option being intended (or the reverse: sensitive RPC marked unauthenticated).
- M: authentication present but authorization coarse where a finer check is available; secret-vs-config placed in
  the wrong store; error message leaking internals; new endpoint with no negative authz test.
- L: log level; redundant validation already enforced upstream.

**Read first:** `docs/guides/go-style-guide.md` (item 16 proto options), repo `AGENTS.md`; memory `feedback_no_numeric_ids`,
`feedback_no_user_message_content_in_queries`, `feedback_no_edit_env`, `feedback_fly_config_vs_secrets`,
`feedback_supabase_public_url`, `feedback_data_api_grants_local_only`.

**Plan mode:** rate H when a section adds an endpoint/role without stating who may call it and how that is checked.

## 5. verifiability-tests

**Applies when:** always for code diffs that add or change behaviour; for plans, any section with acceptance or
verification content.

**Check:**
- New business logic, handlers, and non-trivial helpers have tests (happy path, validation error, domain error).
  Generated code, pure wiring, and trivial constructors do not need tests.
- Tests assert behaviour, not implementation; tests would fail if the feature broke.
- Test conventions: table-driven subtests, `_test` package suffix, project assertion libraries.
- E2E specs that mutate users/roles/circles use dedicated seed users. No shared-fixture mutation.
- Verification tier fits the change (cursory / integration / full / voice) and the commands that prove it are named.
- Flaky patterns: sleeps, un-timeboxed network probes, assertions racing UI transitions.
- For a plan section: is there a concrete, runnable way to know it is done? ("works correctly" is not verifiable.)

**Rubric:**
- H: new auth/authorization or data-migration logic with no test at all; verification step that cannot fail (asserts
  nothing) on a high-risk path.
- M: new biz/handler logic with no tests; e2e spec mutating shared fixture users; plan section with no acceptance
  criteria; test that would still pass if the feature were deleted.
- L: missing subtest naming; test-helper tidiness; extra coverage that would be nice.

**Read first:** repo `AGENTS.md` "Testing Patterns" and E2E sections; memory `feedback_e2e_specs_need_dedicated_mutation_users`,
`feedback_run_make_check`, `feedback_integration_tests_on_project_branch`, `feedback_dont_run_e2e`.

**Plan mode:** rate M/H where a section's work cannot be verified without a human and is not marked human-blocker.

## 6. copy-style

**Applies when:** the diff changes member-facing strings (mobile, web, emails), LLM prompts, tool descriptions, or the
plan specifies copy; and, for any diff, the language-level style guides apply to the languages touched.

**Check:**
- Member-facing copy follows the repo copy guide's vocabulary and voice rules (canonical terms, banned terms,
  literal-over-cute, mechanical outcomes near CTAs, action-labelled confirm buttons, canonical strings verbatim).
- Admin/internal UIs are exempt where the guide says so; do not flag them.
- Language style guides: error wrapping with context, structured logging, line/function length limits, TanStack
  Router file conventions, etc. Linter-enforced rules are L unless the linter is suppressed.
- Lint suppressions (`//nolint`) with no reason, or suppressing a rule the guide says never to suppress.

**Rubric:**
- H: none (style is reversible). Exception: member-facing copy that is factually wrong about a consequence
  (promises a deletion that does not happen).
- M: banned term or wrong canonical string in member-facing copy; suppressed `wrapcheck`; fmt.Print in prod code;
  copy missing the mechanical outcome next to a destructive CTA.
- L: casing, punctuation, ordering, comment wording; style nits a formatter or linter would catch.

**Read first:** `docs/guides/copy-style-guide.md`, `docs/guides/go-style-guide.md`,
`docs/guides/react-typescript-style-guide.md`, `docs/guides/infra-style-guide.md`.

**Plan mode:** flag only sections that specify user-visible text or prompts; rate on the copy rules above.

## 7. provider-agnostic-naming

**Applies when:** the diff adds or renames protos, DB columns, struct fields, variables, or functions that name a
concept tied to an external vendor/provider; the plan names new schema or API fields.

**Check:**
- A name for a *concept* (e.g. "the id the voice provider assigns to a session") is vendor-neutral. The vendor name is
  kept only for the integration itself (env vars, config types, client packages, the vendor's own API) or for a
  concrete implementation behind an interface.
- Disambiguating qualifiers when the subsystem has more than one provider (e.g. voice-agent provider vs LLM provider).
- Proto names get the strictest scrutiny: a shipped proto field name is effectively forever.
- A rename of a column holding data requires a hand-written RENAME migration, not edit-and-reset.

**Rubric:**
- H: vendor-baked name added to a proto that reaches `main` (durable contract) AND the concept is clearly generic.
- M: vendor-baked concept name in a DB column, struct field, or function in new code (can be fixed later in a batched
  sweep, so record it; do not force a rename mid-PR); a rename that edits an original migration instead of adding one.
- L: vendor-baked local variable or test name; comments.

**Read first:** memory `feedback_provider_agnostic_names` (the rule, exceptions, and priority order).

**Plan mode:** rate H/M where a plan section defines new proto/schema names that embed a vendor for a generic concept.

---

## 8. correctness-lifecycle

**Applies when:** the diff changes stateful flows (sessions, jobs, retries, close/finalize paths, reconcilers) or
the plan describes one.

**Check:** every created row/session has a path that finalizes it, including on failure after creation; ordering
between competing writers (client, tool, webhook, worker) is defined; guards cannot make a repair/cleanup path dead;
doc comments' guarantees ("exactly once") are actually true; idempotency on retry.

**Rubric:**
- H: data loss or double billing reachable in normal operation on a path that ships to a hosted environment.
- M: orphaned state on a failure path; a path made unreachable by another change; a stated guarantee the code breaks.
- L: narrow race with a graceful fallback; doc comment wording.

**Read first:** the PR/epic description of the intended behaviour; tests around the flow.

**Plan mode:** flag sections with state transitions that name no failure/cleanup path.

---

## Lens selection cheatsheet (code-reviewer)

| Diff contains | Lenses |
|---------------|--------|
| `schema/`, `migrations/`, `*.sql`, `proto/` | data-model-migrations, security-auth, provider-agnostic-naming |
| `handlers/`, auth, RPCs | security-auth, coupling-boundaries, verifiability-tests |
| new Go/Dart/TS logic | ownership-dry, coupling-boundaries, verifiability-tests, copy-style |
| UI strings, emails, prompts | copy-style |
| tests / e2e / CI scripts | verifiability-tests |
| any new identifier naming a vendor | provider-agnostic-naming |
| sessions, jobs, finalize/close/retry paths | correctness-lifecycle |

A lens with no matching signal is skipped. When unsure, run it.
