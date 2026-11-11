# Client switch and chat retention

Run from the installed skill directory. Use a trusted private file containing ONLY the OmniRoute router key (not a provider access token); protect it with0600 on Unix or user-only ACL on Windows.

```sh
uv run scripts/setup.py client --base-url http://127.0.0.1:20128/v1 --key-file /PRIVATE/router.key --model codex/gpt-6.1-sol --effort max --from-provider openai --native-tools --subagents
```

No apply means preflight ONLY: fetch key-scoped model list, checksum-verified pinned official Codex metadata, then one synthetic inference. It prints counts, not keys or chat text. A model absent from the scoped catalog fails closed. Existing personal catalogs are backed up; a generated catalog keeps native metadata for known Codex models that the key advertises. It is not a universal converter for arbitrary non-Codex LLMs. Use `--catalog-template` only with trusted version-compatible Codex metadata; a model catalog can contain model instructions.

Inspect local provider counts and choose exact old IDs. Other providers remain untouched. Fully quit Desktop/CLI/VS Code before apply; the agent itself may need to finish first. From a normal external terminal repeat the command with `--apply`. Optional `--wait-for-exit 120` waits for user to quit; it never kills processes.

The script merges settings using tomlkit, preserves unrelated keys/comments, writes file-store auth and fixed router bearer, generates native model catalog, backs up auth/config/catalog, both `.codex-global-state.json` files if present and SQLite, then transactionally changes selected `threads.model_provider`. It does not change per-chat model IDs, rewrite rollout JSONL, delete OAuth credentials from OS keychain, or migrate cloud accounts. Legacy `[profiles]` and `openai_base_url` must be reviewed first; project/managed settings can override user defaults. New Codex versions can change internals: verify schema before applying.

If using CodexAcc or another profile manager, retain the same CODEX_HOME. Use API-key auth, provider `omniroute`, Responses, the router URL ending in `/v1`, exact model ID and an absolute native-catalog path. Verify the resulting auth/config privately; do not invent manager UI labels or let a stale saved profile undo the configuration. Keeping chats is different from migrating cloud-account entitlement.

`--native-tools` adds the router's same key as `x-openai-actor-authorization` and enables image generation. It is optional for ordinary coding. This gateway behavior is version dependent and not a public OpenAI guarantee. The server must support `/v1/images/generations`, edits if requested, and native `/v1/alpha/search`; do not redirect that path to `/v1/search`, whose protocol differs. The checked stock 3.8.53 search adapter handles `search_query`, not the full open/find/click/screenshot/encrypted-replay protocol. Full native search and built-in image generation/reference editing were checked on a deployment with additional rebased fixes; the helper does not install them. Route presence or an HTTP400 validation response is insufficient. Use built-in `image_gen` for authorized tests; do not silently change provider/model/prompt or substitute a shell/API runner after failure.

For `Combo "gpt-image-2" has no usable targets`, inspect combo membership, key/account scope and image-specific visibility in both generation and edit resolvers. A chat-hidden model can remain image-visible. The combo name is a routing alias, not proof of the exact upstream image engine. Do not globally unhide chat models as a workaround.

Default remains Sol/max. In the checked Codex route, client `ultra` for GPT-6.1 Sol/Terra maps to upstream `max`; it is not evidence of a separate stronger wire effort. Preserve explicit user model choices and inspect actual metadata/requests.

## Empty Projects after API-key profile switch

Observed Desktop 0.167.0-alpha.3.2 migration: Recents/Pinned remain, but Projects empties at startup. An `electron-account-renderer-state-v1` envelope can hold one saved local project collection while `owner` is null. On the affected build, leaving the envelope in active state causes startup to clear the restored collection again.

```sh
uv run scripts/setup.py repair-projects --codex-home /ABSOLUTE/CODEX_HOME
```

Inspection is offline, does not write and consumes no quota. It requires API-key-only auth without OAuth tokens and the exact single-owner local-project structure; cloud-backed, signed-in, multiple-owner or unknown layouts are refused. Do not bypass those guards. This is not a general workaround for every future build.

After the user fully quits Desktop/CLI/VS Code, run from an external terminal:

```sh
uv run scripts/setup.py repair-projects --codex-home /ABSOLUTE/CODEX_HOME --apply
```

The helper backs up complete state, merges known project globals/UI atoms with current entries taking precedence, and removes only the migration envelope from active state. The original envelope stays in the private backup. Auth/config/chat DB/transcripts are untouched. Normal `client --apply` does not run this repair. Optional `--wait-for-exit 120` waits, never kills; a changed file during quit requires a fresh run. Verify Projects, assignments, archives and pins after reopening. Do not fabricate identity, edit tokens, patch the app binary or downgrade silently.

Project-repair backups have `kind: project-repair` and are excluded from normal `restore`; use their original sidebar files only for selective offline recovery after reviewing newer changes. Do not overwrite a newer whole UI state.

## Client rollback

Restore from external terminal:

```sh
uv run scripts/setup.py restore --backup /ABSOLUTE/CODEX_HOME/omniroute-backups/TIMESTAMP
```

Restore refuses later changed configs and new state schema. It updates original chat IDs only, preserving chats created since setup. Sidebar copies are preserved for selective recovery and are not automatically restored over newer project data. The full SQLite snapshot is emergency recovery only: do not replace a live/newer DB wholesale. If interrupted before status `applied`, inspect snapshot and manifest privately and reconcile config/auth/provider IDs; do not repeatedly apply blindly.
