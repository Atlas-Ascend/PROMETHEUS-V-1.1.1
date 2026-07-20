# AGENTS.md — PROMETHEUS Workforce Spine

Packet: `WSP-PROMETHEUS-20260719-EDGE-001`  
META-FATE: `MF-20260719-MF01-464`

## Repository operating law

- Preserve existing architecture. Patch, route, archive, verify, and promote. Do not replace the system without explicit instruction.
- Work from the authoritative repository root and record the initial branch, HEAD, remotes, and dirty state.
- Before risky Git or filesystem changes, create a reversible checkpoint.
- Never force-push, rewrite published history, delete evidence, or conceal blockers.
- Use one active P0 dependency chain. Independent work may run in parallel only in isolated worktrees or clearly separated artifacts.
- Every code change requires relevant tests. Every sprint exit requires the complete available suite.
- No claim may exceed its evidence.
- Public artifacts must pass Medusa disclosure review.
- Credentials and secrets must stay outside the repository.

## Task execution contract

For every `P-###` or `X-###` task:

1. Confirm dependencies.
2. Mark `In Progress`.
3. Record active role and execution surface.
4. Execute the smallest complete slice.
5. Run direct acceptance checks.
6. Run a reverse check for consequential claims.
7. Emit a receipt under `workforce_spine/receipts/`.
8. Update `queue.json`, `state.json`, and `ledger.jsonl`.
9. Commit only coherent, tested changes.

## Unknown work

Unregistered work is not ignored. Create an `X-###` task with:

- normalized outcome
- dependencies
- role bundle
- approval class
- rollback plan
- acceptance criteria
- proof class
- estimated effort
- result and receipt

## Stop conditions

Stop immediately before A3 actions. Otherwise continue until verified completion or an exact irreducible blocker exists.
