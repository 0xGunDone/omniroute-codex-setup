# Client switch and chat retention

Run from the installed skill directory. Use a trusted private file containing ONLY the OmniRoute router key (not a provider access token); protect it with0600 on Unix or user-only ACL on Windows.

```sh
uv run scripts/setup.py client --base-url http://127.0.0.1:20128/v1 --key-file /PRIVATE/router.key --model codex/gpt-6.1-sol --effort max --from-provider openai --native-tools --subagents
```

No apply means preflight ONLY: fetch key-scoped model list, checksum-verified pinned official Codex metadata, then one synthetic inference. It prints counts, not keys or chat text. A model absent from the scoped catalog fails closed. Existing personal catalogs are backed up; a generated catalog keeps native metadata for known Codex models that the key advertises. It is not a universal converter for arbitrary non-Codex LLMs. Use `--catalog-template` only with trusted version-compatible Codex metadata; a model catalog can contain model instructions.

Inspect local provider counts and choose exact old IDs. Other providers remain untouched. Fully quit Desktop/CLI/VS Code before apply; the agent itself may need to finish first. From a normal external terminal repeat the command with `--apply`. Optional `--wait-for-exit 120` waits for user to quit; it never kills processes.

The script merges settings using tomlkit, preserves unrelated keys/comments, writes file-store auth and fixed router bearer, generates native model catalog, backs up three files and SQLite, then transactionally changes selected `threads.model_provider`. It does not change per-chat model IDs, rewrite rollout JSONL, delete OAuth credentials from OS keychain, or migrate cloud accounts. Legacy `[profiles]` and `openai_base_url` must be reviewed first; project/managed settings can override user defaults. New Codex versions can change internals: verify schema before applying.

`--native-tools` adds the router's same key as `x-openai-actor-authorization` and enables image generation. This gateway behavior is version dependent and not a public OpenAI guarantee. The server must support `/v1/images/generations`, edits if requested, and native `/v1/alpha/search`; do not redirect that path to `/v1/search`, whose protocol differs. Current3.8.52 stable was observed handling the native search path; older builds with identical version labels can differ. Test with a harmless web/image request only when authorized; do not silently change provider/prompt after failure.

Restore from external terminal:

```sh
uv run scripts/setup.py restore --backup /ABSOLUTE/CODEX_HOME/omniroute-backups/TIMESTAMP
```

Restore refuses later changed configs and new state schema. It updates original chat IDs only, preserving chats created since setup. The full SQLite snapshot is emergency recovery only: do not replace a live/newer DB wholesale. If interrupted before status `applied`, inspect snapshot and manifest privately and reconcile config/auth/provider IDs; do not repeatedly apply blindly.
