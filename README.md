# Aqylman — офлайн-протоколы совещаний

Рабочий foundation для desktop-приложения, которое хранит записи и результаты только на локальном компьютере. Никаких cloud API, CDN, телеметрии или загрузки моделей во время запуска нет.

## Структура

```text
PROJECT/
├── FRONT/                 React + TypeScript + Vite + Tauri
│   ├── src/               dashboard, upload, progress, result tabs
│   └── src-tauri/         Windows desktop shell
├── BACKEND/               Python/FastAPI/local AI boundary
│   ├── app/api/           REST endpoints
│   ├── app/models/        SQLAlchemy SQLite models
│   ├── app/schemas/       Pydantic API contract
│   ├── app/services/      use cases and export
│   ├── app/ai/            provider contracts and pipeline
│   ├── uploads/ exports/  local mutable files
│   └── models/            put local whisper/diarization/llm models here
├── README.md
└── .gitignore
```

## Architecture and data flow

```text
Vite/Tauri UI → http://127.0.0.1:8000 → FastAPI → SQLite/local files
file → audio → STT → diarization → speaker mapping → tasks → deadlines
     → summary → database → UI / local DOCX / local PDF
```

The UI never touches models; model adapters are behind `BACKEND/app/ai/contracts.py`. `MOCK_MODE=true` is explicitly a deterministic demo provider. Upload, validation, persistence, progress polling, editing, DOCX and PDF are real local functionality.

## Run in development

```powershell
cd BACKEND
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

In a second terminal:

```powershell
cd FRONT
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. For a desktop build, install Rust/Tauri prerequisites once and run `npm run tauri dev` from `FRONT`.

`MOCK_MODE` defaults to `true`. Set `MOCK_MODE=false` in `BACKEND/.env` only after local providers and model paths have been implemented/configured. Place models under `BACKEND/models/whisper`, `BACKEND/models/diarization`, and `BACKEND/models/llm`; the app never downloads them.

## REST contract

| Method | Endpoint | Purpose |
|---|---|---|
| GET/POST | `/api/v1/meetings` | list/create meeting |
| POST | `/api/v1/meetings/{id}/upload` | local media upload |
| POST | `/api/v1/meetings/{id}/process` | start pipeline |
| GET | `/api/v1/meetings/{id}/status` | `status`, `stage`, `progress` |
| GET | `/api/v1/meetings/{id}` | result: transcript/tasks/participants/summary |
| PATCH | `/api/v1/meetings/{id}/participants/{participant_id}` | rename speaker |
| PATCH | `/api/v1/meetings/{id}/tasks/{task_id}` | edit task |
| GET | `/api/v1/meetings/{id}/export/{pdf|docx}` | local protocol export |
| GET | `/health` | offline startup health |

SQLite entities: `meetings`, `participants`, `transcript_segments`, `tasks`, and `summaries`, connected by meeting foreign keys.

## Offline audit

**OFFLINE AUDIT PASSED (foundation).** Runtime requests are limited to the local FastAPI address. No external URLs, client fonts, analytics, cloud database, provider SDK calls, or model download code are present. `requests`/`httpx` are test/development dependencies only, not used by application runtime. The real-model adapters are intentionally not yet implemented; they must only open local files/process local binaries.

## Next implementation steps

1. Add a locally-installed ffmpeg adapter and real faster-whisper provider.
2. Add a local diarization adapter and merge strategy.
3. Add a local GGUF/llama.cpp structured extraction provider.
4. Bundle the Python backend and pre-provisioned models with the Tauri installer.
