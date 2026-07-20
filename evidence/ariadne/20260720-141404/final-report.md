Implemented and proved the judge-ready one-command demonstration package.

Linux verification result: `PROMETHEUS OMEGA PROVEN`

- 13/13 gates passed
- Runtime: 1.097786 seconds
- Three distinct candidate commits and strategies
- Adversarial transition: exit `1 → 0`
- Repair commit: `3f8f0b3f21e348e14de8e2871dbfb35961acec97`
- Receipt hash: `dddb485fa8235b091392e98d2bdf5a0307beb69b062e26661edc6e59a05a7a22`
- Pristine receipt independently reverified
- Evidence and receipt tampering both rejected
- 390 generated artifacts indexed with SHA-256 hashes

Required deliverables:

- [JUDGE_README.md](/home/eden/Ghost/ARIADNE-20260720-141404/competition/demo/JUDGE_README.md)
- [DEMO_SCRIPT.md](/home/eden/Ghost/ARIADNE-20260720-141404/competition/demo/DEMO_SCRIPT.md)
- [VERIFICATION.md](/home/eden/Ghost/ARIADNE-20260720-141404/competition/demo/VERIFICATION.md)
- [ARTIFACT_INDEX.json](/home/eden/Ghost/ARIADNE-20260720-141404/competition/demo/ARTIFACT_INDEX.json)
- [RUN_DEMO.sh](/home/eden/Ghost/ARIADNE-20260720-141404/competition/demo/RUN_DEMO.sh)
- [RUN_DEMO.ps1](/home/eden/Ghost/ARIADNE-20260720-141404/competition/demo/RUN_DEMO.ps1)

The implementation uses the existing P0 Command-to-Proof kernel; no product redesign occurred. Generated evidence remains under `competition/demo/evidence/` and is ignored by Git. The PowerShell launcher was reviewed but could not be executed because `pwsh` is unavailable in this Linux environment.

No commits or pushes were made. The pre-existing untracked `evidence/ariadne/` directory was untouched.