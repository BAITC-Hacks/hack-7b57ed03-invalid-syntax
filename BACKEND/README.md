# ALEM BACKEND

FastAPI/SQLite backend со встроенным web-интерфейсом. Основной запуск выполняется из корня:

```bash
python main.py
```

При наличии `OPENAI_API_KEY` основной pipeline использует официальный OpenAI SDK,
`gpt-4o-transcribe-diarize` и Structured Outputs. Без ключа автоматически включается явно
обозначенный DEMO mode. Настройки можно положить в `BACKEND/.env`; пример — `.env.example`.

Старый локальный pipeline доступен через `AI_PROVIDER=local`: модели находятся в
`models/whisper`, `models/diarization`, `models/llm`. Текущий режим показывает `/health`.

Для тестов `tests/conftest.py` явно включает mock:

```bash
python -m pytest -q
```

Интерфейс раздаётся из `app/web/`. Схема SQLite расширяется только additive-миграциями без удаления пользовательских данных.
