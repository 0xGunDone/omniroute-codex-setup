# OmniRoute + Codex: установка и перенос без удаления чатов

[English](../en/guide.md) · [Главная](../../README.md) · Проверено: **27 октября 2026**

Инструкция для личного OmniRoute и Codex Desktop / CLI / расширения VS Code. Настраиваем **напрямую через `auth.json` и `config.toml`**, без обязательного CodexAcc. Сохраняем локальные чаты, архивы, закрепления, MCP и пользовательские разрешения. Отдельный [скилл](../../skills/install-omniroute-codex/SKILL.md) помогает агенту выполнить установку.

**Границы обещания:** сохранность данных не означает сохранение всех функций ChatGPT. Доступ к каждой модели определяется аккаунтом/провайдером на сервере, подпиской, квотой и политикой ключа. Каталог не выдаёт подписку. Облачные чаты другого аккаунта этим способом не переносятся. Внутренняя схема SQLite Codex меняется: установщик останавливается на неизвестной схеме.

## Содержание

1. [Что куда идёт](#1-что-куда-идёт)
2. [Сервер](#2-установка-сервера)
3. [Аккаунт и ключ](#3-аккаунт-codex-и-ключ-omniroute)
4. [Файлы Codex](#4-какие-файлы-нужны)
5. [Автоматическое подключение](#5-подключение-с-проверкой-и-резервной-копией)
6. [Старые чаты](#6-перенос-существующих-чатов)
7. [Модели и инструменты](#7-модели-мышление-fast-и-встроенные-инструменты)
8. [Проверка и откат](#8-проверка-откат-и-обновление)
9. [Ошибки](#9-типовые-ошибки)
10. [Скилл и промпт](#10-установка-скилла-и-промпт-агенту)

## 1. Что куда идёт

```mermaid
flowchart LR
    A[Codex Desktop / CLI / VS Code] -->|Responses + ключ OmniRoute| B[OmniRoute /v1]
    B -->|OAuth своего аккаунта| C[Codex provider]
    B --> D[Другие настроенные провайдеры]
    A --- E[Локальные чаты в CODEX_HOME]
```

Три разных секрета:

| Секрет | Где хранится | Для чего |
|---|---|---|
| Пароль панели | Сервер, приватный `.env` | Вход в dashboard |
| ChatGPT OAuth / токены провайдера | Хранилище OmniRoute на сервере | Запросы к upstream |
| **API-ключ OmniRoute** | `auth.json`, секция провайдера в `config.toml` | Запросы Codex к вашему OmniRoute |

Не вставляйте API-ключ OmniRoute в аккаунт OpenAI: `sk-or-…` не становится ключом `api.openai.com`. Не импортируйте в провайдер Codex файл `auth.json`, уже содержащий ключ роутера: для upstream нужен настоящий ChatGPT OAuth или штатный вход.

## 2. Установка сервера

### Требования

- Linux + Docker Engine и Compose v2 либо macOS/Windows + Docker Desktop.
- Python **3.11+**, [uv](https://docs.astral.sh/uv/getting-started/installation/) и Git.
- Установленный Codex на клиенте. На Mac это может быть приложение ChatGPT с Codex; для CLI — [официальная установка](https://developers.openai.com/codex/cli).
- Достаточно памяти: upstream рекомендует для одного кодового агента V8 **8 GiB** и контейнер от **10 GiB**. Нескольким большим контекстам нужно больше. Docker Desktop тоже должен иметь такой лимит ресурсов.

[Docker Engine](https://docs.docker.com/engine/install/) · [Docker Desktop](https://docs.docker.com/desktop/) · [требования OmniRoute](https://github.com/cheaper-inference/OmniRoute/blob/main/docs/guides/DOCKER_GUIDE.md)

```sh
git clone https://github.com/0xGunDone/omniroute-codex-setup.git
cd omniroute-codex-setup
uv run skills/install-omniroute-codex/scripts/setup.py server \
  --directory "$HOME/omniroute-server" --start
```

Windows PowerShell: та же команда в одну строку, без `\` в конце. При необходимости сначала `uv python install 3.11`.

Скрипт генерирует уникальные `INITIAL_PASSWORD`, `JWT_SECRET`, `API_KEY_SECRET`, `STORAGE_ENCRYPTION_KEY`, включает `REQUIRE_API_KEY=true`, сохраняет их в приватном `.env` и поднимает Compose. Существующий непустой каталог не перезаписывает. Без `--start` только готовит файлы.

```text
~/omniroute-server/
├── .env             # СЕКРЕТЫ: не коммитить и не пересылать
├── .gitignore
└── compose.yaml     # закреплённый образ 3.8.52, localhost:20128
```

Данные — в именованном Docker volume `omniroute-data` внутри проекта Compose; внутри контейнера `/app/data`. Имя volume содержит имя проекта, смотрите `docker compose config --volumes`. Не запускайте `docker compose down -v`, если хотите сохранить аккаунты.

```sh
cd "$HOME/omniroute-server"
docker compose ps
```

Панель: `http://127.0.0.1:20128`. Пароль возьмите из `INITIAL_PASSWORD` своего `.env` в приватном редакторе. Не используйте `CHANGEME` на рабочем сервере.

### Удалённый сервер

Команду `server` запускайте **на сервере**, клиентскую настройку ниже — **на своём компьютере**. Сначала откройте SSH-туннель и оставьте его работать:

```sh
ssh -N -L 20128:127.0.0.1:20128 user@YOUR_SERVER
```

Тогда адрес на Mac/Windows остаётся `http://127.0.0.1:20128/v1`. Альтернатива — собственный домен с HTTPS и reverse proxy; не публикуйте панель/API по открытому HTTP. Если20128 занят, выберите другой локальный порт и укажите его в base URL.

### Дополнительные провайдеры и прокси

Добавляйте их через Providers. Для Codex предпочтителен прямой Codex OAuth provider; модели OpenRouter — другой платный/лимитируемый маршрут. Если нужен SOCKS/HTTP, задайте его через Proxy в OmniRoute и назначьте провайдеру/аккаунту. `127.0.0.1` **в Docker** означает контейнер: прокси хоста должен быть доступен из его сети (`host.docker.internal` в Docker Desktop либо явно настроенный Linux host-gateway). Не меняйте домашний роутер ради установки.

## 3. Аккаунт Codex и ключ OmniRoute

Скриншоты сняты с отдельной чистой установки **3.8.52** с фиктивными данными, без личных аккаунтов. Порт21280 выбран только для демонстрации; в командах используется20128. Названия кнопок могут отличаться между сборками.

![RU: страница провайдера Codex](../screenshots/ru-01-codex-provider.png)

1. Откройте **Провайдеры → OpenAI Codex**.
2. Нажмите **Добавить** и завершите штатный OAuth/Device Code вход своим аккаунтом. На удалённом сервере соблюдайте подсказки по callback/порту; вход и согласие выполняет владелец аккаунта.
3. Если используете **Импорт авторизации**, передавайте только приватный оригинальный ChatGPT `auth.json`, поддерживаемый этой сборкой. Не вставляйте токены в чат с агентом и не делайте скриншот содержимого.
4. Убедитесь, что подключение активно. Обновите доступные модели. Скрытая/запрещённая в панели модель может не попасть в каталог ключа.

Если `gpt-6.1-sol` отсутствует, сначала выполните **Import from /models**. Если upstream поддерживает модель, но сборка gateway ещё не знает её, добавьте **Custom Models → Model ID: `gpt-6.1-sol`** у провайдера Codex, включите Chat/Responses и видимость модели. После этого убедитесь, что `/v1/models` **с тем же API-ключом** возвращает точный ID `codex/gpt-6.1-sol` либо `cx/gpt-6.1-sol`. Если доступен только второй, передайте его через `--model`. Не добавляйте фиктивную поддержку модели, которую upstream реально отклоняет.

![RU: добавление аккаунта](../screenshots/ru-02-add-account.png)

5. Откройте **Менеджер API**. Создайте отдельный ключ, например `codex-laptop`.
6. Дайте ему доступ к требуемому Codex-провайдеру, соединениям и моделям. Разрешите Responses; для native tools также соответствующие категории поиска/изображений, если они ограничены в ключе.
7. Сохраните ключ приватно. Ключ роутера не равен паролю панели. Для разных людей создавайте разные ключи с подходящими ограничениями.

![RU: менеджер API](../screenshots/ru-03-api-manager.png)

Не нажимайте «проверить все модели» ради инструкции: это отправляет множество запросов и расходует лимиты. Проверяем только выбранную разрешённую модель.

## 4. Какие файлы нужны

`CODEX_HOME` по умолчанию — `~/.codex` (Windows: `%USERPROFILE%\.codex`). Если переменная `CODEX_HOME` задана, используйте её. Расширение VS Code на SSH/WSL хранит настройки **на удалённой стороне**, а не в домашнем каталоге Mac.

| Файл/каталог | Действие | Назначение |
|---|---|---|
| `config.toml` | аккуратно объединить | Провайдер, адрес, модель, мышление |
| `auth.json` | заменить активную авторизацию, сохранив копию | Ключ OmniRoute |
| `omniroute-model-catalog.json` | создать | Родной формат каталога Codex, модели и уровни мышления |
| `state_N.sqlite` + `-wal`/`-shm` | резервная копия; точечный SQL только при остановленном клиенте | Метаданные и привязка старых чатов к провайдеру |
| `sessions/`, `archived_sessions/`, история, вложения | **не удалять и не переписывать** | Содержимое локальных разговоров |
| `AGENTS.md`, MCP, plugins, permissions | сохранить | Ваши инструкции и доступы |

### `auth.json`

[Готовый пример](../../examples/auth.example.json):

```json
{
  "OPENAI_API_KEY": "REPLACE_WITH_YOUR_OMNIROUTE_KEY"
}
```

Это новый активный API-key login. Старый OAuth сохраняется в **приватной резервной копии**; смешивать в активном файле `tokens` старого ChatGPT и ключ роутера не нужно. Для стабильности установщик задаёт `cli_auth_credentials_store = "file"`; старую запись OS keychain не удаляет.

### `config.toml`

[Полный пример](../../examples/config.example.toml) — **не заменяйте им весь существующий конфиг**. Новые глобальные параметры должны идти **до** `[section]`, иначе TOML относит их к последней таблице. Скрипт использует TOML-парсер и сохраняет другие разделы/комментарии.

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

В `auth.json` и `experimental_bearer_token` — **один ключ OmniRoute**. Здесь фиксированный bearer явно задаёт авторизацию custom provider; секрет хранится и в config, поэтому файл должен быть приватным. Удалённый адрес: `https://router.example/v1`. Не добавляйте `/responses` к `base_url`.

### Каталог

`GET /v1/models` возвращает OpenAI-совместимый список `data[].id`. Это **не** формат `model_catalog_json`. Каталогу Codex нужны `models[].slug`, метаданные инструментов и `supported_reasoning_levels`.

Установщик берёт metadata из **проверенного по SHA256 публичного snapshot openai/codex**, пересекает его с моделями, видимыми данному ключу, и использует точные `codex/…`, `cx/…` либо bare IDs. В результате выбор мышления и метаданные native tools не теряются. Каталог не конвертирует произвольную модель Claude/Gemini в нативную Codex-модель. Для новой модели/сборки нужен совместимый trusted snapshot; используйте `--catalog-template PATH`. Каталог может включать инструкции модели — не берите его из случайных публикаций.

Формат одного элемента: [model-catalog.example.json](../../examples/model-catalog.example.json). Это сокращённый пример структуры, не замена полного каталога с метаданными инструментов. Для рабочей установки используйте генератор.

## 5. Подключение с проверкой и резервной копией

Приватный ключ можно ввести скрыто в терминале: без `--key-file` скрипт сам запросит его. Для запуска агентом удобен приватный файл только с ключом; агент не должен читать его в пользовательский вывод.

Unix: создайте файл `~/.config/omniroute/router.key` приватным редактором, выполните `chmod 600 ~/.config/omniroute/router.key`. Windows: храните файл с ACL только для своего пользователя; доступы проверяйте через `icacls`.

**Сначала preflight, без записи настроек:**

```sh
uv run skills/install-omniroute-codex/scripts/setup.py client \
  --base-url http://127.0.0.1:20128/v1 \
  --key-file "$HOME/.config/omniroute/router.key" \
  --model codex/gpt-6.1-sol --effort max \
  --from-provider openai --native-tools --subagents
```

Preflight читает каталог, проверяет модель/effort, отправляет **один маленький платный/лимитируемый диагностический запрос** `OMNI_SETUP_OK` и показывает количество чатов каждого провайдера. Даже без `--apply` этот запрос расходует upstream-квоту. Содержимое ваших чатов не отправляется.

Если ваши старые чаты были у другого провайдера, укажите его **реальный ID** через `--from-provider previous_id`; параметр повторяемый. Без него старые чаты не мигрируют. Другие провайдеры не затрагиваются.

**Затем полностью закройте Codex/ChatGPT Desktop, CLI и расширение VS Code.** Откройте обычный внешний Terminal/PowerShell и повторите команду с `--apply`. Агент внутри работающего Codex не должен изменять свою живую SQLite-базу; он готовит всё заранее и даёт финальную команду для внешнего терминала. `--wait-for-exit 120` может дождаться вашего выхода, но не завершает процессы сам.

Результат содержит:

```json
{
  "model": "codex/gpt-6.1-sol",
  "effort": "max",
  "threads_to_migrate": 12,
  "inference": {"completed": true, "marker": true},
  "backup": "/YOUR/CODEX_HOME/omniroute-backups/TIMESTAMP"
}
```

Число12 — пример. Бэкап включает исходные auth/config/catalog, согласованный SQLite snapshot и manifest со старыми provider IDs. Скрипт не коммитит эти файлы. Активный `[profiles]`/`openai_base_url` он просит разобрать заранее. Также проверьте project/managed settings: они могут перекрывать пользовательские defaults.

## 6. Перенос существующих чатов

Переключение одного `model_provider` в `config.toml` не гарантирует перенос старых разговоров: provider сохраняется в `threads.model_provider`. Наш скрипт проверяет текущую схему, выбирает максимальную числовую `state_N.sqlite`, создаёт backup и выполняет транзакцию с условием на старое значение.

Пример принципа SQL, **не команда для живой базы**:

```sql
BEGIN IMMEDIATE;
UPDATE threads
SET model_provider = 'omniroute'
WHERE model_provider = 'openai';
COMMIT;
```

В скрипте операция дополнительно ограничена сохранёнными ID и проверяет каждое старое значение. `id`, `rollout_path`, title, archive, pins, проект и содержимое сессий остаются прежними. Модель, явно выбранная внутри старого чата, не заменяется автоматически: если её нет на вашем роутере, выберите доступную в интерфейсе. Не меняйте provider в каждой строке JSONL и не удаляйте SQLite/WAL.

Безопасный ожидаемый результат: старый чат и архив видны под теми же ID, новый ответ проходит через OmniRoute. При иной версии внутренней схемы остановитесь и адаптируйте миграцию, сохранив backup.

## 7. Модели, мышление, Fast и встроенные инструменты

- Название в списке ≠ entitlement. Окончательное доказательство — `response.completed` и правильный текст диагностического ответа.
- Выбор exact ID важен: `codex/gpt-6.1-sol` и `openrouter/openai/gpt-6.1-sol` — разные маршруты, квоты и стоимость.
- `max`/`ultra` должны поддерживаться выбранной моделью/провайдером. Не подставляйте неподдерживаемое значение. Default в этом репозитории: **6.1 Sol / max**.
- `--subagents` задаёт model/effort новым субагентам. Явные overrides конкретного агента имеют приоритет. Существующий AGENTS.md с требованием Astra следует привести к вашему выбору отдельно; установщик его не переписывает.
- Fast (`service_tier = "priority"`) зависит от client metadata, аккаунта и upstream. Список/переключатель сам по себе не гарантирует Fast. Не включаем и не обещаем его автоматически.

### Native image_gen и web.run

`--native-tools` добавляет **тот же ключ роутера** в:

```toml
[model_providers.omniroute.http_headers]
x-openai-actor-authorization = "Bearer REPLACE_WITH_YOUR_OMNIROUTE_KEY"

[features]
image_generation = true
```

Это **зависящая от версии возможность gateway**, не публичная гарантия OpenAI для любого стороннего провайдера. Не добавляйте вымышленные ChatGPT JWT/claims и не подставляйте чужой аккаунт. Для обычных Responses-запросов флаг необязателен.

Требования сервера:

| Функция | Маршрут |
|---|---|
| Чат / код / tool calls | `POST /v1/responses` |
| Генерация | `POST /v1/images/generations` |
| Редактирование | `POST /v1/images/edits` |
| Встроенный web.run | `POST /v1/alpha/search` |

`/v1/alpha/search` и OmniRoute `/v1/search` используют разные протоколы — nginx rewrite одного в другой не исправляет совместимость. На чистом образе3.8.52 из этой инструкции маршрут native search присутствует: пустой запрос отклоняется как400 валидации, а не404. Реальные web/image запросы и доступ аккаунта надо проверять отдельно. Старые сборки с той же строкой версии могут отличаться; не переносите на них вслепую minified JS-патчи из чужой установки.

Если native tool пропал, полностью перезапустите клиент. Если генератор вернул429/401/400, картинка не создана; сохраните код ошибки, проверьте лог privately. Не меняйте промпт/модель/провайдер молча.

## 8. Проверка, откат и обновление

После запуска Codex проверьте:

1. В списке есть выбранная модель и корректные reasoning levels.
2. Один старый чат и один архив открываются, закрепления на месте.
3. Одна короткая реплика завершается; логи сервера показывают выбранный provider/model.
4. Разрешения/MCP работают по-прежнему.
5. Native web/image проверены, **если вы их включали и хотите использовать**. Генерация расходует лимит: используйте простой тест, не повторяйте пачкой.

### Откат

Полностью закройте клиент. В обычном терминале:

```sh
uv run skills/install-omniroute-codex/scripts/setup.py restore \
  --backup "/YOUR/CODEX_HOME/omniroute-backups/TIMESTAMP"
```

Восстанавливаются исходные файлы и provider IDs **только существовавших чатов**. Новые чаты/сообщения не теряются: скрипт не откатывает всю базу поверх текущей. Если config изменён после установки или появилась новая версия state DB — отказ и ручное объединение. Полный SQLite snapshot — аварийная копия; не копируйте его поверх новой базы без оценки потерянных изменений.

Запись файлов и SQLite не является одной crash-atomic транзакцией. При отключении питания/прерывании между этапами изучите приватный `manifest.json` и согласуйте auth/config/provider IDs из бэкапа; не запускайте apply повторно вслепую.

### Обновление OmniRoute

Не обновляйте рабочий сервер установочной командой `server`: она рассчитана на пустой каталог. Сначала сохраните volume, `.env`, исходный образ/digest и остановите новые запросы. **Секрет шифрования и данные восстанавливаются вместе.** После backup можно поменять закреплённый tag, выполнить `docker compose pull && docker compose up -d` и проверить модели/Responses/нужные инструменты. Для отката схемы данных нужен соответствующий backup — одного старого Docker image бывает мало.

На момент проверки latest stable release —3.8.52. Закрепляйте tag или digest; `next` — prerelease, не обещание стабильности.

## 9. Типовые ошибки

| Симптом | Что проверить |
|---|---|
|401 `invalid_api_key` от `api.openai.com`|Неверный provider/base URL; ключ OmniRoute ушёл в OpenAI. Перезапустите клиент после исправления.|
|401 от OmniRoute|Ключ активен? Совпадает с config/auth? Разрешён IP/endpoint?|
|400 model unsupported|У выбранного upstream аккаунта нет этой модели/подписки; запись в каталоге не доказывает доступ.|
|Модели не видны|Не скармливайте `data[].id` вместо нативного каталога. Проверьте absolute path, фильтры, scope ключа и restart.|
|Пропали старые чаты|Проверьте CODEX_HOME и provider в SQLite; не удаляйте sessions и DB.|
|404 `unknown_route` на `/alpha/search`|Сборка gateway не поддерживает новый native route. Не заменяйте на `/search`.|
|413 nginx|Увеличьте `client_max_body_size` на своём reverse proxy; учитывайте лимит и память самого gateway.|
|503 resource pressure|Проверьте RAM/heap/очередь, уменьшите параллельность; не делайте бесконечные ретраи.|
|429|Upstream квота/конкурентность; проверьте аккаунт и reset, не обходите тариф/политику.|
|504 / timeout|Прокси, egress, реальный timeout gateway/upstream; не отправляйте реальную задачу многократно.|
|Конфиг меняется обратно|Account manager/другая сессия/managed policy перезаписывает настройки; согласуйте один источник конфигурации.|

## 10. Установка скилла и промпт агенту

Скилл автономен: скрипт и короткие references лежат внутри его каталога. Он не меняет личную установку при одном чтении.

macOS/Linux:

```sh
mkdir -p "$HOME/.codex/skills"
cp -R skills/install-omniroute-codex "$HOME/.codex/skills/"
```

Если каталог уже существует, сначала сравните версии, не смешивайте их вслепую. Для другого CODEX_HOME скорректируйте путь.

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME/.codex/skills" | Out-Null
Copy-Item -Recurse skills/install-omniroute-codex "$HOME/.codex/skills/"
```

Перезапустите Codex, затем:

```text
Используй $install-omniroute-codex.
Установи OmniRoute и подключи мой Codex напрямую через auth.json/config.toml.
Сохрани локальные чаты, архивы, закрепления, MCP и текущие разрешения.
Используй codex/gpt-6.1-sol с max для основного агента и новых субагентов.
Сначала проверь окружение, подготовь backup и preflight.
Не печатай токены. Если работающий Codex мешает миграции,
подготовь точную команду для внешнего терминала после выхода из приложения.
```

Можно дать агенту URL этого репозитория и попросить установить скилл. Пусть клонирует проверенный commit и читает SKILL.md; не используйте `curl | sh` из случайных форков.

## Источники и проверенная совместимость

- [OmniRoute stable v3.8.52](https://github.com/cheaper-inference/OmniRoute/releases/tag/v3.8.52), исходный commit `ad6f33f66bda34eba98645d3bfdabbde294bc843`.
- Проверенный Docker multi-platform digest: `sha256:b08a12e876baa8a5ccadd1ebbe346fe7267dba3b1c9f4fd6bb02070fae41ab6c`.
- [Custom providers / advanced config](https://developers.openai.com/codex/config-advanced), [config reference](https://developers.openai.com/codex/config-reference), [auth](https://developers.openai.com/codex/auth).
- [Официальный каталог Codex, pinned commit](https://github.com/openai/codex/blob/716b4ec6dffc7b23b1c598400bccb622551bf787/codex-rs/models-manager/models.json).
- [Native search client](https://github.com/openai/codex/blob/716b4ec6dffc7b23b1c598400bccb622551bf787/codex-rs/codex-api/src/endpoint/search.rs).

[Матрица фактических проверок](../VALIDATION.md). Скриншоты показывают реальный demo UI, не подтверждают наличие подписок. Native gateway header и SQLite migration — практическая интеграция этого проекта, а не поддерживаемый OpenAI контракт.
