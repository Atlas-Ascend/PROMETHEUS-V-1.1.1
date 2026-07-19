# Proof Schema

`promotion-receipt.json` contains the mission identity, seed commit, candidate command evidence, leader selection, repair history, promoted commit, runtime facts, and SHA-256 manifest of promoted artifacts.

The `receipt_hash` is SHA-256 over canonical JSON of every receipt field except `receipt_hash` itself. Canonical JSON sorts keys, removes formatting whitespace, and encodes UTF-8. `prometheus verify <receipt>` recomputes this value, validates the complete event chain and chain head, and re-hashes every promoted artifact. Any mismatch returns a nonzero exit code.

This proves that the receipt has not changed since emission. It does not provide signer identity or remote timestamp authority. Signing and external anchoring are later ProofGrid capabilities.

`capability-genome.json` records only capabilities exercised in that run and references the exact receipt hash carrying their evidence.

## Recursive receipt

`prometheus.recursive-receipt.v1` binds the self-build mission, common base commit, all candidate results, selected leader, adversarial repair commit, promoted source commit, intended promotion branch, source artifact manifest, Codex transcript hashes, hash-chained event ledger, and ServerForge publication mode.

The portable proof bundle is committed under `proof/recursive/<run-id>/`. `prometheus verify-recursive` verifies the canonical receipt hash, committed ledger, chain head, event count, and every promoted source artifact. Codex transcripts remain in local evidence by default; the committed proof binds their hashes and sizes without placing full model traces into the public repository.
