# Server installation

Use an empty directory, Docker Engine + Compose v2 (Linux) or Docker Desktop (macOS/Windows), Python 3.11+ and uv. Install missing prerequisites from their official vendors with user's existing authorization. Do not install rootless/rootful Docker variants over an existing setup automatically.

```sh
uv run scripts/setup.py server --directory "$HOME/omniroute-server" --start
```

This path is relative to the installed skill directory. The helper pins stable 3.8.53 at multi-platform digest `sha256:b52a17661a1aff42ffb78f349f423e986dfc55b57274f28559f8387622ef8ee4`. For remote server run the same command THERE; configure Codex HERE. Default port20128 is loopback-only; volume stores SQLite and encrypted credentials. Default10GiB container/8GiB V8 heap follows upstream coding-agent guidance; verify host has headroom. `--heap-mb 1024 --memory-gb 2` is for screenshots/light demos only.

Read INITIAL_PASSWORD from generated `.env` privately. Open dashboard, connect legitimate Codex account through OAuth or private import, create a router key. No login credentials are synthesized. Human may need OAuth consent/device code. Router key is distinct from this session. Use HTTPS or a private SSH tunnel for remote clients:

```sh
ssh -N -L 20128:127.0.0.1:20128 user@YOUR_SERVER
```

An existing installation is not upgraded/restarted by this command. For an authorized upgrade, drain active requests, back up consistent data, secrets, exact image and mounted overlays. Preserve the encryption secret with encrypted storage. Rebase additional fixes against the new image; never copy old compiled chunks blindly. Stage schema migrations on a copy before switching. Verify health, scoped models, completed Responses, effort and required native tools; image generation and reference editing are separate checks. The helper does not distribute deployment-specific overlays. Rolling back schema changes may require the matching data backup after reconciling newer writes. Never delete Docker volumes. Require API keys; do not expose port20128 publicly over HTTP.
