# BACKEND

FastAPI + SQLAlchemy сервер. Все AI-компоненты находятся только в `app/ai` и подключаются через протоколы провайдеров, поэтому mock-реализации можно независимо заменить на faster-whisper, pyannote и локальную LLM.

## Запуск

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Swagger: http://localhost:8000/docs. Для реального inference установите `MOCK_MODE=false` после подключения реализаций провайдеров. Пока при этом API явно вернёт ошибку конфигурации, а не отправит данные наружу.

## Pipeline

`MeetingProcessingPipeline` публикует стадии и прогресс: загрузка, подготовка аудио, STT, diarization, объединение, mapping, поручения, сроки, summary, сохранение, протокол. Обработка запускается как фоновая задача FastAPI; для production worker можно заменить на Celery/RQ без изменения API.

