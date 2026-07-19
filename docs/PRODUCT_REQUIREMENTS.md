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

P1 will add a Discord adapter and deployment plan for one explicitly authorized server. It must inventory the before state, produce three topology candidates, validate permissions, apply one promoted topology, prove a real end-to-end command path, and retain a secrets-redacted rollback package.
