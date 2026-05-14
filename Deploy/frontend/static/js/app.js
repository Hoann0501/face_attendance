/* ============================================================
   Face Attendance SPA – Router + utilities
   ============================================================ */

// ---------- Toast notifications ----------
const Toast = {
  show(msg, type = 'info', duration = 3500) {
    const c = document.getElementById('toast-container');
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    const icons = { success: '', error: '', warning: '', info: '' };
    t.innerHTML = `<span>${msg}</span>`;
    c.appendChild(t);
    setTimeout(() => {
      t.style.animation = 'slideOut .2s ease forwards';
      setTimeout(() => t.remove(), 200);
    }, duration);
  },
  success: (m) => Toast.show(m, 'success'),
  error:   (m) => Toast.show(m, 'error'),
  warning: (m) => Toast.show(m, 'warning'),
  info:    (m) => Toast.show(m, 'info'),
};

// ---------- Utility helpers ----------
const fmt = {
  pct: (v) => v != null ? (v * 100).toFixed(1) + '%' : '–',
  num: (v, d = 3) => v != null ? Number(v).toFixed(d) : '–',
  date: (s) => s ? s.slice(0, 10) : '–',
  time: (s) => s ? s.slice(0, 19) : '–',
  badge(status) {
    const map = {
      active: 'badge-green', inactive: 'badge-red',
      PRESENT: 'badge-green', CHECKED_OUT: 'badge-blue',
      ABSENT: 'badge-red', CHECKED_IN: 'badge-green',
      CHECK_IN: 'badge-green', CHECK_OUT: 'badge-blue',
    };
    return `<span class="badge ${map[status] || 'badge-gray'}">${status}</span>`;
  },
  simBar(sim, threshold = 0.35) {
    const pct = Math.max(0, Math.min(100, sim * 100)).toFixed(0);
    const cls = sim >= threshold ? '' : sim >= threshold * 0.7 ? 'mid' : 'low';
    return `<div class="sim-bar-wrap">
      <div class="sim-bar"><div class="sim-bar-fill ${cls}" style="width:${pct}%"></div></div>
      <span style="font-size:12px;color:var(--text-muted);min-width:38px">${Number(sim).toFixed(3)}</span>
    </div>`;
  },
};

function el(id) { return document.getElementById(id); }
function qs(sel, ctx = document) { return ctx.querySelector(sel); }
function qsa(sel, ctx = document) { return [...ctx.querySelectorAll(sel)]; }

function setContent(html) {
  el('content').innerHTML = html;
}

// ---------- Router ----------
const PAGES = {
  dashboard:       { title: 'Dashboard',           render: renderDashboard },
  people:          { title: 'Quan ly nguoi',        render: renderPeople },
  'face-search':   { title: 'Tim kiem / Xac minh',  render: renderFaceSearch },
  'face-analysis': { title: 'Phan tich anh',        render: renderFaceAnalysis },
  attendance:      { title: 'Bao cao diem danh',    render: renderAttendance },
  pipeline:        { title: 'Pipeline Report',      render: renderPipeline },
  // register still accessible as internal page (no nav item)
  register:        { title: 'Dang ky khuon mat',    render: renderRegister },
};

function navigate(hash) {
  const raw = (hash.replace(/^#/, '') || 'dashboard');

  // Sub-route: #people/person_003
  if (raw.startsWith('people/')) {
    const pid = decodeURIComponent(raw.slice(7));
    qsa('.nav-item').forEach(a => a.classList.toggle('active', a.dataset.page === 'people'));
    el('page-title').textContent = 'Chi tiet nguoi';
    setContent('<div class="loading-spinner"><div class="spinner"></div></div>');
    if (typeof renderPeopleDetail === 'function') renderPeopleDetail(pid);
    return;
  }

  const key  = raw;
  const page = PAGES[key] || PAGES['dashboard'];

  // Update active nav
  qsa('.nav-item').forEach(a => {
    a.classList.toggle('active', a.dataset.page === key);
  });
  el('page-title').textContent = page.title;

  // Render page
  setContent('<div class="loading-spinner"><div class="spinner"></div></div>');
  try { page.render(); } catch(e) {
    setContent(`<div class="empty-state"><p>Page error: ${e.message}</p></div>`);
  }
}

// ---------- Sidebar toggle ----------
el('menu-toggle').addEventListener('click', () => {
  const sidebar = el('sidebar');
  const wrapper = qs('.main-wrapper');
  sidebar.classList.toggle('collapsed');
  wrapper.classList.toggle('expanded');
  // mobile
  sidebar.classList.toggle('open');
});

// ---------- Nav clicks ----------
qsa('.nav-item').forEach(a => {
  a.addEventListener('click', (e) => {
    e.preventDefault();
    const page = a.dataset.page;
    history.pushState(null, '', '#' + page);
    navigate('#' + page);
    // mobile: close sidebar
    if (window.innerWidth < 768) {
      el('sidebar').classList.remove('open');
    }
  });
});

// ---------- Hash routing ----------
window.addEventListener('popstate', () => navigate(window.location.hash));

// ---------- API health check ----------
async function checkApiHealth() {
  const dot   = el('status-dot');
  const label = el('status-label');
  try {
    await API.get('/health');
    dot.className   = 'status-dot online';
    label.textContent = 'Backend online';
  } catch {
    dot.className   = 'status-dot offline';
    label.textContent = 'Backend offline';
  }
}

// ---------- Tab helper ----------
function initTabs(container) {
  const tabs     = qsa('.tab', container);
  const contents = qsa('.tab-content', container);
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      contents.forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      contents[i]?.classList.add('active');
    });
  });
}

// ---------- Boot ----------
checkApiHealth();
setInterval(checkApiHealth, 15000);
navigate(window.location.hash || '#dashboard');
