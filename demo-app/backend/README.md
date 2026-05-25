# Demo backend

这是一个只读取 `demo-data/` 合成 fixtures 的 FastAPI 服务。它不执行真实 OCR，不接收真实病例。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
pytest -q
```

接口定义见 `../../docs/API_CONTRACT.md`。
