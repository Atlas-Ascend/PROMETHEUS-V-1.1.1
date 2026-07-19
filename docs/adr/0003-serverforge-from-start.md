# ADR 0003: ServerForge Bridge from Startup

**Status:** Accepted

ServerForge is part of the ignition command, not a later dashboard. Startup always produces either a complete offline Discord plan or an authenticated preflight/snapshot/apply/verify sequence. Live mutation requires a bot installed into an explicitly confirmed guild and never reads or exports private messages.
