Execution is blocked by the local command runner before any repository command starts.

Evidence:

```text
CreateProcessAsUserW failed: 1920
The file cannot be accessed by the system.
Executable:
C:\Users\User\AppData\Local\Microsoft\WindowsApps\pwsh.exe
```

I retried with:

- The repository working directory
- No explicit working directory
- Non-login shell semantics
- A minimal `Get-Location` command

All failed identically. No files were changed, no tests ran, and no completion is claimed.

The environment’s PowerShell executable/alias must be repaired or the runner configured to use an accessible `pwsh.exe`/`powershell.exe`. Once command execution works, I can resume the full mission-to-proof sequence from repository inspection through Build Truth reconciliation.