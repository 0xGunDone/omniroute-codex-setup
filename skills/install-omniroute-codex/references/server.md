# Server installation

Use an empty directory, Docker Engine + Compose v2 (Linux) or Docker Desktop (macOS/Windows), Python 3.11+ and uv. Install missing prerequisites from their official vendors with user's existing authorization. Do not install rootless/rootful Docker variants over an existing setup automatically.

```sh
uv run scripts/setup.py server --directory "$HOME/omniroute-server" --start
```

This path is relative to the installed skill directory. For remote server run the same command THERE; configure Codex HERE. Default port20128 is loopback-only; volume stores SQLite and encrypted credentials. Default10GiB container/8GiB V8 heap follows current upstream coding-agent guidance; verify host has headroom. `--heap-mb 1024 --memory-gb 2` is for screenshots/light demos only.

Read INITIAL_PASSWORD from generated `.env` privately. Open dashboard, connect legitimate Codex account through OAuth or private import, create a router key. No login credentials are synthesized. Human may need OAuth consent/device code. Router key is distinct from this session. Use HTTPS or a private SSH tunnel for remote clients:

```sh
ssh -N -L 20128:127.0.0.1:20128 user@YOUR_SERVER
```

An existing installation is not upgraded/restarted by this command. Back up its data, secrets and exact image before any explicit upgrade. Never delete Docker volumes. Require API keys; do not expose port20128 publicly over HTTP.
