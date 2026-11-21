#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DeepInfra 数据端点探测器（本机运行，需联网）。
逐个尝试候选 JSON 端点，打印状态码与响应开头，确定真实数据入口。"""
import httpx

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

CANDIDATES = [
    "https://deepinfra.com/api/models",
    "https://api.deepinfra.com/models/list",
    "https://api.deepinfra.com/models",
    "https://deepinfra.com/models?format=json",
    "https://deepinfra.com/api/pricing",
    "https://api.deepinfra.com/pricing",
    "https://deepinfra.com/_next/data/build-id/models.json",
]


def main():
    for url in CANDIDATES:
        try:
            r = httpx.get(url, headers=UA, timeout=15, follow_redirects=True)
            ct = r.headers.get("content-type", "")
            body = r.text
            print(f"{r.status_code} {ct:35s} {url}")
            print("   ", body[:300].replace("\n", " "))
            if r.status_code == 200 and "json" in ct:
                try:
                    j = r.json()
                    if isinstance(j, dict):
                        print("    顶层键:", list(j.keys())[:12])
                    elif isinstance(j, list):
                        print("    列表长度:", len(j))
                except Exception:
                    pass
        except Exception as e:
            print(f"ERR  {url} -> {e}")


if __name__ == "__main__":
    main()
