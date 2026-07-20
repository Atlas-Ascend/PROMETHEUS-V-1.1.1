# Verification Contract

The launcher is successful only when all gates below pass in the same fresh run.

| Gate | Generated proof |
|---|---|
| Root/runtime/dependencies | `judge-transcript.log` |
| Kernel regression | `kernel-regression.log` |
| Three materially distinct candidates | receipt candidate strategies and distinct commit SHAs |
| Real standard execution | candidate results plus hashed execution records |
| Adversarial leader failure | leader challenge attempt 1 has nonzero exit |
| Repair and retest | repair commit exists; final standard and challenge exits are 0 |
| ProofGrid integrity | independent `verify_receipt` result against the pristine campaign |
| Evidence tamper rejection | mutated execution record in `tamper-evidence-copy/` is rejected |
| Receipt tamper rejection | mutated leader field in `tamper-receipt-copy/` is rejected |
| Capability genome | promoted candidate and receipt hash match the receipt |
| Build Truth | state is `PROVEN`, receipt hash matches, live Discord remains not claimed |

Every command execution record contains command arguments, start and finish timestamps, duration, exit code, stdout/stderr artifact paths, and hashes. The generated artifact index records paths, sizes, and SHA-256 hashes. `OMEGA_RESULT.json` records the total measured duration and every promotion decision gate.

## Independent checks

After a passing run, substitute the printed receipt path:

```bash
PYTHONPATH=src python3 -m prometheus_kernel verify competition/demo/evidence/<id>/campaign/<run-id>/promotion-receipt.json
```

The command must print `"valid": true` and exit 0. Editing any receipt-covered packet, execution record, stream, arbitration record, event ledger, or promoted artifact must make it print `"valid": false` and exit 1.

The package has no dependence on previous evidence, ignored local inputs, credentials, external services, or machine-specific absolute paths. Generated evidence contains runtime-resolved absolute working-directory strings inside subprocess records where needed for audit, but committed launchers and artifacts contain none.
