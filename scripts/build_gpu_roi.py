#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU 收益测算页生成器 v3（build_site.py 附属模块）
================================================
三源合一，全部真实数据、不做推算：
  1. GPU 现货：data/gpu_snapshot.json（gpu-radar 纳管的平台实时报价/库存）
  2. 性能实测：data/gpu_perf_local.json（本地 169 点，8×H200）
               + data/gpu_perf.json（InferenceX API 每日实测，Actions 抓）
  3. 售价：本站每日比价（第三方工厂实际值 / 官网参考值）

组合 = 模型 × GPU 型号，仅当三者都齐备才出现：
  该 GPU 有实测性能点 ∧ 该 GPU 有现货报价 ∧ 显存装得下该模型

经济口径（节点 = 8 卡）：
  收入$/卡·h = 3600 × (输入tps/卡×入价 + 输出tps/卡×出价) / 1e6
  日TCO = 市场最低租价 × 24 × 8；日利润 = 日收入 − 日TCO
  ROI = 日利润 / 日TCO；毛利率 =（保本租价 − 市场租价）/ 保本租价
"""
import json
import os
import re
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GPU_PERF_JSON = os.path.join(ROOT, "data", "gpu_perf.json")
GPU_PERF_LOCAL_JSON = os.path.join(ROOT, "data", "gpu_perf_local.json")
GPU_SNAPSHOT_JSON = os.path.join(ROOT, "data", "gpu_snapshot.json")
INFX_COST_JSON = os.path.join(ROOT, "data", "inferencex_cost.json")  # InferenceX overview 实测成本矩阵
INFX_TPUT_JSON = os.path.join(ROOT, "data", "inferencex_throughput.json")  # InferenceX 实测 tok/s（按模型×平台）
ROI_TPL = os.path.join(ROOT, "web", "gpu_roi_template.html")
ROI_OUT = os.path.join(ROOT, "web", "gpu_roi.html")

ROI_MODEL_KEYS = ["glm53", "deepseekv4pro", "deepseekv41flash", "kimik3", "kimik31pro",
                  "minimaxm31flash", "minimaxm25", "qwen38max", "qwen35397b", "qwen38flashnext"]

# 无同型比价组的模型 → 代理价格键（与 extract_inferencex_local.MODEL_DIRS 的 price_key 一致）
PRICE_PROXY = {"qwen35397b": "qwen38max"}

# 暂不展示的模型（用户确认非目标：Qwen3.5 397B 2026-11-15 移除，数据保留，随时可加回）
EXCLUDED_MODELS = {"qwen35397b"}

# 每模型 FP8 部署所需最小整机显存（GB，8 卡合计 = 权重×1.15 含 KV）
MODEL_VRAM_GB = {
    "glm53": 410, "minimaxm25": 265, "qwen35397b": 460, "minimaxm31flash": 150,
    "qwen38max": 550, "deepseekv4pro": 770, "kimik3": 1100, "kimik31pro": 1100,
}

# 现货清单 GPU 型号名 → 归一化 id
GPU_NORM = [
    (re.compile(r"H100", re.I), "h100", "NVIDIA H100 80GB", 80),
    (re.compile(r"H200", re.I), "h200", "NVIDIA H200 141GB", 141),
    (re.compile(r"B300", re.I), "b300", "NVIDIA B300 288GB", 288),
    (re.compile(r"B200", re.I), "b200", "NVIDIA B200 180GB", 180),
    (re.compile(r"A100", re.I), "a100", "NVIDIA A100 80GB", 80),
]

REP_POINT = (2048, 128, 32)  # 代表工作点 (isl, osl, conc)


def roi_prices(models):
    """目标模型价格：第三方工厂实际值（最低/中位）+ 官网参考。"""
    out = {}
    for key in ROI_MODEL_KEYS:
        m = next((x for x in models if x["loose"] == key), None)
        if not m:
            continue
        offers = []
        for src, p in (m.get("prices") or {}).items():
            if p.get("input") is not None and p.get("output") is not None:
                offers.append((src, float(p["input"]), float(p["output"])))
        if not offers:
            continue
        offers.sort(key=lambda t: t[2])
        lo, mid = offers[0], offers[len(offers) // 2]
        out[key] = {"name": m["name"],
                    "median": {"src": mid[0], "input": mid[1], "output": mid[2]},
                    "n_sources": len(offers)}
        orp = (m.get("prices") or {}).get("openrouter")
        if orp and orp.get("input") is not None and orp.get("output") is not None:
            out[key]["or"] = {"input": float(orp["input"]), "output": float(orp["output"])}
        off = m.get("official")
        if off and off.get("output") is not None:
            out[key]["official"] = {"input": off.get("input"), "output": off.get("output")}
    return out


def weighted_prices(models, mix):
    """按 InferenceX AgentX 负载（97.5% 缓存输入 + 2% 未缓存 + 0.5% 输出）
    计算目标模型的第三方加权价（$/百万总 token），取最低/中位。"""
    wc, wi, wo = mix["cache"], mix["input"], mix["output"]
    out = {}
    for key in ROI_MODEL_KEYS:
        m = next((x for x in models if x["loose"] == key), None)
        if not m and key in PRICE_PROXY:  # 无同型组 → 代理（页面已注明）
            m = next((x for x in models if x["loose"] == PRICE_PROXY[key]), None)
        if not m:
            continue
        ws = []
        for src, p in (m.get("prices") or {}).items():
            i, o = p.get("input"), p.get("output")
            if i is None or o is None:
                continue
            cr = p.get("cache_read")
            w = wc * (cr if cr is not None else i) + wi * i + wo * o
            ws.append((w, src, cr is not None))
        if not ws:
            continue
        ws.sort()
        out[key] = {"min": {"v": round(ws[0][0], 4), "src": ws[0][1], "has_cache": ws[0][2]},
                    "med": {"v": round(ws[len(ws) // 2][0], 4), "src": ws[len(ws) // 2][1]},
                    "n_sources": len(ws)}
        orw = next((w for w in ws if w[1] == "openrouter"), None)
        if orw:
            out[key]["or"] = {"v": round(orw[0], 4), "has_cache": orw[2]}
    return out


def gpu_market(snapshot):
    """现货清单按归一化 GPU 聚合。
    口径：price_per_hour 为整机实例价 → 归一化 $/卡·h（÷gpu_count）；
          available_stock 为台数（实例数），卡数 = Σ台数×每台 gpu_count；
          nodes8 = 8 卡整机当量（gpu_count>=8 的实例按 gpu_count//8 折算）；
          min_price = 8 卡整机（gpu_count>=8）中的最低 $/卡·h。"""
    groups = {}
    for l in (snapshot or {}).get("listings") or []:
        name = l.get("gpu_model") or ""
        hit = next(((p, g, n, v) for p, g, n, v in GPU_NORM if p.search(name)), None)
        if not hit:
            continue
        _, gid, gname, vram = hit
        g = groups.setdefault(gid, {"id": gid, "name": gname, "vram_gb": vram, "rows": []})
        if l.get("price_per_hour"):
            g["rows"].append(l)
    out = {}
    for gid, g in groups.items():
        norm = []
        for r in g["rows"]:
            gc = r.get("gpu_count") or 1
            norm.append(dict(r, price_card=r["price_per_hour"] / gc))
        eight = [r for r in norm if (r.get("gpu_count") or 1) >= 8]
        pool = eight or norm
        best = min(pool, key=lambda r: r["price_card"])
        prices = sorted(r["price_card"] for r in norm)
        cards = sum((r.get("gpu_count") or 1) * (r.get("available_stock") or 0) for r in norm)
        nodes = sum(r.get("available_stock") or 0 for r in norm)
        nodes8 = sum((r.get("available_stock") or 0) * ((r.get("gpu_count") or 1) // 8) for r in norm)
        byp = {}
        for r in norm:
            pn = r.get("platform") or "?"
            d = byp.setdefault(pn, {"platform": pn, "nodes": 0, "cards": 0, "min_price": None, "url": None})
            stk = r.get("available_stock") or 0
            d["nodes"] += stk
            d["cards"] += (r.get("gpu_count") or 1) * stk
            if d["min_price"] is None or r["price_card"] < d["min_price"]:
                d["min_price"] = r["price_card"]
                d["url"] = r.get("direct_url")
        out[gid] = {
            "id": gid, "name": g["name"], "vram_gb": g["vram_gb"],
            "min_price": round(best["price_card"], 4),
            "min_platform": best.get("platform"),
            "med_price": round(prices[len(prices) // 2], 4),
            "stock": nodes, "stock_cards": cards, "nodes8": nodes8,
            "n_listings": len(norm), "platforms": sorted(byp),
            "by_platform": sorted(byp.values(), key=lambda x: x["min_price"]),
        }
    return out


def pick_anchor(points):
    """某 (模型,GPU) 的实测点里挑代表工作点：最接近 (isl2048,osl128,conc32)，同距取吞吐最高。"""
    import math
    ti, to, tc = REP_POINT

    def dist(e):
        return (abs(math.log2((e["isl"] or ti) / ti))
                + abs(math.log2((e["conc"] or tc) / tc))
                + abs((e["osl"] or to) - to) / 128)
    return sorted(points, key=lambda e: (dist(e), -e["output_tps"]))[0]


def build_combos(local_entries, api_entries, market):
    """实测点 × 现货报价 交集组合。无实测或无报价的 (模型,GPU) 不出现。"""
    by_pair = {}
    for e in (local_entries or []) + (api_entries or []):
        gid = e.get("gpu")
        if gid in market:
            by_pair.setdefault((e["model_key"], gid), []).append(e)
    combos = []
    for (mk, gid), pts in sorted(by_pair.items()):
        need = pts[0].get("min_vram_gb") or MODEL_VRAM_GB.get(mk)
        g = market[gid]
        if need and g["vram_gb"] * 8 < need:
            continue  # 显存装不下
        a = pick_anchor(pts)
        combos.append({
            "model_key": mk, "model": a["model"],
            "price_key": a.get("price_key") or mk,
            "price_note": a.get("price_note") or "",
            "gpu": gid, "gpu_name": g["name"], "gpus": a.get("gpus") or 8,
            "quant": a.get("quant") or "", "framework": a.get("framework") or "",
            "isl": a.get("isl"), "osl": a.get("osl"), "conc": a.get("conc"),
            "input_tps": a.get("input_tps") or 0, "output_tps": a.get("output_tps") or 0,
            "ttft_s": a.get("ttft_s") or 0, "tpot_s": a.get("tpot_s") or 0,
            "n_points": len(pts),
            "rent_min": g["min_price"], "rent_platform": g["min_platform"],
            "rent_med": g["med_price"], "stock": g["stock"], "stock_cards": g["stock_cards"],
            "measured": True, "src": a.get("src") or "InferenceX 实测",
        })
    return combos


def _load(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:
        print(f"  ROI：{os.path.basename(path)} 读取失败 {e}", file=sys.stderr)
        return default


def build_payload(models):
    """组装 ROI 数据包（独立页与主站内嵌 tab 共用）。无现货快照时 market 为空。"""
    local_entries = (_load(GPU_PERF_LOCAL_JSON, {}) or {}).get("entries", [])
    api_perf = _load(GPU_PERF_JSON, {}) or {}
    market = gpu_market(_load(GPU_SNAPSHOT_JSON, {}) or {})
    combos = [c for c in build_combos(local_entries, api_perf.get("entries", []), market)
              if c["model_key"] not in EXCLUDED_MODELS]
    covered = {c["gpu"] for c in combos}
    waiting = [{"gpu": g["name"], "stock": g["stock"], "min_price": g["min_price"]}
               for gid, g in sorted(market.items()) if gid not in covered]
    payload = {"generated": datetime.now().isoformat(timespec="seconds"),
               "combos": combos,
               "market": list(market.values()), "waiting": waiting,
               "prices": roi_prices(models), "api": api_perf.get("api", {})}
    # InferenceX 官方发布的实测成本矩阵（AgentX 加权负载，$/百万总 token）
    cost = _load(INFX_COST_JSON, None)
    if cost:
        payload["cost"] = dict(cost, costs=[m for m in cost.get("costs", []) if m["model_key"] not in EXCLUDED_MODELS])
        payload["prices_w"] = weighted_prices(models, cost.get("mix") or {})
        # 现货挂靠：只有 b200/b300 在现货清单里
        cost_platforms = {pid for m in cost.get("costs", []) for pid in m.get("cells", {})}
        payload["cost_market"] = {gid: market[gid] for gid in cost_platforms if gid in market}
    # InferenceX 实测吞吐（按 模型×平台），用于有实测产能行的绝对经济列
    tput = _load(INFX_TPUT_JSON, None)
    if tput:
        payload["throughput"] = tput
    return payload, len(local_entries), len(combos), len(market), len(waiting)


def build(models, css):
    """生成 web/gpu_roi.html。缺模板跳过，不影响主站构建。"""
    if not os.path.exists(ROI_TPL):
        print("  ROI：缺 template，跳过", file=sys.stderr)
        return False
    tpl = open(ROI_TPL, encoding="utf-8").read()
    payload, n_local, n_combos, n_market, n_waiting = build_payload(models)
    data_js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</script>", r"<\/script>")
    def sub_once(s, token, val):
        i = s.find(token)
        return s if i < 0 else s[:i] + val + s[i + len(token):]
    html = sub_once(tpl, "/*__CSS__*/", css)
    html = sub_once(html, "/*__DATA__*/ null", data_js)
    with open(ROI_OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"生成 {ROI_OUT}  {os.path.getsize(ROI_OUT)/1024:.0f} KB (自包含) "
          f"| 实测点 {n_local} | 组合 {n_combos} 条（全部实测×现货交集）"
          f"| 现货 GPU {n_market} 种 | 待实测 {n_waiting} 种")
    return True

if __name__ == "__main__":
    d = json.load(open(os.path.join(ROOT, "web", "data.json"), encoding="utf-8"))
    css = open(os.path.join(ROOT, "web", "style.css"), encoding="utf-8").read()
    ok = build(d.get("models", []), css)
    sys.exit(0 if ok else 1)