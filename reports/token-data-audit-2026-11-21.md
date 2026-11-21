# Token 数据采集、单位与展示全链路审计

审计日期：2026-11-21  
范围：采集器、官网价采集、SQLite、每日快照、构建聚合、前端、上传比价、测试与 GitHub Actions。  
方式：逐行代码审查 + 当前数据库/快照全量核对 + 9 个源不落库实时试跑 + 5 个官网解析器实时抽查 + 项目测试与边界复现。

## 一、结论先行

### 1. 抓取逻辑是否正确、准确

**链路设计基本合理，但当前不能判定为准确。**

OpenRouter、Fireworks、Wokey、CheaperInference、硅基流动、String、Venice、NEAR 的常规解析可以运行，基础字段映射大部分正确；但 DeepInfra 实际未进入每日采集，String 存在重复键覆盖，旧来源参与聚合，阶梯价和缓存 TTL 被丢弃，CheaperInference 折扣字段不自洽。

### 2. 单位是否对齐

**基础数学单位大部分已对齐为 USD / 百万 tokens，但计价口径未完全对齐。**

未发现主站前端再次乘 1,000,000 的全局错误。当前主要问题不是“差 1000 倍”，而是：

- 基础档与长上下文阶梯价混在一起比较；
- 5 分钟与 1 小时缓存写入价统一写成“缓存写入”；
- 免费、未标价、字段缺失在部分路径都按 0 或空值处理；
- 折扣率、目录价、实际价来源和含义不统一；
- 各源数据日期不同，主表没有逐单元格标日期。

上传比价另有 `/1B tokens` 未识别和“7折”换算错误，确实会产生数量级错误。

### 3. 展现是否准确

**不准确。** 已确认历史走势、最低/最高列、版本数、过滤后的图表、CSV、折扣空值等存在错误或口径不一致；根目录与分发 HTML 的数据也不是同一版本。

**建议：当前主表仅作二级价格参考；不要直接用历史曲线、汇出 CSV、折扣列或上传分析做采购/定价决策，先修复下列高优先级问题。**

---

## 二、审计基线与正向结论

当前发布数据 `web/data.json`：

- 快照日期：2026-11-15；生成时间：2026-11-16 23:19:12。
- 1148 个模型组、1507 条当前展示源代表记录、发布物内 8 个来源。
- 数据库最新日期为 2026-11-15，Fireworks 最新可用数据停在 2026-11-14。
- 2026-11-15 快照 `rows.json` 有 1222 行，数据库同日和同范围入库后为 1218 行，差异来自 String 的 4 个重复键。
- 当前源码 `build_site.py` 声明 9 个来源，但现有发布物只有 8 个，源码与生成物不同步。

已验证的正确部分：

1. OpenRouter 的 `pricing.prompt/completion` 从 USD/token 乘 1,000,000，输入、输出、缓存读、缓存写分别处理，位置为 `scripts/collect.py:212-241`。
2. Fireworks 的 `inputTokenPrice/outputTokenPrice` 已是 USD/1M，直接读取；实时接口本次成功返回 319 个原始模型。
3. Wokey 当前全部 token SKU 的 `quantity` 都是 1,000,000，因此当前直接读取 `price_usd` 数值正确；图片 SKU 数量则为 1。
4. CheaperInference 的 `ourInputPerM/ourOutputPerM` 直接按 USD/1M 读取，没有重复换算。
5. 硅基流动参考站 USD/1M 直出；官网补充部分 CNY/1M 按汇率换算。本次实时结果为 41 条参考站数据 + 48 条官网补充，汇率 1 CNY = 0.149433 USD。
6. String、Venice、NEAR 原始表均是 USD/1M 口径；通用网关 `/1K` 到 `/1M` 的乘 1000 测试通过。
7. 构建后前端没有再次乘 1,000,000。
8. 每个源代表记录的其他价格字段来自同一个被选版本，没有把甲版本的 input 与乙版本的 output 拼成一条记录。
9. 按“每个源自己的最新日期”回溯数据库，1507 条发布代表记录均找得到同 `model_id` 的数据库版本。除构建时主动清掉的 13 条非文本 0/0 外，未检出 input/output 字段差异；cache、list、discount 字段未发现数值差异。
10. DeepSeek 与 Z.AI 官网实时解析样本正常；DeepSeek 得到 V4.1 Flash 0.66/1.98、V4 Pro 1.32/3.96 USD/1M，Z.AI 得到 GLM-5.3 1.4/4.4、缓存读 0.26。

注意：以上“发布与数据库一致”只证明搬运一致，不等于上游价格本身真实或计价条件完整。

---

## 三、高优先级问题

### H1. 输出、缓存、官方原价走势全部错误地使用输入价

- `scripts/build_site.py:469-478` 虽查询 input/output/cache_read/list_input，最终却只保存 `input` 一个值。
- `web/app.js:286-313` 的 `histVal()` 不区分指标，切换指标只改变纵轴标签。
- 实测 `qwen/qwen3.5-9b`：
  - 2026-11-14：input 0.17，output 0.25，cache_read 0.153；
  - 2026-11-15：input 0.042，output 0.062，cache_read 0.038；
  - 页面三种指标的历史序列都只有 0.17 → 0.042。

**影响：非输入指标的走势图、涨跌提示全部失真。**

### H2. DeepInfra 实际不进入每日采集，专用解析又只保留 1 个模型

- `scripts/collect.py:1077-1080` 在主注册 DeepInfra 之前直接执行并退出 `main()`。
- DeepInfra 到 `scripts/collect.py:1170-1173` 才注册，因此直接执行 `python3 scripts/collect.py` 时不会采集。
- 源一致性测试导入模块时不执行 `main()`，反而能看到已注册的 DeepInfra，所以测试通过掩盖了真实执行路径。
- `scripts/collect.py:1080-1105` 使用“首个非空解析即成功”策略。本次实时：
  - `/models`：94 万字节页面仅解析到 `Qwen/Qwen3-TTS` 1 条；
  - `/pricing`：37 张表、通用表格可提出 179 行，但因为 `/models` 已返回 1 条，不再尝试。
- `/pricing` 提取样本还出现 `DeepSeek-V4.1-Flash-101751% off` 模型名污染、output 缺失。

**影响：源列表看似完整，实际没有可靠的 DeepInfra 全量数据。**

### H3. String 同 ID 多渠道互相覆盖，当前已发生高价覆盖低价

- `scripts/collect.py:670-687` 只用小写 `model_id` 标识记录，渠道 `source_name` 只放在 provider。
- 数据库唯一键是 `(snapshot_date, source, model_id)`，见 `scripts/collect.py:916-939`；`INSERT OR REPLACE` 令后写记录覆盖先写记录。
- 当前快照 40 条 String 记录入库后只剩 36 条，4 组重复：
  - `gemini-3.8-flash`：Gemini 0.60/3.00，Gemini Vertex 1.575/7.875；页面展示后者。
  - `gemini-4-carbon`：Gemini 1.60/8.00，Gemini Vertex 4.20/21.00；页面展示后者。
  - 另有 `gemini-4-argon`、`gemini-4-hydrogen` 同样被覆盖。
- 发布时每组只剩 1 个版本，渠道信息无法追溯，采集状态却仍报 kept=40。

**影响：当前页面存在确定性数值偏差与数据丢失，而不是仅有潜在风险。**

### H4. 旧来源 `openrouter_providers` 污染模型组与版本数

- `scripts/build_site.py:312-338` 对数据库中所有来源取“各自最新日期”，没有先过滤到当前 `SOURCES`。
- 数据库仍有 2026-11-14 的 `openrouter_providers` 1261 行，但前端来源列表不包含它。
- 当前发布数据实测：
  - 1148 个模型组中，**101 个 `n_src=0`、prices 为空**，主要由旧来源生成；
  - 实际有当前报价的模型组为 1047 个；
  - **433 个模型的 `n_ver` 大于页面各当前来源版本数之和**。
- 例：DeepSeek V4.1 Flash 1017 显示 `n_ver=78`，当前可见版本实际为 12。

**影响：模型总数、版本数、分组聚合及后续匹配可信度均受影响。**

### H5. 长上下文阶梯价与缓存 TTL 条件被丢弃

String：

- 原始 API 当前有 **14 行含 `intervals`**，`string_row()` 只读顶层 effective 字段，完全忽略 intervals，见 `scripts/collect.py:653-688`。
- 例：`gpt-6.2-astra` 基准档 effective input/output 为 1.6/8；超过 272K tokens 为 3.2/16。页面只显示 1.6/8，未标上下文范围。
- 多个 Claude/Kimi 行同时有 5 分钟和 1 小时缓存写价，只保留一个通用 `cache_write`。

Wokey：

- 当前原始 SKU 同时有 `cache_write_tokens`、`cache_write_5m_tokens`、`cache_write_1h_tokens`，`scripts/collect.py:347-349` 只选一个值。
- 例：Claude Fable 5 当前 1h cache write 为 4.78，5m 为 2.9875，界面都笼统称“缓存写入”。

**影响：不同上下文、不同缓存 TTL 的价格被当成同口径直接比较。**

### H6. CheaperInference 实际价、目录价、折扣同时展示但不自洽

- `scripts/collect.py:435-452` 原样复制 `ourInputPerM/listInputPerM/discountPercent`。
- 当前发布代表记录有 **26 条**满足 `abs((1-input/list_input)*100-discount)>1.5`，全部来自 CheaperInference。
- 2026-11-21 实时原始数据仍有 **24 条**相同异常。
- 例：
  - DeepSeek V4.1 Flash：折后输入 0.0145，目录输入 0.15，页面折扣 45%；按两价格反算优惠为 90.33%。
  - DeepSeek V3.2：0.229 vs 0.62，标 35%，反算 63.06%。
  - 当前 GLM-5.3 发布记录：0.0003 vs 1.4，标 45%，反算约 99.98%。
- `scripts/verify.py:121-129` 能检测部分异常，但只生成警告，发布继续。

**边界：能确定三字段不自洽，不能仅凭仓库断定哪一个上游字段错。修复前不应直接展示为统一“折扣率”。**

### H7. 主表“最低 / 最高”在输出、缓存、折扣指标下仍显示输入价范围

- `web/app.js:234-235` 固定读取 `m.min_input/max_input`，不随 `S.metric` 改变。
- 例 DeepSeek V4.1 Flash 1017：
  - 输入范围为 0.0145–0.3；
  - 输出真实范围为 0.3–1.2；
  - cache_read 真实范围为 0.0015–0.01；
  - 切到输出或缓存指标时，最低/最高列仍是输入范围。
- `build_site.py` 已另有 `min_output/max_output`，但主表没有使用；缓存和折扣需单独计算。

**影响：用户按指标比较时，汇总列给出错误数值和错误单位语义。**

### H8. 每日复核把旧数据回退误报成 312 条“发布不一致”

- 发布端按各源最新有数据日期回退，见 `scripts/build_site.py:312-324`。
- 复核端却只查全局最新一天，见 `scripts/verify.py:90-119`。
- 当前 Fireworks 回退到 2026-11-14，312 条发布记录因此全部被误判为“页面有价但库中无对应记录”。
- 当前 `reports/latest.md` 的 328 条高优先级中，312 条是这一类假阳性。
- 按正确的逐源日期重新核对后，1507 条发布记录均能在对应源的最新数据库版本中找到。

**影响：真实异常被大量假阳性淹没，复核结果不能作为质量门禁。**

### H9. 上传比价“7折”被算成 0.07，且无表头价格回退会重组错误价格

- `web/app.js:654-668` 把“7折”和“70%”都除以 100。
- 页面内直接复现：7折→0.07、8折→0.08、9折→0.09、10折→0.1、95折→0.95、70%→0.7。
- 后续 `pickPrices()` 用目录价乘该系数，实际价格会被低估 10 倍。
- `web/parsers.js:255-265` 与 `web/app.js:714-727` 的无表头回退还复现为：
  - `0,0` → input/output 都为空；
  - `0,1` → input=1、output=空；
  - `2,2` → output=空；
  - `7,1` → 自动交换成 input=1、output=7。

**影响：上传报价及自动议价分析可能严重错误；不代表主站采集价被该问题回写。**

---

## 四、中优先级问题

### M1. 零值与“未知”语义混用

- String：`effective_value or base_value` 将真实 0 当缺值，见 `scripts/collect.py:661-665`；price_multiplier=0 也失去 100% 折扣，见 684 行。
- 已直接复现：effective 四项均为 0、基础价 2/4 时，采集结果错误变成 2/4、0.2/0.4、discount=None。
- Fireworks：`inputTokenPrice=0` 会回退 `tokenPrice`，见 `scripts/collect.py:257-263`，免费输入价可能被覆盖。
- Wokey：cache_write 使用 `or` 回退，0 同样被当缺值，见 348 行。
- 以上属于确定的代码边界错误；本次 String 实时数据未出现 effective_input=0，不能声称当前所有零价都已错。

### M2. 构建时统一清除非文本 0/0，可能误伤真实限免 token 模型

- `scripts/build_site.py:387-391` 对所有 `kind != 文本` 且 unit=token 的 0/0 统一置空。
- 当前共 13 条发布记录因此与数据库 input/output 不同，其中 6 条是向量/重排序，包括 SiliconFlow 的 BGE 与 reranker。
- 音频/图片按其他单位计费时清理可能合理，但向量、重排序的 token 限免不能靠类型统一判断。

### M3. OpenRouter / Fireworks 自身现价被标成“官方原价”

- `scripts/collect.py:235-237,301-303` 将自身现价同时赋给 `list_input/list_output`。
- `web/app.js:220-225` 又将 list_input 显示为“官方原价(输入)”。
- README 同时说明 OpenRouter / Fireworks 不提供官方原价，语义互相矛盾。
- “模型官网价格”列对 OpenRouter 回退有 OR 角标，做得较清楚；此处是版本/全指标区域的另一处标注问题。

### M4. 每源回退旧价但主表不带逐源日期

- 数据源页会写“今日失败，使用历史数据”，见 `web/app.js:1396-1419`，这是正向处理。
- 但主表、图表、CSV 均不显示该报价实际属于哪一天，只做总体 `D.latest` 标记。
- Fireworks 本次实时已经恢复，当前页面仍是 11 月 14 日旧价。
- 对一个源失败连续多日的情况，用户可能把旧价当作当日价。

### M5. 硅基流动混源与汇率说明不能逐行追溯

- 本次实时为 41 条 llmpricing.dev USD 直出 + 48 条官网 CNY 折算。
- 行记录没有保存 origin、原币种、原数值、汇率、档位，发布层无法区分两类记录。
- `build_site.py:112-123` 将整个硅基流动说明写成“人民币计价折算”，与 41 条直出记录不完全一致。
- 当前 `fx.json` 日期为 2026-11-16，晚于发布数据快照 2026-11-15，也没有足够信息证明它就是每行历史转换时实际使用的汇率。

### M6. 上传 `/1B tokens` 被按 `/1M` 处理，产生 1000 倍误差

- `web/llm.js:67-80` 的独立 `perFactor('1B')` 数学正确。
- 实际规则入口 `web/app.js:672-677` 不识别 1B；AI prompt / `normUnit()` 也未提供可靠的 1B 选项。
- 页面内复现：`readUnit('$1000 / 1B tokens')` 返回 per=null，按当前默认逻辑保持 1000 USD/1M；正确应为 1 USD/1M。
- 孤立数学函数测试通过，但真实入口没有测试覆盖。

### M7. 源筛选、可比源数、图表和 CSV 口径不一致

- `web/app.js:144-195` 的筛选只看全局 `n_src`，不看当前所选源中有几个有效报价。
- 只选 OpenRouter 且保留“≥2源”时，MiniMax-M2 仍显示，尽管其 OpenRouter 单元格为空。
- `web/app.js:51-54,352-440` 的 Top 图表/汇总卡/Top10 不使用搜索、地区、minSrc 等完整过滤条件，Top10 也不按当前源 chips 限定。
- `web/app.js:1505-1515` CSV 始终导出全部源，不遵循源 chips；也不沿用表格排序。
- CSV 缺少 `list_output`，详情缺少完整字段；当前 1094 条代表记录有非空 list_output，但主站全指标与 CSV均取不到该列。

### M8. 排序与折扣显示错误/误导

- 源列第一次按价格降序点击时，缺失值以 1e18 参与排序，null 排在最前，见 `web/app.js:145-162,199-204`。
- 主表 discount 使用 `v>0 ? ... : '—'`，0% 与负折扣均显示为无数据，见 `web/app.js:187-193`。
- 当前有 52 条代表记录 discount=0、17 条负折扣；详情页却会显示 0% 或负数，两个视图不一致。

### M9. 多份 HTML 数据时点不同

- 根目录 `index.html`：latest=2026-10-26，generated=2026-10-27。
- `dist/modelprice-local.html` 及两个分发 HTML：latest=2026-10-27。
- `web/index.html`：latest=2026-11-15，generated=2026-11-16。
- README 目前指向 `web/index.html`，但根目录习惯性入口和分发包会展示明显更旧的数据。

### M10. 原始证据保存不足，历史转换无法独立复核

- `snapshots/<日期>/rows.json` 保存的是归一化后的记录，不是原始 API/HTML，见 `scripts/collect.py:1044-1066`。
- 缺少原始单位、阶梯、SKU quantity、TTL、渠道、原始币种、原始 URL 等完整证据。
- 因此历史数据只能证明“数据库与发布一致”，无法独立重放验证当时抓取与单位换算是否正确。

---

## 五、低优先级但确定的问题

1. 图形把 0 值强制画成至少 2px 柱，见 `web/app.js:401-407`；零价视觉上有非零柱。
2. 走势先删除 null 再连线，缺测日不会断线，见 `web/app.js:337-342`。
3. Top 汇总卡先过滤价格数组，再用过滤后的下标访问原 SRCIDS，来源集合会错位，见 `web/app.js:364-377`；当前快照的集合大小碰巧未变。
4. 代表版本注释写“input 都为空则比 output”，实际 key 只看 input，见 `scripts/build_site.py:351-359`；当前快照未找到该边界实际触发的代表记录差异。
5. 页面及文档仍写“五源/5 providers”，`web/app.js:138` 还会生成 `n_src/5 源`；现有发布物为 8 源，源码声明为 9 源。
6. “5个源全有”的真实实现是 `n_src>=5`，既不是恰好 5，也不是当前来源全集。
7. 图形零值、版本字段缺失、缺测处理及导出字段没有完整专项测试。

---

## 六、测试与发布门禁实测

| 检查 | 结果 | 说明 |
|---|---|---|
| `scripts/test_gateway_parsers.py` | 29/29 通过 | 含 /1K→/1M；源同步测试存在 H2 盲區 |
| `scripts/test_media.py` | 15/15 通过 | 媒体基础单位正常 |
| `scripts/test_parsers.js` | 全部通过 | 未覆盖无表头零值、相等价格、7折等边界 |
| `scripts/test_llm.js` | 全部通过 | 1B 只测独立数学函数，未测真实入口 |
| `scripts/test_upload_tier.js` | 44/44 通过 | 95折等两位数情形通过，无法暴露一位数折扣错误 |
| `scripts/test_official_col.js` | 20/20 通过 | 官网列及 OR 标识正常 |
| `npm test` | 退出码 1 | 冒烟 3 项失败，后续 tier 测试被中止 |
| 9 个采集函数实时试跑 | 均可返回数据 | 可返回不等于全量准确；DeepInfra仅 1 条 |
| 5 个官网解析器实时抽查 | DeepSeek/Z.AI/MiniMax有结果 | Anthropic/Moonshot为 0，当前依赖人工维护，与文档预期一致 |

冒烟失败的三个断言：

- chips 仍断言为 5；当前发布物为 8。
- 汇总卡仍断言为 4；当前实际为 3。
- 走势模型下拉要求大于 100；当前为 10。

GitHub Actions 风险：

- `.github/workflows/pages.yml:44-48` 采集失败后继续。
- `pages.yml:61` 执行 `verify.py || true`，复核再高优先级也不阻断发布。
- Logic tests 未运行 smoke、tier、official_col，因此当前仓库已知失败或关键边界无法阻止部署。
- 组合结果是：DeepInfra 只有 1 条、复核 328 条高优先级告警，也仍可能正常发布。

---

## 七、建议修复顺序与验收标准

### 第一批：先修会产生错误数值或错误曲线的代码

1. 历史序列按 input/output/cache_read/cache_write/list_input/list_output 分字段保存和读取，缺测日断线。
2. 最低/最高价按当前指标独立计算，折扣列不要使用美元范围。
3. 修复 DeepInfra 注册位置；低于合理模型数时视为失败，不允许 1 条结果时提前成功；模型名剥离折扣文案。
4. String 记录键加入渠道，或明确定义并验证“同 ID 多渠道选价规则”；禁止 `INSERT OR REPLACE` 静默丢数据。
5. 聚合前只读取当前受支持来源，清除 ghost 模型和隐藏版本计数。
6. String/Venice/Wokey 等统一定义上下文档位和缓存 TTL 数据模型；至少展示“基准档范围”，不得直接混比。
7. CheaperInference 未澄清上游 discountPercent 语义前，重新计算优惠率或隐藏不一致折扣，不要三字段无说明并列。

验收：上述每一个当前真实案例加入回归测试，断言数值和模型名均符合预期。

### 第二批：修复质量门禁和审计证据

1. `verify.py` 与发布端共用逐源最新日期逻辑，按 model_id 核对代表记录全部字段，消除 312 条假阳性。
2. 对采集设置最小行数、重复键、字段缺失率、折扣自洽、单位必填和源日期检查。
3. 保存原始响应或最小原始字段包，增加 `origin/channel/currency/original_unit/tier/cache_ttl/fx/collected_at/source_url`。
4. 将 smoke、tier、official_col 纳入 CI，更新过时断言；高优先级数据错误应阻断发布，而不是 `|| true`。
5. 发布只保留一个入口和一份最新 HTML，旧版移到明确 archive，不把根目录旧页当当前版。

### 第三批：统一前端状态与上传边界

1. 让表格、图中模型、Top10、源数、排序、CSV共享同一筛选/排序后的数据集。
2. null、免费 0、负折扣分别显示；源价格排序时缺失值固定置底。
3. 修复 `N折`：一位数 N折乘 N/10，两位数 95折乘 95/100；补充 7/8/9/10/95 折测试。
4. 无表头时保留列位置，不删除相等价格，不按大小交换 input/output；支持 0 价。
5. 在实际单位识别入口支持 1B，并补齐端到端测试。
6. 增加逐源报价日期与缓存 TTL；将“官方原价”和“源内参考价”分开命名。

---

## 八、审计边界

- 实时采集只调用公开读取接口和既有解析函数，没有执行主采集写入流程，也没有改数据库、快照或页面。
- 上游价格会变化，实时异常数量代表 2026-11-21 检查时点；当前发布数据异常数量单独按 2026-11-15 快照统计。
- 未执行真实付费 LLM 上传识别，避免额外费用；相关结论来自真实页面函数执行和假 LLM 测试。
- 对上游三字段冲突等情形，只判定本项目展示不自洽，不武断替代供应商确定真实结算价。
