# OmniRoute + Codex Setup

**[Русская инструкция со скриншотами](docs/ru/guide.md) · [English guide with screenshots](docs/en/guide.md)**

Подключение Codex напрямую через `auth.json` / `config.toml`, установка OmniRoute и отдельный скилл для агента. Локальные чаты и архивы сохраняются; обновление provider IDs выполняется с резервной копией и только при остановленном клиенте.

Install OmniRoute, connect Codex directly through `auth.json` / `config.toml`, and let an agent use the bundled skill. Local chats and archives are retained through a backed-up, offline provider migration.

**Обновлено / Updated: 2026-11-11.** Сервер закреплён на **OmniRoute 3.8.53** по digest. Добавлены резервная копия состояния проектов и отдельное восстановление пустого раздела **Projects** в API-key-профиле Codex. / The server pins **OmniRoute 3.8.53** by digest. Setup now backs up project state and includes a separate recovery for an empty **Projects** section in an API-key-only Codex profile.

![OmniRoute Codex provider](docs/screenshots/en-01-codex-provider.png)

Скриншоты: чистая demo 3.8.52, 27 октября; 3.8.53 меняет оформление. / Screenshots: clean 3.8.52 demo from 27 October; 3.8.53 changes the theme. [Provenance](docs/screenshots/PROVENANCE.md).

## Start / Начать

| RU | EN |
|---|---|
| [Полная установка и настройка](docs/ru/guide.md) | [Complete installation and configuration](docs/en/guide.md) |
| [Скилл установки для агента](skills/install-omniroute-codex/SKILL.md) | [Agent installation skill](skills/install-omniroute-codex/SKILL.md) |
| [Что проверено](docs/VALIDATION.md) | [Validation and limitations](docs/VALIDATION.md) |
| [Если пропали проекты](docs/ru/guide.md#если-после-переключения-профиля-пропали-проекты) | [If Projects disappeared](docs/en/guide.md#if-projects-disappear-after-switching-profiles) |

```sh
git clone https://github.com/0xGunDone/omniroute-codex-setup.git
cd omniroute-codex-setup
uv run skills/install-omniroute-codex/scripts/setup.py --help
```

Helper requires Python3.11+ and [uv](https://docs.astral.sh/uv/getting-started/installation/). It uses pinned `tomlkit`. `server` creates a new loopback-only Docker installation. `client` defaults to preflight; writing requires `--apply`. Preflight includes one quota-consuming synthetic inference.

**Примеры / Examples**

- [auth.example.json](examples/auth.example.json) — only placeholder values; use your own router key.
- [config.example.toml](examples/config.example.toml) — merge settings; never replace a whole existing config.
- [model-catalog.example.json](examples/model-catalog.example.json) — native JSON structure; generate a complete catalog with the helper.
- [compose.example.yaml](examples/compose.example.yaml) — persistent storage, loopback binding and version pin.

Default: **`codex/gpt-6.1-sol` / `max`**. Existing sandbox, approvals, plugins and MCP settings are not relaxed. No shared accounts, real API keys, personal endpoints, chat history or production data are included.

**Compatibility:** model listings do not grant upstream access. Native image/search tools require compatible client and gateway builds; SQLite metadata is an internal, version-dependent interface. This is an independent community guide, not an official OmniRoute/OpenAI product. See both guides for limits and rollback.

`repair-projects` is an explicit, offline workaround for the observed Codex Desktop 0.167.0-alpha.3.2 account-state migration. It defaults to inspection, needs an API-key-only profile with one saved local project collection, and refuses signed-in, multiple-owner, cloud-backed or unknown layouts. It never edits authentication or chat databases. Read the linked recovery section before `--apply`.

## Development

```sh
uv run --with tomlkit==0.13.3 python -m unittest discover -s tests -v
```

Original helper/docs: MIT. OmniRoute and Codex retain their respective licenses; official model metadata is downloaded from a checksum-verified public commit, not bundled from a personal installation.
