#!/usr/bin/env python3
"""vivo API 真实凭证 smoke test——仅对合成材料运行。

使用方式：cd demo-app/backend && python3 tests/smoke_vivo_live.py
需要本地 .env 文件包含 VIVO_APP_ID 与 VIVO_APP_KEY。
"""
from __future__ import annotations

import base64
import json
import os
import sys
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

# 加载 .env
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

APP_ID = os.getenv("VIVO_APP_ID", "")
APP_KEY = os.getenv("VIVO_APP_KEY", "")

if not APP_KEY and not APP_ID:
    # 尝试用同一个 token
    APP_KEY = os.getenv("VIVO_APP_KEY", "")
    APP_ID = os.getenv("VIVO_APP_ID", "")

print(f"=== vivo API Live Smoke Test ===")
print(f"APP_ID: {APP_ID[:8] if APP_ID else '<empty>'}...")
print(f"APP_KEY: {APP_KEY[:8] if APP_KEY else '<empty>'}...\n")

# 合成测试图片（demo-data 中的 SVG，实际 OCR 需要 PNG/JPG，但测试下 HTTP 连接）
DEMO_SVG = Path(__file__).resolve().parents[3] / "demo-data" / "assets" / "evidence-query-001" / "2024-12-20-clinic.svg"
DEMO_PNG = Path(__file__).resolve().parents[3] / "demo-data" / "capture-samples" / "originals" / "cardiac_lab_clear.png"

results = {"ocr": None, "llm": None}

# ─────────────────────────────────────────────────────────────
# 1. OCR smoke test
# ─────────────────────────────────────────────────────────────
print("--- OCR: 测试 vivo 通用 OCR ---")

# 尝试 HTTPS 优先
for scheme in ["https", "http"]:
    url = f"{scheme}://api-ai.vivo.com.cn/ocr/general_recognition"
    print(f"\n尝试: {url}")

    if not DEMO_PNG.exists():
        print(f"  跳过: 合成图片不存在 {DEMO_PNG}")
        continue

    image_bytes = DEMO_PNG.read_bytes()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    business_id = f"aigc{APP_ID}" if APP_ID else "aigcunknown"

    headers = {
        "Authorization": f"Bearer {APP_KEY}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    params = {"requestId": request_id}
    data = {
        "image": image_base64,
        "pos": "2",
        "businessid": business_id,
        "sessid": session_id,
    }

    try:
        resp = httpx.post(
            url,
            headers=headers,
            params=params,
            data=data,
            timeout=15,
        )
        print(f"  HTTP {resp.status_code}")
        resp_data = resp.json()
        print(f"  响应 (前300字): {json.dumps(resp_data, ensure_ascii=False)[:300]}")

        error_code = resp_data.get("error_code", -1)
        if error_code == 0:
            result = resp_data.get("result", {})
            ocr_entries = result.get("OCR", []) if isinstance(result, dict) else []
            print(f"  识别词数: {len(ocr_entries)}")
            if ocr_entries:
                for entry in ocr_entries[:3]:
                    words = entry.get("words", "")
                    location = entry.get("location", {})
                    print(f"    - '{words}' 位置: {str(location)[:80]}")
            results["ocr"] = {"success": True, "scheme": scheme, "blocks": len(ocr_entries)}
            break
        elif error_code == 1:
            print("  OCR 识别失败 (error_code=1)")
            results["ocr"] = {"success": False, "error": "recognition_failed"}
        elif error_code == 2:
            print("  图像错误 (error_code=2)")
            results["ocr"] = {"success": False, "error": "image_error"}
        else:
            print(f"  未知错误码: {error_code}")
            results["ocr"] = {"success": False, "error": f"error_code={error_code}"}

    except httpx.ConnectError as e:
        print(f"  连接失败: {e}")
        if scheme == "http":
            results["ocr"] = {"success": False, "error": "connection_failed"}
    except httpx.TimeoutException:
        print(f"  超时")
        if scheme == "http":
            results["ocr"] = {"success": False, "error": "timeout"}
    except Exception as e:
        print(f"  异常: {e}")
        if scheme == "http":
            results["ocr"] = {"success": False, "error": str(e)[:100]}

# ─────────────────────────────────────────────────────────────
# 2. LLM smoke test
# ─────────────────────────────────────────────────────────────
print("\n--- LLM: 测试 vivo Chat Completions ---")

llm_url = "https://api-ai.vivo.com.cn/v1/chat/completions"
print(f"端点: {llm_url}")

for req_style in ["request_id", "requestId"]:
    print(f"\n  尝试 query 参数: {req_style}")

    headers = {
        "Authorization": f"Bearer {APP_KEY}",
        "Content-Type": "application/json",
    }
    params = {req_style: str(uuid.uuid4())}

    body = {
        "model": "qwen3.5-plus",
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是'历刻'中的证据联查排序模块，仅处理合成演示病历文本。"
                    "从给定 candidate_segments 中筛选与医生查询直接相关的片段。"
                    "返回 JSON: {\"items\": [...]}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "query": "病人最近的材料中是否提到食欲不振？",
                    "candidate_segments": [
                        {
                            "segment_id": "seg-001",
                            "date": "2024-12-20",
                            "document_type": "病历记录",
                            "raw_text": "患者食欲不振三天，伴恶心。",
                        },
                        {
                            "segment_id": "seg-002",
                            "date": "2025-01-09",
                            "document_type": "随访记录",
                            "raw_text": "患者血压120/80，心率正常。",
                        },
                    ],
                }, ensure_ascii=False),
            },
        ],
        "stream": False,
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    try:
        resp = httpx.post(
            llm_url,
            headers=headers,
            params=params,
            json=body,
            timeout=45,
        )
        print(f"  HTTP {resp.status_code}")
        resp_data = resp.json()
        print(f"  响应 (前400字): {json.dumps(resp_data, ensure_ascii=False)[:400]}")

        error_code = resp_data.get("error_code", 0)
        if error_code == 1001:
            print(f"  request id 参数名错误，重试另一种格式...")
            continue

        if error_code != 0:
            print(f"  API 错误码: {error_code}")
            if req_style == "requestId":
                results["llm"] = {"success": False, "error": f"error_code={error_code}"}
            continue

        # 提取 content
        choices = resp_data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            print(f"  LLM 返回内容: {content[:300]}")
            # 尝试解析 JSON
            try:
                parsed = json.loads(content)
                items = parsed.get("items", [])
                print(f"  解析出 {len(items)} 个证据项")
                results["llm"] = {"success": True, "items": len(items), "query_style": req_style}
            except json.JSONDecodeError:
                print("  返回不是 JSON")
                results["llm"] = {"success": True, "raw_text": content[:100], "query_style": req_style}
            break
        else:
            print(f"  无 choices 字段")
            if req_style == "requestId":
                results["llm"] = {"success": False, "error": "no_choices"}

    except Exception as e:
        print(f"  异常: {e}")
        if req_style == "requestId":
            results["llm"] = {"success": False, "error": str(e)[:100]}

# ─────────────────────────────────────────────────────────────
# 3. 汇总
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 50)
print("测试汇总:")
print(f"  OCR: {results['ocr']}")
print(f"  LLM: {results['llm']}")

all_pass = results.get("ocr", {}).get("success") and results.get("llm", {}).get("success")
if all_pass:
    print("\n✅ 两项 API 均通过！")
else:
    print("\n⚠️ 部分失败，查看详情")

# 更新完成报告用 JSON
report_path = Path(__file__).resolve().parents[1] / "runtime" / "smoke_test_result.json"
report_path.parent.mkdir(parents=True, exist_ok=True)
with open(report_path, "w") as fp:
    json.dump(results, fp, ensure_ascii=False, indent=2)
print(f"结果已保存: {report_path}")
