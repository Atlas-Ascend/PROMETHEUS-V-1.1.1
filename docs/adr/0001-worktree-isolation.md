# ADR 0001: Git Worktrees as the P0 Isolation Primitive

**Status:** Accepted

P0 uses one seed commit and one Git worktree per candidate. This preserves independent lineage with minimal dependencies and makes candidate diffs inspectable. Worktrees do not isolate host resources, so container or microVM executors remain required before untrusted missions are supported.
