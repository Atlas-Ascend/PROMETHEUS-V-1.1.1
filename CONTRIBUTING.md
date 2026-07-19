# Contributing

Every change begins with a mission and ends with evidence. Keep the current baseline runnable with Python and Git only. Add or update tests, preserve the truth boundary in `docs/BUILD_TRUTH.md`, and never promote a capability description without executable proof.

Before proposing a change:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m prometheus_kernel run missions/bootstrap.json
```

Security-sensitive findings should follow `SECURITY.md` rather than public issue discussion.
