# Validation / Проверки

Checked on 2026-10-27 (Europe/Moscow).

| Check / Проверка | Evidence / Результат |
|---|---|
| Fresh Docker installation / Чистая установка | macOS ARM64 Docker Desktop; generated Compose started OmniRoute3.8.52; health200. |
| Image / Образ | `diegosouzapw/omniroute:3.8.52`, multi-platform digest `sha256:b08a12e876baa8a5ccadd1ebbe346fe7267dba3b1c9f4fd6bb02070fae41ab6c`. |
| Model metadata / Каталог | Pinned official openai/codex commit `716b4ec6dffc7b23b1c598400bccb622551bf787`; downloaded bytes verified by SHA256. |
| Actual Codex parser / Парсер клиента | Installed Codex app-server accepted generated native metadata and listed four GPT6 model IDs, including provider-prefixed IDs. Isolated CODEX_HOME. |
| Synthetic live inference / Реальный запрос | `codex/gpt-6.1-sol` / `max` returned `response.completed` and exact `OMNI_SETUP_OK` through a private SSH tunnel. No user conversation sent. |
| Missing catalog entry / Отсутствующая модель | Live scoped catalog omitted6.1 Sol even though inference worked; preflight correctly refused before any client writes. Guides include import/visibility remediation. |
| Migration / Миграция | Automated fixtures cover current/archived/pinned chats, unrelated providers, transcript bytes, transaction rollback and original OAuth backup. |
| Restore / Откат | Later new chat retained; original provider restored; later config edits rejected. |
| Guard rails / Защита | Active client, unknown DB schema, unsupported model/effort, remote HTTP and symlink handling fail closed. No forbidden-model probe. |
| Native search route / Маршрут поиска | Clean gateway returned400 validation for empty `/v1/alpha/search`; presence only, not live account entitlement. |
| Screenshots / Скриншоты | Real clean local gateway UI, RU and EN locales. No real upstream account or token in screenshots. Demo port21280. |

The helper passes21 local regression tests. GitHub Actions is configured for Linux/macOS/Windows; inspect the workflow run for its current results. Unit tests validate transformations; they do not replace an actual Windows Desktop installation or provider OAuth flow. Full live search/image generation is not asserted for every client/account/build combination.

The server demo used1GiB heap/2GiB container for dashboard screenshots. Production helper defaults to8GiB heap/10GiB container per upstream coding-agent guidance. Never treat the small demo budget as a long-context coding recommendation.

## Reproduce

```sh
uv run --with tomlkit==0.13.3 python -m unittest discover -s tests -v
```

All tests use synthetic homes and credentials. No user chat database is migrated during validation. Installed personal Codex configuration and production gateway remain unchanged by this documentation project.
