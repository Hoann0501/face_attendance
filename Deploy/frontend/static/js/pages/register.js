/* Face registration page */

function renderRegister() {
  setContent(`
    <div class="two-col">
      <div>
        <div class="card">
          <div class="card-title">Registration Info</div>
          <form id="reg-form" onsubmit="return _submitRegister(event)">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Person ID *</label>
                <input class="form-input" id="reg-id" placeholder="person_001" required />
              </div>
              <div class="form-group">
                <label class="form-label">Full Name</label>
                <input class="form-input" id="reg-name" placeholder="Nguyen Van A" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Student / Staff Code</label>
                <input class="form-input" id="reg-code" placeholder="SV001" />
              </div>
              <div class="form-group">
                <label class="form-label">Class / Department</label>
                <input class="form-input" id="reg-class" placeholder="CNTT01" />
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">Face Images &nbsp;(2 – 10 photos)</label>
              <div class="upload-zone" id="reg-dropzone">
                <input type="file" id="reg-files" accept="image/*" multiple />
                <div class="upload-icon-placeholder"></div>
                <div class="upload-text">
                  <strong>Choose files</strong> or drag and drop here<br>
                  <small>JPG, PNG, WEBP &bull; up to 10 images</small>
                </div>
              </div>
              <div class="preview-grid" id="reg-preview"></div>
            </div>

            <div class="btn-group">
              <button class="btn btn-primary" type="submit" id="reg-submit-btn">Register</button>
              <button class="btn btn-secondary" type="button" onclick="_clearReg()">Clear</button>
            </div>
          </form>
        </div>
      </div>

      <div>
        <div class="card">
          <div class="card-title">Enrollment Status</div>
          <div id="reg-status-list">
            <div class="loading-spinner"><div class="spinner"></div></div>
          </div>
        </div>

        <div class="card" id="reg-result" style="display:none">
          <div class="card-title">Registration Result</div>
          <div id="reg-result-body"></div>
        </div>
      </div>
    </div>
  `);

  _loadRegStatus();
  _initRegDrop();
}

let _regFiles = [];

function _initRegDrop() {
  const input = el('reg-files');
  const zone  = el('reg-dropzone');
  if (!input || !zone) return;

  input.addEventListener('change', () => { _addRegFiles([...input.files]); input.value = ''; });
  zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('drag-over');
    _addRegFiles([...e.dataTransfer.files].filter(f => f.type.startsWith('image/')));
  });
}

function _addRegFiles(files) {
  _regFiles = [..._regFiles, ...files].slice(0, 10);
  _renderRegPreview();
}

function _renderRegPreview() {
  const grid = el('reg-preview');
  if (!grid) return;
  grid.innerHTML = _regFiles.map((f, i) => {
    const url = URL.createObjectURL(f);
    return `<div class="preview-item">
      <img src="${url}" alt="${f.name}" />
      <button class="rm-btn" onclick="_removeRegFile(${i})">&#x2715;</button>
    </div>`;
  }).join('');
}

function _removeRegFile(i) { _regFiles.splice(i, 1); _renderRegPreview(); }

function _clearReg() {
  _regFiles = []; _renderRegPreview();
  ['reg-id','reg-name','reg-code','reg-class'].forEach(id => { const e = el(id); if(e) e.value=''; });
}

async function _loadRegStatus() {
  try {
    const people = await API.get('/people');
    const listEl = el('reg-status-list');
    if (!listEl) return;

    const hasT = people.filter(p => p.has_template);
    const noT  = people.filter(p => !p.has_template);

    listEl.innerHTML = `
      <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px">
        ${people.length} people &nbsp;&bull;&nbsp; ${hasT.length} enrolled
      </p>
      <div style="margin-bottom:14px">
        <p style="font-size:12px;font-weight:600;color:var(--green);margin-bottom:6px">Enrolled (${hasT.length})</p>
        ${hasT.map(p => `<div style="font-size:13px;padding:3px 0;color:var(--text-muted)">
          <span class="td-mono">${p.person_id}</span> &nbsp;${p.full_name || '&ndash;'}
        </div>`).join('') || '<p style="font-size:12px;color:var(--text-muted)">None yet</p>'}
      </div>
      ${noT.length ? `
      <div>
        <p style="font-size:12px;font-weight:600;color:var(--yellow);margin-bottom:6px">Not enrolled (${noT.length})</p>
        ${noT.map(p => `<div style="font-size:13px;padding:3px 0;color:var(--text-muted)">
          <span class="td-mono">${p.person_id}</span> &nbsp;${p.full_name || '&ndash;'}
        </div>`).join('')}
      </div>` : ''}
    `;

    const nums = people.map(p => { const m = p.person_id.match(/^person_(\d+)$/); return m ? parseInt(m[1]) : 0; });
    const next = (nums.length ? Math.max(...nums) : 0) + 1;
    const pidEl = el('reg-id');
    if (pidEl && !pidEl.value) pidEl.value = `person_${String(next).padStart(3,'0')}`;

  } catch(e) {
    const l = el('reg-status-list'); if(l) l.innerHTML = `<p style="color:var(--red)">${e.message}</p>`;
  }
}

async function _submitRegister(e) {
  e.preventDefault();
  if (!_regFiles.length) { Toast.error('Upload at least one image'); return false; }

  const pid   = el('reg-id').value.trim();
  const fname = el('reg-name').value.trim();
  const code  = el('reg-code').value.trim();
  const cls   = el('reg-class').value.trim();
  if (!pid) { Toast.error('Person ID is required'); return false; }

  const btn = el('reg-submit-btn');
  btn.disabled = true; btn.textContent = 'Processing...';

  const fd = new FormData();
  fd.append('person_id', pid); fd.append('full_name', fname);
  fd.append('student_code', code); fd.append('class_name', cls);
  _regFiles.forEach(f => fd.append('images', f, f.name));

  try {
    const res = await API.post('/face/register', fd);
    Toast.success(res.message);

    const rc = el('reg-result'), rb = el('reg-result-body');
    if (rc && rb) {
      rc.style.display = '';
      rb.innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
          <div class="face-metric-item"><div class="face-metric-label">Person ID</div>
            <div style="color:var(--blue);font-weight:700;font-family:monospace">${res.person_id}</div></div>
          <div class="face-metric-item"><div class="face-metric-label">Images processed</div>
            <div class="face-metric-val">${res.num_images_processed}</div></div>
          <div class="face-metric-item"><div class="face-metric-label">Embeddings created</div>
            <div class="face-metric-val">${res.num_embeddings_created}</div></div>
          <div class="face-metric-item"><div class="face-metric-label">Template</div>
            <div style="color:${res.template_updated?'var(--green)':'var(--red)'};font-weight:700">
              ${res.template_updated ? 'Updated' : 'Failed'}</div></div>
        </div>`;
    }
    _loadRegStatus();
  } catch(err) {
    Toast.error(err.message);
  } finally {
    btn.disabled = false; btn.textContent = 'Register';
  }
  return false;
}
