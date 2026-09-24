// UVA Capital Plan Tracker: renders window.DATA (built by build.py) with plain DOM and SVG, no libraries.
(function () {
  "use strict";
  const D = window.DATA;
  const F = window.Finance;
  const NS = "http://www.w3.org/2000/svg";
  const FUND = D.fund_keys;
  const FUND_LABEL = D.fund_labels;
  const FUND_VAR = { state_gf: "--s1", gifts: "--s2", debt: "--s3", other_funds: "--s4" };
  const LINK_TEXT = {
    "single-name": "same name every year",
    "exact-key": "same name, spelling or punctuation differs",
    "fuzzy": "near-identical name (fuzzy match, checked by hand)",
    "override-confirmed": "renamed; link confirmed from the plans",
    "override-probable": "probable link; kept out of totals",
  };
  const $ = (s, el = document) => el.querySelector(s);
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

  // ---- formatting -------------------------------------------------------------------------------------------
  const fmtM = (v) => {
    const a = Math.abs(v);
    const s = a >= 1000 ? a.toLocaleString("en-US", { maximumFractionDigits: 0 })
      : a.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    return (v < 0 ? "−$" : "$") + s + "M";
  };
  const fmtDollarsM = (v, d = 2) => (v < 0 ? "−$" : "$") + (Math.abs(v) / 1e6).toFixed(d) + "M";
  const fmtPct = (v, d = 0, sign = false) => (sign && v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d) + "%";

  function el(tag, attrs = {}, text) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") e.className = v; else if (v !== false && v != null) e.setAttribute(k, v === true ? "" : v);
    }
    if (text != null) e.textContent = text;
    return e;
  }
  function sv(tag, attrs = {}, text) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) if (v != null) e.setAttribute(k, v);
    if (text != null) e.textContent = text;
    return e;
  }
  function niceTicks(max, n = 4) {
    if (max <= 0) return [0];
    const raw = max / n;
    const p = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * p).find((s) => s >= raw);
    const out = [];
    for (let t = 0; t <= max + step * 0.001; t += step) out.push(+t.toFixed(10));
    if (out[out.length - 1] < max) out.push(out[out.length - 1] + step);
    return out;
  }
  function niceRange(lo, hi, n = 5) {
    const span = hi - lo || 1;
    const raw = span / n;
    const p = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * p).find((s) => s >= raw);
    const a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step;
    const out = [];
    for (let t = a; t <= b + step * 0.001; t += step) out.push(+t.toFixed(10));
    return out;
  }

  // ---- tooltip ----------------------------------------------------------------------------------------------
  const tip = $("#tip");
  function showTip(evt, title, rows) {
    tip.replaceChildren(el("div", { class: "t" }, title));
    for (const r of rows) {
      const row = el("div", { class: "r" });
      const k = el("span", { class: "k" });
      if (r.color) { const i = el("i"); i.style.background = r.color; k.append(i); }
      k.append(document.createTextNode(r.label));
      row.append(k, el("b", {}, r.value));
      tip.append(row);
    }
    tip.style.display = "block";
    let x, y;
    if (evt && evt.clientX != null && evt.type !== "focus") { x = evt.clientX; y = evt.clientY; }
    else { const b = evt.target.getBoundingClientRect(); x = b.left + b.width / 2; y = b.top; }
    const w = tip.offsetWidth, h = tip.offsetHeight;
    let left = x + 14, top = y - h - 10;
    if (left + w > window.innerWidth - 8) left = x - w - 14;
    if (top < 8) top = y + 16;
    tip.style.left = Math.max(8, left) + "px";
    tip.style.top = top + "px";
  }
  const hideTip = () => { tip.style.display = "none"; };
  function hoverable(node, fn) {
    node.setAttribute("tabindex", "0");
    node.classList.add("mark");
    node.addEventListener("pointermove", (e) => fn(e));
    node.addEventListener("focus", (e) => fn(e));
    node.addEventListener("pointerleave", hideTip);
    node.addEventListener("blur", hideTip);
  }

  // ---- stacked columns (funding sources by year) ----------------------------------------------------------------
  // cats: [{label, sub?, values: {fundKey: number}, title}] ; mode: "abs" | "share"
  function stackedColumns(host, cats, mode, opts = {}) {
    host.replaceChildren();
    const W = Math.max(320, host.clientWidth || 700), H = opts.height || 280;
    const m = { t: 22, r: 8, b: 40, l: 56 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const totals = cats.map((c) => FUND.reduce((a, k) => a + (c.values ? c.values[k] || 0 : 0), 0));
    const maxV = mode === "share" ? 100 : Math.max(...totals, 1);
    const ticks = mode === "share" ? [0, 25, 50, 75, 100] : niceTicks(maxV);
    const top = ticks[ticks.length - 1];
    const y = (v) => m.t + ih - (v / top) * ih;
    const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": opts.label || "" });
    for (const t of ticks) {
      svg.append(sv("line", { x1: m.l, x2: W - m.r, y1: y(t), y2: y(t), stroke: css(t === 0 ? "--axis" : "--grid"), "stroke-width": 1 }));
      svg.append(sv("text", { x: m.l - 8, y: y(t) + 4, "text-anchor": "end", "font-size": 11, fill: css("--muted") },
        mode === "share" ? t + "%" : "$" + t.toLocaleString("en-US") + (t ? "M" : "")));
    }
    const band = iw / cats.length;
    const bw = Math.min(opts.barWidth || 24, band * 0.6);
    const GAP = 2, R = 4;
    cats.forEach((c, i) => {
      const cx = m.l + band * i + band / 2;
      svg.append(sv("text", { x: cx, y: H - m.b + 18, "text-anchor": "middle", "font-size": 12, fill: css("--ink-2") }, c.label));
      if (c.sub) svg.append(sv("text", { x: cx, y: H - m.b + 33, "text-anchor": "middle", "font-size": 10.5, fill: css("--muted") }, c.sub));
      if (!c.values || !totals[i]) return;
      const scale = mode === "share" ? 100 / totals[i] : 1;
      const segs = FUND.map((k) => ({ k, v: (c.values[k] || 0) * scale, raw: c.values[k] || 0 })).filter((s) => s.v > 0);
      let acc = 0;
      segs.forEach((s, j) => {
        const y0 = y(acc), y1 = y(acc + s.v);
        acc += s.v;
        const isTop = j === segs.length - 1;
        const h = Math.max(0, y0 - y1 - (j > 0 ? GAP : 0));
        const yb = y0 - (j > 0 ? GAP : 0);
        if (h <= 0) return;
        const x0 = cx - bw / 2, r = isTop ? Math.min(R, h, bw / 2) : 0;
        const d = `M${x0},${yb} V${yb - h + r} ${r ? `Q${x0},${yb - h} ${x0 + r},${yb - h}` : ""} H${x0 + bw - r} ${r ? `Q${x0 + bw},${yb - h} ${x0 + bw},${yb - h + r}` : ""} V${yb} Z`;
        const p = sv("path", { d, fill: css(FUND_VAR[s.k]) });
        hoverable(p, (e) => showTip(e, c.title || c.label, [
          { color: css(FUND_VAR[s.k]), label: FUND_LABEL[s.k], value: fmtM(s.raw) },
          { label: "Share of total", value: fmtPct((s.raw / totals[i]) * 100, 1) },
          { label: "Total", value: fmtM(totals[i]) },
        ]));
        p.setAttribute("aria-label", `${c.title || c.label}: ${FUND_LABEL[s.k]} ${fmtM(s.raw)}`);
        svg.append(p);
      });
      if (mode === "abs" && opts.capLabels !== false) {
        svg.append(sv("text", { x: cx, y: y(totals[i]) - 7, "text-anchor": "middle", "font-size": 11.5, "font-weight": 600, fill: css("--ink") }, fmtM(totals[i])));
      }
    });
    host.append(svg);
  }

  function fundLegend(host) {
    host.replaceChildren();
    for (const k of FUND) {
      const s = el("span"); const i = el("i"); i.style.background = `var(${FUND_VAR[k]})`;
      s.append(i, document.createTextNode(FUND_LABEL[k])); host.append(s);
    }
  }

  function table(host, head, rows, numFrom = 1) {
    const t = el("table");
    const tr = el("tr");
    head.forEach((h, i) => tr.append(el("th", { class: i >= numFrom ? "num" : "" }, h)));
    const th = el("thead"); th.append(tr); t.append(th);
    const tb = el("tbody");
    for (const r of rows) {
      const row = el("tr");
      r.forEach((v, i) => row.append(el("td", { class: i >= numFrom ? "num" : "" }, v)));
      tb.append(row);
    }
    t.append(tb);
    host.replaceChildren(t);
  }

  // ---- overview ---------------------------------------------------------------------------------------------
  const years = D.years;
  const share = (y, k) => (D.funding[y][k] / D.totals[y]) * 100;
  let fundingMode = "abs";

  function renderOverview() {
    const last = years[years.length - 1];
    const peakYear = years.reduce((a, y) => (D.totals[y] > D.totals[a] ? y : a), years[0]);
    const debtPeak = years.reduce((a, y) => (share(y, "debt") > share(a, "debt") ? y : a), years[0]);
    const s = D.drift_summary;
    const tiles = [
      { label: `${last} plan total`, value: fmtM(D.totals[last]), note: `Peak ${fmtM(D.totals[peakYear])} in ${peakYear}` },
      { label: "Debt share of the plan", value: fmtPct(share(last, "debt")), note: `${fmtPct(share(years[0], "debt"))} in ${years[0]}; peak ${fmtPct(share(debtPeak, "debt"))} in ${debtPeak}` },
      { label: "State General Fund share", value: fmtPct(share(last, "state_gf")), note: `${fmtPct(share(years[0], "state_gf"))} in ${years[0]}` },
      { label: "Projects whose budget grew", value: `${s.increased} of ${s.tracked}`, note: `Median increase +${s.median_increase_pct}%; ${s.unchanged} unchanged, ${s.decreased} fell` },
    ];
    const host = $("#overview-tiles"); host.replaceChildren();
    for (const t of tiles) {
      const d = el("div", { class: "tile" });
      d.append(el("div", { class: "label" }, t.label), el("div", { class: "value" }, t.value), el("div", { class: "note" }, t.note));
      host.append(d);
    }
    fundLegend($("#funding-legend"));
    renderFundingChart();
    table($("#funding-table"), ["Year", ...FUND.map((k) => FUND_LABEL[k]), "Total"],
      years.map((y) => [String(y), ...FUND.map((k) => `${fmtM(D.funding[y][k])} (${fmtPct(share(y, k))})`), fmtM(D.totals[y])]));
    const divs = [...new Set(years.flatMap((y) => Object.keys(D.division[y])))].sort();
    table($("#division-table"), ["Division", ...years.map(String)],
      divs.map((d) => [d, ...years.map((y) => (D.division[y][d] ? fmtM(D.division[y][d]) : "—"))]));
  }
  function renderFundingChart() {
    $("#funding-sub").textContent = fundingMode === "share"
      ? "Share of each year's authorized budget, by funding source"
      : "Authorized budget across all projects in each year's plan";
    stackedColumns($("#funding-chart"), years.map((y) => ({ label: String(y), title: `${y} plan`, values: D.funding[y] })),
      fundingMode, { label: "Stacked columns of funding sources by plan year", height: 300 });
  }
  document.querySelectorAll("#view-overview .seg button").forEach((b) => b.addEventListener("click", () => {
    fundingMode = b.dataset.mode;
    document.querySelectorAll("#view-overview .seg button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    renderFundingChart();
  }));

  // ---- projects ---------------------------------------------------------------------------------------------
  const P = D.projects;
  let selected = null;
  const divs = [...new Set(P.map((p) => p.division))].sort();
  for (const d of divs) $("#f-div").append(el("option", { value: d }, d));
  const tracked = P.filter((p) => p.drift).length;
  $("#projects-sub").textContent = `${P.length} projects linked across ${years.length} plans from ${D.projects.reduce((a, p) => a + p.rows.length, 0)} plan entries. `
    + `${tracked} have two or more full budgets to compare. Click a project to see it year by year.`;

  function renamed(p) { return p.rows.some((r) => r.link !== "single-name") || new Set(p.rows.map((r) => r.name)).size > 1; }
  function matches(p, q) {
    if (!q) return true;
    q = q.toLowerCase();
    return p.id.toLowerCase().includes(q) || p.rows.some((r) => r.name.toLowerCase().includes(q));
  }

  function renderProjects() {
    const q = $("#q").value.trim(), div = $("#f-div").value, show = $("#f-show").value, sort = $("#f-sort").value;
    let list = P.filter((p) => matches(p, q) && (!div || p.division === div)
      && (show !== "tracked" || p.drift) && (show !== "grew" || (p.drift && p.drift.delta > 0.005))
      && (show !== "renamed" || renamed(p)));
    const byPct = (p) => (p.drift ? p.drift.pct : -Infinity);
    list.sort({
      pct: (a, b) => byPct(b) - byPct(a) || b.latest_total - a.latest_total,
      latest: (a, b) => b.latest_total - a.latest_total,
      name: (a, b) => a.id.localeCompare(b.id),
      years: (a, b) => b.years.length - a.years.length || a.id.localeCompare(b.id),
    }[sort]);
    const t = $("#projects-table");
    const head = el("tr");
    [["Project", ""], ["Division", "hide-sm"], ["In plan", ""], ["Latest", "num"], ["Budget change", "num"]]
      .forEach(([h, c]) => head.append(el("th", { class: c }, h)));
    const tb = el("tbody");
    for (const p of list) {
      const tr = el("tr", { class: "pick", tabindex: "0", "aria-selected": String(selected === p.id) });
      const name = el("td"); name.append(document.createTextNode(p.id));
      if (p.conf === "probable") { name.append(" "); name.append(el("span", { class: "badge", title: "Linked by a probable match; kept out of totals" }, "probable link")); }
      else if (renamed(p) && new Set(p.rows.map((r) => r.name)).size > 1) { name.append(" "); name.append(el("span", { class: "badge", title: "Listed under more than one name" }, "renamed")); }
      const dots = el("span", { class: "dots", "aria-label": "Years in plan: " + p.years.join(", ") });
      for (const y of years) {
        const r = p.rows.find((x) => x.year === y);
        dots.append(el("i", { class: r ? (r.phase === "planning" ? "plan" : "on") : "", title: r ? `${y}: ${r.phase === "planning" ? "planning authorization" : "full budget"} ${fmtM(r.total)}` : `${y}: not in plan` }));
      }
      const dc = el("td"); dc.append(dots);
      const ch = el("td", { class: "num" });
      if (p.drift) {
        const bar = el("span", { class: "bar", "aria-hidden": "true" });
        const w = Math.min(Math.abs(p.drift.pct), 150) / 150 * 45;
        const i = el("i");
        i.style.width = w + "px";
        i.style.background = p.drift.pct >= 0 ? "var(--up)" : "var(--down)";
        i.style[p.drift.pct >= 0 ? "left" : "right"] = "50%";
        i.style.borderRadius = p.drift.pct >= 0 ? "0 3px 3px 0" : "3px 0 0 3px";
        if (Math.abs(p.drift.pct) > 0.005) bar.append(i);
        ch.append(bar, document.createTextNode(Math.abs(p.drift.pct) < 0.005 ? "no change" : fmtPct(p.drift.pct, 0, true)));
      } else ch.append(el("span", { class: "muted" }, "—"));
      tr.append(name, el("td", { class: "hide-sm" }, p.division), dc, el("td", { class: "num" }, p.latest_total ? fmtM(p.latest_total) : "—"), ch);
      const open = () => { selected = p.id; renderProjects(); renderDetail(p, true); };
      tr.addEventListener("click", open);
      tr.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
      tb.append(tr);
    }
    if (!list.length) { const tr = el("tr"); tr.append(el("td", { colspan: "5", class: "muted" }, "No projects match.")); tb.append(tr); }
    const thead = el("thead"); thead.append(head);
    t.replaceChildren(thead, tb);
  }
  ["#q", "#f-div", "#f-show", "#f-sort"].forEach((s) => $(s).addEventListener("input", renderProjects));

  function renderDetail(p, scroll) {
    const host = $("#detail");
    host.hidden = false;
    host.replaceChildren();
    const head = el("div", { class: "detail-head" });
    const left = el("div");
    left.append(el("h2", {}, p.id), el("p", { class: "sub" }, `${p.division} · latest status: ${p.status} · in ${p.years.length} of ${years.length} plans`));
    head.append(left);
    host.append(head);
    const d = p.drift;
    let story;
    if (d) {
      const moved = Math.abs(d.delta) > 0.005;
      story = moved
        ? `Full budget went from ${fmtM(d.first)} (${d.first_year}) to ${fmtM(d.last)} (${d.last_year}), ${fmtPct(d.pct, 1, true)}, over ${d.revisions} revision${d.revisions === 1 ? "" : "s"}${d.peak > Math.max(d.first, d.last) + 0.005 ? `; it peaked at ${fmtM(d.peak)}` : ""}.`
        : `Full budget unchanged at ${fmtM(d.last)} across ${d.n_years} plans (${d.first_year}-${d.last_year}).`;
    } else {
      story = "Fewer than two full budgets in the plans, so there is no budget change to measure.";
    }
    if (p.conf === "probable") story += " This project is joined to an earlier name by a probable match, so it is kept out of the site's totals.";
    host.append(el("p", {}, story));
    const leg = el("div", { class: "legend" }); fundLegend(leg); host.append(leg);
    const chart = el("div"); host.append(chart);
    const cats = years.map((y) => {
      const r = p.rows.find((x) => x.year === y);
      return { label: String(y), sub: r ? (r.phase === "planning" ? "planning" : "") : "not listed", title: r ? `${y}: ${r.name}` : String(y), values: r ? r : null };
    });
    stackedColumns(chart, cats, "abs", { label: `Budget by funding source for ${p.id}`, height: 240 });
    const tw = el("div", { class: "tablewrap" }); host.append(tw);
    table(tw, ["Year", "Name in that plan", "Status", ...FUND.map((k) => FUND_LABEL[k]), "Total", "How it was linked"],
      p.rows.map((r) => [String(r.year), r.name + (r.phase === "planning" ? " (planning authorization)" : ""), r.status,
        ...FUND.map((k) => (r[k] ? fmtM(r[k]) : "—")), r.total ? fmtM(r.total) : "—", LINK_TEXT[r.link] || r.link]), 3);
    tw.querySelectorAll("tr").forEach((tr) => { const c = tr.lastChild; if (c) c.className = ""; });
    if (scroll) host.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // ---- feasibility ------------------------------------------------------------------------------------------
  const EX = D.feasibility.examples;
  let exKey = "course";
  let base = EX[exKey].case;
  let baseSum = F.summarize(base);
  const medianOverrun = D.drift_summary.median_increase_pct;
  const SL = [
    { id: "discount", label: "Discount rate", min: 1, max: 8, step: 0.25, value: () => base.discount * 100, fmt: (v) => v.toFixed(2) + "%" },
    { id: "egi_growth", label: "Revenue growth a year", min: 0, max: 6, step: 0.25, value: () => base.egi_growth * 100, fmt: (v) => v.toFixed(2) + "%" },
    { id: "om_growth", label: "O&M cost growth a year", min: 0, max: 8, step: 0.25, value: () => base.om_growth * 100, fmt: (v) => v.toFixed(2) + "%" },
    { id: "egi0", label: "First-year revenue vs. the example", min: -30, max: 30, step: 1, value: 0, fmt: (v) => fmtPct(v, 0, true), hint: () => `Example: ${fmtDollarsM(base.egi0)} in year ${base.op_start}` },
    { id: "overrun", label: "Construction cost overrun", min: 0, max: 50, step: 0.1, value: 0, fmt: (v) => "+" + v.toFixed(1) + "%", hint: `Median increase among UVA projects whose budget grew: +${medianOverrun}%`, apply: medianOverrun },
    { id: "delay", label: "Construction delay", min: 0, max: 3, step: 1, value: 0, fmt: (v) => v + (v === 1 ? " year" : " years"), hint: "Last construction year and opening move later; costs escalate 3% a year" },
  ];
  const host = $("#sliders");
  for (const s of SL) {
    const w = el("div", { class: "slider" });
    const lab = el("label", { for: "s-" + s.id });
    lab.append(document.createTextNode(s.label), el("output", { id: "o-" + s.id }));
    const inp = el("input", { type: "range", id: "s-" + s.id, min: s.min, max: s.max, step: s.step, value: valueOf(s) });
    inp.addEventListener("input", renderFeasibility);
    w.append(lab, inp);
    if (s.hint) {
      const h = el("div", { class: "hint" });
      h.append(el("span", { id: "h-" + s.id }, (typeof s.hint === "function" ? s.hint() : s.hint) + " "));
      if (s.apply != null) {
        const b = el("button", { class: "linkbtn", type: "button" }, "Use it");
        b.addEventListener("click", () => { inp.value = s.apply; renderFeasibility(); });
        h.append(b);
      }
      w.append(h);
    }
    host.append(w);
  }
  function valueOf(s) { return typeof s.value === "function" ? s.value() : s.value; }
  function resetSliders() {
    for (const s of SL) {
      $("#s-" + s.id).value = valueOf(s);
      if (typeof s.hint === "function") $("#h-" + s.id).textContent = s.hint() + " ";
    }
  }
  $("#reset").addEventListener("click", () => { resetSliders(); renderFeasibility(); });
  const pick = $("#example-pick");
  for (const [key, e] of Object.entries(EX)) {
    const b = el("button", { type: "button", "data-key": key, "aria-pressed": String(key === exKey) }, e.label);
    b.addEventListener("click", () => {
      exKey = key; base = EX[key].case; baseSum = F.summarize(base);
      pick.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      showExampleNote(); resetSliders(); renderFeasibility();
    });
    pick.append(b);
  }
  function showExampleNote() {
    const n = $("#example-note");
    n.replaceChildren(el("strong", {}, EX[exKey].title + ". "), document.createTextNode(EX[exKey].note));
  }
  showExampleNote();

  function currentCase() {
    const v = (id) => parseFloat($("#s-" + id).value);
    let c = { ...base, discount: v("discount") / 100, egi_growth: v("egi_growth") / 100, om_growth: v("om_growth") / 100,
      egi0: base.egi0 * (1 + v("egi0") / 100) };
    c = F.overrun(c, v("overrun") / 100);
    c = F.delayed(c, v("delay"));
    return c;
  }

  function renderFeasibility() {
    for (const s of SL) $("#o-" + s.id).textContent = s.fmt(parseFloat($("#s-" + s.id).value));
    const c = currentCase();
    const rows = F.cashFlows(c);
    const sum = F.summarize(c);
    const dN = sum.npv - baseSum.npv;
    const tiles = [
      { label: "Net present value", value: fmtDollarsM(sum.npv), note: sum.npv >= 0 ? "Clears the discount rate" : "Below the discount rate", cls: "" },
      { label: "Internal rate of return", value: sum.irr == null ? "none" : (sum.irr * 100).toFixed(2) + "%", note: `${EX[exKey].label}: ${(baseSum.irr * 100).toFixed(2)}%` },
      { label: "Change from the example", value: (dN >= 0 ? "+" : "−") + "$" + (Math.abs(dN) / 1e6).toFixed(2) + "M", note: `Example NPV ${fmtDollarsM(baseSum.npv)} at ${(base.discount * 100).toFixed(0)}%`, delta: Math.abs(dN) < 500 ? 0 : Math.sign(dN) },
    ];
    const th = $("#feas-tiles"); th.replaceChildren();
    for (const t of tiles) {
      const d = el("div", { class: "tile" });
      const v = el("div", { class: "value" + (t.delta > 0 ? " delta-up" : t.delta < 0 ? " delta-down" : "") }, t.value);
      d.append(el("div", { class: "label" }, t.label), v, el("div", { class: "note" }, t.note));
      th.append(d);
    }
    const disc = rows.ncf.map((v, t) => v / Math.pow(1 + c.discount, t));
    const cum = []; disc.reduce((a, v, i) => (cum[i] = a + v), 0);
    lineChart($("#cum-chart"), cum, rows.ncf, disc);
    const cols = ["equity", "loan", "expenses", "egi", "opex", "debt_service", "ncf"];
    const names = ["Equity", "Loan", "Project expenses", "Revenue (EGI)", "O&M", "Debt service", "Net cash flow"];
    table($("#cf-table"), ["Year", ...names, "Discounted", "Cumulative"],
      rows.ncf.map((_, t) => [String(t), ...cols.map((k) => (Math.abs(rows[k][t]) < 0.5 ? "—" : fmtDollarsM(rows[k][t]))), fmtDollarsM(disc[t]), fmtDollarsM(cum[t])]));
  }

  function lineChart(host, cum, ncf, disc) {
    host.replaceChildren();
    const W = Math.max(320, host.clientWidth || 700), H = 280;
    const m = { t: 18, r: 64, b: 34, l: 60 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const lo = Math.min(0, ...cum) / 1e6, hi = Math.max(0, ...cum) / 1e6;
    const ticks = niceRange(lo, hi, 5);
    const y0 = ticks[0], y1 = ticks[ticks.length - 1];
    const x = (t) => m.l + (t / (cum.length - 1)) * iw;
    const y = (v) => m.t + ih - ((v / 1e6 - y0) / (y1 - y0)) * ih;
    const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Line chart of cumulative discounted cash flow by year" });
    for (const t of ticks) {
      svg.append(sv("line", { x1: m.l, x2: m.l + iw, y1: y(t * 1e6), y2: y(t * 1e6), stroke: css(Math.abs(t) < 1e-9 ? "--axis" : "--grid"), "stroke-width": 1 }));
      svg.append(sv("text", { x: m.l - 8, y: y(t * 1e6) + 4, "text-anchor": "end", "font-size": 11, fill: css("--muted") },
        (t < 0 ? "−$" : "$") + Math.abs(t) + (t ? "M" : "")));
    }
    const stepX = cum.length > 16 ? 5 : 1;
    for (let t = 0; t < cum.length; t += stepX) {
      svg.append(sv("text", { x: x(t), y: H - m.b + 18, "text-anchor": "middle", "font-size": 11, fill: css("--muted") }, t === 0 ? "Year 0" : String(t)));
    }
    const color = css("--s1");
    const d = cum.map((v, t) => `${t ? "L" : "M"}${x(t).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    svg.append(sv("path", { d: d + ` L${x(cum.length - 1)},${y(0)} L${x(0)},${y(0)} Z`, fill: color, "fill-opacity": 0.1 }));
    svg.append(sv("path", { d, fill: "none", stroke: color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    const lastT = cum.length - 1;
    svg.append(sv("circle", { cx: x(lastT), cy: y(cum[lastT]), r: 5, fill: color, stroke: css("--surface"), "stroke-width": 2 }));
    svg.append(sv("text", { x: x(lastT) + 9, y: y(cum[lastT]) + 4, "font-size": 11.5, "font-weight": 600, fill: css("--ink") }, "NPV " + fmtDollarsM(cum[lastT])));
    const cross = sv("line", { y1: m.t, y2: m.t + ih, stroke: css("--axis"), "stroke-width": 1, visibility: "hidden" });
    const dot = sv("circle", { r: 4, fill: color, stroke: css("--surface"), "stroke-width": 2, visibility: "hidden" });
    svg.append(cross, dot);
    const hit = sv("rect", { x: m.l, y: m.t, width: iw, height: ih, fill: "transparent", tabindex: 0, "aria-label": "Hover or use arrow keys to read each year" });
    let cur = lastT;
    const show = (t, e) => {
      cur = Math.max(0, Math.min(lastT, t));
      cross.setAttribute("x1", x(cur)); cross.setAttribute("x2", x(cur)); cross.setAttribute("visibility", "visible");
      dot.setAttribute("cx", x(cur)); dot.setAttribute("cy", y(cum[cur])); dot.setAttribute("visibility", "visible");
      showTip(e, `Year ${cur}`, [
        { color, label: "Cumulative, discounted", value: fmtDollarsM(cum[cur]) },
        { label: "Net cash flow that year", value: fmtDollarsM(ncf[cur]) },
        { label: "Discounted to year 0", value: fmtDollarsM(disc[cur]) },
      ]);
    };
    hit.addEventListener("pointermove", (e) => {
      const b = svg.getBoundingClientRect();
      const px = (e.clientX - b.left) * (W / b.width);
      show(Math.round(((px - m.l) / iw) * lastT), e);
    });
    hit.addEventListener("focus", (e) => show(cur, e));
    hit.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); show(cur + (e.key === "ArrowRight" ? 1 : -1), { target: dot, type: "focus" }); }
    });
    const off = () => { cross.setAttribute("visibility", "hidden"); dot.setAttribute("visibility", "hidden"); hideTip(); };
    hit.addEventListener("pointerleave", off); hit.addEventListener("blur", off);
    svg.append(hit);
    host.append(svg);
  }

  // ---- method -----------------------------------------------------------------------------------------------
  function renderAbout() {
    const s = D.drift_summary;
    const a = $("#about");
    const blocks = [
      ["h2", "Method and sources"],
      ["p", "The data are the University of Virginia's Major Capital Plans for 2021 through 2026 (the 2026 plan is the FY2027 plan), public documents presented to the Board of Visitors. Each plan lists every authorized project with its total budget and its funding split: State General Fund, gifts, debt, and institutional or cash funds. All amounts are in millions of dollars as printed in the plans."],
      ["h3", "From PDFs to one table"],
      ["p", `The six plans don't share a table layout, so the parser classifies divisions, statuses and money cells by keyword rather than by position. Every one of the ${D.projects.reduce((n, p) => n + p.rows.length, 0)} project rows reconciles to the dollar: its stated total equals the sum of its funding sources, and each year's totals match the plan's own. Rows with no budget assigned (marked TBD in the source) are left out.`],
      ["h3", "Linking a project across years"],
      ["p", `Project names change between plans (spacing damage from the PDFs, added donor names, outright renames). Names are linked in three passes: an exact match on a normalized name; a fuzzy match (similarity of 0.85 or more) allowed only between names that never appear in the same plan, each checked by hand; and a short list of hand-checked overrides. The result is ${D.projects.length} projects. Links the plans don't prove are marked "probable" and kept out of every total; the project view shows how each year's entry was linked.`],
      ["h3", "Budget change"],
      ["p", `Change is measured only between years with a full project budget. Planning-and-design authorizations (usually $1.5-5M) are a different kind of number and are shown but not compared. Among ${s.tracked} projects with two or more full budgets (confirmed links only), ${s.increased} increased, ${s.unchanged} were unchanged and ${s.decreased} fell; together their budgets went from ${fmtM(s.first_sum)} to ${fmtM(s.last_sum)} (+${s.net_pct}%), and the median increase was +${s.median_increase_pct}%. Projects that never moved were also watched for fewer years on average, so "unchanged" partly means "not tracked long enough to change".`],
      ["h3", "The feasibility model"],
      ["p", `The model follows the cash-flow template from UVA's CE 3010 (Capital Projects) course: equity, loan proceeds, project expenses, revenue (effective gross income), operating costs, debt service and net cash flow each year, with NPV and IRR on the net cash flow. It reproduces the course's debt-financed example from lecture S19 (shown here with attribution) to within $1.10 of the slide's printed NPV, and it was also checked cell by cell against the course's example workbook, which isn't published here. The second example is made up for this site. The page runs a JavaScript copy of the model, tested to match the Python original on ${D.feasibility.checks.length} cases.`],
      ["h3", "Limits"],
      ["p", "Six plans is a short series. A capital plan authorizes budgets; it doesn't report what was spent, so budget change is not the same as a final cost overrun. Neither feasibility example is a real UVA project."],
    ];
    a.replaceChildren(...blocks.map(([t, x]) => el(t, {}, x)));
    const f = $("#footer");
    f.replaceChildren(document.createTextNode("Independent student project; not affiliated with or endorsed by the University of Virginia. Source: " + D.source + ". "));
    const link = el("a", { href: "https://github.com/WillMcNulty/UVA-Capital-Plan-Tracker" }, "Code and data on GitHub");
    f.append(link, document.createTextNode("."));
  }

  // ---- tabs & boot ------------------------------------------------------------------------------------------
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  function select(id, push) {
    for (const t of tabs) {
      const on = t.id === "tab-" + id;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    }
    if (push) history.replaceState(null, "", "#" + id);
    renderVisible();
  }
  tabs.forEach((t, i) => {
    t.addEventListener("click", () => select(t.id.slice(4), true));
    t.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      const n = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
      n.focus(); select(n.id.slice(4), true);
    });
  });
  function renderVisible() {
    if (!$("#view-overview").hidden) renderFundingChart();
    if (!$("#view-feasibility").hidden) renderFeasibility();
    if (!$("#view-projects").hidden && selected) renderDetail(P.find((p) => p.id === selected));
  }
  window.addEventListener("hashchange", () => {
    const h = location.hash.slice(1);
    if (["overview", "projects", "feasibility", "about"].includes(h)) select(h, false);
  });
  let rt;
  window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(renderVisible, 120); });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", renderVisible);

  renderOverview();
  renderProjects();
  renderAbout();
  const start = location.hash.slice(1);
  select(["overview", "projects", "feasibility", "about"].includes(start) ? start : "overview", false);
})();
