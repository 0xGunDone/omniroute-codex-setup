---
name: install-omniroute-codex
description: Use when installing OmniRoute or connecting Codex Desktop, CLI, or VS Code to an OmniRoute gateway while retaining existing local chats and model choices.
---

# Install OmniRoute for Codex

Use the bundled `scripts/setup.py` through `uv run`. It generates a loopback-only Docker installation or performs a reversible Codex switch. Scripts require Python 3.11+ and pinned tomlkit; `uv` resolves the dependency.

## Scope and route

Identify server versus client host, OS, actual Codex home, existing providers, chosen model, and router endpoint. Default model: `codex/gpt-6.1-sol`, effort `max`; preserve an explicit user choice. The selected ID must exist in the key-scoped `/models` response. Do not replace an existing gateway installation; use it or plan an explicit upgrade.

For server installation, read [server.md](references/server.md). For the client and existing chats, read [client.md](references/client.md). These references include exact commands. Authentication is configured directly in `auth.json` and `config.toml`; an account manager is optional.

## Execution invariants

- Keep real tokens and config out of chat, screenshots, repository, and shell arguments. Use a private key file or hidden terminal input. An OmniRoute key authenticates to the router; ChatGPT OAuth credentials stay with the server's provider account. Never send the router key to api.openai.com.
- Complete ordinary preparation and run the client preflight within existing authorization. Preflight includes ONE paid/quota-consuming synthetic inference. No retry loop and no real task replay.
- Apply to the real Codex home only after all Codex/ChatGPT Desktop, CLI and VS Code Codex processes have exited. The executing agent itself can hold that home open. Prepare first, then give an external-terminal command or wait for user to quit; never kill their app mid-turn or bypass the process guard.
- Select exact old provider IDs with repeated `--from-provider`; no blanket SQL update. The script changes only `threads.model_provider`, including archives, and leaves transcripts, IDs, pins and other providers intact. SQLite is an internal schema: stop on unknown schema or a newer database, not guess.
- Preserve sandbox/approval/MCP/plugin settings. No access escalation, prompt injection into catalogs, fabricated subscriptions, or promise that listing a model proves access. Native image/web tools need compatible client AND server; opt into `--native-tools` only after reading the version notes.
- `gpt-5.1-codex-mini` is excluded, including diagnostic probes. Never request it. New subagents use the selected allowed model, not an older fallback.
- Before completion verify a completed inference marker, model list, one old chat plus one archived chat, and any requested native tool. HTTP 200 without completion is insufficient. If OAuth/captcha/login is required, let the user complete that step privately; continue afterward.

## Recovery and report

The script saves auth/config/catalog and a consistent state snapshot before apply. Prefer `restore --backup PATH`: it restores original provider IDs without replacing later chat contents, and refuses conflicting later config edits. After an interruption, inspect the private manifest before rerunning; writes across files and SQLite are not crash-atomic.

Report exact server URL, selected model, number of migrated chats, private backup path, checks passed and any untested feature. Never publish credentials. Do not claim that cloud chats or all upstream entitlements were migrated.
