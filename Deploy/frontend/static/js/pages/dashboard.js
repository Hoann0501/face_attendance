/* Dashboard page */
let _dashTimer = null;

function renderDashboard() {
  setContent(`
    <div id="dash-root">
      <div class="metrics-grid" id="dash-metrics">
        ${[...Array(6)].map(() => `
          <div class="metric-card">
            <div class="metric-label">Loading</div>
            <div class="metric-value">-</div>
          </div>`).join('')}
      </div>

      <div class="two-col">
        <div class="card">
          <div class="card-title">Recent Activity</div>
          <div id="dash-events"><div class="loading-spinner"><div class="spinner"></div></div></div>
        </div>
        <div class="card">
          <div class="card-title" id="dash-today-title">Today</div>
          <div id="dash-today"></div>
        </div>
      </div>
    </div>
  `);

  _loadDash();
  if (_dashTimer) clearInterval(_dashTimer);
  _dashTimer = setInterval(_loadDash, 5000);
  qsa('.nav-item').forEach(a => a.addEventListener('click', () => {
    clearInterval(_dashTimer); _dashTimer = null;
  }, { once: true }));
}

async function _loadDash() {
  const today = new Date().toISOString().slice(0, 10);
  try {
    const [people, report, events] = await Promise.all([
      API.get('/people'),
      API.get(`/attendance/report?date=${today}`),
      API.get('/attendance/events/recent?limit=15'),
    ]);

    const total      = people.length;
    const active     = people.filter(p => p.status === 'active').length;
    const inactive   = total - active;
    const checkedIn  = (report.present_count || 0) + (report.checked_out_count || 0);
    const checkedOut = report.checked_out_count || 0;
    const absent     = report.absent_count || 0;

    const m = el('dash-metrics');
    if (m) m.innerHTML = `
      <div class="metric-card"><div class="metric-label">Total</div><div class="metric-value">${total}</div></div>
      <div class="metric-card blue"><div class="metric-label">Active</div><div class="metric-value">${active}</div></div>
      <div class="metric-card"><div class="metric-label">Inactive</div><div class="metric-value">${inactive}</div></div>
      <div class="metric-card green"><div class="metric-label">Checked In</div><div class="metric-value">${checkedIn}</div></div>
      <div class="metric-card purple"><div class="metric-label">Checked Out</div><div class="metric-value">${checkedOut}</div></div>
      <div class="metric-card red"><div class="metric-label">Absent</div><div class="metric-value">${absent}</div></div>
    `;

    const evEl = el('dash-events');
    if (evEl) {
      const evs = events.events || [];
      if (!evs.length) {
        evEl.innerHTML = '<div class="empty-state"><p>No activity yet</p></div>';
      } else {
        evEl.innerHTML = `
          <div class="table-wrap">
            <table>
              <thead><tr><th>Time</th><th>Type</th><th>Name</th><th>Student Code</th><th>Similarity</th></tr></thead>
              <tbody>${evs.map(e => `
                <tr>
                  <td class="td-muted">${fmt.time(e.event_time)}</td>
                  <td>${fmt.badge(e.event_type)}</td>
                  <td class="td-strong">${e.full_name || '-'}</td>
                  <td class="td-muted">${e.student_code || '-'}</td>
                  <td>${fmt.simBar(e.similarity || 0)}</td>
                </tr>`).join('')}
              </tbody>
            </table>
          </div>`;
      }
    }

    const todayEl = el('dash-today');
    const titleEl = el('dash-today-title');
    if (titleEl) titleEl.textContent = `Today  ${today}`;
    if (todayEl) {
      const rows = [
        ...(report.present || []).map(r => ({ ...r, _st: 'PRESENT' })),
        ...(report.checked_out || []).map(r => ({ ...r, _st: 'CHECKED_OUT' })),
        ...(report.absent || []).map(r => ({ ...r, _st: 'ABSENT' })),
      ];
      if (!rows.length) {
        todayEl.innerHTML = '<div class="empty-state"><p>No data</p></div>';
      } else {
        todayEl.innerHTML = `
          <div class="table-wrap" style="max-height:340px;overflow-y:auto">
            <table>
              <thead><tr><th>Name</th><th>Code</th><th>Status</th><th>Check-in</th></tr></thead>
              <tbody>${rows.map(r => {
                const cls = r._st === 'PRESENT' ? 'row-present' : r._st === 'ABSENT' ? 'row-absent' : 'row-checkout';
                return `<tr class="${cls}">
                  <td class="td-strong">${r.full_name || r.person_id || '-'}</td>
                  <td class="td-muted">${r.student_code || '-'}</td>
                  <td>${fmt.badge(r._st)}</td>
                  <td class="td-muted td-time">${fmt.time(r.check_in_time)}</td>
                </tr>`;
              }).join('')}</tbody>
            </table>
          </div>`;
      }
    }
  } catch(e) {
    const r = el('dash-metrics');
    if (r) r.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><p>Cannot connect to backend: ${e.message}</p></div>`;
  }
}
