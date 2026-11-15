# 模型价格每日复核报告 — 2026-11-15

生成时间：2026-11-15T21:10:20　|　快照日期：2026-11-15（对比基准：2026-11-14）

## 结论

- 高优先级 **328** 项 / 警告 **69** 项 / 信息 **388** 项
- 发布价与采集价一致性问题：**312** 项
- **需要人工/联网核对**：见下方「待核对清单」

## 高优先级差异（需联网核对）（328 项）

| 级别 | 类型 | 源 | 模型 | 说明 |
|---|---|---|---|---|
| high | 价格异动 | OpenRouter | `qwen/qwen3.5-9b` | input 0.16999999999999998 → 0.041999999999999996 (-75.3%) |
| high | 价格异动 | OpenRouter | `qwen/qwen3.5-9b` | output 0.25 → 0.062 (-75.2%) |
| high | 价格异动 | OpenRouter | `qwen/qwen3.5-9b` | cache_read 0.153 → 0.038000000000000006 (-75.2%) |
| high | 发布不一致 | Fireworks | `deepseekv41flash` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `deepseekv4pro` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `glm53` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `glm53flash` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `kimik3` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `kimik31pro` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `minimaxm31flash` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen38max` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `minimaxm2` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `deepseekv4flash` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `deepseekv32` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `kimik26` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen3827b` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `glm52` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `kimik25` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `kimik27code` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen3535ba3b` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen3627b` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen3635ba3b` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen37plus` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen3vl30ba3binstruct` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `deepseekr1` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `glm45air` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `glm45v` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `glm5` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `glm51` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `minimaxm25` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `minimaxm27` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `minimaxm3` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen314b` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen332b` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen35122ba10b` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen3527b` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen35397ba17b` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen359b` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen36plus` | 页面有价但库中无对应记录 |
| high | 发布不一致 | Fireworks | `qwen37max` | 页面有价但库中无对应记录 |

_（仅显示前 40 项，共 328 项）_


## 警告（69 项）

| 级别 | 类型 | 源 | 模型 | 说明 |
|---|---|---|---|---|
| warn | 价格异动 | OpenRouter | `deepseek/deepseek-v4-flash-0731` | input 0.0434 → 0.06 (+38.2%) |
| warn | 价格异动 | OpenRouter | `deepseek/deepseek-v4-flash-0731` | output 0.3 → 0.18 (-40.0%) |
| warn | 价格异动 | OpenRouter | `deepseek/deepseek-v4-flash-0731` | cache_read 0.035 → 0.015 (-57.1%) |
| warn | 价格异动 | OpenRouter | `openai/gpt-5.6-sol` | output 20.0 → 22.0 (+10.0%) |
| warn | 价格异动 | OpenRouter | `z-ai/glm-4.7` | input 0.6 → 0.39999999999999997 (-33.3%) |
| warn | 字段缺失 | OpenRouter | `deepseek/deepseek-r1-0528` | cache_read 由 有 变为 无 |
| warn | 价格异动 | CheaperInference | `beam` | input 0.07283768147351824 → 0.03774336964220425 (-48.2%) |
| warn | 价格异动 | CheaperInference | `beam` | output 0.24306458384467097 → 0.15096658634172944 (-37.9%) |
| warn | 价格异动 | CheaperInference | `beam` | cache_read 0.072826 → 0.037737 (-48.2%) |
| warn | 价格异动 | CheaperInference | `claude-fable-5.2` | input 6.7354148 → 5.2 (-22.8%) |
| warn | 价格异动 | CheaperInference | `claude-fable-5.2` | output 33.677074 → 26.0 (-22.8%) |
| warn | 价格异动 | CheaperInference | `claude-sonnet-5.5` | output 8.3584623 → 6.5 (-22.2%) |
| warn | 价格异动 | CheaperInference | `eleven-flash-v2.5` | input 17.0 → 13.0 (-23.5%) |
| warn | 价格异动 | CheaperInference | `eleven-multilingual-v2` | input 34.0 → 26.0 (-23.5%) |
| warn | 价格异动 | CheaperInference | `eleven-v4-turbo` | input 17.0 → 13.0 (-23.5%) |
| warn | 价格异动 | CheaperInference | `fugu-ultra-v2` | output 23.7244899 → 25.3717044 (+6.9%) |
| warn | 价格异动 | CheaperInference | `gpt-6-sol` | output 8.1 → 6.6868599 (-17.4%) |
| warn | 价格异动 | CheaperInference | `gpt-image-2.5-sunburst` | input 3.25 → 4.25 (+30.8%) |
| warn | 价格异动 | CheaperInference | `gpt-image-2.5-sunburst` | output 19.5 → 25.5 (+30.8%) |
| warn | 价格异动 | CheaperInference | `gpt-image-2.5-sunburst` | cache_read 0.8125 → 1.0625 (+30.8%) |
| warn | 价格异动 | CheaperInference | `grok-4.20-non-reasoning` | output 2.125 → 1.625 (-23.5%) |
| warn | 价格异动 | CheaperInference | `mimo-v2.6-pro-ultraspeed` | input 2.8275 → 3.637624512 (+28.7%) |
| warn | 价格异动 | CheaperInference | `mimo-v2.6-pro-ultraspeed` | output 5.655 → 7.275249024 (+28.7%) |
| warn | 价格异动 | CheaperInference | `nemotron-3.5-super-vl` | output 0.325 → 0.425 (+30.8%) |
| warn | 价格异动 | CheaperInference | `qwen3.8-max-0902` | output 5.1 → 3.9 (-23.5%) |
| warn | 价格异动 | CheaperInference | `qwen3.8-max-prime` | output 9.41961264 → 10.2 (+8.3%) |
| warn | 价格异动 | CheaperInference | `rerank-v3.5` | input 1700.0 → 1300.0 (-23.5%) |
| warn | 价格异动 | CheaperInference | `rerank-v4-fast` | input 1700.0 → 1300.0 (-23.5%) |
| warn | 价格异动 | CheaperInference | `rerank-v4-pro` | input 2125.0 → 1625.0 (-23.5%) |
| warn | 价格异动 | CheaperInference | `gemini-3.1-pro-preview` | input 1.3 → 1.7 (+30.8%) |
| warn | 价格异动 | CheaperInference | `gemini-3.1-pro-preview` | output 7.8 → 10.2 (+30.8%) |
| warn | 价格异动 | CheaperInference | `gemini-3.1-pro-preview` | cache_read 0.13 → 0.17 (+30.8%) |
| warn | 价格异动 | CheaperInference | `claude-opus-5-fast` | output 39.3868475 → 37.911025 (-3.7%) |
| warn | 折扣不自洽 | CheaperInference | `deepseek-v3.2` | 标注折扣 35.089069% 但按官方价算应为 63.1% |
| warn | 折扣不自洽 | CheaperInference | `deepseek-v4.1-flash` | 标注折扣 45.0% 但按官方价算应为 90.3% |
| warn | 折扣不自洽 | CheaperInference | `deepseek-v4.1-flash-1017` | 标注折扣 56.0% 但按官方价算应为 90.3% |
| warn | 折扣不自洽 | CheaperInference | `gemma-4-31b-it` | 标注折扣 35.0% 但按官方价算应为 49.0% |
| warn | 折扣不自洽 | CheaperInference | `glm-4.7-flash` | 标注折扣 35.0% 但按官方价算应为 51.2% |
| warn | 折扣不自洽 | CheaperInference | `glm-5.3` | 标注折扣 45.0% 但按官方价算应为 100.0% |
| warn | 缓存价异常 | CheaperInference | `glm-5.3` | 缓存命中价高于输入价，通常不合理 |

_（仅显示前 40 项，共 69 项）_


## 信息（388 项）

| 级别 | 类型 | 源 | 模型 | 说明 |
|---|---|---|---|---|
| info | 新增 | string | `gpt-6-astra` | 新上架模型 |
| info | 新增 | string | `gpt-6.1-sol` | 新上架模型 |
| info | 新增 | string | `gpt-6.1-terra` | 新上架模型 |
| info | 新增 | string | `gpt-6-sol` | 新上架模型 |
| info | 新增 | string | `gpt-6-luna` | 新上架模型 |
| info | 新增 | string | `gpt-5.6-luna` | 新上架模型 |
| info | 新增 | string | `claude-fable-5-2` | 新上架模型 |
| info | 新增 | string | `claude-fable-5-1` | 新上架模型 |
| info | 新增 | string | `claude-opus-5-5` | 新上架模型 |
| info | 新增 | string | `claude-opus-5` | 新上架模型 |
| info | 新增 | string | `claude-sonnet-5-5` | 新上架模型 |
| info | 新增 | string | `claude-sonnet-5` | 新上架模型 |
| info | 新增 | string | `claude-haiku-5-5` | 新上架模型 |
| info | 新增 | string | `claude-opus-4-8` | 新上架模型 |
| info | 新增 | string | `grok-4.7-build-fast` | 新上架模型 |

_（仅显示前 15 项，共 388 项）_


## 待核对清单

对以下条目，搜索官网/官方定价页确认真实价格：

1. **OpenRouter** `qwen/qwen3.5-9b` — input 0.16999999999999998 → 0.041999999999999996 (-75.3%)
2. **OpenRouter** `qwen/qwen3.5-9b` — output 0.25 → 0.062 (-75.2%)
3. **OpenRouter** `qwen/qwen3.5-9b` — cache_read 0.153 → 0.038000000000000006 (-75.2%)
4. **Fireworks** `deepseekv41flash` — 页面有价但库中无对应记录
5. **Fireworks** `deepseekv4pro` — 页面有价但库中无对应记录
6. **Fireworks** `glm53` — 页面有价但库中无对应记录
7. **Fireworks** `glm53flash` — 页面有价但库中无对应记录
8. **Fireworks** `kimik3` — 页面有价但库中无对应记录
9. **Fireworks** `kimik31pro` — 页面有价但库中无对应记录
10. **Fireworks** `minimaxm31flash` — 页面有价但库中无对应记录
11. **Fireworks** `qwen38max` — 页面有价但库中无对应记录
12. **Fireworks** `minimaxm2` — 页面有价但库中无对应记录
13. **Fireworks** `deepseekv4flash` — 页面有价但库中无对应记录
14. **Fireworks** `deepseekv32` — 页面有价但库中无对应记录
15. **Fireworks** `kimik26` — 页面有价但库中无对应记录
16. **Fireworks** `qwen3827b` — 页面有价但库中无对应记录
17. **Fireworks** `glm52` — 页面有价但库中无对应记录
18. **Fireworks** `kimik25` — 页面有价但库中无对应记录
19. **Fireworks** `kimik27code` — 页面有价但库中无对应记录
20. **Fireworks** `qwen3535ba3b` — 页面有价但库中无对应记录