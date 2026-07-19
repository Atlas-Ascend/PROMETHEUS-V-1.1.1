# Proof Schema

`promotion-receipt.json` contains the mission identity, seed commit, candidate command evidence, leader selection, repair history, promoted commit, runtime facts, and SHA-256 manifest of promoted artifacts.

The `receipt_hash` is SHA-256 over canonical JSON of every receipt field except `receipt_hash` itself. Canonical JSON sorts keys, removes formatting whitespace, and encodes UTF-8. `prometheus verify <receipt>` recomputes this value, validates the complete event chain and chain head, and re-hashes every promoted artifact. Any mismatch returns a nonzero exit code.

This proves that the receipt has not changed since emission. It does not provide signer identity or remote timestamp authority. Signing and external anchoring are later ProofGrid capabilities.

`capability-genome.json` records only capabilities exercised in that run and references the exact receipt hash carrying their evidence.
