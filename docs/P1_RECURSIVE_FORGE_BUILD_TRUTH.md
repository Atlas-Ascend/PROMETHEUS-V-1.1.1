# P1 Recursive Forge Build Truth

## META-FATE registration

- **ID:** MF-20260719-MF01-464
- **Title:** PROMETHEUS V-1.1.1 As Above / So Below Full Recursive Campaign
- **Type:** SOFTWARE-CAMPAIGN / DESIGN-TO-INSTALL / COMMAND-TO-PROOF RUNTIME
- **Parent:** PROMETHEUS V-1.1.1
- **Primary organs:** PROMETHEUS, Codex, MetaForge, ServerForge, ProofGrid
- **Secondary organs:** EDEN/Cali, Thoth, SECA/DevOS, Medusa, CrownGrid, GitHub
- **Status:** IMPLEMENTED IN REPOSITORY; AUTHENTICATED LOCAL EXECUTION AND PROMOTION RECEIPT PENDING
- **Version:** 1.1.1-P1

## Identity

P1 Recursive Forge is the model-backed execution layer above the deterministic P0 kernel. It applies the same mission-to-proof law to the PROMETHEUS repository itself:

`frozen self-build mission → parallel Codex worktrees → standard gates → deterministic leader → independent Codex challenge/repair → passing leader → portable receipt → Git branch → draft PR → install artifact → ServerForge proof`

P1 patches the existing organism. It does not replace the P0 engine, its deterministic fixture, the hash-chained ledger, ServerForge topology reconciliation, or the verified HYDRA recovery path.

## Implemented claim

Given a clean authorized Git worktree, an authenticated Codex CLI, and the frozen `missions/self-build.json`, PROMETHEUS can:

1. Resolve and freeze the exact source commit.
2. Create at least three independent candidate branches and Git worktrees.
3. invoke `codex exec` concurrently in the worktrees using explicit `workspace-write`, ephemeral sessions, and JSONL evidence.
4. Strip Discord, GitHub, and API-key credentials from every Codex candidate environment; Codex uses the authenticated local CLI session.
5. Require each candidate to leave a real repository patch.
6. Commit and test every candidate independently.
7. Rank only candidates that pass the standard command gate.
8. Invoke a separate Codex Adversarial Twin against the leader.
9. Commit proven repairs and rerun standard and adversarial gates.
10. Bind source artifacts, Codex transcript hashes, event-chain evidence, candidate results, and the promotion decision into a recursive receipt.
11. Commit the portable proof bundle with the promoted source.
12. Push only after an exact repository-name confirmation.
13. Open a draft PR through authenticated GitHub CLI when requested.
14. Publish bounded campaign events into the existing live ServerForge case-study channels while the local campaign runs.
15. Produce an installable Python wheel and SHA-256 release manifest.

## As above / so below mapping

| Design truth | Runtime embodiment | Proof surface |
|---|---|---|
| Mission plane | frozen recursive mission JSON | mission SHA-256 |
| Counterfactual Forge | three concurrent Codex worktrees | candidate commits and JSONL hashes |
| SECA arbitration | passing-only deterministic score | selected leader event |
| Adversarial Twin | independent Codex review/repair turn | findings, repair commit, retest evidence |
| MetaForge | promoted source lineage | Git branch and draft PR |
| ProofGrid | canonical receipt and capability genome | committed proof bundle |
| ServerForge | live bounded event publication | Discord message IDs and local publication ledger |
| Product body | virtual environment, launcher, wheel | install tests and release manifest |

## Promotion gates

The recursive result is promoted only when:

1. The source repository is clean.
2. Codex CLI preflight resolves.
3. Three candidate worktrees are created from the same base commit.
4. Every candidate execution is transcript-bound.
5. At least one candidate produces changes and passes the standard gate.
6. Exactly one leader is selected.
7. The independent challenge completes.
8. Standard and challenge commands pass after any repair.
9. The artifact manifest and event ledger verify.
10. The proof bundle is committed.
11. Push confirmation exactly matches `Atlas-Ascend/PROMETHEUS-V-1.1.1` when external publication is requested.
12. The draft PR points at the committed evidence branch.

## Current proof state

- P0 deterministic kernel: verified locally and in the existing CI design.
- HYDRA ServerForge: live and verified by campaign `HYDRA-SERVERFORGE-20260719T023826Z`, receipt `26ccd3be5d15b170e24e54855db50f747ebf3c2fbfccac3622fb629b07665ffc`.
- P1 recursive implementation: unit and fake-provider integration tests pass.
- P1 authenticated Codex self-build: pending execution on the local authorized host.
- P1 GitHub promotion PR: pending the authenticated local run.

## Explicit non-claims

Repository implementation and fake-provider tests do not prove that a real Codex run, GitHub push, draft PR, wheel build, or new Discord event publication occurred. Those capabilities become live only when the local full-campaign command completes and its recursive receipt verifies.

Git worktrees isolate repository lineages, not the Windows host. Codex receives `workspace-write`, not an OS-level VM boundary. EDEN/Cali process isolation, Thoth persistence, asymmetric receipt signing, and external timestamp authority remain later promotion gates.
