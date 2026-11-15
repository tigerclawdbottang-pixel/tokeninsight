#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""InferenceX 实测吞吐导入器（interactivity CSV 版）
=================================================
输入：InferenceX /inference 页导出的 *_interactivity.csv（含 # 注释头、
     Throughput/Chip、Output/Input Throughput/Chip、P90 交互性等列）。
每个 模型×平台 保留吞吐最高的配置（仅最优口径），并入 data/inferencex_throughput.json。

用法：
  python3 scripts/import_inferencex_throughput.py file1.csv [file2.csv ...]
"""
import csv, io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "inferencex_throughput.json")

MODEL_MAP = [
    ("deepseek v4 1 flash", "deepseekv41flash"), ("deepseek v4 pro", "deepseekv4pro"),
    ("kimi k3 1 pro", "kimik31pro"), ("kimi k3", "kimik3"),
    ("glm 5 2", "glm53"), ("glm 5 3", "glm53"),
    ("minimax m3 1 flash", "minimaxm31flash"), ("minimax m2 5", "minimaxm25"),
    ("qwen3 5 397b", "qwen35397b"), ("qwen3 8 flash next", "qwen38flashnext"),
    ("qwen3 8 max", "qwen38max"),
]
PLAT_MAP = [
    (re.compile(r"^b300$", re.I), "b300"), (re.compile(r"^b200$", re.I), "b200"),
    (re.compile(r"^h200$", re.I), "h200"), (re.compile(r"^h100$", re.I), "h100"),
    (re.compile(r"^a100$", re.I), "a100"),
    (re.compile(r"mi355x", re.I), "mi355x"), (re.compile(r"gb300", re.I), "gb300"),
    (re.compile(r"gb200", re.I), "gb200"), (re.compile(r"vr200|rubin", re.I), "rubin"),
    (re.compile(r"mi325x", re.I), "mi325x"), (re.compile(r"mi300x", re.I), "mi300x"),
    (re.compile(r"tpuv7", re.I), "tpuv7"),
]
STOCKED = {"b200", "b300", "h100", "h200", "a100"}


def map_model(name):
    low = re.sub(r"[-_./]", " ", name or "").lower().strip()
    return next((k for pat, k in MODEL_MAP if pat in low), None)


def map_plat(hw):
    return next((g for pat, g in PLAT_MAP if pat.search(hw or "")), None)


def fnum(x):
    try:
        return float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def load_rows(path):
    raw = open(path, encoding="utf-8-sig").read()
    body = "\n".join(l for l in raw.splitlines() if not l.startswith("#"))
    out = []
    for r in csv.DictReader(io.StringIO(body)):
        tps = fnum(r.get("Throughput/Chip (tok/s)"))
        if tps is None:
            continue
        out.append({
            "model": r.get("Model"), "hw": r.get("Hardware"),
            "framework": r.get("Framework"), "prec": r.get("Precision"),
            "conc": fnum(r.get("Concurrency")), "date": r.get("Date"),
            "tps": tps,
            "out_tps": fnum(r.get("Output Throughput/Chip (tok/s)")),
            "in_tps": fnum(r.get("Input Throughput/Chip (tok/s)")),
            "p90": fnum(r.get("P90 交互性 (tok/s/user)")),
            "disagg": (r.get("Disaggregated") or "").lower() == "true",
            "spec": r.get("Spec Decoding") or "", "url": r.get("Run URL") or "",
        })
    return out


def main(paths):
    cur = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    bmp = cur.setdefault("by_model_platform", {})
    n_add = n_skip = 0
    for path in paths:
        for r in load_rows(path):
            mk, gid = map_model(r["model"]), map_plat(r["hw"])
            if not mk or not gid or gid not in STOCKED:
                n_skip += 1
                continue
            slot = bmp.setdefault(mk, {})
            if gid not in slot or r["tps"] > slot[gid]["tps"]:
                slot[gid] = {
                    "tps": round(r["tps"], 1), "m_h": round(r["tps"] * 3600 / 1e6, 2),
                    "out_tps": r["out_tps"], "in_tps": r["in_tps"],
                    "conc": r["conc"], "framework": r["framework"], "prec": r["prec"],
                    "p90_intvty": r["p90"], "disagg": r["disagg"], "spec": r["spec"],
                    "date": r["date"], "url": r["url"],
                }
                n_add += 1
    json.dump(cur, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"导入/更新 {n_add} 条（跳过 {n_skip} 条非目标/非现货平台）-> {os.path.relpath(OUT, ROOT)}")
    for mk, v in sorted(bmp.items()):
        print(f"  {mk}: " + ", ".join(f"{g} {x['tps']:,.0f} tok/s" for g, x in sorted(v.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
