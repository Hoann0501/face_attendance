/* Attendance report page */
let _attTimer = null;

function renderAttendance() {
  const today = new Date().toISOString().slice(0, 10);

  setContent(`
    <!-- Top tabs -->
    <div class="tabs" id="att-tabs">
      <div class="tab active" data-tab="report">Attendance Report</div>
      <div class="tab" data-tab="captures">Face Captures</div>
    </div>

    <!-- ── REPORT TAB ─────────────────────────────────────── -->
    <div class="tab-content active" id="tc-report">
      <!-- Controls bar -->
      <div class="card">
        <div class="filter-bar">
          <div class="form-group">
            <label class="form-label">Date</label>
            <input type="date" class="form-input" id="att-date" value="${today}" style="width:auto" />
          </div>
          <div class="form-group">
            <label class="form-label">Search</label>
            <input type="text" class="form-input" id="att-search"
                   placeholder="Name / student code" oninput="_filterAtt()" style="min-width:180px" />
          </div>
          <div class="form-group">
            <label class="form-label">Status</label>
            <select class="form-select" id="att-filter-status" onchange="_filterAtt()" style="width:auto">
              <option value="">All</option>
              <option value="PRESENT">PRESENT</option>
              <option value="CHECKED_OUT">CHECKED_OUT</option>
              <option value="ABSENT">ABSENT</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Class</label>
            <select class="form-select" id="att-filter-class" onchange="_filterAtt()" style="width:auto">
              <option value="">All classes</option>
            </select>
          </div>
          <div style="display:flex;gap:8px;align-items:flex-end">
            <button class="btn btn-secondary" onclick="_loadAtt()">Reload</button>
            <button class="btn btn-blue" onclick="_exportAtt('csv')">Export CSV</button>
            <button class="btn btn-blue" onclick="_exportAtt('xlsx')">Export Excel</button>
          </div>
        </div>
      </div>

      <!-- Stats -->
      <div class="metrics-grid" id="att-stats"></div>

      <!-- Table -->
      <div class="card" style="padding:0">
        <div id="att-table" style="padding:20px">
          <div class="loading-spinner"><div class="spinner"></div></div>
        </div>
      </div>

      <!-- Delete record -->
      <div class="card">
        <div class="card-title">Delete Attendance Record</div>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:14px">
          Remove a specific person's attendance record for the selected date. This cannot be undone.
        </p>
        <div style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap">
          <div class="form-group" style="margin-bottom:0;min-width:220px">
            <label class="form-label">Person</label>
            <select class="form-select" id="att-del-person"></select>
          </div>
          <div class="form-group" style="margin-bottom:0">
            <label class="form-label">Date</label>
            <input type="date" class="form-input" id="att-del-date" value="${today}" style="width:auto" />
          </div>
          <button class="btn btn-danger" onclick="_deleteAttRecord()">Delete Record</button>
        </div>
      </div>
    </div>

    <!-- ── CAPTURES TAB ───────────────────────────────────── -->
    <div class="tab-content" id="tc-captures">
      <div class="card">
        <div class="filter-bar" style="margin-bottom:0">
          <div class="form-group" style="margin-bottom:0">
            <label class="form-label">Date</label>
            <input type="date" class="form-input" id="cap-date" value="${today}" style="width:auto"
                   onchange="_loadCaptures()" />
          </div>
          <div class="form-group" style="margin-bottom:0">
            <label class="form-label">Mode</label>
            <select class="form-select" id="cap-mode-filter" onchange="_filterCaptures()" style="width:auto">
              <option value="">All</option>
              <option value="checkin">Check-In</option>
              <option value="checkout">Check-Out</option>
            </select>
          </div>
          <div class="form-group" style="margin-bottom:0">
            <label class="form-label">Person</label>
            <input type="text" class="form-input" id="cap-person-filter"
                   placeholder="Name / ID" oninput="_filterCaptures()" style="min-width:160px" />
          </div>
          <div style="align-self:flex-end">
            <button class="btn btn-secondary" onclick="_loadCaptures()">Reload</button>
          </div>
        </div>
      </div>

      <div id="cap-stats" style="margin-bottom:16px"></div>
      <div id="cap-grid">
        <div class="loading-spinner"><div class="spinner"></div></div>
      </div>
    </div>
  `);

  // Tab switching
  const tabs = qsa('.tab', el('att-tabs'));
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      qsa('.tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      el('tc-' + tab.dataset.tab).classList.add('active');
      if (tab.dataset.tab === 'captures') _loadCaptures();
    });
  });

  // Pre-load captures in background so it's ready when user clicks
  setTimeout(_loadCaptures, 800);

  el('att-date').addEventListener('change', _loadAtt);
  _loadAtt();
  _loadDeleteDropdown();

  _delDelegationAttached = false;
  _refreshPaused = false;

  if (_attTimer) clearInterval(_attTimer);
  _attTimer = setInterval(() => {
    if (_refreshPaused) return;
    const d = el('att-date');
    if (d && d.value === new Date().toISOString().slice(0, 10)) _loadAtt();
  }, 5000);

  qsa('.nav-item').forEach(a => a.addEventListener('click', () => {
    clearInterval(_attTimer); _attTimer = null;
  }, { once: true }));
}

// ── REPORT logic ──────────────────────────────────────────────────────────────

let _attAllRows = [];

async function _loadAtt() {
  const dateEl = el('att-date');
  if (!dateEl) return;
  const date = dateEl.value;

  const statsEl = el('att-stats');
  const tableEl = el('att-table');
  if (tableEl) tableEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';

  try {
    const report = await API.get(`/attendance/report?date=${date}`);

    if (statsEl) statsEl.innerHTML = `
      <div class="metric-card"><div class="metric-label">Active people</div><div class="metric-value">${report.total_active}</div></div>
      <div class="metric-card green"><div class="metric-label">Present</div><div class="metric-value">${report.present_count}</div></div>
      <div class="metric-card blue"><div class="metric-label">Checked Out</div><div class="metric-value">${report.checked_out_count}</div></div>
      <div class="metric-card red"><div class="metric-label">Absent</div><div class="metric-value">${report.absent_count}</div></div>
    `;

    _attAllRows = [
      ...(report.present     || []).map(r => ({ ...r, _status: 'PRESENT' })),
      ...(report.checked_out || []).map(r => ({ ...r, _status: 'CHECKED_OUT' })),
      ...(report.absent      || []).map(r => ({ ...r, _status: 'ABSENT' })),
    ];

    const classes = [...new Set(_attAllRows.map(r => r.class_name).filter(Boolean))].sort();
    const cf = el('att-filter-class');
    if (cf) {
      const cur = cf.value;
      cf.innerHTML = '<option value="">All classes</option>' +
        classes.map(c => `<option value="${c}"${c===cur?' selected':''}>${c}</option>`).join('');
    }
    _filterAtt();
  } catch(e) {
    if (tableEl) tableEl.innerHTML = `<p style="color:var(--red)">Error: ${e.message}</p>`;
  }
}

function _filterAtt() {
  const search = (el('att-search')?.value || '').trim().toLowerCase();
  const status = el('att-filter-status')?.value || '';
  const classF = el('att-filter-class')?.value || '';

  let rows = _attAllRows;
  if (status) rows = rows.filter(r => r._status === status);
  if (classF) rows = rows.filter(r => r.class_name === classF);
  if (search) rows = rows.filter(r =>
    (r.full_name || '').toLowerCase().includes(search) ||
    (r.student_code || '').toLowerCase().includes(search) ||
    (r.person_id || '').toLowerCase().includes(search)
  );
  _renderAttTable(rows);
}

function _renderAttTable(rows) {
  const tableEl = el('att-table');
  if (!tableEl) return;

  if (!rows.length) {
    tableEl.innerHTML = '<div class="empty-state"><p>No records</p></div>';
    return;
  }

  const date = el('att-date')?.value || '';

  tableEl.innerHTML = `
    <p style="font-size:12px;color:var(--text-muted);margin-bottom:10px">${rows.length} records</p>
    <div class="table-wrap">
      <table id="att-rows-table">
        <thead><tr>
          <th>Full Name</th><th>Student Code</th><th>Class</th>
          <th>Status</th><th>Check-in</th><th>Check-out</th>
          <th>Similarity</th><th>Liveness</th><th></th>
        </tr></thead>
        <tbody>${rows.map(r => {
          const cls      = r._status === 'PRESENT' ? 'row-present' : r._status === 'ABSENT' ? 'row-absent' : 'row-checkout';
          const sim      = parseFloat(r.check_in_similarity || 0);
          const canDelete = r._status !== 'ABSENT';
          return `<tr class="${cls}" data-person="${r.person_id}" data-date="${date}">
            <td class="td-strong">${r.full_name || r.person_id || '-'}</td>
            <td class="td-mono">${r.student_code || '-'}</td>
            <td class="td-muted">${r.class_name || '-'}</td>
            <td>${fmt.badge(r._status)}</td>
            <td class="td-muted td-time">${fmt.time(r.check_in_time)}</td>
            <td class="td-muted td-time">${fmt.time(r.check_out_time)}</td>
            <td>${r.check_in_similarity ? fmt.simBar(sim) : '-'}</td>
            <td class="td-muted" style="font-size:12px">${r.check_in_liveness_status || '-'}</td>
            <td class="att-del-cell">${canDelete
              ? `<button class="btn-row-del att-del-btn" data-person="${r.person_id}" data-date="${date}">&#x2715;</button>`
              : ''}</td>
          </tr>`;
        }).join('')}
        </tbody>
      </table>
    </div>`;

  // Event delegation — survives re-renders because listener is on tableEl (static)
  _attachDeleteDelegation(tableEl);
}

// Keep track so we don't double-attach
let _delDelegationAttached = false;

function _attachDeleteDelegation(tableEl) {
  if (_delDelegationAttached) return;
  _delDelegationAttached = true;

  tableEl.addEventListener('click', (e) => {
    const btn = e.target.closest('.att-del-btn');
    if (!btn || btn.dataset.state === 'confirming' || btn.dataset.state === 'loading') return;

    const personId = btn.dataset.person;
    const date     = btn.dataset.date;

    // Inline two-step confirmation: first click → show "Confirm?", second click → delete
    btn.dataset.state = 'confirming';
    btn.textContent   = 'Confirm?';
    btn.style.cssText = 'color:#fff;background:var(--red-bg);border:1px solid var(--red);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600';

    // Auto-cancel confirm after 3s if no second click
    const cancelTimer = setTimeout(() => _resetDelBtn(btn), 3000);

    btn.addEventListener('click', async (e2) => {
      e2.stopPropagation();
      if (btn.dataset.state !== 'confirming') return;
      clearTimeout(cancelTimer);

      btn.dataset.state = 'loading';
      btn.textContent   = '...';
      btn.style.cssText += ';pointer-events:none;opacity:.7';

      // Pause auto-refresh while deleting to prevent DOM collision
      _pauseRefresh();

      try {
        const res = await API.delete(`/attendance?person_id=${encodeURIComponent(personId)}&date=${date}`);
        const imgs = res?.deleted_images?.length || 0;
        Toast.success(`Deleted: ${personId}` + (imgs ? `  (+${imgs} image${imgs > 1 ? 's' : ''})` : ''));
        _delDelegationAttached = false;
        _loadAtt();
        // Refresh captures grid if visible
        if (el('tc-captures')?.classList.contains('active')) _loadCaptures();
      } catch(err) {
        Toast.error(`Delete failed: ${err.message}`);
        _resetDelBtn(btn);
      } finally {
        _resumeRefresh();
      }
    }, { once: true });
  });
}

function _resetDelBtn(btn) {
  btn.dataset.state = '';
  btn.innerHTML     = '&#x2715;';
  btn.style.cssText = '';
}

let _refreshPaused = false;
function _pauseRefresh()  { _refreshPaused = true; }
function _resumeRefresh() {
  _refreshPaused = false;
  // Resume the timer cycle
  if (_attTimer) {
    clearInterval(_attTimer);
    _attTimer = setInterval(() => {
      if (_refreshPaused) return;
      const d = el('att-date');
      if (d && d.value === new Date().toISOString().slice(0, 10)) _loadAtt();
    }, 5000);
  }
}

function _exportAtt(format) {
  const date = el('att-date')?.value;
  if (!date) return;
  window.location.href = `/attendance/export?date=${date}&format=${format}`;
}

async function _loadDeleteDropdown() {
  try {
    const people = await API.get('/people');
    const sel = el('att-del-person');
    if (!sel) return;
    sel.innerHTML = people.map(p =>
      `<option value="${p.person_id}">${p.person_id} — ${p.full_name || ''}</option>`
    ).join('');
  } catch {}
}

async function _deleteAttRecord() {
  const pid  = el('att-del-person')?.value;
  const date = el('att-del-date')?.value;
  if (!pid || !date) { Toast.warning('Select person and date'); return; }

  const btn = document.querySelector('button[onclick="_deleteAttRecord()"]');

  // Two-step: first click shows warning, second confirms
  if (!btn || btn.dataset.confirming !== '1') {
    if (btn) {
      btn.dataset.confirming = '1';
      btn.textContent = 'Click again to confirm';
      btn.style.background = 'var(--orange)';
      setTimeout(() => {
        if (btn.dataset.confirming === '1') {
          btn.dataset.confirming = '';
          btn.textContent = 'Delete Record';
          btn.style.background = '';
        }
      }, 3000);
    }
    return;
  }

  // Confirmed
  if (btn) {
    btn.dataset.confirming = '';
    btn.textContent = 'Deleting...';
    btn.disabled = true;
  }

  _pauseRefresh();
  try {
    const res2 = await API.delete(`/attendance?person_id=${encodeURIComponent(pid)}&date=${date}`);
    const imgs2 = res2?.deleted_images?.length || 0;
    Toast.success(`Deleted ${pid} on ${date}` + (imgs2 ? `  (+${imgs2} image${imgs2 > 1 ? 's' : ''})` : ''));
    const attDate = el('att-date');
    if (attDate && attDate.value === date) {
      _delDelegationAttached = false;
      _loadAtt();
    }
    if (el('tc-captures')?.classList.contains('active')) _loadCaptures();
  } catch(e) {
    Toast.error(`Delete failed: ${e.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Delete Record';
      btn.style.background = '';
    }
    _resumeRefresh();
  }
}

// ── CAPTURES logic ────────────────────────────────────────────────────────────

let _allCaptures = [];

async function _loadCaptures() {
  const dateEl = el('cap-date');
  const date   = dateEl?.value || new Date().toISOString().slice(0, 10);
  const gridEl  = el('cap-grid');
  const statsEl = el('cap-stats');
  if (gridEl)  gridEl.innerHTML  = '<div class="loading-spinner"><div class="spinner"></div></div>';
  if (statsEl) statsEl.innerHTML = '';

  try {
    const data = await API.get(`/attendance/captures?date=${date}`);
    _allCaptures = data.captures || [];
    console.log('[Captures] Loaded', _allCaptures.length, 'items for', date);

    const checkinCnt  = _allCaptures.filter(c => c.mode === 'checkin').length;
    const checkoutCnt = _allCaptures.filter(c => c.mode === 'checkout').length;

    if (statsEl) statsEl.innerHTML = _allCaptures.length ? `
      <div style="display:flex;gap:12px;flex-wrap:wrap">
        <div class="metric-card green" style="padding:12px 18px;flex:none">
          <div class="metric-label">Check-In photos</div>
          <div class="metric-value">${checkinCnt}</div>
        </div>
        <div class="metric-card blue" style="padding:12px 18px;flex:none">
          <div class="metric-label">Check-Out photos</div>
          <div class="metric-value">${checkoutCnt}</div>
        </div>
      </div>` : '';

    _filterCaptures();
  } catch(e) {
    if (gridEl) gridEl.innerHTML = `<p style="color:var(--red)">Error: ${e.message}</p>`;
  }
}

function _filterCaptures() {
  const mode   = el('cap-mode-filter')?.value || '';
  const search = (el('cap-person-filter')?.value || '').trim().toLowerCase();

  let items = _allCaptures;
  if (mode)   items = items.filter(c => c.mode === mode);
  if (search) items = items.filter(c =>
    (c.full_name   || '').toLowerCase().includes(search) ||
    (c.person_id   || '').toLowerCase().includes(search) ||
    (c.student_code|| '').toLowerCase().includes(search)
  );

  _renderCaptureGrid(items);
}

function _renderCaptureGrid(items) {
  const gridEl = el('cap-grid');
  if (!gridEl) return;

  if (!items.length) {
    gridEl.innerHTML = `
      <div class="empty-state" style="padding:60px 0">
        <p>No face captures found for this date</p>
        <p style="font-size:12px;color:var(--text-muted);margin-top:8px">
          Captures are saved automatically when check-in/check-out succeeds via the camera app.
        </p>
      </div>`;
    return;
  }

  // Group by person for display
  const byPerson = {};
  items.forEach(c => {
    const key = c.person_id;
    if (!byPerson[key]) byPerson[key] = { info: c, items: [] };
    byPerson[key].items.push(c);
  });

  gridEl.innerHTML = Object.values(byPerson).map(group => {
    const info = group.info;
    const name = info.full_name || info.person_id;

    const photos = group.items.map(c => `
      <div class="capture-photo-wrap">
        <div class="capture-photo-img"
             onclick="_openCaptureLightbox('${c.url}','${name}','${c.mode}','${c.timestamp||''}')"
             style="cursor:zoom-in">
          <img src="${c.url}" alt="${name}" loading="lazy"
               onerror="this.style.display='none';this.nextElementSibling&&(this.nextElementSibling.style.display='flex');console.error('[Captures] Failed to load:',this.src)" />
          <div class="capture-broken" style="display:none">Image not found</div>
          <div class="capture-photo-mode ${c.mode === 'checkin' ? 'capture-mode-in' : 'capture-mode-out'}">
            ${c.mode === 'checkin' ? 'Check-In' : 'Check-Out'}
          </div>
        </div>
        <div class="capture-photo-time">${c.timestamp || c.filename}</div>
        <a href="${c.url}" download="${c.filename}" class="capture-dl-btn" title="Download">
          <svg viewBox="0 0 14 14" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M7 1v8M4 6l3 3 3-3M2 11h10"/>
          </svg>
          Download
        </a>
      </div>`).join('');

    return `
      <div class="capture-person-group">
        <div class="capture-person-header">
          <div>
            <span class="capture-person-name">${name}</span>
            <span class="td-mono" style="font-size:12px;margin-left:10px;color:var(--text-muted)">${info.person_id}</span>
            ${info.student_code ? `<span style="font-size:12px;color:var(--text-muted);margin-left:6px">${info.student_code}</span>` : ''}
          </div>
          <span style="font-size:12px;color:var(--text-muted)">${group.items.length} photo(s)</span>
        </div>
        <div class="capture-photos-row">${photos}</div>
      </div>`;
  }).join('');
}

// ── Lightbox ──────────────────────────────────────────────────────────────────

function _openCaptureLightbox(url, name, mode, timestamp) {
  const existing = document.getElementById('cap-lightbox');
  if (existing) existing.remove();

  const lb = document.createElement('div');
  lb.id = 'cap-lightbox';
  lb.style.cssText = `
    position:fixed;inset:0;background:rgba(0,0,0,.88);z-index:9000;
    display:flex;align-items:center;justify-content:center;cursor:zoom-out;
    animation:fadeIn .15s ease;
  `;
  lb.innerHTML = `
    <div style="max-width:90vw;max-height:90vh;text-align:center" onclick="event.stopPropagation()">
      <img src="${url}" style="max-width:100%;max-height:80vh;border-radius:8px;display:block;margin:0 auto" />
      <div style="margin-top:14px;color:#fff;font-size:14px;font-weight:600">${name}</div>
      <div style="color:rgba(255,255,255,.55);font-size:12px;margin-top:4px">
        ${mode === 'checkin' ? 'Check-In' : 'Check-Out'} &nbsp;&bull;&nbsp; ${timestamp}
      </div>
      <div style="margin-top:12px">
        <a href="${url}" download style="color:var(--blue);font-size:13px">Download</a>
        &nbsp;&nbsp;
        <button onclick="document.getElementById('cap-lightbox').remove()"
                style="color:rgba(255,255,255,.6);background:none;border:none;cursor:pointer;font-size:13px">
          Close
        </button>
      </div>
    </div>`;
  lb.addEventListener('click', () => lb.remove());
  document.body.appendChild(lb);
}
