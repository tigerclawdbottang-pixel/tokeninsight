#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地 InferenceX 实测数据抽取器
==============================
解析本地 InferenceX 克隆 experimental/token_position_decode_slo/ 下各模型的
results/*.json（vLLM benchmark 输出，8×H200），归一化成测点表写入
data/gpu_perf_local.json —— 提交进仓库后 GitHub Actions 可直接使用
（本地克隆本身不进 Actions，这份抽取结果就是它的固化快照）。

用法：
    python3 scripts/extract_inferencex_local.py
    INFERENCEX_DIR=/path/to/InferenceX python3 scripts/extract_inferencex_local.py
"""
import glob
import json
import os
import re
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "gpu_perf_local.json")
INFX = os.environ.get(
    "INFERENCEX_DIR",
    os.path.expanduser("~/WorkBuddy/2026-11-02-18-11-54/InferenceX"))
SLO_DIR = os.path.join(INFX, "experimental", "token_position_decode_slo")

# 目录名 → (model_key, 展示名, price_key, 价格备注)
# price_key 指向比价数据中的 loose：同型直接对，无同型用最近旗舰代理并注明
MODEL_DIRS = {
    "glm-5":       ("glm53", "GLM 5.3", "glm53", ""),
    "minimax-m2.5": ("minimaxm25", "MiniMax M2.5", "minimaxm25", ""),
    "qwen3.5":     ("qwen35397b", "Qwen3.5 397B", "qwen38max", "价格以 Qwen3.8 Max 代理"),
}
# 文件名： <name>_vllm_<parallel>_isl<INT>_osl<INT>_conc<INT>.json
FNAME = re.compile(r"_isl(\d+)_osl(\d+)_conc(\d+)\.json$")
PARALLEL = re.compile(r"_vllm_([a-z]+\d+)")


def main():
    if not os.path.isdir(SLO_DIR):
        print(f"[local-infx] 未找到 {SLO_DIR}（设 INFERENCEX_DIR 指向本地克隆）", file=sys.stderr)
        return 1
    rows = []
    for d, (mkey, mname, pkey, pnote) in MODEL_DIRS.items():
        files = glob.glob(os.path.join(SLO_DIR, d, "results", "*.json"))
        ok = 0
        for fp in sorted(files):
            base = os.path.basename(fp)
            m = FNAME.search(base)
            if not m:
                continue
            try:
                j = json.load(open(fp))
            except Exception:
                continue
            isl, osl, conc = int(m.group(1)), int(m.group(2)), int(m.group(3))
            out_tps = j.get("output_throughput")
            if not out_tps:
                continue
            par = PARALLEL.search(base)
            rows.append({
                "model_key": mkey, "model": mname,
                "price_key": pkey, "price_note": pnote,
                "inferencex_model": j.get("model_id") or "",
                "gpu": "h200", "gpus": 8,
                "quant": "FP8" if "fp8" in base else "",
                "framework": f"vLLM {par.group(1).upper() if par else ''}".strip(),
                "parallel": par.group(1) if par else "",
                "isl": isl, "osl": osl, "conc": conc,
                "input_tps": round(j.get("input_throughput") or 0, 1),
                "output_tps": round(out_tps, 1),
                "ttft_s": round(j.get("median_ttft") or 0, 4),
                "tpot_s": round(j.get("median_tpot") or 0, 5),
                "measured": True,
                "src": f"InferenceX 本地实测 experimental/{d}（8×H200 vLLM）",
                "date": (j.get("date") or "")[:8],
            })
            ok += 1
        print(f"  {d}: {ok}/{len(files)} 条")
    payload = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "source_dir": os.path.relpath(SLO_DIR, os.path.expanduser("~")),
        "gpu": "NVIDIA H200 141GB × 8",
        "entries": rows,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print(f"[local-infx] 共 {len(rows)} 个实测测点 -> {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
