document.addEventListener('DOMContentLoaded', () => {
  // ── Tab switching (with search persistence) ────
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
      // Re-apply search filter to the newly active tab
      applySearchFilter();
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

  // ── Framework pills ────────────────────────────
  document.querySelectorAll('.fw-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const fw = pill.dataset.fw;
      document.querySelectorAll('.fw-pill')
        .forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      document.querySelectorAll('.card[data-framework]').forEach(card => {
        if (fw === 'all') {
          card.style.display = '';
        } else {
          card.style.display = card.dataset.framework === fw ? '' : 'none';
        }
      });
    });
  });

  // ── Search (persists across tabs) ──────────────
  const searchBox = document.getElementById('search-box');

  function applySearchFilter() {
    if (!searchBox) return;
    const query = searchBox.value.toLowerCase().trim();
    const activePanel = document.querySelector('.tab-panel.active');
    if (!activePanel) return;

    // Filter cards
    activePanel.querySelectorAll('.card').forEach(card => {
      if (!query) { card.style.display = ''; return; }
      card.style.display = card.textContent.toLowerCase().includes(query) ? '' : 'none';
    });

    // Document Reader: filter chunks (text-based)
    activePanel.querySelectorAll('.doc-reader-chunk').forEach(chunk => {
      if (!query) { chunk.style.display = ''; return; }
      chunk.style.display = chunk.textContent.toLowerCase().includes(query) ? '' : 'none';
    });

    // PDF viewer: filter pages containing matching overlays
    activePanel.querySelectorAll('.pdf-page').forEach(page => {
      if (!query) { page.style.display = ''; return; }
      const overlays = page.querySelectorAll('.pdf-overlay');
      const hasMatch = Array.from(overlays).some(o =>
        (o.dataset.popover || '').toLowerCase().includes(query)
      );
      const pageText = page.textContent.toLowerCase();
      page.style.display = (hasMatch || pageText.includes(query)) ? '' : 'none';
    });
  }

  if (searchBox) {
    let debounceTimer;
    searchBox.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(applySearchFilter, 200);
    });

    // Keyboard shortcut: Cmd+K / Ctrl+K
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchBox.focus();
        searchBox.select();
      }
    });

    // Show correct modifier key for the platform
    const kbdEl = document.getElementById('search-kbd');
    if (kbdEl) {
      const isMac = /Mac|iPod|iPhone|iPad/.test(navigator.platform);
      kbdEl.textContent = isMac ? '⌘K' : 'Ctrl+K';
    }
  }

  // ── PDF document selector ──────────────────────
  const pdfSelector = document.getElementById('pdf-doc-selector');
  if (pdfSelector) {
    pdfSelector.addEventListener('change', () => {
      const selected = pdfSelector.value;
      document.querySelectorAll('.pdf-doc-pages').forEach(el => {
        el.style.display = el.id === selected ? '' : 'none';
      });
      const activeDocs = document.getElementById(selected);
      if (activeDocs) {
        const pages = activeDocs.querySelectorAll('.pdf-page');
        const info = document.getElementById('pdf-page-info');
        if (info) info.textContent = `${pages.length} pages`;
      }
      // Clear detail panel on document switch
      clearDetailPanel();
    });
    pdfSelector.dispatchEvent(new Event('change'));
  }

  // ── Detail panel for PDF overlays ──────────────
  const detailPanel = document.getElementById('pdf-detail-panel');
  const detailContent = document.getElementById('pdf-detail-content');
  const detailEmpty = document.getElementById('pdf-detail-empty');
  let activeChunkId = null;

  // Get sibling overlays for a chunk, scoped to the nearest PDF
  // doc container so the same chunk ID on a different page won't match.
  function _getSiblings(chunkId, referenceEl) {
    const scope = referenceEl
      ? (referenceEl.closest('.pdf-doc-pages') || document)
      : document;
    return scope.querySelectorAll(`.pdf-overlay[data-chunk-id="${chunkId}"]`);
  }

  function clearDetailPanel() {
    if (detailContent) { detailContent.style.display = 'none'; detailContent.innerHTML = ''; }
    if (detailEmpty) detailEmpty.style.display = '';
    if (activeChunkId) {
      _getSiblings(activeChunkId).forEach(o => o.classList.remove('pdf-overlay--active'));
      activeChunkId = null;
    }
  }

  function populateDetailPanel(overlay) {
    if (!detailPanel || !detailContent || !detailEmpty) return;
    if (!overlay.dataset.popover) return;
    const chunkId = overlay.dataset.chunkId;

    // Deselect prev
    if (activeChunkId) {
      _getSiblings(activeChunkId).forEach(o => o.classList.remove('pdf-overlay--active'));
    }
    // Activate ALL overlays with this chunk_id (cross-page linking)
    activeChunkId = chunkId;
    _getSiblings(chunkId).forEach(o => o.classList.add('pdf-overlay--active'));

    try {
      const controls = JSON.parse(overlay.dataset.popover);
      if (!Array.isArray(controls) || controls.length === 0) {
        clearDetailPanel();
        return;
      }

      let cards = '';
      controls.forEach(ctrl => {
        cards += `
          <div class="pdf-detail-card">
            <div class="pdf-detail-card-id">${escHtml(ctrl.id)}</div>
            <div class="pdf-detail-card-title">${escHtml(ctrl.title)}</div>
            <div class="pdf-detail-card-meta">
              <span class="badge badge-${complianceCls(ctrl.compliance)}">${escHtml(ctrl.compliance)}</span>
              ${ctrl.confidence ? `<span class="score">${escHtml(ctrl.confidence)}</span>` : ''}
            </div>
            ${ctrl.description ? `
              <div class="pdf-detail-card-section">
                <div class="pdf-detail-card-label">Requirement</div>
                <div class="pdf-detail-card-text">${escHtml(ctrl.description)}</div>
              </div>
            ` : ''}
            ${ctrl.rationale ? `
              <div class="pdf-detail-card-section">
                <div class="pdf-detail-card-label">AI Justification</div>
                <div class="pdf-detail-card-text">${escHtml(ctrl.rationale)}</div>
              </div>
            ` : ''}
          </div>
        `;
      });

      detailContent.innerHTML = cards;
      detailContent.style.display = '';
      detailEmpty.style.display = 'none';
    } catch { /* ignore parse errors */ }
  }

  // Pick the first overlay in DOM order — the HTML renderer outputs
  // paragraph-level chunks before sentence-level sub-chunks, so the
  // first match is always the most inclusive overlay.
  function _pickFirst(overlays) {
    return overlays[0] || null;
  }

  // Find all overlays whose bounding rect contains the given point.
  // Unlike elementsFromPoint, this works through clip-paths.
  function _overlaysAtPoint(clientX, clientY) {
    // Find the page container under the cursor
    const elems = document.elementsFromPoint(clientX, clientY);
    let container = null;
    for (const el of elems) {
      if (el.classList.contains('pdf-page-container')) { container = el; break; }
      const c = el.closest('.pdf-page-container');
      if (c) { container = c; break; }
    }
    if (!container) return [];
    const overlays = container.querySelectorAll('.pdf-overlay');
    const hits = [];
    for (const o of overlays) {
      const r = o.getBoundingClientRect();
      if (clientX >= r.left && clientX <= r.right &&
          clientY >= r.top && clientY <= r.bottom) {
        hits.push(o);
      }
    }
    return hits;
  }

  // Click an overlay to pin it to the detail panel
  document.addEventListener('click', (e) => {
    const allAtPoint = _overlaysAtPoint(e.clientX, e.clientY);
    const overlay = _pickFirst(allAtPoint);
    if (overlay) {
      populateDetailPanel(overlay);
    } else if (detailPanel && !e.target.closest('.pdf-detail-panel')) {
      clearDetailPanel();
    }
  });

  // Track currently hovered chunk ID and a reference overlay for cleanup
  let hoveredChunkId = null;
  let hoveredRefEl = null;

  // Find all overlays on the same page(s) that physically overlap with
  // any of the given overlay elements but belong to a different chunk.
  function _findOverlapping(hoveredOverlays, hoveredCid) {
    const hidden = [];
    for (const hov of hoveredOverlays) {
      const container = hov.closest('.pdf-page-container');
      if (!container) continue;
      const hr = hov.getBoundingClientRect();
      for (const other of container.querySelectorAll('.pdf-overlay')) {
        if (other.dataset.chunkId === hoveredCid) continue;
        const or = other.getBoundingClientRect();
        if (hr.left < or.right && hr.right > or.left &&
            hr.top < or.bottom && hr.bottom > or.top) {
          hidden.push(other);
        }
      }
    }
    return hidden;
  }

  // Hover: highlight the first (most inclusive) overlay at cursor position
  document.addEventListener('mousemove', (e) => {
    const allAtPoint = _overlaysAtPoint(e.clientX, e.clientY);
    const topOverlay = _pickFirst(allAtPoint);
    const topCid = topOverlay ? topOverlay.dataset.chunkId : null;

    // Same chunk — no change needed
    if (topCid === hoveredChunkId) return;

    // Remove previous hover + reset z-index + restore hidden overlays
    if (hoveredChunkId) {
      _getSiblings(hoveredChunkId, hoveredRefEl).forEach(o => {
        o.classList.remove('pdf-overlay--hover');
        o.style.zIndex = '';
      });
      document.querySelectorAll('[data-hover-hidden]').forEach(o => {
        o.style.visibility = '';
        o.removeAttribute('data-hover-hidden');
      });
    }

    // Add new hover + boost z-index + hide overlapping overlays
    hoveredChunkId = topCid;
    hoveredRefEl = topOverlay;
    if (topCid) {
      const siblings = _getSiblings(topCid, topOverlay);
      siblings.forEach(o => {
        o.classList.add('pdf-overlay--hover');
        o.style.zIndex = '20';
      });
      // Hide non-hovered overlays that physically overlap
      _findOverlapping(siblings, topCid).forEach(o => {
        o.style.visibility = 'hidden';
        o.setAttribute('data-hover-hidden', 'true');
      });
    }

    // Populate detail panel with topmost overlay (if nothing pinned)
    if (!activeChunkId && topOverlay) {
      populateDetailPanel(topOverlay);
    }
  });

  document.addEventListener('mouseout', (e) => {
    const overlay = e.target.closest('.pdf-overlay');
    if (!overlay) return;
    if (hoveredChunkId) {
      _getSiblings(hoveredChunkId, hoveredRefEl).forEach(o => {
        o.classList.remove('pdf-overlay--hover');
        o.style.zIndex = '';
      });
      document.querySelectorAll('[data-hover-hidden]').forEach(o => {
        o.style.visibility = '';
        o.removeAttribute('data-hover-hidden');
      });
      hoveredChunkId = null;
      hoveredRefEl = null;
    }
  });

  // ── Popover for text-based reader tags ─────────
  const popoverEl = document.createElement('div');
  popoverEl.className = 'ctrl-popover';
  popoverEl.style.display = 'none';
  document.body.appendChild(popoverEl);

  document.addEventListener('mouseover', (e) => {
    const tag = e.target.closest('.ctrl-tag[data-popover]');
    if (!tag) return;
    try {
      const data = JSON.parse(tag.dataset.popover);
      popoverEl.innerHTML = `
        <div class="ctrl-popover-id">${escHtml(data.id)}</div>
        <div class="ctrl-popover-title">${escHtml(data.title)}</div>
        <div class="ctrl-popover-meta">
          <span class="badge badge-${complianceCls(data.compliance)}">${escHtml(data.compliance)}</span>
          ${data.confidence ? `<span class="score">${escHtml(data.confidence)}</span>` : ''}
        </div>
        ${data.explanation ? `<div class="ctrl-popover-explanation">${escHtml(data.explanation)}</div>` : ''}
      `;
      const rect = tag.getBoundingClientRect();
      popoverEl.style.position = 'fixed';
      popoverEl.style.display = 'block';
      popoverEl.style.left = Math.min(rect.left, window.innerWidth - 320) + 'px';
      popoverEl.style.bottom = (window.innerHeight - rect.top + 8) + 'px';
      popoverEl.style.maxWidth = '300px';
      popoverEl.style.transform = 'none';
    } catch { /* ignore parse errors */ }
  });

  document.addEventListener('mouseout', (e) => {
    const tag = e.target.closest('.ctrl-tag[data-popover]');
    if (tag) popoverEl.style.display = 'none';
  });

  function escHtml(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
  }

  function complianceCls(label) {
    if (!label) return 'noncompliant';
    const l = label.toLowerCase();
    if (l.includes('non')) return 'noncompliant';
    if (l.includes('partial')) return 'partial';
    if (l.includes('compliant')) return 'compliant';
    return 'noncompliant';
  }
});
