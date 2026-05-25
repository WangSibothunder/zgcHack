#!/usr/bin/env python3
"""vivo LLM Chat Completions 快速 smoke test——只用合成数据。"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

APP_KEY = os.getenv("VIVO_APP_KEY", "")
print(f"APP_KEY: {APP_KEY[:8]}...")

llm_url = "https://api-ai.vivo.com.cn/v1/chat/completions"
print(f"端点: {llm_url}")

for req_style in ["request_id", "requestId"]:
    print(f"\n尝试 query={req_style}")
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
                "content": "你是转诊迹证据排序模块，仅处理合成演示病历。返回JSON {\"items\":[{\"segment_id\":\"...\",\"relevance_level\":\"...\",\"evidence_summary\":\"...\"}]}",
            },
            {
                "role": "user",
                "content": json.dumps({
                    "query": "最近材料是否提到食欲不振？",
                    "candidate_segments": [
                        {"segment_id": "seg-001", "date": "2024-12-20", "raw_text": "患者食欲不振三天，伴恶心。"},
                        {"segment_id": "seg-002", "date": "2025-01-09", "raw_text": "患者血压120/80，心率正常。"},
                    ],
                }, ensure_ascii=False),
            },
        ],
        "stream": False,
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    try:
        resp = httpx.post(llm_url, headers=headers, params=params, json=body, timeout=10)
        print(f"  HTTP {resp.status_code}")
        data = resp.json()
        print(f"  响应: {json.dumps(data, ensure_ascii=False)[:400]}")
        if data.get("error_code") == 1001:
            print(f"  1001 — request id 参数名错误，重试...")
            continue
        choices = data.get("choices", [])
        if choices:
            content = choices[0]["message"]["content"]
            print(f"  Content: {content[:400]}")
        if req_style == "requestId":
            print(f"  requestId 也不成功")
        break
    except httpx.TimeoutException:
        print(f"  超时(10s)")
    except Exception as e:
        print(f"  异常: {e}")
        if req_style == "requestId":
            print("  最后重试也失败")
