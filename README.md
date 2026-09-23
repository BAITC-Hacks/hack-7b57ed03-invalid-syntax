# Aqylman Meeting Protocol

Локально разворачиваемый MVP для загрузки записи совещания, построения транскрипта, выделения поручений и экспорта протокола. `FRONT` обращается к `BACKEND` только через REST API.

## Быстрый запуск

```bash
docker compose up --build
```

- UI: http://localhost:3000
- Swagger: http://localhost:8000/docs

Без Docker:

```bash
cd BACKEND
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

cd ../FRONT
copy .env.example .env.local
npm install
npm run dev
```

По умолчанию включён `MOCK_MODE=true`: тяжёлые модели не нужны, но весь путь от загрузки до результата и экспорта работает.

## Дерево проекта

```text
project/
├── FRONT/
│   ├── app/                 # dashboard, upload, processing, result
│   ├── components/          # общие UI-компоненты
│   ├── features/            # пользовательские сценарии
│   ├── hooks/  lib/  services/  types/
│   └── public/
├── BACKEND/
│   ├── app/
│   │   ├── api/  core/  models/  schemas/
│   │   ├── repositories/  services/
│   │   ├── ai/
│   │   │   ├── audio/  stt/  diarization/
│   │   │   ├── speaker_mapping/  task_extraction/
│   │   │   ├── deadline_parser/  summarization/
│   │   │   ├── pipelines/  providers/
│   │   │   └── contracts.py
│   │   ├── workers/  utils/
│   │   └── main.py
│   ├── tests/  uploads/  exports/
│   └── requirements.txt
├── README.md
├── docker-compose.yml
└── .gitignore
```

## Архитектура

FRONT: Next.js App Router отвечает за маршрутизацию, интерактивная логика вынесена в `features`. Все HTTP-вызовы централизованы в `services/api.ts`; UI не знает о БД, Python или AI-моделях. Статус pipeline опрашивается hook-ом, после завершения автоматически открывается результат.

BACKEND:

- `api` валидирует HTTP-ввод и отдаёт DTO;
- `services` реализует use cases;
- `repositories` изолирует SQLAlchemy;
- `models` хранит совещания, участников, реплики, поручения и summary;
- `ai/contracts.py` задаёт заменяемые STT/diarization/extraction/summary интерфейсы;
- `MeetingProcessingPipeline` оркестрирует этапы и публикует прогресс;
- `providers/mock.py` даёт результат без внешних сервисов;
- `export_service.py` формирует PDF/DOCX.

Поток данных:

```text
Browser -> REST API -> SQLite / uploads
                     -> validate -> audio -> STT -> diarization
                     -> merge -> mapping -> tasks -> deadlines
                     -> summary -> persistence -> PDF/DOCX
                     -> Browser
```

## REST API contract

| Method | Path | Назначение |
|---|---|---|
| `GET/POST` | `/api/v1/meetings` | список / создание |
| `POST` | `/api/v1/meetings/{id}/upload` | загрузка media |
| `POST` | `/api/v1/meetings/{id}/process` | запуск pipeline |
| `GET` | `/api/v1/meetings/{id}/status` | stage и progress |
| `GET` | `/api/v1/meetings/{id}` | полный результат |
| `GET` | `/api/v1/meetings/{id}/transcript` | транскрипт |
| `GET/PATCH` | `/api/v1/meetings/{id}/tasks[/{task_id}]` | поручения |
| `GET` | `/api/v1/meetings/{id}/summary` | summary |
| `GET/PATCH` | `/api/v1/meetings/{id}/participants[/{participant_id}]` | участники |
| `GET` | `/api/v1/meetings/{id}/export/pdf` | PDF |
| `GET` | `/api/v1/meetings/{id}/export/docx` | DOCX |

```json
{"meeting_id": 1, "status": "processing", "stage": "task_extraction", "progress": 75, "error": null}
```

## Что работает сейчас

- dashboard, drag-and-drop загрузка, экран прогресса и результат;
- SQLite, streaming upload с проверкой типа/лимита и background pipeline;
- транскрипт, участники, summary и поручения;
- ручная коррекция участников и поручений;
- PDF/DOCX, CORS, Docker Compose и интеграционный API-тест.

В `MOCK_MODE` этапы STT, diarization, mapping, task extraction и summary возвращают детерминированный пример. Загрузка, БД, API, прогресс, редактирование и экспорт при этом настоящие.

## Границы команд

- Developer 1: `FRONT/`
- Developer 2: `BACKEND/app/api`, `services`, `models`, `schemas`, `repositories`
- Developer 3: `BACKEND/app/ai`

## Следующие этапы

1. faster-whisper с RU/KZ auto-detect.
2. pyannote.audio и локальный model cache.
3. ffmpeg preprocessing и извлечение WAV из видео.
4. Локальная LLM для multi-turn extraction/summary со строгой JSON schema.
5. Полная нормализация русских/казахских сроков и timezone.
6. Redis + Celery/RQ вместо in-process background task.
7. Alembic, PostgreSQL, авторизация, аудит и object storage для production/on-premise.
