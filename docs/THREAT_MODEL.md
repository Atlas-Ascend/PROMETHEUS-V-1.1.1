# Threat Model

## Protected assets

- source repositories and commit lineage
- mission definitions and acceptance gates
- promotion decisions and proof artifacts
- Discord bot token and application credentials
- Discord roles, channels, permission boundaries, and audit trail
- private member data and messages, which are intentionally outside case-study capture

## Principal threats and controls

| Threat | P0 control | Remaining work |
|---|---|---|
| Mission command injection | commands are string arrays executed without a shell; executable allowlist | signed mission provenance and richer command policy |
| Workspace escape | operation paths resolve inside the candidate root | OS sandbox/container boundary |
| Hung or noisy process | timeout and retained-output limits | CPU, memory, disk, and network quotas |
| Candidate self-promotion | deterministic external arbiter and separate challenge command | independent evaluator identities |
| Receipt tampering | canonical SHA-256 receipt and hash-chained event ledger | asymmetric signatures and external timestamping |
| Secret leakage | `.env*` ignored, snapshots omit token/messages/member lists | automatic structured redaction and secret scanning |
| Wrong Discord target | exact `--confirm-guild` match | out-of-band owner confirmation receipt |
| Discord privilege escalation | minimum bridge permission request; created roles have zero guild permissions | permission simulation with test identities |
| Destructive reconciliation | create-missing behavior; no delete path | confirmed exact-state plan and reversible trash model |
| API rate limits | bounded retry using Discord `retry_after` | distributed rate-limit coordinator |

## Non-negotiable evidence boundary

Case-study capture may include server topology, role/permission definitions, command results, redacted audit facts, and public demonstration messages. It must not ingest private messages, bot tokens, member PII, or unrelated server content.
