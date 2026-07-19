# ServerForge: New-Server Bootstrap

ServerForge is connected from the first startup, but Discord retains one human trust boundary: a server owner creates the empty server and approves the application installation. Bots are added to servers through Discord’s OAuth2 bot authorization flow; once installed with the required permissions, the documented guild, role, and channel endpoints support the live build.

## One-time trust handoff

1. Create a new empty Discord server named `PROMETHEUS Forge — Live Case Study`.
2. Create or select the Discord application and bot in the Developer Portal.
3. Record the application ID and the new server’s guild ID.
4. Generate the pinned install URL:

   ```powershell
   $env:DISCORD_APPLICATION_ID = "YOUR_APPLICATION_ID"
   $env:DISCORD_GUILD_ID = "YOUR_NEW_SERVER_ID"
   $env:PYTHONPATH = "$PWD/src"
   python -m prometheus_kernel serverforge install-url
   ```

5. Open the returned URL and approve installation into the preselected server.
6. Store the bot token in the current shell or a local secret manager—never in a repository file:

   ```powershell
   $env:DISCORD_BOT_TOKEN = "YOUR_BOT_TOKEN"
   ```

## Direct startup

```powershell
./scripts/Start-Prometheus.ps1 -ConfirmGuild $env:DISCORD_GUILD_ID
```

The command runs kernel tests, executes the P0 candidate-to-proof mission, performs Discord preflight, captures the before state, applies the topology, and verifies the live result.

## Individual bridge commands

```powershell
python -m prometheus_kernel serverforge plan serverforge/topology.json
python -m prometheus_kernel serverforge preflight
python -m prometheus_kernel serverforge snapshot
python -m prometheus_kernel serverforge apply serverforge/topology.json --confirm-guild $env:DISCORD_GUILD_ID
python -m prometheus_kernel serverforge verify serverforge/topology.json
```

## Mutation boundary

The initial bridge creates missing named resources and updates the target guild’s baseline safety settings. It does not delete unrelated roles, categories, or channels. A future exact-state reconciler may add deletion only behind a separately confirmed destructive plan.

## Primary references

- Discord OAuth2 bot authorization: https://docs.discord.com/developers/topics/oauth2#bot-authorization-flow
- Discord guild, channel, and role endpoints: https://docs.discord.com/developers/resources/guild
- Discord permission hierarchy and bitfields: https://docs.discord.com/developers/topics/permissions
