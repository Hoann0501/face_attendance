/* People management page */

function renderPeople() {
  setContent(`
    <div class="two-col-lg">
      <div>
        <div class="section-header">
          <h2>Registered People</h2>
          <button class="btn btn-secondary btn-sm" onclick="_reloadPeople()">Refresh</button>
        </div>
        <div class="card" style="padding:0">
          <div id="people-table-wrap" style="padding:20px">
            <div class="loading-spinner"><div class="spinner"></div></div>
          </div>
        </div>
      </div>

      <div>
        <div class="card" id="person-form-card">
          <div class="card-title">Add / Update Person</div>
          <form id="person-form" onsubmit="return _submitPerson(event)">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Person ID *</label>
                <input class="form-input" id="pf-id" placeholder="person_001" required />
              </div>
              <div class="form-group">
                <label class="form-label">Full Name</label>
                <input class="form-input" id="pf-name" placeholder="Nguyen Van A" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Student Code</label>
                <input class="form-input" id="pf-code" placeholder="SV001" />
              </div>
              <div class="form-group">
                <label class="form-label">Class / Department</label>
                <input class="form-input" id="pf-class" placeholder="CNTT01" />
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">Status</label>
              <select class="form-select" id="pf-status">
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
            <div class="btn-group">
              <button class="btn btn-primary" type="submit">Save</button>
              <button class="btn btn-secondary" type="button" onclick="_clearPersonForm()">Clear</button>
            </div>
          </form>
        </div>

        <div class="card">
          <div class="card-title">Quick Actions</div>
          <div class="form-group">
            <label class="form-label">Select Person</label>
            <select class="form-select" id="pf-select"></select>
          </div>
          <div class="btn-group">
            <button class="btn btn-primary btn-sm" onclick="_setStatus('active')">Set Active</button>
            <button class="btn btn-secondary btn-sm" onclick="_setStatus('inactive')">Set Inactive</button>
            <button class="btn btn-blue btn-sm" onclick="_editPerson()">Edit</button>
            <button class="btn btn-danger btn-sm" onclick="_deletePerson()">Delete</button>
          </div>
        </div>
      </div>
    </div>
  `);

  _loadPeople();
}

let _peopleCache = [];

async function _loadPeople() {
  try {
    _peopleCache = await API.get('/people');
    _renderPeopleTable(_peopleCache);
    _renderPeopleSelect(_peopleCache);
    _setNextId(_peopleCache);
  } catch(e) {
    el('people-table-wrap').innerHTML = `<p style="color:var(--red)">Error: ${e.message}</p>`;
  }
}

function _reloadPeople() { _loadPeople(); }

function _renderPeopleTable(people) {
  const wrap = el('people-table-wrap');
  if (!people.length) {
    wrap.innerHTML = '<div class="empty-state"><p>No people registered yet</p></div>';
    return;
  }
  wrap.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th>ID</th><th>Full Name</th><th>Student Code</th><th>Class</th><th>Status</th><th>Template</th>
        </tr></thead>
        <tbody>${people.map(p => `
          <tr>
            <td class="td-mono">${p.person_id}</td>
            <td class="td-strong">${p.full_name || '-'}</td>
            <td class="td-muted">${p.student_code || '-'}</td>
            <td class="td-muted">${p.class_name || '-'}</td>
            <td>${fmt.badge(p.status)}</td>
            <td>${p.has_template
              ? '<span style="color:var(--green);font-size:12px;font-weight:600">Enrolled</span>'
              : '<span style="color:var(--text-muted);font-size:12px">Not enrolled</span>'}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
}

function _renderPeopleSelect(people) {
  const sel = el('pf-select');
  if (!sel) return;
  sel.innerHTML = people.length
    ? people.map(p => `<option value="${p.person_id}">${p.person_id} — ${p.full_name || ''}</option>`).join('')
    : '<option>No people found</option>';
}

function _setNextId(people) {
  const pfId = el('pf-id');
  if (!pfId || pfId.dataset.edited) return;
  const nums = people.map(p => { const m = p.person_id.match(/^person_(\d+)$/); return m ? parseInt(m[1]) : 0; });
  const next = (nums.length ? Math.max(...nums) : 0) + 1;
  pfId.value = `person_${String(next).padStart(3, '0')}`;
}

function _clearPersonForm() {
  ['pf-id','pf-name','pf-code','pf-class'].forEach(id => { const e = el(id); if(e) e.value=''; });
  const sel = el('pf-status'); if(sel) sel.value = 'active';
  const pfId = el('pf-id'); if(pfId) { pfId.dataset.edited = ''; _setNextId(_peopleCache); }
}

function _editPerson() {
  const sel = el('pf-select');
  if (!sel || !sel.value) return;
  const p = _peopleCache.find(x => x.person_id === sel.value);
  if (!p) return;
  el('pf-id').value     = p.person_id;
  el('pf-id').dataset.edited = '1';
  el('pf-name').value   = p.full_name || '';
  el('pf-code').value   = p.student_code || '';
  el('pf-class').value  = p.class_name || '';
  el('pf-status').value = p.status || 'active';
}

async function _submitPerson(e) {
  e.preventDefault();
  const pid    = el('pf-id').value.trim();
  const fname  = el('pf-name').value.trim();
  const code   = el('pf-code').value.trim();
  const cls    = el('pf-class').value.trim();
  const status = el('pf-status').value;
  if (!pid) { Toast.error('person_id is required'); return false; }
  const exists = _peopleCache.find(p => p.person_id === pid);
  try {
    if (exists) {
      await API.put(`/people/${pid}`, { full_name: fname, student_code: code, class_name: cls, status });
      Toast.success(`Updated ${pid}`);
    } else {
      await API.post('/people', { person_id: pid, full_name: fname, student_code: code, class_name: cls, status });
      Toast.success(`Added ${pid}`);
    }
    _clearPersonForm(); _loadPeople();
  } catch(err) { Toast.error(err.message); }
  return false;
}

async function _setStatus(status) {
  const sel = el('pf-select');
  if (!sel || !sel.value) { Toast.warning('Select a person first'); return; }
  try {
    await API.patch(`/people/${sel.value}/status`, { status });
    Toast.success(`${sel.value} set to ${status}`);
    _loadPeople();
  } catch(e) { Toast.error(e.message); }
}

async function _deletePerson() {
  const sel = el('pf-select');
  if (!sel || !sel.value) { Toast.warning('Select a person first'); return; }
  if (!confirm(`Delete ${sel.value}? This cannot be undone.`)) return;
  try {
    await API.delete(`/people/${sel.value}`);
    Toast.success(`Deleted ${sel.value}`);
    _loadPeople();
  } catch(e) { Toast.error(e.message); }
}
