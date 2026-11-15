# GPU 收益测算 · 业务逻辑与数据源文档

> 页面位置：主站 tab「GPU 收益测算」（GPU 资源池之后）；独立页 `web/gpu_roi.html` 同源生成。
> 数据组装：`scripts/build_gpu_roi.py`（`build_payload()`，独立页与主站 tab 共用同一份数据包 `D.roi`）。
> 最后更新：2026-11-16。

## 1. 页面回答的业务问题

> **今天，我能纳管到的 GPU 现货，部署哪些主力模型，每台 8 卡主机每天能赚多少钱？**

面向 GPU 租赁/算力转手业务：左手的成本是「当日可租到的 GPU 现货价」，右手的收入是「按市场挂牌价卖出模型 token」，中间的桥梁是「InferenceX 实测的部署性能/成本」。页面把三条真实数据流合成一张表，让「哪台机器、跑哪个模型、有多少毛利空间」可以当日决策。

**铁律：全部真实数据，不做推算/外推。** 没有实测的组合不编造数字，宁可留空标注「待实测」。（2026-11-15 用户明确推翻了早期的 GPU 系数外推方案。）

## 2. 数据源

### 2.1 GPU 现货（成本侧）—— `data/gpu_snapshot.json`

- **来源**：gpu-radar 项目（`~/Documents/TAI/gpu-radar`）的 SQLite 库，`scripts/collect_gpu.py` 导出快照。
- **内容**：各云平台（Vast.ai / RunPod / TensorDock / Lambda / Orca / Paperspace / Crusoe / AWS / Azure / GCP / FluidStack）的实例报价、库存、地区、直达链接。
- **字段口径（2026-11-15 修正过的坑）**：
  - `price_per_hour` 是**整机实例价**——必须 ÷ `gpu_count` 归一化成 $/卡·h（AWS p5.48xlarge $100.93/h = 8×H100 整机，即 $12.6/卡·h，曾误当单卡价导致 TCO 虚高 8 倍）。
  - `available_stock` 是**台数（实例数）**，不是卡数；卡数 = Σ（台数 × 每台 gpu_count）。页面所有现货数字按「台 / 卡」双口径显示。
  - `nodes8` = 8 卡整机当量（gpu_count≥8 的实例按 gpu_count//8 折算），只有它能跑大模型。
- **聚合**（`gpu_market()`）：按型号归一化（H100/H200/B200/B300/A100），取 8 卡整机池中的最低 $/卡·h 作为 TCO 基准，保留按平台分解（台数/卡数/单卡价）供悬停浮层。
- **更新频率**：定时任务 `daily-gpu-snapshot`（每天 08:20 本地）自动采集重建提交；或手动 `python3 scripts/collect_gpu.py`。

### 2.2 性能与实测成本（产能侧）—— 三个文件

| 文件 | 内容 | 来源 | 更新 |
|---|---|---|---|
| `data/inferencex_cost.json` | InferenceX 官方发布的**成本矩阵**：模型×平台的实测成本 $/百万总 token（AgentX 加权负载），含部署配置与 30-60 天趋势 | inferencex.semianalysis.com/zh/overview（2026-11-13 价，11-15 抓取录入） | 手工快照 |
| `data/inferencex_throughput.json` | InferenceX /inference 页逐配置**实测吞吐** tok/s/卡（含并发、P90 交互性、框架、精度、运行 URL） | 用户导出的 interactivity CSV，`scripts/import_inferencex_throughput.py` 导入 | 手工喂 CSV；API 打通后可自动 |
| `data/gpu_perf_local.json` | 本地 InferenceX 克隆 experimental 目录 **169 点实测**（8×H200 vLLM：GLM-5 / MiniMax-M2.5 / Qwen3.5-397B，2026-02 测） | `scripts/extract_inferencex_local.py` 一次性固化 | 固定快照 |

**成本矩阵负载口径（AgentX）**：缓存输入 97.5% / 未缓存输入 2.0% / 输出 0.5%（Qwen3.8 Next 为 94.5/4.7/0.8）。成本和价格必须同一负载口径才能相减——这是全页最关键的口径纪律。

**禁止的推导**（已写入数据文件边界声明）：
- 不用 `tok/$` 或「成本基准≈现货租价」反推产能——验算证伪过（DeepSeek 会推出 133 万 tok/s/卡，超 B200 HBM 带宽物理上限）。
- 不做跨 GPU 的带宽/算力系数外推（早期方案，已废弃）。

### 2.3 模型售价（收入侧）—— 本站每日比价 `web/data.json`

- **来源**：`scripts/collect.py` 每日两次采集（GitHub Actions，UTC 00:00/12:00）：OpenRouter、Fireworks、Wokey、CheaperInference、硅基流动、String、Venice、NEAR。
- **定价锚**：**OpenRouter 加权价**为市场实际值（缺失时静默回退中位价）；**官方价仅作参考列**。
- **AgentX 加权价**（与成本矩阵同负载，$/百万总 token）：
  `价 = 0.975 × 缓存读价 + 0.02 × 输入价 + 0.005 × 输出价`（无缓存价的源按输入价计）。
  已交叉验证：Kimi K3.1 Pro 按此式算 OpenRouter 加权 0.285 vs 官方加权 0.284，吻合。
- **价格代理**：无同型比价组的模型用最近旗舰代理并在页面注明（当前：Qwen3.5 397B → Qwen3.8 Max）。

## 3. 行生成逻辑（三源合流）

每行 = 模型 × GPU 平台，**只列有纳管现货的平台**（无现货整行不列）。三段并集：

- **A. 成本矩阵行**：InferenceX 成本矩阵中有该 模型×平台 的成本 → 带实测成本 $/M、配置、成本趋势；若同时有实测吞吐 → 绝对经济列全填。
- **B. 吞吐实测行**：CSV 实测吞吐 × 现货，成本矩阵未覆盖的 模型×平台（如 H100/H200 上的 DeepSeek/MiniMax/Qwen3.8FN）。
- **C. 本地实测行**：本地 169 点（全新鲜负载，0% 缓存）× 现货，覆盖 A/B 没有的模型（当前 MiniMax M2.5）。**负载口径不同，不与 A/B 的 $/M 列混算**（只给绝对经济列）。

过滤规则：`EXCLUDED_MODELS`（当前 qwen35397b，2026-11-15 用户确认非目标，数据保留可恢复）；显存装不下的组合不列（`MODEL_VRAM_GB` = 权重 FP8 × 1.15 含 KV）。

## 4. 每列定义与公式

| 列 | 定义 | 公式 / 来源 |
|---|---|---|
| 实测吞吐 | 单卡实测总吞吐（AgentX 负载） | InferenceX CSV `Throughput/Chip (tok/s)`，同组取最高配置；悬停见并发/P90/日期 |
| 实测成本 $/M | 每百万总 token 全包部署成本 | InferenceX overview 发布值 |
| 价格 $/M | 市场售价（OpenRouter 锚） | AgentX 加权（见 2.3） |
| 官方价（参考） | 厂商官方同负载加权价 | InferenceX overview 发布值 |
| 毛利 $/M | 每百万 token 价差 | 价格 − 实测成本 |
| 倍率 | 价差倍数 | 价格 ÷ 实测成本 |
| 成本趋势 | 30-60 天成本变化 | InferenceX 发布值（↓ 为降） |
| 现货 | 纳管量与最低价 | 台 / 卡 双口径；悬停看平台分解 |
| 日 TCO | 单台 8 卡主机日租金 | 最低 $/卡·h × 24 × 8（真实现货价） |
| 日收入 | 单台日售 token 收入 | 实测 tok/s/卡 × 86400 × 8 × 利用率 × 价格 $/M ÷ 1M |
| 日利润 | | 日收入 − 日 TCO |
| ROI | | 日利润 ÷ 日 TCO（与卡数无关） |
| 保本日产量 | 达到即保本的付费量 | 日 TCO ÷ 价格（M token/天，纯真实数字） |

**利用率滑块**（默认 60%）：只作用于日收入（租金 24 小时照付，TCO 不动）。保本利用率 = 1 ÷ 倍率。

**配色**：红 = 盈利/正数/成本下降（中文财经惯例），绿 = 亏损/负数；仅在 `#p-gpuroi` 作用域内反转，主站其他页保持绿涨红跌。

## 5. 更新链路

```
每日自动（无需人工）：
  GitHub Actions collect.yml/pages.yml（UTC 00:00/12:00）
    → collect.py 采集八源价格 → collect_inferencex.py 探 API → build_site.py 重建部署

每日自动（本机定时任务 08:20，daily-gpu-snapshot）：
  gpu-radar 单轮采集（backend/scripts/collect_once.py）
    → collect_gpu.py 导出快照 → 重建 → commit → push（推送前自动 rebase 远端）

手工喂（拿到新数据时）：
  吞吐 CSV   → python3 scripts/import_inferencex_throughput.py <csv...>
  成本矩阵   → 更新 data/inferencex_cost.json（参照现有结构）
  本地实测   → INFERENCEX_DIR=<克隆路径> python3 scripts/extract_inferencex_local.py
```

沙箱/CI 说明：公开站构建不含 AI 密钥（`MODELPRICE_EMBED_KEY=0`）；沙箱内 git push 无凭据，需本机执行；Actions 机器人在 main 上有每日提交，本地推送前必须先 `git pull --rebase`（生成物冲突取本地版，rebase 期间 ours/theirs 方向反转）。

## 6. 维护指南

**加一个新模型**，四处对齐：
1. `extract_inferencex_local.py` 的 `MODEL_DIRS`（本地实测目录 → model_key）
2. `collect_inferencex.py` 的 `MODEL_MAP`（API 模型名正则）
3. `build_gpu_roi.py` 的 `ROI_MODEL_KEYS` + `MODEL_VRAM_GB`（显存门槛）+ 必要时 `PRICE_PROXY`
4. `import_inferencex_throughput.py` 的 `MODEL_MAP`（CSV 模型名）

**加 GPU 平台**：`GPU_NORM` 加型号正则；InferenceX 平台 id 加进 `import_inferencex_throughput.py` 的 `PLAT_MAP` 和 `STOCKED`。

**下架模型**：加进 `EXCLUDED_MODELS`（数据保留，随时恢复）。

**独立页与主站 tab 的关系**：同一份 `build_payload()` 数据包；独立页 `gpu_roi.html` 自包含单文件，主站 tab 走 `D.roi`。改业务逻辑只改 `build_gpu_roi.py` 的数据组装 + `web/roi.js` / `web/gpu_roi_template.html` 两份渲染（注意保持同步——历史遗留：两处的行生成逻辑是平行实现）。

## 7. 已验证的口径自洽点

- OpenRouter 加权价 vs 官方加权价：K3.1 Pro 0.285 vs 0.284 ✓
- 我方倍率 vs InferenceX 自标倍率：K3.1P@B300 ×5.4 = ×5.4 ✓；Qwen3.5 AgentX ×44.8 ≈ 官方 ×45 ✓
- 现货价归一化：AWS 8×H100 $100.93/h ÷8 = $12.6/卡·h，与 AWS 官方 p5 定价吻合 ✓
- GLM×H200 实测满产 547M tok/天 < 保本量 6,196M tok/天，与其负 ROI 自洽 ✓

## 8. 当前数据边界（如实）

- 现货为 gpu-radar 快照，非实时撮合；价格是该平台可下单广告价。
- 成本矩阵为 2026-11-13 价格口径的 InferenceX 发布值，其 TCO 基准可能低于本站现货价（长约/批量），倍率视为上限参考。
- AgentX 加权假设 97.5% 缓存命中，与实际流量结构有出入时，$/M 列按比例失真；绝对列（实测吞吐×直接价）不受影响。
- 模型授权成本、带宽/存储/运维、获客折扣均未计入。
