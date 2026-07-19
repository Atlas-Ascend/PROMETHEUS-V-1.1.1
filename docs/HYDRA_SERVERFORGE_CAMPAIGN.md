# HYDRA ServerForge Campaign

The live ServerForge deployment uses seven independently evidenced HYDRA heads. “HYDRA” here is an executable gate composition, not a claim that unimplemented agents are running.

| Head | Function | Passing evidence |
|---|---|---|
| H0 Intake | authenticate bot and exact guild | Discord preflight identity |
| H1 Topology | reconcile roles, categories, channels, topics, and overwrites | applied topology snapshot |
| H2 Adversarial | challenge required resources after mutation | zero missing resources |
| H3 Recovery | preserve the pre-mutation state | hashed backup manifest |
| H4 Idempotency | prove a second planning pass requires no creation actions | empty residual plan |
| H5 ProofGrid | bind evidence into a canonical receipt | SHA-256 campaign receipt |
| H6 ServerForge | publish verified state into the live Discord surface | returned channel/message IDs |

Run the complete campaign:

```powershell
python -m prometheus_kernel serverforge campaign `
    serverforge/topology.json `
    --confirm-guild $env:DISCORD_GUILD_ID
```

Evidence is written under `.prometheus/serverforge/campaigns/<campaign-id>/`. The bot is explicitly allowed in every managed category overwrite so it cannot lock itself out of private control surfaces.
