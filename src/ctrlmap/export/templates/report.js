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
