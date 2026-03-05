"""Self-contained interactive HTML report for compliance mapping results.

Produces a single ``.html`` file with embedded CSS and JS — no external
dependencies.  Two report modes in one page:

1. **Framework Gap Analysis** — one card per framework control showing
   which policy chunks support it and the LLM verdict.
2. **Policy Coverage** — one card per source document showing which
   framework controls each policy section satisfies.

Ref: GitHub Issue #22.
"""

from __future__ import annotations

import html
import tempfile
from collections import defaultdict
from pathlib import Path

from ctrlmap.models.schemas import (
    InsufficientEvidence,
    MappedResult,
    MappingRationale,
    ParsedChunk,
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_CSS = """\
:root {
  --bg: #0f1117;
  --surface: #1a1d27;
  --surface-hover: #222635;
  --border: #2a2e3d;
  --text: #e1e4ed;
  --text-dim: #8b8fa7;
  --accent: #6c63ff;
  --accent-glow: rgba(108, 99, 255, 0.12);
  --green: #22c55e;
  --green-bg: rgba(34, 197, 94, 0.1);
  --yellow: #f59e0b;
  --yellow-bg: rgba(245, 158, 11, 0.1);
  --red: #ef4444;
  --red-bg: rgba(239, 68, 68, 0.1);
  --gray: #6b7280;
  --gray-bg: rgba(107, 114, 128, 0.08);
}
*, *::before, *::after {
  box-sizing: border-box; margin: 0; padding: 0;
}
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont,
    'Segoe UI', sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  padding: 2rem;
  max-width: 1100px;
  margin: 0 auto;
}
h1 {
  font-size: 1.75rem; font-weight: 700;
  margin-bottom: 0.25rem;
  background: linear-gradient(135deg, #6c63ff, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.subtitle {
  color: var(--text-dim);
  margin-bottom: 1.5rem;
  font-size: 0.9rem;
}

/* ── Tabs ─────────────────────────────────────── */
.tabs {
  display: flex; gap: 0; margin-bottom: 1.5rem;
  border-bottom: 2px solid var(--border);
}
.tab-btn {
  background: none; border: none;
  color: var(--text-dim);
  padding: 0.75rem 1.5rem;
  font-size: 0.9rem; font-weight: 600;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s ease;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}
.tab-panel { display: none; }
.tab-panel.active { display: block; }

/* ── Stats ────────────────────────────────────── */
.stats-bar {
  display: flex; gap: 1.5rem;
  margin-bottom: 2rem; flex-wrap: wrap;
}
.stat {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem 1.5rem;
  min-width: 140px; text-align: center;
}
.stat-value { font-size: 1.5rem; font-weight: 700; }
.stat-label {
  font-size: 0.75rem; color: var(--text-dim);
  text-transform: uppercase; letter-spacing: 0.05em;
}

/* ── Filter pills ─────────────────────────────── */
.filters {
  display: flex; gap: 0.5rem;
  margin-bottom: 1.5rem; flex-wrap: wrap;
}
.filter-btn {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text-dim);
  padding: 0.4rem 1rem; border-radius: 20px;
  cursor: pointer; font-size: 0.8rem;
  transition: all 0.2s ease;
}
.filter-btn:hover {
  border-color: var(--accent); color: var(--text);
}
.filter-btn.active {
  background: var(--accent-glow);
  border-color: var(--accent);
  color: var(--accent);
}

/* ── Cards ────────────────────────────────────── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  margin-bottom: 0.75rem; overflow: hidden;
  transition: border-color 0.2s ease;
}
.card:hover { border-color: var(--accent); }
.card-header {
  display: flex; align-items: center;
  gap: 0.75rem; padding: 1rem 1.25rem;
  cursor: pointer; user-select: none;
}
.card-header:hover { background: var(--surface-hover); }
.chevron {
  transition: transform 0.2s ease;
  color: var(--text-dim);
  font-size: 0.75rem; flex-shrink: 0;
}
.card.open .chevron { transform: rotate(90deg); }
.ctrl-id {
  font-weight: 700; font-size: 0.95rem;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: var(--accent); min-width: 80px;
}
.ctrl-title { font-size: 0.9rem; flex: 1; }
.badge {
  padding: 0.2rem 0.75rem; border-radius: 20px;
  font-size: 0.7rem; font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em; white-space: nowrap;
}
.badge-compliant {
  background: var(--green-bg); color: var(--green);
}
.badge-noncompliant, .badge-gap {
  background: var(--yellow-bg); color: var(--yellow);
}
.score {
  font-size: 0.8rem; color: var(--text-dim);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  min-width: 3rem; text-align: right;
}
.card-body {
  display: none;
  padding: 0 1.25rem 1.25rem;
  border-top: 1px solid var(--border);
}
.card.open .card-body {
  display: block; padding-top: 1rem;
}

/* ── Tags & rationale ─────────────────────────── */
.framework-tag {
  display: inline-block; font-size: 0.7rem;
  padding: 0.15rem 0.5rem; border-radius: 4px;
  background: var(--accent-glow); color: var(--accent);
  margin-bottom: 0.75rem;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}
.ctrl-desc {
  font-size: 0.82rem; color: var(--text-dim);
  line-height: 1.5; margin: 0.5rem 0 0.75rem 0;
  padding: 0.5rem 0.85rem;
  background: var(--bg); border-radius: 6px;
  border-left: 3px solid var(--accent);
}
.ctrl-tag[title] { cursor: help; }
.ctrl-tag {
  display: inline-block; font-size: 0.7rem;
  padding: 0.15rem 0.5rem; border-radius: 4px;
  background: var(--green-bg); color: var(--green);
  margin-right: 0.4rem; margin-bottom: 0.3rem;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}
.rationale {
  background: var(--bg); border-radius: 8px;
  padding: 0.75rem 1rem; font-size: 0.85rem;
  margin-bottom: 1rem; line-height: 1.5;
  color: var(--text-dim);
  border-left: 3px solid var(--accent);
}
.evidence-label {
  font-size: 0.75rem; text-transform: uppercase;
  color: var(--text-dim);
  letter-spacing: 0.05em; margin-bottom: 0.5rem;
}

/* ── Policy-view doc header ───────────────────── */
.doc-header {
  font-size: 0.85rem; color: var(--text-dim);
  margin-bottom: 0.25rem;
}
.doc-count {
  color: var(--text-dim); font-size: 0.8rem;
}
.chunk-section {
  margin-bottom: 1rem; padding-top: 0.5rem;
}
.chunk-section:not(:last-child) {
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.75rem;
}
.chunk-text {
  font-size: 0.85rem; color: var(--text-dim);
  line-height: 1.55; margin: 0.5rem 0;
  padding: 0.6rem 0.85rem;
  background: var(--bg); border-radius: 6px;
}
.chunk-meta {
  font-size: 0.78rem; color: var(--text-dim);
  margin-bottom: 0.4rem;
}
.chunk-num {
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem; font-weight: 600;
  color: var(--accent);
  background: rgba(99,102,241,0.1);
  padding: 1px 6px; border-radius: 4px;
  margin-right: 4px;
}
.page-separator {
  display: flex; align-items: center; gap: 0.75rem;
  margin: 1.25rem 0 0.75rem 0;
  font-size: 0.7rem; font-weight: 600;
  color: var(--accent); text-transform: uppercase;
  letter-spacing: 0.05em;
}
.page-separator::before, .page-separator::after {
  content: ''; flex: 1;
  border-top: 1px dashed var(--border);
}
.page-separator:first-child { margin-top: 0; }

/* ── Tables ───────────────────────────────────── */
table {
  width: 100%; border-collapse: collapse;
  font-size: 0.82rem;
}
th {
  text-align: left; padding: 0.5rem 0.75rem;
  background: var(--bg); color: var(--text-dim);
  font-size: 0.7rem; text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid var(--border);
}
td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
tr:last-child td { border-bottom: none; }
tr:hover td { background: var(--surface-hover); }
.source-doc {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.78rem; color: var(--accent);
}
.page-num { text-align: center; }
.section-name {
  color: var(--text-dim); font-style: italic;
}
.excerpt {
  max-width: 420px; font-size: 0.8rem;
  color: var(--text-dim); line-height: 1.4;
}
.empty-msg {
  text-align: center; color: var(--text-dim);
  padding: 4rem 2rem; font-size: 1rem;
}
@media (max-width: 768px) {
  body { padding: 1rem; }
  .stats-bar { gap: 0.75rem; }
  .stat { min-width: 100px; padding: 0.75rem; }
  .card-header { flex-wrap: wrap; gap: 0.5rem; }
  .score { min-width: auto; }
}
"""

# ---------------------------------------------------------------------------
# JS
# ---------------------------------------------------------------------------

_JS = """\
document.addEventListener('DOMContentLoaded', () => {
  // ── Tab switching ──────────────────────────────
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      document.querySelectorAll('.tab-btn')
        .forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel')
        .forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(target)
        .classList.add('active');
    });
  });

  // ── Collapsible cards ──────────────────────────
  document.querySelectorAll('.card-header').forEach(h => {
    h.addEventListener('click', () =>
      h.closest('.card').classList.toggle('open'));
  });

  // ── Filter buttons (framework-gap tab) ─────────
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const filter = btn.dataset.filter;
      const panel = btn.closest('.tab-panel');
      panel.querySelectorAll('.filter-btn')
        .forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      panel.querySelectorAll('.card').forEach(card => {
        if (filter === 'all') {
          card.style.display = '';
        } else {
          const v = card.dataset.verdict;
          card.style.display = v === filter ? '' : 'none';
        }
      });
    });
  });
});
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def format_html(
    results: list[MappedResult],
    all_chunks: list[ParsedChunk] | None = None,
) -> str:
    """Format mapping results as a dual-tab interactive HTML page.

    Tab 1 — *Framework Gap Analysis*: one card per framework control.
    Tab 2 — *Policy Coverage*: one card per source document showing
    which controls each policy chunk satisfies.

    Args:
        results: List of MappedResult objects to format.
        all_chunks: Optional list of all extracted chunks. When provided,
            the Policy Coverage tab shows every chunk, not just matched ones.

    Returns:
        A complete HTML document string.
    """
    gap_html = _render_framework_gap_tab(results)
    cov_html = _render_policy_coverage_tab(results, all_chunks=all_chunks)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ctrlmap — Compliance Mapping Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter\
:wght@400;500;600;700"
      rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono\
:wght@400;600"
      rel="stylesheet">
<style>{_CSS}</style>
</head>
<body>
<h1>Compliance Mapping Report</h1>
<p class="subtitle">\
Generated by ctrlmap — policy-to-framework control mapping\
 with AI rationale</p>

<div class="tabs">
  <button class="tab-btn active" data-tab="framework-gap">\
Framework Gap Analysis</button>
  <button class="tab-btn" data-tab="policy-coverage">\
Policy Coverage</button>
</div>

<div id="framework-gap" class="tab-panel active">
{gap_html}
</div>

<div id="policy-coverage" class="tab-panel">
{cov_html}
</div>

<script>{_JS}</script>
</body>
</html>
"""


def export_html(
    results: list[MappedResult],
    path: Path,
    all_chunks: list[ParsedChunk] | None = None,
) -> None:
    """Write mapping results as an interactive HTML report to disk.

    Args:
        results: List of MappedResult objects to export.
        path: Output file path.
    """
    content = format_html(results, all_chunks=all_chunks)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        suffix=".tmp",
        delete=False,
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.rename(path)


# ---------------------------------------------------------------------------
# Tab 1: Framework Gap Analysis (control-centric)
# ---------------------------------------------------------------------------


def _render_framework_gap_tab(results: list[MappedResult]) -> str:
    """Build the content for the Framework Gap Analysis tab."""
    if not results:
        return '<div class="empty-msg">No mapping results to display.</div>'

    compliant = sum(
        1 for r in results if isinstance(r.rationale, MappingRationale) and r.rationale.is_compliant
    )
    noncompliant = len(results) - compliant

    stats = f"""
    <div class="stats-bar">
      <div class="stat">
        <div class="stat-value">{len(results)}</div>
        <div class="stat-label">Total Controls</div>
      </div>
      <div class="stat">
        <div class="stat-value" style="color:var(--green)">\
{compliant}</div>
        <div class="stat-label">Compliant</div>
      </div>
      <div class="stat">
        <div class="stat-value" style="color:var(--yellow)">\
{noncompliant}</div>
        <div class="stat-label">Non-Compliant</div>
      </div>
    </div>
    """

    filters = """
    <div class="filters">
      <button class="filter-btn active" data-filter="all">\
All</button>
      <button class="filter-btn" data-filter="compliant">\
Compliant</button>
      <button class="filter-btn" data-filter="noncompliant">\
Non-Compliant</button>
    </div>
    """

    cards = "\n".join(_render_gap_card(r) for r in results)
    return f"{stats}\n{filters}\n{cards}"


def _render_gap_card(result: MappedResult) -> str:
    """Render one card for the Framework Gap tab."""
    ctrl = result.control
    vcls, vlbl, score = _classify_verdict(result.rationale)

    rows = []
    for i, c in enumerate(result.supporting_chunks, 1):
        src = html.escape(c.document_name)
        sec = html.escape(c.section_header or "\u2014")
        exc = html.escape(c.raw_text.replace("\n", " ").strip())
        rows.append(
            f"<tr><td>{i}</td>"
            f'<td class="source-doc">{src}</td>'
            f'<td class="page-num">{c.page_number}</td>'
            f'<td class="section-name">{sec}</td>'
            f'<td class="excerpt">{exc}</td></tr>'
        )

    ev = ""
    if rows:
        ev = (
            '<div class="evidence-label">Supporting Evidence</div>'
            "<table><thead><tr>"
            "<th>#</th><th>Source</th><th>Page</th>"
            "<th>Section</th><th>Excerpt</th>"
            "</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    _icon_clipboard = (
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" style="vertical-align:-2px;margin-right:4px">'
        '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1'
        '-2-2V6a2 2 0 0 1 2-2h2"/>'
        '<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>'
        '<path d="M9 14l2 2 4-4"/></svg>'
    )
    _icon_sparkle = (
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" style="vertical-align:-2px;margin-right:4px">'
        '<path d="M12 3l1.912 5.813a2 2 0 0 0 1.275 1.275L21 12l-5.813 '
        "1.912a2 2 0 0 0-1.275 1.275L12 21l-1.912-5.813a2 2 0 0 0-1.275"
        '-1.275L3 12l5.813-1.912a2 2 0 0 0 1.275-1.275L12 3z"/></svg>'
    )

    rat = ""
    rtxt = _get_rationale_text(result.rationale)
    if rtxt:
        rat = (
            f'<div class="evidence-label">{_icon_sparkle}AI Analysis</div>'
            f'<div class="rationale">{html.escape(rtxt)}</div>'
        )

    desc = html.escape(ctrl.description) if ctrl.description else ""
    desc_html = (
        f'<div class="evidence-label">{_icon_clipboard}'
        f"Framework Requirement</div>"
        f'<div class="ctrl-desc">{desc}</div>'
        if desc
        else ""
    )

    return f"""
    <div class="card" data-verdict="{vcls}">
      <div class="card-header">
        <span class="chevron">&#9654;</span>
        <span class="ctrl-id">{html.escape(ctrl.control_id)}</span>
        <span class="ctrl-title">{html.escape(ctrl.title)}</span>
        <span class="badge badge-{vcls}">{vlbl}</span>
        <span class="score">{score}</span>
      </div>
      <div class="card-body">
        <span class="framework-tag">\
{html.escape(ctrl.framework)}</span>
        {desc_html}
        {rat}
        {ev}
      </div>
    </div>
    """


# ---------------------------------------------------------------------------
# Tab 2: Policy Coverage (document-centric)
# ---------------------------------------------------------------------------


def _render_policy_coverage_tab(
    results: list[MappedResult],
    all_chunks: list[ParsedChunk] | None = None,
) -> str:
    """Build the content for the Policy Coverage tab.

    Shows ALL extracted chunks grouped by document. Chunks matched to
    framework controls display their control tags; unmatched chunks
    display an "Unmapped" tag.

    Args:
        results: Mapping results (used to build chunk→control index).
        all_chunks: Complete chunk list.  Falls back to only matched
            chunks when ``None``.
    """
    # Build an inverted index:  chunk_id → list of control labels
    chunk_controls: dict[str, list[str]] = defaultdict(list)
    # Also keep a unique-chunk registry  chunk_id → ParsedChunk
    chunk_registry: dict[str, ParsedChunk] = {}
    # Control info lookup:  label → (title, description)
    ctrl_info: dict[str, tuple[str, str]] = {}

    for result in results:
        ctrl = result.control
        label = f"{ctrl.framework} {ctrl.control_id}"
        ctrl_info[label] = (ctrl.title, ctrl.description or "")
        for chunk in result.supporting_chunks:
            chunk_controls[chunk.chunk_id].append(label)
            chunk_registry[chunk.chunk_id] = chunk

    # Use all_chunks when provided, falling back to matched-only
    if all_chunks:
        for chunk in all_chunks:
            if chunk.chunk_id not in chunk_registry:
                chunk_registry[chunk.chunk_id] = chunk

    if not chunk_registry:
        return '<div class="empty-msg">No mapping results to display.</div>'

    # Preserve extraction order: use position in all_chunks list
    order_index = {c.chunk_id: i for i, c in enumerate(all_chunks)} if all_chunks else {}

    # Group chunks by document_name
    docs: dict[str, list[ParsedChunk]] = defaultdict(list)
    seen: set[str] = set()
    for cid, chunk in chunk_registry.items():
        if cid not in seen:
            docs[chunk.document_name].append(chunk)
            seen.add(cid)

    # Sort by extraction order (index in all_chunks), falling back to page
    for chunks in docs.values():
        chunks.sort(key=lambda c: order_index.get(c.chunk_id, (c.page_number * 1000)))

    unique_docs = len(docs)
    total_chunks = len(chunk_registry)
    mapped_chunks = sum(1 for cid in chunk_registry if chunk_controls.get(cid))

    stats = f"""
    <div class="stats-bar">
      <div class="stat">
        <div class="stat-value">{unique_docs}</div>
        <div class="stat-label">Source Documents</div>
      </div>
      <div class="stat">
        <div class="stat-value">{total_chunks}</div>
        <div class="stat-label">Extracted Controls</div>
      </div>
      <div class="stat">
        <div class="stat-value" style="color:var(--green)">\
{mapped_chunks}</div>
        <div class="stat-label">Mapped to Framework</div>
      </div>
      <div class="stat">
        <div class="stat-value" style="color:var(--yellow)">\
{total_chunks - mapped_chunks}</div>
        <div class="stat-label">Unmapped</div>
      </div>
    </div>
    """

    cards = "\n".join(
        _render_coverage_card(doc_name, chunks, chunk_controls, ctrl_info)
        for doc_name, chunks in sorted(docs.items())
    )
    return f"{stats}\n{cards}"


def _render_coverage_card(
    doc_name: str,
    chunks: list[ParsedChunk],
    chunk_controls: dict[str, list[str]],
    ctrl_info: dict[str, tuple[str, str]],
) -> str:
    """Render one document card for the Policy Coverage tab.

    Chunks are displayed in extraction order with page separators,
    sequential numbering, and full control text.
    """
    # Collect all unique controls this document covers
    all_ctrls: set[str] = set()
    mapped_count = 0
    for c in chunks:
        ctrls_for_chunk = chunk_controls.get(c.chunk_id, [])
        all_ctrls.update(ctrls_for_chunk)
        if ctrls_for_chunk:
            mapped_count += 1

    sections_html = []
    current_page = -1

    for idx, chunk in enumerate(chunks, 1):
        # Page separator
        if chunk.page_number != current_page:
            current_page = chunk.page_number
            sections_html.append(
                f'<div class="page-separator"><span>Page {current_page}</span></div>'
            )

        ctrls = chunk_controls.get(chunk.chunk_id, [])
        if ctrls:
            tag_parts = []
            for c in sorted(set(ctrls)):
                title, desc = ctrl_info.get(c, ("", ""))
                tooltip = html.escape(f"{title}: {desc}" if desc else title)
                tag_parts.append(
                    f'<span class="ctrl-tag" title="{tooltip}">{html.escape(c)}</span>'
                )
            tags = "".join(tag_parts)
        else:
            tags = (
                '<span class="ctrl-tag" style="background:var(--yellow);color:#000">Unmapped</span>'
            )
        sec = html.escape(chunk.section_header or "\u2014")
        txt = html.escape(chunk.raw_text.replace("\n", " ").strip())
        sections_html.append(f"""
        <div class="chunk-section">
          <div class="chunk-meta">\
<span class="chunk-num">#{idx}</span> \
<em>{sec}</em></div>
          <div class="chunk-text">{txt}</div>
          <div>{tags}</div>
        </div>
        """)

    unmapped_count = len(chunks) - mapped_count

    return f"""
    <div class="card">
      <div class="card-header">
        <span class="chevron">&#9654;</span>
        <span class="ctrl-id">{html.escape(doc_name)}</span>
        <span class="ctrl-title">\
{len(chunks)} chunks · \
<span style="color:var(--green)">{mapped_count} mapped</span> · \
<span style="color:var(--yellow)">{unmapped_count} unmapped</span></span>
      </div>
      <div class="card-body">
        {"".join(sections_html)}
      </div>
    </div>
    """


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _classify_verdict(
    rationale: MappingRationale | InsufficientEvidence | None,
) -> tuple[str, str, str]:
    """Return (css_class, label, score_display) for a verdict."""
    if isinstance(rationale, MappingRationale) and rationale.is_compliant:
        return (
            "compliant",
            "Compliant",
            f"{rationale.confidence_score:.2f}",
        )
    # Everything else is Non-Compliant: explicit non-compliance,
    # insufficient evidence, or no evidence at all.
    score = ""
    if isinstance(rationale, MappingRationale):
        score = f"{rationale.confidence_score:.2f}"
    return ("noncompliant", "Non-Compliant", score)


def _get_rationale_text(
    rationale: MappingRationale | InsufficientEvidence | None,
) -> str:
    """Extract the explanation text from a rationale."""
    if rationale is None:
        return ""
    if isinstance(rationale, MappingRationale):
        return rationale.explanation
    return rationale.reason


def _truncate(text: str, max_len: int = 150) -> str:
    """Truncate text to max_len characters, adding ellipsis if needed."""
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
