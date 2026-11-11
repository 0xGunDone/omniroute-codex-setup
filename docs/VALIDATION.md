# Validation / Проверки

Updated on **2026-11-11** (Europe/Moscow). Evidence is split by date and environment: a passing helper test is not an OAuth, UI or upstream entitlement check. / Обновлено **11 ноября 2026**. Проверки разделены по дате и окружению: тест скрипта не подтверждает OAuth, интерфейс или права upstream-аккаунта.

## 2026-11-11 — current helper / Текущий установщик

| Check / Проверка | Evidence / Результат |
|---|---|
| macOS | All **32** tests passed using Python and pinned tomlkit 0.13.3. |
| Linux | All **32** tests passed in an official `python:3.11-slim` Docker container with the repository mounted read-only. |
| New server pin / Образ | Helper and Compose example pin `diegosouzapw/omniroute:3.8.53@sha256:b52a17661a1aff42ffb78f349f423e986dfc55b57274f28559f8387622ef8ee4`; latest stable release checked through the official GitHub release API. |
| Sidebar backup / Копия проектов | Original global-state bytes retained during client switch; normal restore keeps newer project state. |
| Project repair / Восстановление | Synthetic API-key-only, single-owner local-project fixtures: offline inspection, selective merge, current-entry precedence, original envelope retained in backup, auth/pins/chat rows retained. |
| Repair refusal / Отказ | OAuth/signed-in, multiple-owner, cloud-backed, unknown/changed schemas, active client, quit-time state/auth changes and partial writes covered. No original state is replaced by a stale quit-time plan. |
| Existing safety checks / Остальные проверки | Targeted provider migration/restore, later chat retention, transaction rollback, symlinks, redirects, credential-safe errors, exact model/effort validation and forbidden-model refusal before network inference. |
| Skill / Скилл | Skill frontmatter validator passed. |

The 3.8.53 pin comes from the checked deployment. A fresh Docker Hub manifest query from this Mac timed out during this update; the new stock image was not pulled or started for the documentation check. / Digest взят из проверенного развёртывания. Повторный запрос manifest к Docker Hub с Mac завершился таймаутом; чистый образ 3.8.53 для этой проверки не скачивался и не запускался.

Tests use synthetic homes and credentials. They do not migrate a user's chat database or change a production gateway. `repair-projects` is a new packaged helper; its transformations are fixture-tested. The original offline recovery of the same migration was confirmed in the installed Desktop UI, but that is not a fresh installation test of this helper on every Codex build.

Тесты используют фиктивные профили и ключи, не изменяют пользовательскую базу или сервер. Новый `repair-projects` проверен на синтетических данных. Первоначальное восстановление той же миграции подтверждено в установленном Desktop, но это не проверка установщика на всех версиях клиента.

## 2026-11-11 — separate deployment / Отдельное развёртывание

| Check / Проверка | Evidence / Результат |
|---|---|
| OmniRoute runtime | Pinned 3.8.53, health passed after an upgrade with staged schema migration and rebased local overlays. This was **not a clean stock installation**. |
| Responses | GPT‑6.1 Sol / max completed a stream; key-scoped model listing checked. |
| Native search | Search and page opening returned output and encrypted state on the patched deployment. Stock search adapter handles `search_query`, not the full native protocol. |
| Built-in image_gen | Generation and reference edit both succeeded after fixing image-specific combo visibility in the separate edit resolver. |
| Overlay checks | 54 checks passed: 49 existing checks plus 5 image-edit cases. These deployment-specific checks and patches are not bundled by this repository. |
| Desktop Projects | Observed 0.167.0-alpha.3.2 API-key-only migration; selective offline restoration recovered local projects and assignments, user confirmed Projects returned. Authentication stayed unchanged. |

These results describe a specific client/gateway/account combination. They do not promise that the stock image, another subscription or a future Desktop build will have identical behavior. No private data, credentials or compiled app chunks are distributed here.

Результаты относятся к конкретной паре клиент/gateway и доступному аккаунту. Они не гарантируют то же поведение на чистом образе, другой подписке или будущей версии Desktop. Приватные данные, ключи и compiled chunks приложений не публикуются.

## 2026-10-27 — original clean demo / Исходная чистая установка

| Check / Проверка | Evidence / Результат |
|---|---|
| Fresh installation | macOS ARM64 Docker Desktop; generated Compose started clean OmniRoute 3.8.52; health 200. |
| Original image | `diegosouzapw/omniroute:3.8.52`, multi-platform digest `sha256:b08a12e876baa8a5ccadd1ebbe346fe7267dba3b1c9f4fd6bb02070fae41ab6c`. |
| Model metadata | Pinned official openai/codex commit `716b4ec6dffc7b23b1c598400bccb622551bf787`; downloaded bytes verified by SHA256. This pin remains unchanged. |
| Actual Codex parser | Installed app-server accepted generated native metadata with provider-prefixed GPT6 IDs in an isolated CODEX_HOME. |
| Synthetic inference | `codex/gpt-6.1-sol` / `max` returned `response.completed` and exact `OMNI_SETUP_OK` through a private SSH tunnel. No user conversation sent. |
| Missing catalog entry | Preflight refused a model omitted by the scoped catalog before client writes, even though inference worked. Guides include visibility/import remediation. |
| Original tests | 21 tests passed on macOS and Linux. Current suite contains 32. |
| Search route presence | Clean gateway returned 400 validation for empty `/v1/alpha/search`; this was **not** proof of complete live search. |
| Screenshots | Six real clean-demo UI images, RU and EN, no real account/token, port 21280. Retained as 3.8.52 illustrations; 3.8.53 uses Keak UI Kit / Editions. |

The demo used 1 GiB heap / 2 GiB container for screenshots. Production helper defaults to 8 GiB heap / 10 GiB container per upstream coding-agent guidance; the small demo budget is not a long-context recommendation.

## Hosted CI and platform limits / CI и ограничения платформ

GitHub Actions is configured for Linux/macOS/Windows. Dispatch was rejected on 27 October and again after this update on **11 November** with `HTTP 422: Actions has been disabled for this user.` Repository Actions permissions report enabled, but this account-level restriction still prevents execution. No Windows CI or actual Windows Desktop/OAuth success is claimed here. Unit tests do not replace those checks.

GitHub Actions настроен на Linux/macOS/Windows. Запуск был отклонён 27 октября и повторно после этого обновления **11 ноября**: `HTTP 422: Actions has been disabled for this user.` Actions разрешён в настройках репозитория, но ограничение аккаунта всё ещё мешает запуску. Успешная проверка Windows CI, установки Windows Desktop и OAuth в этом документе не заявляется.

## Reproduce / Повторить

```sh
uv run --with tomlkit==0.13.3 python -m unittest discover -s tests -v
```

```sh
docker run --rm -v "$PWD:/work:ro" -w /work python:3.11-slim \
  sh -c 'pip install --quiet --disable-pip-version-check tomlkit==0.13.3 && python -m unittest discover -s tests -v'
```
