# Product Requirements

## User promise

PROMETHEUS turns a software mission into one promoted, evidence-backed result while preserving the competing attempts and the reason for promotion.

## P0 functional requirements

- Accept a versioned JSON mission.
- Validate required fields and at least three unique candidates.
- Capture the seed project as a Git commit.
- Create one isolated Git worktree per candidate.
- Apply deterministic, path-contained file operations.
- Commit each candidate independently.
- Execute the declared standard test command in every worktree.
- Rank only candidates that pass the standard gate.
- Execute an adversarial command against the leader.
- Apply and commit a declared repair when required.
- Re-run both gates after repair.
- Promote exactly one result.
- Hash every promoted artifact.
- Emit and verify a canonical receipt hash.
- Emit a capability genome linked to the receipt.

## P0 non-functional requirements

- Python 3.11+ and Git are the only runtime dependencies.
- No network is required.
- Mission operations cannot escape the candidate workspace.
- Commands and their exit evidence are retained.
- Generated evidence is excluded from Git by default.
- A clean CI runner can reproduce the proof in under ten minutes.

## P1 requirements

P1 has executed the existing ServerForge bridge against an explicitly authorized server. It inventories the before state, validates permissions, applies and verifies the topology, publishes proof messages, and retains a secrets-redacted recovery package.

## Recursive forge requirements

- Use the actual PROMETHEUS repository as the source worktree.
- Require a clean captured base commit.
- Create at least three independent candidate branches and worktrees.
- Run Codex candidates concurrently with explicit workspace-write scope.
- Remove Discord and GitHub credentials from Codex child environments.
- Retain JSONL and final-message evidence for every Codex execution.
- Reject candidates that produce no patch, exceed change limits, or fail standard tests.
- Select exactly one standard-gate survivor deterministically.
- Run an independent Codex challenge against the leader and commit proven repairs.
- Re-run standard and adversarial commands after repair.
- Commit a portable proof bundle with the promoted source.
- Require exact repository confirmation before push.
- Open a draft PR only after the promoted branch exists remotely.
- Publish bounded mission, candidate, challenge, repair, and promotion events into ServerForge while execution proceeds.
- Build an installable wheel and SHA-256 release manifest.
