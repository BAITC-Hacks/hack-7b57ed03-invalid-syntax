# Aqylman frontend

React + TypeScript + Vite frontend for the local FastAPI service. It makes calls only to `http://127.0.0.1:8000` by default.

```powershell
npm install
npm run dev
```

The Tauri configuration in `src-tauri/` provides the desktop shell. Runtime assets are bundled; no CDN, web fonts, or external image URL is used.
