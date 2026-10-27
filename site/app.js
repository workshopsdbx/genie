/* Genie BYOQ Workshop site: config wiring, tabs, progress, copy buttons, curation panels, scorecard, BYOQ worksheet. */
(function () {
  const CFG = window.WORKSHOP_CONFIG || {};
  const CONTENT = window.WORKSHOP_CONTENT || { domains: {}, answers: {} };
  const store = {
    get: (k, d) => { try { return JSON.parse(localStorage.getItem("byoq-nyc:" + k)) ?? d; } catch (e) { return d; } },
    set: (k, v) => localStorage.setItem("byoq-nyc:" + k, JSON.stringify(v)),
  };
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  // Each attendee has their own Free Edition catalog; the setup box lets them override the default.
  CFG.catalog = store.get("catalog", "") || CFG.catalog || "workspace";
  const withCatalog = (s) => s.replaceAll("{{CATALOG}}", CFG.catalog);
  const catInput = $("#catalog-input");
  if (catInput) {
    catInput.value = CFG.catalog;
    const save = () => { const v = catInput.value.trim(); if (v) { store.set("catalog", v); location.reload(); } };
    $("#catalog-save").addEventListener("click", save);
    catInput.addEventListener("keydown", (e) => { if (e.key === "Enter") save(); });
  }
  const nbUrl = $("#nb-url");

  /* ---------- config-driven text ---------- */
  $$(".cfg").forEach((el) => { if (CFG[el.dataset.cfg]) el.textContent = CFG[el.dataset.cfg]; });

  /* ---------- answers ---------- */
  $$("[data-ans]").forEach((el) => { const v = CONTENT.answers[el.dataset.ans]; if (v != null) el.textContent = v; });

  /* ---------- copy buttons ---------- */
  function copyBtn(getText) {
    const b = document.createElement("button");
    b.className = "copy"; b.type = "button"; b.textContent = "Copy";
    b.addEventListener("click", async (e) => {
      e.preventDefault(); e.stopPropagation();
      try { await navigator.clipboard.writeText(getText()); } catch (err) {
        const t = document.createElement("textarea"); t.value = getText(); document.body.appendChild(t); t.select(); document.execCommand("copy"); t.remove();
      }
      b.textContent = "Copied"; b.classList.add("done");
      setTimeout(() => { b.textContent = "Copy"; b.classList.remove("done"); }, 1400);
    });
    return b;
  }
  function codeBlock(text) {
    const wrap = document.createElement("div"); wrap.className = "codeblock";
    const pre = document.createElement("pre"); pre.textContent = text;
    wrap.appendChild(pre); wrap.appendChild(copyBtn(() => text));
    return wrap;
  }
  function decorateQuestions(root = document) {
    $$(".q", root).forEach((q) => { if (!$(".copy", q)) { const t = q.textContent.trim(); q.appendChild(copyBtn(() => t)); } });
  }

  /* ---------- curation panels (Lab 4) ---------- */
  $$("[data-domain]").forEach((panel) => {
    const d = CONTENT.domains[panel.dataset.domain];
    if (!d) return;
    const section = (title, intro) => {
      const h = document.createElement("h3"); h.textContent = title; panel.appendChild(h);
      if (intro) { const p = document.createElement("p"); p.className = "muted small"; p.textContent = intro; panel.appendChild(p); }
    };
    const phase = (label, note) => {
      const h = document.createElement("p"); h.className = "phase";
      h.innerHTML = `<span>${esc(label)}</span> ${esc(note)}`; panel.appendChild(h);
    };
    phase("Core · Hands-on lab", "Do these two in the 10:15 lab.");
    section("1 · Text instructions", "Paste into Configure → Text. Then cut anything your agency wouldn't say.");
    panel.appendChild(codeBlock(d.instructions));

    const t = d.trusted;
    section("2 · Trusted asset (parameterized query)", "Configure → Examples → Add. Use the question as the title and paste the SQL. Each :name becomes a parameter. Click the gear next to it to set its Data type. When Genie answers with this query, the answer is marked Trusted: reviewed, repeatable, and exact.");
    const ti = document.createElement("div"); ti.className = "curate-item";
    const tq = document.createElement("p"); tq.className = "q"; tq.textContent = t.question; ti.appendChild(tq);
    ti.appendChild(codeBlock(withCatalog(t.sql)));
    const kv = document.createElement("div"); kv.className = "kv";
    t.params.forEach((pm) => { kv.innerHTML += `<div>:${esc(pm.name)}</div><div>Data type <strong>${esc(pm.type)}</strong>. Try asking about <em>${esc(pm.example)}</em>.</div>`; });
    ti.appendChild(kv);
    panel.appendChild(ti);

    phase("Go deeper · Open lab", "Pick any of these after the break.");

    section("3 · Joins", "Configure → Examples → Add → Joins. Pick the left and right tables, enter the join condition, and set the Relationship Type.");
    d.joins.forEach((j) => {
      const it = document.createElement("div"); it.className = "curate-item";
      it.innerHTML = `<div class="kv"><div>Left</div><div><code>${esc(j.left)}</code></div><div>Right</div><div><code>${esc(j.right)}</code></div>
        <div>Relationship</div><div>${esc(j.rel)}</div></div>`;
      it.appendChild(codeBlock(j.on.replaceAll("`", "")));
      panel.appendChild(it);
    });

    section("4 · SQL expressions (measures)", "Configure → Examples → Add → Measure. Fill in Name, Code and Synonyms: synonyms are how Genie maps user words to the measure.");
    d.measures.forEach((m) => {
      const it = document.createElement("div"); it.className = "curate-item";
      it.innerHTML = `<div class="label">Measure</div><div class="title">${esc(m.name)}</div>
        <div class="kv"><div>Synonyms</div><div>${m.synonyms.map(esc).join(", ")}</div></div>`;
      it.appendChild(codeBlock(m.sql));
      panel.appendChild(it);
    });

    section("5 · Example SQL queries", "Configure → Examples → Add. Use the question as the title, then paste the SQL. Add only the ones your space still gets wrong.");
    d.examples.forEach((x) => {
      const it = document.createElement("div"); it.className = "curate-item";
      it.innerHTML = `<div class="label">Question</div>`;
      const q = document.createElement("p"); q.className = "q"; q.textContent = x.question; it.appendChild(q);
      it.appendChild(codeBlock(withCatalog(x.sql)));
      panel.appendChild(it);
    });

    const mv = d.metric_view;
    section("6 · Metric view", "A governed semantic layer in Unity Catalog. The definitions you just wrote as instructions become named measures that every Genie space, dashboard and SQL query shares.");
    const mvA = document.createElement("div"); mvA.className = "curate-item";
    mvA.innerHTML = `<div class="label">Option A · add the one the setup notebook built</div>
      <div class="title">Configure → Sources → Add → <code>${esc(withCatalog(mv.fq))}</code></div>
      <p class="muted small">Then ask a trap question again and open the SQL: Genie now calls <code>MEASURE(\`…\`)</code> on the metric view instead of writing the math itself. Try it in the SQL editor:</p>`;
    mvA.appendChild(codeBlock(withCatalog(mv.query)));
    panel.appendChild(mvA);
    const mvB = document.createElement("div"); mvB.className = "curate-item";
    mvB.innerHTML = `<div class="label">Option B · build your own (stretch)</div>
      <div class="title">Paste into the SQL editor, replace <code>YOURINITIALS</code>, run, then add your view to your space</div>
      <p class="muted small">Change one thing: add a measure, a synonym, or a dimension your agency uses. Then swap it into your space in place of the pre-built one.</p>`;
    mvB.appendChild(codeBlock(withCatalog(mv.create).replaceAll("{{INITIALS}}", "YOURINITIALS")));
    panel.appendChild(mvB);

    section("7 · Benchmarks (for Lab 5)", "Benchmarks → Add benchmark. Paste the question, and the SQL into SQL Answer.");
    d.benchmarks.forEach((x) => {
      const it = document.createElement("div"); it.className = "curate-item";
      const q = document.createElement("p"); q.className = "q"; q.textContent = x.question; it.appendChild(q);
      it.appendChild(codeBlock(withCatalog(x.sql)));
      panel.appendChild(it);
    });
  });
  decorateQuestions();

  /* ---------- tabs ---------- */
  $$(".tabs").forEach((tabs) => {
    const key = "tab:" + tabs.dataset.tabs;
    const activate = (id) => {
      $$(".tab-buttons button", tabs).forEach((b) => b.classList.toggle("active", b.dataset.tab === id));
      $$(".tab-panel", tabs).forEach((p) => p.classList.toggle("active", p.id === id));
    };
    $$(".tab-buttons button", tabs).forEach((b) => b.addEventListener("click", () => { activate(b.dataset.tab); store.set(key, b.dataset.tab); }));
    const saved = store.get(key); if (saved && document.getElementById(saved)) activate(saved);
  });

  /* ---------- checklists + progress ---------- */
  const checks = store.get("checks", {});
  const boxes = $$('input[type="checkbox"][data-id]');
  function updateProgress() {
    const done = boxes.filter((b) => b.checked).length;
    const pct = boxes.length ? Math.round((100 * done) / boxes.length) : 0;
    $("#progress-bar").style.width = pct + "%"; $("#progress-label").textContent = pct + "%";
  }
  boxes.forEach((b) => {
    b.checked = !!checks[b.dataset.id];
    b.addEventListener("change", () => { checks[b.dataset.id] = b.checked; store.set("checks", checks); updateProgress(); });
  });
  updateProgress();

  /* ---------- scorecard ---------- */
  const score = store.get("score", {});
  const marks = ["", "✅", "❌"];
  const tbody = $("#scorecard tbody");
  $$(".trapcard > .q").forEach((q, i) => {
    const text = q.childNodes[0].textContent.trim();
    const tr = document.createElement("tr");
    tr.innerHTML = `<td><span class="qid-chip">${esc(q.dataset.qid || "")}</span> ${esc(text)}</td>`;
    addScoreCells(tr, i);
    tbody.appendChild(tr);
  });
  function addScoreCells(tr, key) {
    ["raw", "curated"].forEach((col) => {
      const k = `${key}:${col}`; const td = document.createElement("td"); td.className = "cell";
      td.textContent = score[k] || "";
      td.addEventListener("click", () => {
        const next = marks[(marks.indexOf(td.textContent) + 1) % marks.length];
        td.textContent = next; score[k] = next; store.set("score", score);
      });
      tr.appendChild(td);
    });
  }

  /* ---------- BYOQ worksheet ---------- */
  // Built to be taken back to the agency: each card is a candidate question for a real Genie pilot.
  const FIELDS = [
    ["question", "My question (in my users' words)", "textarea"],
    ["who", "Who asks it, and how often?", "input"],
    ["priority", "Priority for my agency", "select"],
    ["why", "Why it matters: the decision it informs", "textarea"],
    ["definition", "Terms that need defining (e.g. 'active', 'this year')", "textarea"],
    ["agency_data", "Where the data lives at my agency (system, table, owner)", "textarea"],
    ["domain", "Closest workshop domain", "select"],
    ["result", "What Genie did in the workshop", "select"],
    ["expected", "What a correct answer looks like", "textarea"],
    ["fix", "What I added to fix it, or the data that's missing", "textarea"],
  ];
  const WIDE = new Set(["question", "why", "expected", "fix"]);
  const OPTIONS = {
    priority: ["", "High", "Medium", "Low"],
    domain: ["", "Aging & Home Care", "Transit Finance", "DEP Water & Sewer", "DOHMH Food Safety & Rodents", "None: needs my agency's data"],
    result: ["", "Correct on first try", "Correct after curation", "Partially right", "Wrong", "Data not available", "Didn't try yet"],
  };
  const META = [["name", "Your name"], ["agency", "Agency / office"], ["team", "Team or program"]];
  let meta = store.get("byoq-meta", {});
  let items = store.get("byoq", null) || [{}];
  const list = $("#byoq-list");

  const metaBox = document.createElement("div"); metaBox.className = "byoq-meta";
  META.forEach(([key, label]) => {
    const box = document.createElement("div");
    box.innerHTML = `<label for="byoq-meta-${key}">${esc(label)}</label>`;
    const el = document.createElement("input"); el.id = `byoq-meta-${key}`; el.value = meta[key] || "";
    el.addEventListener("input", () => { meta[key] = el.value; store.set("byoq-meta", meta); });
    box.appendChild(el); metaBox.appendChild(box);
  });
  list.before(metaBox);

  function renderByoq() {
    list.innerHTML = "";
    items.forEach((it, idx) => {
      const card = document.createElement("div"); card.className = "byoq-card";
      card.innerHTML = `<div class="head"><strong>Question ${idx + 1}</strong><button class="rm" type="button">Remove</button></div>`;
      const row = document.createElement("div"); row.className = "row";
      FIELDS.forEach(([key, label, kind]) => {
        const box = document.createElement("div");
        if (WIDE.has(key)) box.style.gridColumn = "1 / -1";
        const id = `byoq-${idx}-${key}`;
        box.innerHTML = `<label for="${id}">${esc(label)}</label>`;
        let el;
        if (kind === "select") {
          el = document.createElement("select");
          OPTIONS[key].forEach((o) => { const op = document.createElement("option"); op.value = o; op.textContent = o || "Choose…"; el.appendChild(op); });
        } else el = document.createElement(kind);
        el.id = id; el.value = it[key] || "";
        const save = () => { items[idx][key] = el.value; store.set("byoq", items); };
        el.addEventListener("input", save);
        el.addEventListener("change", save);
        box.appendChild(el); row.appendChild(box);
      });
      card.appendChild(row);
      $(".rm", card).addEventListener("click", () => { items.splice(idx, 1); if (!items.length) items = [{}]; store.set("byoq", items); renderByoq(); });
      list.appendChild(card);
    });
  }
  renderByoq();
  $("#byoq-add").addEventListener("click", () => { items.push({}); store.set("byoq", items); renderByoq(); renderOwnScore(); });

  // Your own questions also get scorecard rows, so Rounds 1 and 2 track them alongside the traps.
  function renderOwnScore() {
    $$("tr.own", tbody).forEach((r) => r.remove());
    items.forEach((it, idx) => {
      const q = (it.question || "").trim();
      if (!q) return;
      const tr = document.createElement("tr"); tr.className = "own";
      tr.innerHTML = `<td><span class="qid-chip own">You</span> ${esc(q.length > 110 ? q.slice(0, 110) + "…" : q)}</td>`;
      addScoreCells(tr, `own:${q}`);
      tbody.appendChild(tr);
    });
  }
  renderOwnScore();
  list.addEventListener("change", renderOwnScore);
  list.addEventListener("click", (e) => { if (e.target.closest(".rm")) renderOwnScore(); });

  // Exports: only cards with a question; High priority first.
  const RANK = { High: 0, Medium: 1, Low: 2 };
  const filled = () => items.filter((it) => (it.question || "").trim())
    .map((it, i) => ({ ...it, _n: i }))
    .sort((x, y) => (RANK[x.priority] ?? 3) - (RANK[y.priority] ?? 3) || x._n - y._n);
  const stamp = () => new Date().toISOString().slice(0, 10);
  const slug = () => (meta.agency || "my-agency").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "my-agency";
  function download(name, text, type) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
  }
  function nothingYet() {
    if (filled().length) return false;
    alert("Add at least one question first."); return true;
  }

  $("#byoq-export-md").addEventListener("click", () => {
    if (nothingYet()) return;
    const rows = filled();
    const one = (v) => (v || "").replace(/\s*\n\s*/g, " ").replace(/\|/g, "\\|").trim();
    const md = [
      `# Genie questions for ${meta.agency || "my agency"}`, "",
      `Prepared by ${meta.name || "—"}${meta.team ? ` (${meta.team})` : ""} · NYC Databricks Day Genie Workshop · ${stamp()}`, "",
      "These are the questions our team actually needs answered. Each one is a candidate for a Genie pilot on our own data.", "",
      "## Summary", "",
      "| # | Question | Priority | Who asks | Data source |",
      "|---|---|---|---|---|",
      ...rows.map((it, i) => `| ${i + 1} | ${one(it.question)} | ${one(it.priority) || "—"} | ${one(it.who) || "—"} | ${one(it.agency_data) || "—"} |`),
      "",
      "## Details", "",
      ...rows.flatMap((it, i) => [
        `### ${i + 1}. ${one(it.question)}`, "",
        ...FIELDS.slice(1).filter(([k]) => (it[k] || "").trim()).map(([k, label]) => `- **${label}:** ${one(it[k])}`), "",
      ]),
      "## Next steps", "",
      "- [ ] Confirm the definitions above with the program owner.",
      "- [ ] Identify the gold tables (or metric views) that answer the High-priority questions.",
      "- [ ] Turn these questions into Genie benchmarks before the pilot.", "",
    ].join("\n");
    download(`genie-questions-${slug()}-${stamp()}.md`, md, "text/markdown;charset=utf-8");
  });

  $("#byoq-export-csv").addEventListener("click", () => {
    if (nothingYet()) return;
    const cell = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const head = ["#", "Agency / office", "Prepared by", "Team or program", ...FIELDS.map(([, label]) => label)];
    const lines = [head.map(cell).join(",")].concat(filled().map((it, i) =>
      [i + 1, meta.agency, meta.name, meta.team, ...FIELDS.map(([k]) => it[k])].map(cell).join(",")));
    // UTF-8 BOM + CRLF so Excel opens it with the right encoding; Google Sheets imports it as-is.
    download(`genie-questions-${slug()}-${stamp()}.csv`, "﻿" + lines.join("\r\n"), "text/csv;charset=utf-8");
  });

  /* ---------- dataset picker (setup) ---------- */
  // Each attendee loads one dataset. Remember it, point the download/import links at its notebook,
  // and open that dataset's tab in every tabbed section of the page.
  const TAB_PREFIX = { data: "d-", build: "b-", traps: "t-", curate: "c-" };
  function pickDomain(dom, save) {
    const btn = $(`#domain-picker [data-pick="${dom}"]`);
    if (!btn) return;
    $$("#domain-picker button").forEach((b) => b.classList.toggle("active", b === btn));
    const nb = btn.dataset.nb;
    const nbAbs = new URL(nb, location.href).href;
    $("#nb-download").innerHTML = `<a class="btn" href="${nb}" download>Download ${esc(nb)}</a>`;
    if (nbUrl) nbUrl.textContent = nbAbs;
    $$(".my-schema").forEach((el) => { el.textContent = btn.dataset.schema; });
    Object.entries(TAB_PREFIX).forEach(([group, prefix]) => {
      const tabBtn = $(`.tabs[data-tabs="${group}"] .tab-buttons button[data-tab="${prefix}${dom}"]`);
      if (tabBtn) { tabBtn.click(); }
    });
    if (save) store.set("domain", dom);
  }
  $$("#domain-picker button").forEach((b) => b.addEventListener("click", () => pickDomain(b.dataset.pick, true)));
  const savedDomain = store.get("domain", "");
  if (savedDomain) pickDomain(savedDomain, false);

  /* ---------- print / PDF ---------- */
  // Open every collapsible answer while printing, then put them back.
  let closedForPrint = [];
  window.addEventListener("beforeprint", () => {
    closedForPrint = $$("details:not([open])");
    closedForPrint.forEach((d) => d.setAttribute("open", ""));
  });
  window.addEventListener("afterprint", () => { closedForPrint.forEach((d) => d.removeAttribute("open")); closedForPrint = []; });
  $("#print-btn").addEventListener("click", () => window.print());

  /* ---------- active nav ---------- */
  const links = $$(".sidebar a");
  const sections = links.map((a) => document.querySelector(a.getAttribute("href"))).filter(Boolean);
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) links.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === "#" + e.target.id));
    });
  }, { rootMargin: "-40% 0px -55% 0px" });
  sections.forEach((s) => obs.observe(s));
})();
