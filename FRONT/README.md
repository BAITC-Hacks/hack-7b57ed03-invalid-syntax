# FRONT

Next.js/TypeScript интерфейс. Не импортирует Python/AI/DB-код и получает все данные только через REST API.

```bash
copy .env.example .env.local
npm install
npm run dev
```

Маршруты:

- `/` — список совещаний и метрики;
- `/meetings/new` — создание и загрузка аудио/видео;
- `/meetings/[id]/processing` — прогресс pipeline;
- `/meetings/[id]` — summary, поручения, участники, транскрипт и экспорт.

