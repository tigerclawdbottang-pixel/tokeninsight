/* ===================================================================
   GPU 收益测算 tab（主站内嵌，数据源 D.roi —— build_gpu_roi.build_payload）
   口径与独立页 gpu_roi.html 完全一致：
   日收入/日TCO/日利润 = 单台 8 卡主机 × 24h；日收入随利用率缩放；
   无实测吞吐的行只给保本日产量（日TCO÷价格）；红盈绿亏（样式限定本 pane）。
   =================================================================== */
const ROI_STATE = { sortU: 'mult', ascU: false, util: 0.60, bound: false };

const rfmt0 = v => v == null ? '—' : Math.round(v).toLocaleString();
const rfmt1 = v => v == null ? '—' : v.toFixed(1);
const rfmt2 = v => v == null ? '—' : v.toFixed(2);
const rfmt$ = v => (v < 0 ? '-$' : '$') + (Math.abs(v) >= 1e6 ? (Math.abs(v) / 1e6).toFixed(1) + 'M' : Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 0 }));
const rfmtPct = v => v == null ? '—' : (v * 100).toFixed(1) + '%';
const $roi = id => document.getElementById(id);

function roiPriceOf(key) {
  const p = D.roi.prices[key];
  if (!p) return null;
  if (p.or) return { pin: p.or.input, pout: p.or.output, tag: 'OpenRouter' };
  if (p.median) return { pin: p.median.input, pout: p.median.output, tag: p.median.src };
  if (p.official) return { pin: p.official.input, pout: p.official.output, tag: '官方' };
  return null;
}

function roiRows() {
  const R = D.roi;
  const rows = [];
  const seen = new Set();
  const key2 = (mk, pid) => mk + '|' + pid;
  const tpAll = (R.throughput && R.throughput.by_model_platform) || {};
  const mktById = {}; (R.market || []).forEach(g => mktById[g.id] = g);
  const nameOf = mk => {
    const c = ((R.cost || {}).costs || []).find(m => m.model_key === mk);
    if (c) return c.model;
    const p = R.prices[mk];
    return p ? p.name : mk;
  };
  const mkAbs = (tp, priceW, rent) => {
    if (!tp || priceW == null) return null;
    const dayTco = rent * 24 * 8;
    const dayRev = tp.tps * 86400 * 8 * ROI_STATE.util * priceW / 1e6;
    return { dayTco, dayRev, dayProfit: dayRev - dayTco, roi: (dayRev - dayTco) / dayTco };
  };
  // A) InferenceX 成本矩阵 × 现货（成本/趋势 + 吞吐若有）
  const cost = R.cost || { costs: [], platforms: [] };
  const platName = {}; (cost.platforms || []).forEach(p => platName[p.id] = p.name);
  for (const m of cost.costs) {
    const ow = (cost.official_weighted[m.model_key] || {}).weighted;
    const tw = R.prices_w && R.prices_w[m.model_key];
    const twOr = tw && (tw.or || tw.med);
    for (const [pid, cell] of Object.entries(m.cells)) {
      const mk = (R.cost_market || {})[pid];
      if (!mk) continue;
      const tp = tpAll[m.model_key] && tpAll[m.model_key][pid];
      const dayTco = mk.min_price * 24 * 8;
      rows.push({
        model: m.model, workload: m.workload, plat: platName[pid] || pid,
        config: cell.config, costM: cell.cost,
        priceM: twOr ? twOr.v : null,
        priceSrc: twOr ? (tw.or ? 'OpenRouter' : (tw.med || {}).src) : null,
        offM: ow != null ? ow : null, trend: cell.trend,
        stock: mk.stock, stockCards: mk.stock_cards, rent: mk.min_price,
        abs: mkAbs(tp, twOr && twOr.v, mk.min_price),
        beVol: twOr ? dayTco / twOr.v : null,
        tput: tp || null, gpuId: pid, dayTco,
      });
      seen.add(key2(m.model_key, pid));
    }
  }
  // B) 吞吐实测 × 现货（成本矩阵未覆盖的 模型×平台）
  for (const [mk, plats] of Object.entries(tpAll)) {
    const tw = R.prices_w && R.prices_w[mk];
    const twOr = tw && (tw.or || tw.med);
    for (const [pid, tp] of Object.entries(plats)) {
      if (seen.has(key2(mk, pid))) continue;
      const mket = mktById[pid];
      if (!mket) continue;
      const dayTco = mket.min_price * 24 * 8;
      rows.push({
        model: nameOf(mk), workload: 'AgentX 实测',
        plat: (mket.name || pid).replace('NVIDIA ', ''),
        config: `${(tp.framework || '').toUpperCase()}·${tp.prec || ''}·并发 ${tp.conc ?? '—'}`,
        costM: null, priceM: twOr ? twOr.v : null,
        priceSrc: twOr ? (tw.or ? 'OpenRouter' : (tw.med || {}).src) : null,
        offM: null, trend: null,
        stock: mket.stock, stockCards: mket.stock_cards, rent: mket.min_price,
        abs: mkAbs(tp, twOr && twOr.v, mket.min_price),
        beVol: twOr ? dayTco / twOr.v : null,
        tput: tp, gpuId: pid, dayTco,
      });
      seen.add(key2(mk, pid));
    }
  }
  // C) 本地吞吐实测 × 现货（InferenceX CSV 未覆盖的模型）
  for (const c of R.combos || []) {
    if (seen.has(key2(c.model_key, c.gpu))) continue;
    const gpus = c.gpus || 8;
    const pr = roiPriceOf(c.price_key || c.model_key);
    const revCardH = pr ? 3600 * ((c.input_tps / gpus) * (pr.pin || 0) + (c.output_tps / gpus) * (pr.pout || 0)) / 1e6 : null;
    const dayTco = c.rent_min * 24 * gpus;
    const dayRev = revCardH != null ? revCardH * 24 * gpus * ROI_STATE.util : null;
    const pwB = (R.prices_w || {})[c.price_key] || {};
    const pwOrB = pwB.or || pwB.med;
    rows.push({
      model: c.model, workload: `本地实测 · 全新鲜负载 · 并发 ${c.conc}`,
      plat: c.gpu_name.replace('NVIDIA ', '') + ' × ' + gpus,
      config: (c.framework || '') + (c.quant ? '·' + c.quant : ''),
      costM: null, priceM: null, priceSrc: pr ? pr.tag : null, offM: null, trend: null,
      stock: c.stock, stockCards: c.stock_cards || c.stock, rent: c.rent_min, gpuId: c.gpu,
      abs: dayRev != null ? { dayTco, dayRev, dayProfit: dayRev - dayTco, roi: (dayRev - dayTco) / dayTco } : null,
      beVol: pwOrB ? dayTco / pwOrB.v : null, tput: null, dayTco,
    });
    seen.add(key2(c.model_key, c.gpu));
  }
  for (const r of rows) {
    r.grossM = (r.priceM != null && r.costM != null) ? r.priceM - r.costM : null;
    r.mult = (r.priceM != null && r.costM) ? r.priceM / r.costM : null;
  }
  return rows;
}

function roiRenderTable() {
  const rows = roiRows();
  rows.sort((a, b) => ((a[ROI_STATE.sortU] ?? -9e9) - (b[ROI_STATE.sortU] ?? -9e9)) * (ROI_STATE.ascU ? 1 : -1));
  const cntEl = $roi('roi-cnt');
  if (cntEl) cntEl.textContent = `${rows.length} 条 · 仅列有纳管现货的平台`;
  $roi('roi-rows').innerHTML = rows.map(r => `<tr>
    <td class="l"><span class="mname">${r.model}</span><br><span class="mven">${r.workload}</span></td>
    <td class="l"><b>${r.plat}</b><br><span class="mven">${r.config || ''}</span></td>
    <td class="tput" title="${r.tput ? `并发 ${r.tput.conc ?? '—'} · P90 交互性 ${r.tput.p90_intvty ?? '—'} tok/s/用户 · ${r.tput.date || ''}` : ''}">${r.tput ? `<b>${r.tput.tps >= 10000 ? (r.tput.tps / 10000).toFixed(1) + '万' : rfmt0(r.tput.tps)}</b><br><span class="dim">${r.tput.m_h}M/h/卡</span>` : '<span class="dim">—</span>'}</td>
    <td>${r.costM != null ? `<b>$${r.costM < 0.01 ? r.costM.toFixed(4) : rfmt2(r.costM)}</b>` : '<span class="dim">—</span>'}</td>
    <td>${r.priceM != null ? '$' + (r.priceM < 0.01 ? r.priceM.toFixed(4) : rfmt2(r.priceM)) + `<br><span class="dim" style="font-size:10px">${r.priceSrc || ''}</span>` : '—'}</td>
    <td class="dim">${r.offM != null ? '$' + r.offM : '—'}</td>
    <td class="${r.grossM != null && r.grossM >= 0 ? 'pos' : 'neg'}">${r.grossM != null ? '$' + rfmt2(r.grossM) : '—'}</td>
    <td>${r.mult != null ? `<span class="pill ${r.mult >= 2 ? 'lo' : r.mult >= 1 ? 'n' : 'hi'}">×${r.mult.toFixed(1)}</span>` : '—'}</td>
    <td>${r.trend != null ? `<span class="${r.trend < 0 ? 'pos' : 'neg'}">${r.trend > 0 ? '↑' : '↓'}${Math.abs(r.trend)}%</span>` : '<span class="dim">—</span>'}</td>
    <td class="stk" data-gpu="${r.gpuId}"><span class="pill n">${r.stock}</span> 台 <span class="dim">${r.stockCards || r.stock} 卡</span><br><span class="dim" style="font-size:10px">$${rfmt2(r.rent)}/卡·h 起</span></td>
    <td>${r.abs ? rfmt$(r.abs.dayRev) : '<span class="dim">—</span>'}</td>
    <td>${rfmt$(r.dayTco)}</td>
    <td class="${r.abs && r.abs.dayProfit >= 0 ? 'pos' : 'neg'}">${r.abs ? '<b>' + rfmt$(r.abs.dayProfit) + '</b>' : '<span class="dim">—</span>'}</td>
    <td>${r.abs ? `<span class="${r.abs.roi >= 0 ? 'pos' : 'neg'}">${(r.abs.roi * 100).toFixed(0)}%</span>` : '<span class="dim" style="font-size:10px">待吞吐实测</span>'}</td>
    <td>${r.beVol != null ? (r.beVol >= 100 ? rfmt0(r.beVol) : r.beVol.toFixed(1)) + ' M tok' : '—'}</td>
  </tr>`).join('') || '<tr><td colspan="15" style="text-align:center;color:var(--tx3);padding:30px">暂无可纳管组合</td></tr>';
  return rows;
}

function roiRenderCards(rows) {
  const R = D.roi;
  const withMult = rows.filter(r => r.mult != null);
  const bestMult = withMult.length ? withMult.reduce((a, b) => b.mult > a.mult ? b : a) : null;
  const withAbs = rows.filter(r => r.abs);
  const bestE = withAbs.length ? withAbs.reduce((a, b) => b.abs.roi > a.abs.roi ? b : a) : null;
  const totStock = R.market.reduce((s, g) => s + g.stock, 0);
  const totCards = R.market.reduce((s, g) => s + (g.stock_cards || 0), 0);
  const nPlat = R.cost_market ? Object.keys(R.cost_market).length : 0;
  $roi('roi-cards').innerHTML = `
    <div class="card"><h3>最高毛利倍率（价格 ÷ 实测成本）</h3>
      <div class="big ${bestMult && bestMult.mult >= 1 ? 'pos' : 'neg'}">${bestMult ? '×' + bestMult.mult.toFixed(1) : '—'}</div>
      <div class="sm">${bestMult ? `${bestMult.model} · ${bestMult.plat} · 价 $${bestMult.priceM} / 成本 $${bestMult.costM}` : '暂无数据'}</div></div>
    <div class="card"><h3>最佳当日 ROI（实测吞吐行 @ ${Math.round(ROI_STATE.util * 100)}% 利用率）</h3>
      <div class="big ${bestE && bestE.abs.roi >= 0 ? 'pos' : 'neg'}">${bestE ? (bestE.abs.roi * 100).toFixed(0) + '%' : '—'}</div>
      <div class="sm">${bestE ? `${bestE.model} · ${bestE.plat} · 日利润 ${rfmt$(bestE.abs.dayProfit)} / TCO ${rfmt$(bestE.abs.dayTco)}` : '暂无吞吐实测行'}</div></div>
    <div class="card"><h3>纳管现货覆盖</h3>
      <div class="big acc">${R.market.length} 种 · ${totStock} 台 / ${totCards} 卡</div>
      <div class="sm">${R.market.map(g => g.name.split(' ').slice(1).join(' ') + ' $' + rfmt2(g.min_price)).join(' · ')}</div></div>
    <div class="card"><h3>可纳管组合</h3>
      <div class="big acc">${rows.length} 条</div>
      <div class="sm">${nPlat} 个现货平台 · 成本截至 ${R.cost ? R.cost.asof_prices : '—'}</div></div>`;
}

function renderGpuRoi() {
  try {
  if (!D.roi) { $roi('roi-note').textContent = 'ROI 数据未生成（构建时缺 gpu_snapshot/inferencex 数据）'; return; }
  const R = D.roi;
  const apiOk = R.api && R.api.found && R.api.found.length;
  const waitTxt = (R.waiting || []).length
    ? `；<b>待实测</b>：${R.waiting.map(w => w.gpu.replace('NVIDIA ', '')).join('、')}（InferenceX 实测接入后自动出现）` : '';
  $roi('roi-note').innerHTML =
    `<b>当日可纳管 GPU 的模型部署收益（全部真实数据，无推算）：</b>GPU 成本为本站纳管<b>现货报价</b>（${R.market.length} 种型号、${R.market.reduce((s, g) => s + g.stock, 0)} 台 / ${R.market.reduce((s, g) => s + (g.stock_cards || 0), 0)} 卡；价格为整机报价折算的 $/卡·h，取 8 卡整机当日最低价）；` +
    `性能/成本为 <b>InferenceX 官方发布实测</b>（成本矩阵截至 ${R.cost ? R.cost.asof_prices : '—'}；吞吐为 /inference 页逐配置实测 + 本地仓库实测）${apiOk ? '，API 已连通' : ''}；` +
    `价格以 <b>OpenRouter 为市场定价锚</b>（AgentX 同负载加权：缓存 97.5%/输入 2%/输出 0.5%），官方价仅作参考。` +
    `每行 = 有实测性能 ∧ 有现货 ∧ 显存装得下的模型×平台${waitTxt}。`;
  $roi('roi-chips').innerHTML = R.market.map(g =>
    `<div class="gpu-chip"><b>${g.name.replace('NVIDIA ', '')}</b>` +
    `<span>纳管 ${g.stock} 台 / ${g.stock_cards} 卡</span>` +
    `<span class="dim">最低 $${rfmt2(g.min_price)}/卡·h${g.min_platform ? ' · ' + g.min_platform : ''}</span></div>`
  ).join('');
  const concl = R.cost && R.cost.conclusions ? '<b>中转站设计结论（InferenceX）：</b>' + R.cost.conclusions.join('；') : '';
  $roi('roi-foot').innerHTML = concl;
  roiRenderCards(roiRenderTable());
  } catch (e) {
    const el = $roi('roi-note');
    if (el) el.innerHTML = '<b style="color:var(--hi)">渲染异常：' + (e && e.message) + '</b>';
    throw e;
  }
}

/* 事件绑定（在 app.js init 里调用一次） */
function bindGpuRoi() {
  if (ROI_STATE.bound || !document.getElementById('roi-util')) return;
  ROI_STATE.bound = true;
  $roi('roi-util').addEventListener('input', e => {
    ROI_STATE.util = +e.target.value / 100;
    $roi('roi-utilVal').textContent = e.target.value + '%';
    if (D.roi) roiRenderCards(roiRenderTable());
  });
  document.querySelectorAll('#roi-tbl th').forEach(th => th.addEventListener('click', () => {
    const k = th.dataset.u; if (!k) return;
    if (ROI_STATE.sortU === k) ROI_STATE.ascU = !ROI_STATE.ascU; else { ROI_STATE.sortU = k; ROI_STATE.ascU = false; }
    roiRenderTable();
  }));
  // 现货悬停浮层：平台分解
  const platByGpu = {}; (D.roi ? D.roi.market : []).forEach(g => platByGpu[g.id] = g);
  let tip = null;
  const tbody = document.getElementById('roi-rows');
  tbody.addEventListener('mouseover', e => {
    const td = e.target.closest('td.stk'); if (!td) return;
    const g = platByGpu[td.dataset.gpu]; if (!g) return;
    if (!tip) { tip = document.createElement('div'); tip.className = 'plat-tip'; document.body.appendChild(tip); }
    tip.innerHTML = `<div class="pt-t">${g.name.replace('NVIDIA ', '')} · ${g.stock} 台 / ${g.stock_cards} 卡 · ${g.n_listings} 条报价</div>` +
      g.by_platform.map(pp => `<div class="pt-r"><span>${pp.platform}</span><span><b>${pp.nodes}</b> 台 · ${pp.cards} 卡 · $${rfmt2(pp.min_price)}/卡·h</span></div>`).join('');
    tip.style.display = 'block';
  });
  tbody.addEventListener('mousemove', e => {
    if (!tip || tip.style.display === 'none') return;
    tip.style.left = Math.min(e.clientX + 14, innerWidth - 250) + 'px';
    tip.style.top = (e.clientY + 14) + 'px';
  });
  tbody.addEventListener('mouseout', e => {
    if (e.target.closest('td.stk') && tip) tip.style.display = 'none';
  });
}

/* 在 roi.js 自身末尾自举绑定（不能放 app.js init：const ROI_STATE 有时序死区） */
bindGpuRoi();
if (document.getElementById('p-gpuroi')) renderGpuRoi();  // 加载即预渲染，切 tab 即时可见
