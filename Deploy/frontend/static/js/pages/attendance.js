/* Attendance report page */
let _attTimer = null;

function renderAttendance() {
  const today = new Date().toISOString().slice(0, 10);

  setContent(`
    <div>
      <!-- Controls bar -->
      <div class="card">
        <div class="filter-bar">
          <div class="form-group">
            <label class="form-label">Date</label>
            <input type="date" class="form-input" id="att-date" value="${today}" style="width:auto" />
          </div>
          <div class="form-group">
            <label class="form-label">Search</label>
            <input type="text" class="form-input" id="att-search" placeholder="Name / student code" oninput="_filterAtt()" style="min-width:180px" />
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
  `);

  el('att-date').addEventListener('change', _loadAtt);
  _loadAtt();
  _loadDeleteDropdown();

  if (_attTimer) clearInterval(_attTimer);
  _attTimer = setInterval(() => {
    const d = el('att-date');
    if (d && d.value === new Date().toISOString().slice(0, 10)) _loadAtt();
  }, 5000);

  qsa('.nav-item').forEach(a => a.addEventListener('click', () => {
    clearInterval(_attTimer); _attTimer = null;
  }, { once: true }));
}

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
      <table>
        <thead><tr>
          <th>Full Name</th><th>Student Code</th><th>Class</th>
          <th>Status</th><th>Check-in</th><th>Check-out</th>
          <th>Similarity</th><th>Liveness</th><th></th>
        </tr></thead>
        <tbody>${rows.map(r => {
          const cls = r._status === 'PRESENT' ? 'row-present' : r._status === 'ABSENT' ? 'row-absent' : 'row-checkout';
          const sim = parseFloat(r.check_in_similarity || 0);
          const canDelete = r._status !== 'ABSENT';
          return `<tr class="${cls}">
            <td class="td-strong">${r.full_name || r.person_id || '-'}</td>
            <td class="td-mono">${r.student_code || '-'}</td>
            <td class="td-muted">${r.class_name || '-'}</td>
            <td>${fmt.badge(r._status)}</td>
            <td class="td-muted td-time">${fmt.time(r.check_in_time)}</td>
            <td class="td-muted td-time">${fmt.time(r.check_out_time)}</td>
            <td>${r.check_in_similarity ? fmt.simBar(sim) : '-'}</td>
            <td class="td-muted" style="font-size:12px">${r.check_in_liveness_status || '-'}</td>
            <td>${canDelete ? `<button class="btn-row-del" title="Delete record"
              onclick="_deleteRow('${r.person_id}','${date}')">&#x2715;</button>` : ''}</td>
          </tr>`;
        }).join('')}
        </tbody>
      </table>
    </div>`;
}

async function _deleteRow(personId, date) {
  if (!confirm(`Delete attendance record for ${personId} on ${date}?`)) return;
  try {
    await API.delete(`/attendance?person_id=${encodeURIComponent(personId)}&date=${date}`);
    Toast.success(`Deleted record for ${personId}`);
    _loadAtt();
  } catch(e) { Toast.error(e.message); }
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
  if (!confirm(`Delete attendance record for ${pid} on ${date}?`)) return;
  try {
    await API.delete(`/attendance?person_id=${encodeURIComponent(pid)}&date=${date}`);
    Toast.success(`Deleted ${pid} on ${date}`);
    const attDate = el('att-date');
    if (attDate && attDate.value === date) _loadAtt();
  } catch(e) { Toast.error(e.message); }
}
