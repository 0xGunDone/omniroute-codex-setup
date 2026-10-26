# OmniRoute + Codex: install and switch without deleting chats

[Русский](../ru/guide.md) · [Home](../../README.md) · Checked: **27 October 2026**

For your own OmniRoute gateway and Codex Desktop / CLI / VS Code extension. Configure Codex **directly through `auth.json` and `config.toml`**; an account manager is optional. Retain local conversations, archives, pins, MCP settings and permission settings. The separate [agent skill](../../skills/install-omniroute-codex/SKILL.md) can carry out the setup.

**Scope:** preserving local data does not preserve every ChatGPT product feature. Actual model access depends on the upstream account, subscription, quota and router-key policy. A model catalog does not grant a subscription. This does not migrate cloud chats between accounts. Codex's internal SQLite schema can change; the installer stops on unknown schemas.

## Contents

1. [Architecture](#1-architecture)
2. [Server installation](#2-server-installation)
3. [Provider account and router key](#3-codex-account-and-omniroute-key)
4. [Codex files](#4-required-codex-files)
5. [Automated switch](#5-preflight-backup-and-client-switch)
6. [Existing chats](#6-migrating-existing-chats)
7. [Models and tools](#7-models-reasoning-fast-and-native-tools)
8. [Validation and rollback](#8-validation-rollback-and-upgrades)
9. [Troubleshooting](#9-troubleshooting)
10. [Skill and agent prompt](#10-install-the-skill-and-give-it-to-an-agent)

## 1. Architecture

```mermaid
flowchart LR
    A[Codex Desktop / CLI / VS Code] -->|Responses + OmniRoute key| B[OmniRoute /v1]
    B -->|Your upstream OAuth| C[Codex provider]
    B --> D[Other configured providers]
    A --- E[Local chats in CODEX_HOME]
```

Three different secrets:

| Secret | Stored in | Purpose |
|---|---|---|
| Dashboard password | Server's private `.env` | Dashboard login |
| ChatGPT OAuth / provider credentials | OmniRoute server storage | Upstream authentication |
| **OmniRoute API key** | Client `auth.json` and provider section in `config.toml` | Codex → your router |

Do not send an OmniRoute key to the OpenAI API: `sk-or-…` does not become an `api.openai.com` key. Do not import a router-key `auth.json` as a Codex provider account. That provider needs genuine upstream ChatGPT OAuth or its normal sign-in flow.

## 2. Server installation

### Prerequisites

- Linux: Docker Engine and Compose v2. macOS/Windows: Docker Desktop.
- Python **3.11+**, [uv](https://docs.astral.sh/uv/getting-started/installation/), and Git.
- Codex installed on the client. On macOS this can be Codex within the ChatGPT app; use the [official CLI instructions](https://developers.openai.com/codex/cli) for CLI installation.
- RAM headroom: current upstream guidance recommends an **8 GiB V8 heap** and a container of at least **10 GiB** for one coding agent. Concurrent large contexts need more. Docker Desktop's resource allocation must also cover that budget.

[Docker Engine](https://docs.docker.com/engine/install/) · [Docker Desktop](https://docs.docker.com/desktop/) · [OmniRoute RAM guidance](https://github.com/cheaper-inference/OmniRoute/blob/main/docs/guides/DOCKER_GUIDE.md)

```sh
git clone https://github.com/0xGunDone/omniroute-codex-setup.git
cd omniroute-codex-setup
uv run skills/install-omniroute-codex/scripts/setup.py server \
  --directory "$HOME/omniroute-server" --start
```

Windows PowerShell: use the same command on one line, without trailing `\`. Run `uv python install 3.11` first if needed.

The script generates unique `INITIAL_PASSWORD`, `JWT_SECRET`, `API_KEY_SECRET` and `STORAGE_ENCRYPTION_KEY`, sets `REQUIRE_API_KEY=true`, writes a private `.env`, and starts Docker Compose. It refuses a nonempty installation directory. Omit `--start` to prepare files only.

```text
~/omniroute-server/
├── .env             # SECRETS: never commit or share
├── .gitignore
└── compose.yaml     # pinned 3.8.52 image, localhost:20128
```

Persistent data lives in the Compose project's named `omniroute-data` volume, mounted at `/app/data`. Docker adds the project prefix to the volume name; inspect `docker compose config --volumes`. Do not run `docker compose down -v` if you need to retain accounts.

```sh
cd "$HOME/omniroute-server"
docker compose ps
```

Open `http://127.0.0.1:20128`. Read `INITIAL_PASSWORD` from your `.env` in a private editor. Do not use `CHANGEME` in a real deployment.

### Remote server

Run `server` **on the server** and the client setup **on your computer**. Open an SSH tunnel and keep it running:

```sh
ssh -N -L 20128:127.0.0.1:20128 user@YOUR_SERVER
```

Your Mac/Windows base URL remains `http://127.0.0.1:20128/v1`. Alternatively, configure your own HTTPS domain and reverse proxy. Do not expose dashboard/API credentials over public HTTP. If20128 is occupied, choose another local port and adjust the base URL.

### Other providers and outbound proxies

Add providers in the dashboard. For Codex plan usage, choose the direct Codex OAuth provider. OpenRouter models are a separate route with separate billing and quotas. Set SOCKS/HTTP proxies in OmniRoute's Proxy page and assign them to the provider/account as needed. `127.0.0.1` **inside Docker** is the container: a host proxy needs a reachable address (`host.docker.internal` on Docker Desktop or an explicitly configured Linux host-gateway). This setup does not require changing your home router.

## 3. Codex account and OmniRoute key

Screenshots come from an isolated, clean **3.8.52** demo with no personal accounts. Demo port21280 is only for screenshot isolation; normal commands use20128. Labels can differ between builds.

![EN: Codex provider page](../screenshots/en-01-codex-provider.png)

1. Open **Providers → OpenAI Codex**.
2. Click **Add** and complete the normal OAuth/Device Code sign-in with your own account. For a remote server, follow the callback/port instructions. The account owner completes sign-in and consent.
3. For **Import Auth**, use a private, original ChatGPT `auth.json` supported by that build. Never paste tokens into agent chat or screenshot the contents.
4. Verify that the connection is active and refresh available models. Models hidden or blocked in the dashboard can be absent from the key-scoped catalog.

If `gpt-6.1-sol` is missing, use **Import from /models** first. If upstream supports it but the gateway registry is older, add **Custom Models → Model ID: `gpt-6.1-sol`** under the Codex provider, enable Chat/Responses and keep it visible. Then verify `/v1/models` **using the same API key** returns the exact `codex/gpt-6.1-sol` or `cx/gpt-6.1-sol` ID. If only the latter is listed, pass that exact ID through `--model`. Do not fabricate access to a model that upstream actually rejects.

![EN: Add account](../screenshots/en-02-add-account.png)

5. Open **API Keys / API Manager** and create a separate key, such as `codex-laptop`.
6. Allow the required provider, connections and models. Enable Responses and, if endpoint categories are restricted, the search/image categories needed by native tools.
7. Store the key privately. It is not the dashboard password. Use separate keys with suitable restrictions for different people.

![EN: API manager](../screenshots/en-03-api-manager.png)

Do not run “test every model” for this guide: it generates many upstream calls and consumes quota. Test only the selected allowed model.

## 4. Required Codex files

`CODEX_HOME` defaults to `~/.codex` (Windows: `%USERPROFILE%\.codex`). Honor an existing `CODEX_HOME` environment variable. VS Code Remote SSH/WSL uses the home **on the remote side**, not your Mac's local home.

| File/directory | Action | Purpose |
|---|---|---|
| `config.toml` | merge carefully | Provider, URL, model and reasoning |
| `auth.json` | replace active login after backup | Router API key |
| `omniroute-model-catalog.json` | generate | Native Codex model metadata and reasoning choices |
| `state_N.sqlite`, `-wal`/`-shm` | consistent backup; targeted SQL only with client stopped | Metadata and provider binding for existing chats |
| `sessions/`, `archived_sessions/`, history, attachments | **do not delete or rewrite** | Local conversation contents |
| `AGENTS.md`, MCP, plugins, permissions | retain | Your instructions and access settings |

### `auth.json`

[Complete example](../../examples/auth.example.json):

```json
{
  "OPENAI_API_KEY": "REPLACE_WITH_YOUR_OMNIROUTE_KEY"
}
```

This selects an active API-key login. The old OAuth file is retained in a **private backup**. Do not mix old ChatGPT `tokens` with a router key in the active file. The installer sets `cli_auth_credentials_store = "file"`; it does not remove old OS-keychain entries.

### `config.toml`

[Full example](../../examples/config.example.toml). **Do not replace your entire configuration with it.** Global TOML keys must appear **before** `[section]`; otherwise they become fields of the preceding table. The installer uses a TOML parser and preserves unrelated settings/comments.

```toml
model_provider = "omniroute"
model = "codex/gpt-6.1-sol"
model_reasoning_effort = "max"
cli_auth_credentials_store = "file"
model_catalog_json = "/ABSOLUTE/PATH/TO/.codex/omniroute-model-catalog.json"

[model_providers.omniroute]
name = "OmniRoute"
base_url = "http://127.0.0.1:20128/v1"
wire_api = "responses"
requires_openai_auth = false
experimental_bearer_token = "REPLACE_WITH_YOUR_OMNIROUTE_KEY"
```

Use the **same router key** in `auth.json` and `experimental_bearer_token`. The fixed bearer explicitly authenticates the custom provider; because config also contains a secret, keep that file private. A remote endpoint is `https://router.example/v1`. Do not append `/responses` to the base URL. Windows absolute catalog example: `C:/Users/YOU/.codex/omniroute-model-catalog.json`.

### Model catalog

`GET /v1/models` returns the OpenAI-compatible `data[].id` format. It is **not** the `model_catalog_json` format. Codex needs `models[].slug`, native tool metadata and `supported_reasoning_levels`.

The installer downloads a **SHA256-verified, pinned public openai/codex snapshot**, intersects it with model IDs visible to this router key, and uses exact `codex/…`, `cx/…` or bare IDs. It preserves reasoning choices and native metadata. It does not turn an arbitrary Claude/Gemini route into a native Codex model. A newer model/build needs compatible trusted metadata; use `--catalog-template PATH`. A model catalog can include model instructions: do not use untrusted catalogs.

Single-entry format: [model-catalog.example.json](../../examples/model-catalog.example.json). This is a reduced structural example, not a replacement for the full native-tool metadata catalog. Use the generator for an actual installation.

## 5. Preflight, backup and client switch

Without `--key-file`, the script prompts privately for the key in a terminal. For an agent, prepare a private key file; the agent must not print its contents.

Unix: use a private editor to create `~/.config/omniroute/router.key`, then `chmod 600 ~/.config/omniroute/router.key`. Windows: use a user-only ACL and verify it with `icacls`.

**First run preflight without changing client settings:**

```sh
uv run skills/install-omniroute-codex/scripts/setup.py client \
  --base-url http://127.0.0.1:20128/v1 \
  --key-file "$HOME/.config/omniroute/router.key" \
  --model codex/gpt-6.1-sol --effort max \
  --from-provider openai --native-tools --subagents
```

Preflight reads the key-scoped catalog, validates model/effort, sends **one small billed/quota-consuming synthetic inference** requesting `OMNI_SETUP_OK`, and prints provider/chat counts. Even without `--apply`, this uses upstream quota. It does not send your conversation contents.

For a different old provider, use its **actual ID** with `--from-provider previous_id`; repeat for multiple IDs. Without this flag, existing chats are not migrated. Other providers are untouched.

**Fully quit Codex/ChatGPT Desktop, CLI and the VS Code Codex extension.** From a normal external Terminal/PowerShell, repeat the command with `--apply`. An agent inside active Codex must not migrate its own live SQLite database: it prepares the setup and provides the final external-terminal command. `--wait-for-exit 120` can wait for you to exit; it never kills your processes.

Example result:

```json
{
  "model": "codex/gpt-6.1-sol",
  "effort": "max",
  "threads_to_migrate": 12,
  "inference": {"completed": true, "marker": true},
  "backup": "/YOUR/CODEX_HOME/omniroute-backups/TIMESTAMP"
}
```

The count12 is illustrative. Backup includes original auth/config/catalog files, a consistent SQLite snapshot and a manifest of previous provider IDs. It is never committed. Legacy `[profiles]` and `openai_base_url` require review before the script proceeds. Also inspect project/managed settings, which can override user defaults.

## 6. Migrating existing chats

Changing `model_provider` in config alone does not reliably move old conversations: their provider is stored in `threads.model_provider`. The installer checks the schema, selects the highest numeric `state_N.sqlite`, creates a backup, and updates matching rows transactionally with previous-value checks.

SQL concept only, **not a command to run against a live database**:

```sql
BEGIN IMMEDIATE;
UPDATE threads
SET model_provider = 'omniroute'
WHERE model_provider = 'openai';
COMMIT;
```

The script additionally limits updates to recorded IDs and checks each original value. Chat IDs, `rollout_path`, titles, archives, pins, project bindings and session contents are retained. An explicitly selected model inside an old chat is not automatically replaced; choose an available model in the UI if that old one is absent from the router. Do not rewrite provider names throughout JSONL or delete SQLite/WAL.

Expected result: the same old and archived chats remain visible with unchanged IDs, and a new response uses OmniRoute. Stop and adapt the migration if a different schema appears, retaining the backup.

## 7. Models, reasoning, Fast and native tools

- Catalog listing is not entitlement. A completed inference with the expected marker verifies access for that request.
- Exact IDs matter: `codex/gpt-6.1-sol` and `openrouter/openai/gpt-6.1-sol` have separate routing, quotas and billing.
- `max`/`ultra` must be supported by the selected model/provider. Do not invent reasoning levels. Repository default: **6.1 Sol / max**.
- `--subagents` sets the model/effort for new subagents. Explicit agent overrides take priority. Update any existing Astra-specific AGENTS.md instructions separately; the installer does not rewrite them.
- Fast (`service_tier = "priority"`) depends on client metadata, account and upstream support. A picker entry does not prove it works. It is not enabled or promised automatically.

### Native image_gen and web.run

`--native-tools` adds the **same router key** here:

```toml
[model_providers.omniroute.http_headers]
x-openai-actor-authorization = "Bearer REPLACE_WITH_YOUR_OMNIROUTE_KEY"

[features]
image_generation = true
```

This is **version-dependent gateway behavior**, not a public OpenAI guarantee for all custom providers. Do not fabricate ChatGPT JWTs/claims or borrow someone else's account. The flag is optional for ordinary Responses inference.

Server requirements:

| Feature | Route |
|---|---|
| Chat / code / tool calls | `POST /v1/responses` |
| Generation | `POST /v1/images/generations` |
| Editing | `POST /v1/images/edits` |
| Native web.run | `POST /v1/alpha/search` |

`/v1/alpha/search` and OmniRoute `/v1/search` use different protocols; rewriting one to the other in nginx does not provide compatibility. The clean3.8.52 image checked for this guide exposes native search: an empty request returns400 validation, not404. Actual search/image inference and account access must be tested separately. Older builds sharing the same version string can differ; do not blindly copy minified-JS patches from someone else's installation.

If a native tool disappears, fully restart the client. A failed generation returning429/401/400 means no image was created: retain the technical code and inspect logs privately. Do not silently change prompt, provider or model.

## 8. Validation, rollback and upgrades

After restarting Codex:

1. Verify the selected model and reasoning levels in the picker.
2. Open one old chat and one archived chat; check pins.
3. Complete one short response and inspect server provider/model metadata.
4. Check that permissions/MCP remain intact.
5. Test native search/image **if you enabled and need them**. Image tests consume quota; use one harmless example, not a batch retry.

### Rollback

Fully quit the client. From an external terminal:

```sh
uv run skills/install-omniroute-codex/scripts/setup.py restore \
  --backup "/YOUR/CODEX_HOME/omniroute-backups/TIMESTAMP"
```

This restores original files and the provider IDs of **previously existing chats only**. It does not replace the whole database, so chats/messages created afterward remain. Later config edits or a new state DB schema cause a refusal and require manual merging. The complete SQLite snapshot is emergency recovery: do not overwrite a newer database without evaluating changes that would be lost.

File writes and SQLite updates are not one crash-atomic transaction. After power loss/interruption between steps, inspect the private `manifest.json` and reconcile auth/config/provider IDs from the backup. Do not blindly repeat apply.

### OmniRoute upgrades

The `server` setup command is for a new empty installation, not a live upgrade. Back up the volume, `.env`, exact image/digest and drain requests first. **Keep encrypted storage and its encryption secret together.** After backup, change the pinned tag, run `docker compose pull && docker compose up -d`, and verify models/Responses/required tools. Rolling back a data-schema migration may require restoring its matching data backup, not only the old image.

At the time checked, latest stable release was3.8.52. Pin a version or digest; `next` is a prerelease channel.

## 9. Troubleshooting

| Symptom | Check |
|---|---|
|401 `invalid_api_key` from `api.openai.com`|Wrong provider/base URL: the router key was sent to OpenAI. Correct and restart.|
|401 from OmniRoute|Active key, matching config/auth, IP and endpoint permissions.|
|400 unsupported model|The selected upstream account lacks model/subscription access; a listing is not proof.|
|Missing models|Native catalog format, absolute path, hidden filters, key scope and restart.|
|Missing old chats|Actual CODEX_HOME and SQLite provider bindings; do not delete sessions or DB.|
|404 `unknown_route` on `/alpha/search`|Gateway build lacks native route support. Do not alias it to `/search`.|
|413 nginx|Adjust `client_max_body_size` on your reverse proxy; also check gateway body/memory limits.|
|503 resource pressure|RAM, heap, queue and concurrency. Avoid endless retries.|
|429|Upstream quota/concurrency; inspect account/reset and respect plan/key policy.|
|504 / timeout|Outbound proxy, egress and actual upstream/gateway timeout; do not replay real tasks repeatedly.|
|Settings revert|Account manager, another client or managed configuration is writing them; choose a consistent config source.|

## 10. Install the skill and give it to an agent

The skill is self-contained: helper and references live inside its directory. Reading the skill does not modify your installation.

macOS/Linux:

```sh
mkdir -p "$HOME/.codex/skills"
cp -R skills/install-omniroute-codex "$HOME/.codex/skills/"
```

If that directory exists, compare versions before replacing; do not merge blindly. Honor a custom CODEX_HOME.

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME/.codex/skills" | Out-Null
Copy-Item -Recurse skills/install-omniroute-codex "$HOME/.codex/skills/"
```

Restart Codex and ask:

```text
Use $install-omniroute-codex.
Install OmniRoute and connect my Codex directly through auth.json/config.toml.
Keep local chats, archives, pins, MCP and my existing permission settings.
Use codex/gpt-6.1-sol with max for the main agent and new subagents.
Inspect the environment, prepare backup and run preflight first.
Do not print tokens. If active Codex prevents the migration,
prepare the exact external-terminal command to run after I quit the app.
```

You can give an agent this repository URL and ask it to install the skill. Clone a reviewed commit and read SKILL.md; avoid `curl | sh` from random forks.

## Sources and checked compatibility

- [OmniRoute stable v3.8.52](https://github.com/cheaper-inference/OmniRoute/releases/tag/v3.8.52), source commit `ad6f33f66bda34eba98645d3bfdabbde294bc843`.
- Checked Docker multi-platform digest: `sha256:b08a12e876baa8a5ccadd1ebbe346fe7267dba3b1c9f4fd6bb02070fae41ab6c`.
- [Advanced configuration / custom providers](https://developers.openai.com/codex/config-advanced), [config reference](https://developers.openai.com/codex/config-reference), [authentication](https://developers.openai.com/codex/auth).
- [Pinned official Codex metadata](https://github.com/openai/codex/blob/716b4ec6dffc7b23b1c598400bccb622551bf787/codex-rs/models-manager/models.json).
- [Native search client](https://github.com/openai/codex/blob/716b4ec6dffc7b23b1c598400bccb622551bf787/codex-rs/codex-api/src/endpoint/search.rs).

[Actual validation matrix](../VALIDATION.md). Screenshots show real demo UI, not subscription entitlement. The native gateway header and SQLite migration are practical integration features, not supported public OpenAI contracts.
