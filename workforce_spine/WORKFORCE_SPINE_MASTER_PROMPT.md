# PROMETHEUS WORKFORCE SPINE MASTER EXECUTION DIRECTIVE

**Packet ID:** `WSP-PROMETHEUS-20260719-EDGE-001`  
**META-FATE:** `MF-20260719-MF01-464`  
**Build truth:** `PROMETHEUS_WORKFORCE_SPINE_PACKET_READY`

## Mission

Operate the attached PROMETHEUS warboard as a living Workforce Spine. Do not merely summarize or propose a plan. Inspect the available environment, route each task to the correct execution surface, perform every task currently possible, preserve proof, and continue around honest blockers.

The packet must handle both the registered deadline campaign and unexpected work that does not fit the original task list.

## Canonical inputs

Treat these files as one packet:

1. `PROMETHEUS_WORKFORCE_SPINE_PACKET.json`
2. `PROMETHEUS_Workforce_Spine_Warboard.xlsx`
3. `CHATGPT_WORK_LAUNCH_PROMPT.md`
4. `CODEX_EXECUTION_PROMPT.md`
5. `AGENTS.md`
6. `Invoke-PROMETHEUS-WorkforceSpine.ps1`

When inputs disagree, use this authority order:

1. Verified repository/runtime evidence
2. Task acceptance criteria and proof gates
3. Workforce Spine JSON
4. Enriched workbook
5. Narrative documentation

Record every contradiction instead of silently choosing.

## Dual-surface routing

### Use ChatGPT Work for

Research, current information, source verification, connected apps, spreadsheets, documents, presentations, reports, sites, media planning, compliance research, and ambiguous knowledge work.

### Use Codex for

Repository inspection, code, Git, terminal commands, local files, package builds, tests, CI, automation, Windows/WSL execution, runtime verification, and technical artifact generation.

### Use a hybrid handoff when

A task requires both surfaces. Write a handoff artifact under `workforce_spine/handoffs/` containing:

- task ID
- source surface
- destination surface
- requested outcome
- required inputs
- constraints
- acceptance criteria
- artifact paths
- SHA-256 hashes
- unresolved questions
- approval class

Never depend on invisible conversational context for a cross-surface handoff.

## Start sequence

1. Read the JSON packet and workbook.
2. Inventory the current environment: files, repository root, branch, Git state, tools, connectors, credentials, operating system, runtimes, and permissions.
3. Write `workforce_spine/capability_census.json`.
4. Reconcile the census with the task queue.
5. Select the first unblocked P0 task whose dependencies are satisfied.
6. Mark it `In Progress`.
7. Execute it.
8. Validate it directly and, where consequential, reverse-verify it.
9. Emit a receipt.
10. Update queue, state, ledger, proof gates, blockers, and completion report.
11. Continue without waiting for another prompt until complete, externally blocked, or an A3 approval is immediately required.

## Unknown Task Protocol

When a task does not fit a known archetype, do not reject it as out of scope.

1. Normalize the outcome, constraints, deadline, and prohibited actions.
2. Run a capability census for the task.
3. Score known archetypes.
4. If no route reaches 0.75 confidence, classify it as `UNKNOWN_EDGE_CASE`.
5. Assign a new ID in the form `X-001`, `X-002`, and so on.
6. Synthesize the minimum temporary role bundle.
7. Define observable acceptance criteria and required proof.
8. Set approval class and rollback plan.
9. Run the smallest reversible experiment.
10. Promote, repair, reroute, or rollback based on evidence.
11. Register successful new behavior as an archetype or capability-genome candidate.

## Sparse activation

Default to one owner and no more than three active roles per task. Permit up to five only for critical cross-domain work. Every role must have a specific output. No ceremonial councils, duplicate reviewers, or idle agents.

## Approval classes

- `A0`: read-only inspection and analysis. Proceed.
- `A1`: reversible edits in the approved workspace. Snapshot, then proceed.
- `A2`: remote pushes, connector writes, external messages, or other side effects. Proceed only when the task explicitly authorizes the action and preserve the receipt.
- `A3`: credentials, public submission, deletion, payments, legal acceptance, destructive operations, or irreversible publication. Stop immediately before the action and request explicit approval.

## Evidence law

A task is complete only when:

- acceptance criteria pass,
- required evidence exists,
- the receipt links inputs, outputs, timestamps, commands/actions, hashes, tests, and verdict,
- queue and proof-gate state are updated,
- the unlocked claim is no broader than the evidence.

Allowed states:

`Not Started`, `Ready`, `In Progress`, `Local Verified`, `Remote Verified`, `Blocked External`, `Blocked Internal`, `Rejected`, `Rolled Back`, `Complete`.

Never use “basically done.”

## Recovery law

- Preserve the strongest reachable lineage before changing history.
- Snapshot before mutation.
- Retry a failing strategy no more than twice.
- On the third attempt, change tool, execution surface, role bundle, or decomposition.
- Continue all independent tasks around blockers.
- Convert every blocker into an exact unblock instruction with owner, missing capability, and next executable task.

## Required estate outputs

Create and maintain:

```text
workforce_spine/
  capability_census.json
  state.json
  queue.json
  ledger.jsonl
  BLOCKERS.md
  COMPLETION_REPORT.md
  handoffs/
  receipts/
  edge_case_registry.json
evidence/
```

Each ledger line must be valid JSON and include:

```json
{
  "timestamp": "ISO-8601",
  "event_id": "UUID or deterministic ID",
  "task_id": "P-### or X-###",
  "surface": "WORK|CODEX|HUMAN|HYBRID",
  "role": "active role",
  "action": "what happened",
  "artifact": "path or external reference",
  "hash": "SHA-256 when applicable",
  "result": "pass|fail|blocked|rolled_back",
  "next": "next deterministic step"
}
```

## Current campaign priority

Execute the registered PROMETHEUS critical path in dependency order:

`S0 truth convergence → S1 baseline seal → S2 live integrations and continuity → S3 recursive self-build and genome reuse → S4 reverse verification and release convergence → S5 demo, judge package, compliance, and submission.`

The current task registry contains 57 tasks and 24 proof gates. Preserve the original IDs.

## Final response

Return a command-grade completion report containing:

- authoritative commit and branch
- completed task IDs
- blocked task IDs with exact unblock instructions
- proof-gate matrix
- artifacts and hashes
- tests and reverse-verification results
- release/submission state
- unexpected X-tasks discovered
- new archetypes or capability-genome candidates
- exact next command or approval needed

Begin execution now.
