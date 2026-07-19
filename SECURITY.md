# Security

Report vulnerabilities privately to the repository owner. Do not open public issues containing tokens, credentials, private Discord content, member information, or exploitable deployment details.

PROMETHEUS executes commands declared in mission files. Treat every mission as code: review it before execution, run it only in an authorized environment, and never execute untrusted mission files.

P1 must capture a pre-change Discord manifest and a rollback path. Bot tokens live only in local or managed secret storage and must never enter Git history, receipts, logs, screenshots, or case-study artifacts.
