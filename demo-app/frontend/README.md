# zgcHack Demo Frontend

Vite + React + TypeScript 前端。页面通过 `VITE_API_BASE_URL` 或默认 `http://127.0.0.1:8000` 访问 FastAPI 后端，不内置完整病例 fixture。

```bash
npm install
npm run dev -- --port 5173
npm run lint
npm run typecheck
npm test
npm run build
npm run smoke
```

先确保 backend 已运行在本地 `8000` 端口。`npm run smoke` 使用本机 Google Chrome 执行 Playwright 流程。
