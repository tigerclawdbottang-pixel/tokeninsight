#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
InferenceX 实测性能采集器
=========================
每天从 InferenceX 公开 API（https://inferencex.semianalysis.com/api/v1）抓取
目标模型 × GPU 的实测吞吐，与种子数据 data/gpu_perf_seed.json 合并，
输出 data/gpu_perf.json 供 build_site.py 合入 GPU ROI 页面。

设计要点：
- API 结构在迭代探明中：逐端点探测，原始响应落盘 data/inferencex_raw/ 供事后分析
- 自动归一化：递归遍历 JSON，凡是同时含 模型名 + GPU 名 + 吞吐字段 的记录都抽取
- API 实测覆盖种子估计（同 model_key+gpu）；API 没覆盖的组合保留种子
- 任何失败只告警，exit 0 —— 不阻塞价格采集与站点构建

用法：
    python3 scripts/collect_inferencex.py
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "data", "gpu_perf_seed.json")
OUT = os.path.join(ROOT, "data", "gpu_perf.json")
RAW_DIR = os.path.join(ROOT, "data", "inferencex_raw")

API_BASE = "https://inferencex.semianalysis.com/api/v1"
# 候选端点：API 结构探明前列全；返回非 JSON/404 自动跳过
CANDIDATES = [
    "", "/inference", "/models", "/benchmarks", "/results",
    "/inference/results", "/inference/benchmarks", "/runs", "/sweeps",
]

# InferenceX 模型名 → 本站 model_key（与 data.json 的 loose 对齐）
MODEL_MAP = [
    (re.compile(r"glm[-_]?5", re.I), "glm53"),
    (re.compile(r"deepseek.*v4.*pro|deepseek[-_]?v4", re.I), "deepseekv4pro"),
    (re.compile(r"deepseek.*v3\.2", re.I), "deepseekv32"),
    (re.compile(r"kimi[-_]?k3\.?1.*pro|k3p", re.I), "kimik31pro"),
    (re.compile(r"kimi[-_]?k3", re.I), "kimik3"),
    (re.compile(r"minimax[-_]?m3\.?1.*flash", re.I), "minimaxm31flash"),
    (re.compile(r"minimax[-_]?m2\.?5", re.I), "minimaxm25"),
    (re.compile(r"qwen3\.5.*397", re.I), "qwen35397b"),
    (re.compile(r"qwen3.*max|qwen3\.8.*max", re.I), "qwen38max"),
]
# GPU 名归一化
GPU_MAP = [
    (re.compile(r"h100", re.I), "h100"),
    (re.compile(r"h200", re.I), "h200"),
    (re.compile(r"b300", re.I), "b300"),
    (re.compile(r"b200|gb200", re.I), "b200"),
]
# 吞吐字段候选（按优先级）
TPS_KEYS = ["output_throughput", "output_tps", "output_tokens_per_second",
            "decode_throughput", "throughput_output", "gen_throughput"]
MODEL_KEYS = ["model", "model_name", "model_id", "modelId"]
GPU_KEYS = ["gpu", "gpu_type", "gpu_model", "hardware", "accelerator", "device"]
CONC_KEYS = ["concurrency", "max_concurrency", "conc"]
TTFT_KEYS = ["median_ttft", "ttft", "ttft_s", "median_ttft_s"]


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": "modelprice-collector/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def map_model(s):
    for pat, key in MODEL_MAP:
        if pat.search(s or ""):
            return key
    return None


def map_gpu(s):
    for pat, key in GPU_MAP:
        if pat.search(s or ""):
            return key
    return None


def pick(d, keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def walk(obj, out, ctx=None):
    """递归找「模型+GPU+吞吐」记录。ctx 携带外层上下文（如列表外的 model/gpu 字段）。"""
    ctx = dict(ctx or {})
    if isinstance(obj, dict):
        m = pick(obj, MODEL_KEYS)
        g = pick(obj, GPU_KEYS)
        t = pick(obj, TPS_KEYS)
        new_ctx = dict(ctx)
        if m:
            new_ctx["model"] = m
        if g:
            new_ctx["gpu"] = g
        if t is not None and (new_ctx.get("model") or m) and (new_ctx.get("gpu") or g):
            out.append({
                "model_raw": str(new_ctx.get("model") or m),
                "gpu_raw": str(new_ctx.get("gpu") or g),
                "tps": t,
                "conc": pick(obj, CONC_KEYS),
                "ttft": pick(obj, TTFT_KEYS),
                "quant": obj.get("quant") or obj.get("precision") or obj.get("dtype"),
                "framework": obj.get("framework") or obj.get("engine"),
            })
        for v in obj.values():
            walk(v, out, new_ctx)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, out, ctx)


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    api_status = {"base": API_BASE, "tried": [], "found": []}
    found_rows = []

    for path in CANDIDATES:
        url = API_BASE + path
        api_status["tried"].append(path or "/")
        try:
            status, body = fetch(url)
        except Exception as e:
            print(f"  {url} -> {type(e).__name__}: {e}", file=sys.stderr)
            continue
        ctype_ok = body[:1] in (b"{", b"[")
        if status != 200 or not ctype_ok:
            print(f"  {url} -> HTTP {status}（跳过）", file=sys.stderr)
            continue
        try:
            data = json.loads(body)
        except Exception:
            continue
        # 原始响应落盘：API 结构迭代探明的依据
        safe = (path or "root").strip("/").replace("/", "_") or "root"
        with open(os.path.join(RAW_DIR, f"{safe}.json"), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        api_status["found"].append(path or "/")
        walk(data, found_rows)
        print(f"  {url} -> OK，累计抽取 {len(found_rows)} 条候选")

    # 归一化 + 只留目标模型
    measured = {}
    for r in found_rows:
        mk, gk = map_model(r["model_raw"]), map_gpu(r["gpu_raw"])
        if not mk or not gk:
            continue
        try:
            tps = float(r["tps"])
        except (TypeError, ValueError):
            continue
        if tps <= 0:
            continue
        measured[(mk, gk)] = {
            "model_key": mk, "model": r["model_raw"], "inferencex_model": r["model_raw"],
            "gpu": gk, "gpus": 8,
            "quant": r.get("quant") or "", "framework": r.get("framework") or "",
            "isl": 0, "osl": 0, "conc": r.get("conc") or 0,
            "output_tps": round(tps, 1),
            "input_tps": 0,
            "ttft_s": r.get("ttft") or 0,
            "measured": True,
            "src": "InferenceX API 实测（inferencex.semianalysis.com）",
            "date": datetime.now().date().isoformat(),
        }

    # 输出 API 实测条目（种子锚点在 build_gpu_roi.py 里合并，这里不重复）
    entries = sorted(measured.values(), key=lambda e: (e["model_key"], e["gpu"]))
    payload = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "api": api_status,
        "entries": entries,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print(f"[inferencex] API 实测 {len(entries)} 条 -> {os.path.relpath(OUT, ROOT)}")
    if not entries:
        print("  提示：API 未抽到目标模型数据（结构可能未探明），本次仅种子/本地实测支撑页面。"
              "原始响应见 data/inferencex_raw/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # 任何异常都不阻塞流水线：种子数据仍可支撑页面
        print(f"[inferencex] 采集失败（沿用种子数据）: {e}", file=sys.stderr)
        sys.exit(0)
