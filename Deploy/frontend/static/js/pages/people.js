/* ================================================================
   People Management  —  full-page list  +  full-page detail
   ================================================================ */

/* ================================================================
   Capture Widget  —  Upload + Live Camera, shared file pool
   ================================================================ */
const _cw = {};   // state keyed by widget id

function _cwCreate(id) {
  _cw[id] = { files: [], stream: null };
  return `
    <div class="cw-wrap" id="${id}-wrap">
      <!-- Tabs -->
      <div class="cw-tabs">
        <button type="button" class="cw-tab active" data-cwtab="upload" onclick="_cwSwitch('${id}','upload')">Upload anh</button>
        <button type="button" class="cw-tab" data-cwtab="cam" onclick="_cwSwitch('${id}','cam')">Chup bang camera</button>
      </div>

      <!-- Upload pane -->
      <div class="cw-pane active" id="${id}-pane-upload">
        <div class="upload-zone" id="${id}-zone" style="padding:16px">
          <input type="file" id="${id}-file" accept="image/*" multiple />
          <div class="upload-icon-placeholder" style="width:24px;height:24px;margin:0 auto 6px"></div>
          <div class="upload-text" style="font-size:12px">
            <strong>Chon anh</strong> hoac keo tha vao day
          </div>
        </div>
      </div>

      <!-- Camera pane -->
      <div class="cw-pane" id="${id}-pane-cam">
        <div style="display:flex;gap:8px;margin-bottom:10px;align-items:center;flex-wrap:wrap">
          <select class="form-select" id="${id}-dev" style="flex:1;font-size:13px">
            <option value="">-- Chon camera --</option>
          </select>
          <button type="button" class="btn btn-secondary btn-sm" id="${id}-toggle"
                  onclick="_cwToggle('${id}')">Bat camera</button>
        </div>
        <div id="${id}-vwrap" class="cw-video-wrap">
          <video id="${id}-video" autoplay muted playsinline
                 style="width:100%;height:100%;object-fit:cover;display:none;border-radius:6px;transform:scaleX(-1)"></video>
          <div id="${id}-vmsg" class="cw-video-msg">Bam "Bat camera" de xem preview</div>
        </div>
        <div style="display:flex;gap:10px;margin-top:10px;align-items:center">
          <button type="button" class="btn btn-primary" id="${id}-snap" disabled onclick="_cwSnap('${id}')">
            Chup anh
          </button>
          <span id="${id}-snapcount" style="font-size:12px;color:var(--text-muted)"></span>
        </div>
      </div>

      <!-- Shared preview + counter -->
      <div class="preview-grid" id="${id}-preview" style="margin-top:12px"></div>
      <div id="${id}-total" style="font-size:12px;color:var(--text-muted);margin-top:6px"></div>
    </div>`;
}

function _cwInit(id) {
  const fileInput = document.getElementById(`${id}-file`);
  const zone      = document.getElementById(`${id}-zone`);
  if (!fileInput || !zone) return;

  fileInput.addEventListener('change', () => { _cwAddFiles(id, [...fileInput.files]); fileInput.value = ''; });
  zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('drag-over');
    _cwAddFiles(id, [...e.dataTransfer.files].filter(f => f.type.startsWith('image/')));
  });
}

async function _cwSwitch(id, tab) {
  const wrap = document.getElementById(`${id}-wrap`);
  if (!wrap) return;
  wrap.querySelectorAll('.cw-tab').forEach(t => t.classList.toggle('active', t.dataset.cwtab === tab));
  wrap.querySelectorAll('.cw-pane').forEach(p => p.classList.remove('active'));
  const pane = document.getElementById(`${id}-pane-${tab}`);
  if (pane) pane.classList.add('active');

  if (tab === 'cam') await _cwEnumDevices(id);
}

async function _cwEnumDevices(id) {
  const sel = document.getElementById(`${id}-dev`);
  if (!sel) return;
  try {
    const devs = await navigator.mediaDevices.enumerateDevices();
    const vids = devs.filter(d => d.kind === 'videoinput');
    sel.innerHTML = vids.length
      ? vids.map((d, i) => `<option value="${d.deviceId}">${d.label || 'Camera ' + (i + 1)}</option>`).join('')
      : '<option value="">Khong tim thay camera</option>';
  } catch {
    sel.innerHTML = '<option value="">Loi: khong the quet camera</option>';
  }
}

async function _cwToggle(id) {
  if (_cw[id]?.stream) { _cwStop(id); return; }
  const sel    = document.getElementById(`${id}-dev`);
  const video  = document.getElementById(`${id}-video`);
  const vmsg   = document.getElementById(`${id}-vmsg`);
  const toggle = document.getElementById(`${id}-toggle`);
  const snap   = document.getElementById(`${id}-snap`);
  if (!video) return;

  try {
    const deviceId   = sel?.value;
    const constraint = deviceId ? { video: { deviceId: { exact: deviceId } } } : { video: true };
    const stream     = await navigator.mediaDevices.getUserMedia(constraint);
    _cw[id].stream   = stream;
    video.srcObject  = stream;
    video.style.display = 'block';
    if (vmsg)   vmsg.style.display   = 'none';
    if (toggle) { toggle.textContent = 'Tat camera'; toggle.className = 'btn btn-danger btn-sm'; }
    if (snap)   snap.disabled = false;
    await _cwEnumDevices(id);   // re-enumerate to get device labels after permission
  } catch(e) {
    if (vmsg) vmsg.textContent = 'Khong the mo camera: ' + e.message;
  }
}

function _cwStop(id) {
  const s = _cw[id];
  if (!s) return;
  if (s.stream) { s.stream.getTracks().forEach(t => t.stop()); s.stream = null; }
  const video  = document.getElementById(`${id}-video`);
  const vmsg   = document.getElementById(`${id}-vmsg`);
  const toggle = document.getElementById(`${id}-toggle`);
  const snap   = document.getElementById(`${id}-snap`);
  if (video)  { video.srcObject = null; video.style.display = 'none'; }
  if (vmsg)   { vmsg.textContent = 'Bam "Bat camera" de xem preview'; vmsg.style.display = ''; }
  if (toggle) { toggle.textContent = 'Bat camera'; toggle.className = 'btn btn-secondary btn-sm'; }
  if (snap)   snap.disabled = true;
}

function _cwSnap(id) {
  const video = document.getElementById(`${id}-video`);
  const count = document.getElementById(`${id}-snapcount`);
  if (!video || !_cw[id]?.stream) return;

  const canvas  = document.createElement('canvas');
  canvas.width  = video.videoWidth  || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  ctx.save();
  ctx.scale(-1, 1);
  ctx.drawImage(video, -canvas.width, 0);   // draw un-mirrored (correct orientation)
  ctx.restore();

  canvas.toBlob(blob => {
    if (!blob) return;
    const ts   = Date.now();
    const file = new File([blob], `cam_${ts}.jpg`, { type: 'image/jpeg' });
    _cwAddFiles(id, [file]);
    const snapped = (_cw[id]?.files || []).filter(f => f.name.startsWith('cam_')).length;
    if (count) count.textContent = snapped + ' anh da chup';
  }, 'image/jpeg', 0.92);
}

function _cwAddFiles(id, newFiles) {
  if (!_cw[id]) return;
  _cw[id].files = [..._cw[id].files, ...newFiles].slice(0, 15);
  _cwRenderPreview(id);
}

function _cwRemove(id, i) {
  if (!_cw[id]) return;
  _cw[id].files.splice(i, 1);
  _cwRenderPreview(id);
}

function _cwRenderPreview(id) {
  const grid  = document.getElementById(`${id}-preview`);
  const total = document.getElementById(`${id}-total`);
  if (!grid) return;
  const files = _cw[id]?.files || [];

  grid.innerHTML = files.map((f, i) => {
    const url = URL.createObjectURL(f);
    const isCapture = f.name.startsWith('cam_');
    return `<div class="preview-item">
      <img src="${url}" alt="${f.name}" />
      ${isCapture ? '<div class="cw-cam-badge">CAM</div>' : ''}
      <button type="button" class="rm-btn" onclick="_cwRemove('${id}',${i})">&#x2715;</button>
    </div>`;
  }).join('');

  if (total) total.textContent = files.length ? `${files.length} anh (upload + camera)` : '';
}

function _cwClear(id) {
  _cwStop(id);
  if (_cw[id]) { _cw[id].files = []; _cwRenderPreview(id); }
}

function _cwGetFiles(id) {
  return _cw[id]?.files || [];
}

// ── Shared state ─────────────────────────────────────────────
const _pm = {
  all: [], filtered: [],
  page: 1, pageSize: 10,
  sortVal: 'full_name:asc',
  search: '', filterStatus: '', filterTemplate: '',
  detailTab: 'info',
};

// ── LIST PAGE ─────────────────────────────────────────────────
function renderPeople() {
  el('page-title').textContent = 'Quan ly nguoi';
  setContent(`
    <div class="pm-list-root">

      <div class="pm-page-head">
        <div>
          <h2 class="pm-page-title">Quan ly nguoi</h2>
          <p class="pm-page-sub">Danh sach nguoi dang ky khuon mat trong he thong</p>
        </div>
        <button class="btn btn-primary" onclick="_pmOpenAdd()">+ Them nguoi moi</button>
      </div>

      <div class="pm-toolbar card">
        <div class="pm-search-wrap">
          <svg class="pm-search-icon" viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="6.5" cy="6.5" r="4.5"/><line x1="10" y1="10" x2="14" y2="14"/>
          </svg>
          <input class="pm-search" id="pm-search" type="text"
                 placeholder="Tim theo ten, ma SV, lop, person ID..."
                 oninput="_pmOnSearch(this.value)" autocomplete="off" />
        </div>
        <select class="form-select" id="pm-f-status" onchange="_pmFilter()" style="width:auto;font-size:13px">
          <option value="">Tat ca trang thai</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
        <select class="form-select" id="pm-f-tmpl" onchange="_pmFilter()" style="width:auto;font-size:13px">
          <option value="">Tat ca template</option>
          <option value="enrolled">Da enroll</option>
          <option value="missing">Chua enroll</option>
        </select>
        <select class="form-select" id="pm-f-sort" onchange="_pmSort(this.value)" style="width:auto;font-size:13px">
          <option value="full_name:asc">Ten A→Z</option>
          <option value="full_name:desc">Ten Z→A</option>
          <option value="person_id:asc">ID tang dan</option>
          <option value="last_check_in:desc">Check-in moi nhat</option>
        </select>
        <button class="btn btn-secondary btn-sm" onclick="_pmLoad()">Lam moi</button>
      </div>

      <div class="card" style="padding:0">
        <div id="pm-table-area">
          <div class="loading-spinner" style="padding:40px"><div class="spinner"></div></div>
        </div>
      </div>

      <div id="pm-pager" class="pm-pagination"></div>
    </div>

    <!-- Modal -->
    <div class="pm-modal-overlay" id="pm-add-modal" style="display:none" onclick="_pmModalClose(event,'pm-add-modal')">
      <div class="pm-modal-box" onclick="event.stopPropagation()">
        <div class="pm-modal-header">
          <span>Them nguoi moi</span>
          <button class="pm-modal-close" onclick="_pmModalClose(null,'pm-add-modal')">&#x2715;</button>
        </div>
        <div class="pm-modal-body" id="pm-add-body"></div>
      </div>
    </div>
  `);
  _pmLoad();
}

async function _pmLoad() {
  try {
    _pm.all = await API.get('/people');
    _pmApply();
    _pmRenderTable();
  } catch(e) {
    const t = el('pm-table-area');
    if (t) t.innerHTML = `<p style="color:var(--red);padding:24px">Loi: ${e.message}</p>`;
  }
}

function _pmApply() {
  const q = _pm.search.toLowerCase();
  let r   = [..._pm.all];
  if (q) r = r.filter(p =>
    (p.person_id||'').toLowerCase().includes(q) ||
    (p.full_name||'').toLowerCase().includes(q) ||
    (p.student_code||'').toLowerCase().includes(q) ||
    (p.class_name||'').toLowerCase().includes(q)
  );
  if (_pm.filterStatus)   r = r.filter(p => p.status === _pm.filterStatus);
  if (_pm.filterTemplate) {
    r = _pm.filterTemplate === 'enrolled' ? r.filter(p => p.has_template) : r.filter(p => !p.has_template);
  }
  const [col, dir] = _pm.sortVal.split(':');
  r.sort((a,b) => {
    const av = (a[col]||'').toString().toLowerCase();
    const bv = (b[col]||'').toString().toLowerCase();
    return dir==='asc' ? av.localeCompare(bv) : bv.localeCompare(av);
  });
  _pm.filtered = r; _pm.page = 1;
}

function _pmRenderTable() {
  const area  = el('pm-table-area');
  const pager = el('pm-pager');
  if (!area) return;
  const total = _pm.filtered.length;
  if (!total) {
    area.innerHTML = '<div class="empty-state" style="padding:48px"><p>Khong co du lieu</p></div>';
    if (pager) pager.innerHTML = '';
    return;
  }
  const s    = (_pm.page-1) * _pm.pageSize;
  const e    = Math.min(s + _pm.pageSize, total);
  const rows = _pm.filtered.slice(s, e);

  area.innerHTML = `
    <div class="table-wrap">
      <table class="pm-table">
        <thead><tr>
          <th style="width:36px">#</th>
          <th>Person ID</th><th>Ho ten</th><th>Ma SV</th><th>Lop</th>
          <th>Trang thai</th><th>Template</th>
          <th>Check-in cuoi</th><th>Check-out cuoi</th>
          <th style="width:80px">Xem</th>
        </tr></thead>
        <tbody>${rows.map((p,i) => `
          <tr class="pm-row" onclick="_pmView('${p.person_id}')">
            <td class="td-muted" style="font-size:12px">${s+i+1}</td>
            <td class="td-mono">${p.person_id}</td>
            <td class="td-strong">${p.full_name||'&ndash;'}</td>
            <td class="td-muted">${p.student_code||'&ndash;'}</td>
            <td class="td-muted">${p.class_name||'&ndash;'}</td>
            <td>${p.status==='active'
              ? '<span class="badge badge-green">ACTIVE</span>'
              : '<span class="badge badge-red">INACTIVE</span>'}</td>
            <td>${p.has_template
              ? '<span class="badge badge-blue">ENROLLED</span>'
              : '<span class="badge badge-yellow">NO TEMPLATE</span>'}</td>
            <td class="td-muted td-time">${_t(p.last_check_in)}</td>
            <td class="td-muted td-time">${_t(p.last_check_out)}</td>
            <td><button class="btn btn-secondary btn-sm" onclick="event.stopPropagation();_pmView('${p.person_id}')">
              Chi tiet</button></td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>`;

  if (pager) pager.innerHTML = _pmPagerHTML(total, s, e);
}

function _pmView(pid) {
  history.pushState(null, '', '#people/' + pid);
  el('page-title').textContent = 'Chi tiet nguoi';
  setContent('<div class="loading-spinner" style="padding:60px"><div class="spinner"></div></div>');
  renderPeopleDetail(pid);
}

// ── DETAIL PAGE ───────────────────────────────────────────────
async function renderPeopleDetail(pid) {
  try {
    const [person, enrollData] = await Promise.all([
      API.get(`/people/${pid}`),
      API.get(`/people/${pid}/enroll-images`),
    ]);
    _pmRenderDetailPage(person, enrollData.images || []);
  } catch(e) {
    setContent(`<div class="empty-state"><p style="color:var(--red)">Loi: ${e.message}</p>
      <button class="btn btn-secondary" style="margin-top:16px" onclick="_pmBack()">← Quay lai</button>
    </div>`);
  }
}

function _pmRenderDetailPage(person, images) {
  const isActive = person.status === 'active';
  const hasT     = person.has_template;

  setContent(`
    <!-- Breadcrumb -->
    <div class="pm-breadcrumb">
      <button class="pm-bc-back" onclick="_pmBack()">
        <svg viewBox="0 0 14 14" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.8">
          <polyline points="9,2 4,7 9,12"/>
        </svg>
        Danh sach nguoi
      </button>
      <span class="pm-bc-sep">/</span>
      <span class="pm-bc-cur">${person.full_name || person.person_id}</span>
    </div>

    <!-- Hero card -->
    <div class="pm-hero-card card">
      <div class="pm-hero-main">
        <div class="pm-hero-avatar">${_initials(person.full_name || person.person_id)}</div>
        <div class="pm-hero-info">
          <div class="pm-hero-name">${person.full_name || person.person_id}</div>
          <div class="pm-hero-meta">
            <span class="td-mono" style="font-size:13px">${person.person_id}</span>
            ${person.student_code ? `<span class="pm-dot"></span><span>${person.student_code}</span>` : ''}
            ${person.class_name   ? `<span class="pm-dot"></span><span>${person.class_name}</span>`   : ''}
          </div>
          <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
            ${isActive
              ? '<span class="badge badge-green">ACTIVE</span>'
              : '<span class="badge badge-red">INACTIVE</span>'}
            ${hasT
              ? '<span class="badge badge-blue">ENROLLED</span>'
              : '<span class="badge badge-yellow">NO TEMPLATE</span>'}
          </div>
        </div>
      </div>
      <div class="pm-hero-actions">
        <button class="btn btn-secondary" onclick="_pmOpenEditModal('${person.person_id}')">Chinh sua</button>
        ${isActive
          ? `<button class="btn btn-secondary" onclick="_pmSetStatus('${person.person_id}','inactive')">Set Inactive</button>`
          : `<button class="btn btn-primary"   onclick="_pmSetStatus('${person.person_id}','active')">Set Active</button>`}
        <button class="btn btn-danger" onclick="_pmConfirmDel('${person.person_id}','${person.full_name||person.person_id}')">Xoa</button>
      </div>
    </div>

    <!-- Content tabs -->
    <div class="pm-content-tabs" id="pd-tabs">
      <div class="pm-ct-tab active" data-tab="info">Thong tin ca nhan</div>
      <div class="pm-ct-tab" data-tab="photos">Anh dang ky <span class="pm-tab-count">${images.length}</span></div>
      <div class="pm-ct-tab" data-tab="history">Lich su diem danh</div>
    </div>

    <div id="pd-body">
      ${_pdTabInfo(person)}
    </div>

    <!-- Edit modal -->
    <div class="pm-modal-overlay" id="pd-edit-modal" style="display:none" onclick="_pmModalClose(event,'pd-edit-modal')">
      <div class="pm-modal-box" onclick="event.stopPropagation()">
        <div class="pm-modal-header">
          <span>Chinh sua thong tin</span>
          <button class="pm-modal-close" onclick="_pmModalClose(null,'pd-edit-modal')">&#x2715;</button>
        </div>
        <div class="pm-modal-body" id="pd-edit-body"></div>
      </div>
    </div>

    <!-- Delete confirm modal -->
    <div class="pm-modal-overlay" id="pd-del-modal" style="display:none" onclick="_pmModalClose(event,'pd-del-modal')">
      <div class="pm-modal-box pm-modal-sm" onclick="event.stopPropagation()">
        <div class="pm-modal-header" style="color:var(--red)">Xoa nguoi</div>
        <div class="pm-modal-body" id="pd-del-body"></div>
      </div>
    </div>
  `);

  // Store data for tab switching
  el('pd-body')._person = person;
  el('pd-body')._images = images;

  qsa('.pm-ct-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      qsa('.pm-ct-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      _pm.detailTab = tab.dataset.tab;
      _pdSwitchTab(person, images);
    });
  });
}

function _pdSwitchTab(person, images) {
  const body = el('pd-body');
  if (!body) return;
  if (_pm.detailTab === 'info')    body.innerHTML = _pdTabInfo(person);
  if (_pm.detailTab === 'photos')  { body.innerHTML = _pdTabPhotos(person, images); setTimeout(_initPhotoUpload, 50); }
  if (_pm.detailTab === 'history') { body.innerHTML = _pdTabHistSkeleton(); _pdLoadHist(person.person_id, 7); }
}

// ── Tab: Info ─────────────────────────────────────────────────
function _pdTabInfo(p) {
  const rows = [
    ['Person ID',       `<span class="td-mono">${p.person_id}</span>`],
    ['Ho ten',           p.full_name     || '&ndash;'],
    ['Ma SV / Nhan vien',p.student_code  || '&ndash;'],
    ['Lop / Phong ban',  p.class_name    || '&ndash;'],
    ['Trang thai',       p.status === 'active'
      ? '<span class="badge badge-green">ACTIVE</span>'
      : '<span class="badge badge-red">INACTIVE</span>'],
    ['Template',         p.has_template
      ? '<span class="badge badge-blue">ENROLLED</span>'
      : '<span class="badge badge-yellow">NO TEMPLATE</span>'],
    ['Ngay tao',         _t(p.created_at) || '&ndash;'],
    ['Cap nhat luc',     _t(p.updated_at) || '&ndash;'],
  ];
  return `
    <div class="pm-detail-section">
      <div class="pm-ds-title">Thong tin co ban</div>
      <div class="pm-info-cards">
        ${rows.map(([k,v]) => `
          <div class="pm-info-card">
            <div class="pm-ic-label">${k}</div>
            <div class="pm-ic-value">${v}</div>
          </div>`).join('')}
      </div>
      <div style="margin-top:20px">
        <button class="btn btn-secondary" onclick="_pmOpenEditModal('${p.person_id}')">
          Chinh sua thong tin
        </button>
      </div>
    </div>`;
}

// ── Tab: Photos ───────────────────────────────────────────────
let _uploadFiles = [];

function _pdTabPhotos(person, images) {
  const pid = person.person_id;
  const grid = images.length ? `
    <div class="pm-photo-grid" style="margin-bottom:24px">
      ${images.map(img => `
        <div class="pm-photo-cell">
          <div class="pm-photo-wrap" onclick="_pmLB('${img.url}','${img.filename}')">
            <img src="${img.url}" alt="${img.filename}" loading="lazy"
                 onerror="this.closest('.pm-photo-wrap').innerHTML='<div class=pm-photo-broken>?</div>'" />
            <div class="pm-photo-zoom-icon">
              <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="#fff" stroke-width="1.5">
                <circle cx="6.5" cy="6.5" r="4.5"/>
                <line x1="10" y1="10" x2="14" y2="14"/>
                <line x1="6.5" y1="4.5" x2="6.5" y2="8.5"/>
                <line x1="4.5" y1="6.5" x2="8.5" y2="6.5"/>
              </svg>
            </div>
          </div>
          <div class="pm-photo-label">${img.filename}</div>
        </div>`).join('')}
    </div>` : `
    <div style="padding:28px 0 16px;text-align:center;color:var(--text-muted);font-size:13px">
      Chua co anh dang ky.
    </div>`;

  return `
    <div class="pm-detail-section">
      <div class="pm-ds-header">
        <div class="pm-ds-title">Anh khuon mat da dang ky (${images.length})</div>
      </div>
      ${grid}
    </div>

    <div class="pm-detail-section">
      <div class="pm-section-divider"><span>${images.length ? 'Cap nhat / Bo sung them anh' : 'Dang ky khuon mat'}</span></div>
      <p style="font-size:12px;color:var(--text-muted);margin:10px 0">
        Upload hoac chup truc tiep bang camera. Se tao lai template moi (trung binh embeddings cu + moi).
      </p>
      ${_cwCreate('pdu')}
      <div style="margin-top:14px;display:flex;gap:8px;align-items:center">
        <button class="btn btn-primary" id="pd-upload-btn"
                onclick="_pdUpload('${pid}')">Dang ky / Cap nhat khuon mat</button>
        <span id="pd-upload-status" style="font-size:12px;color:var(--text-muted)"></span>
      </div>
    </div>`;
}

function _initPhotoUpload() {
  setTimeout(() => _cwInit('pdu'), 50);
}

async function _pdUpload(pid) {
  const files  = _cwGetFiles('pdu');
  if (!files.length) { Toast.warning('Chon hoac chup it nhat 1 anh'); return; }

  const btn    = el('pd-upload-btn');
  const status = el('pd-upload-status');
  btn.disabled = true; btn.textContent = 'Dang xu ly...';
  if (status) status.textContent = '';

  const person = el('pd-body')?._person || {};
  const fd     = new FormData();
  fd.append('person_id',    pid);
  fd.append('full_name',    person.full_name    || '');
  fd.append('student_code', person.student_code || '');
  fd.append('class_name',   person.class_name   || '');
  files.forEach(f => fd.append('images', f, f.name));

  try {
    const res = await API.post('/face/register', fd);
    Toast.success(`Da cap nhat ${res.num_embeddings_created} anh khuon mat`);
    if (status) status.textContent = `${res.num_embeddings_created} embeddings da tao`;
    _cwClear('pdu');
    renderPeopleDetail(pid);
  } catch(err) {
    Toast.error(err.message);
    if (status) status.textContent = 'That bai: ' + err.message;
  } finally {
    btn.disabled = false; btn.textContent = 'Dang ky / Cap nhat khuon mat';
  }
}

// ── Tab: Attendance History ───────────────────────────────────
function _pdTabHistSkeleton() {
  return `
    <div class="pm-detail-section">
      <div class="pm-ds-header">
        <div class="pm-ds-title">Lich su diem danh</div>
        <div id="pd-hist-filter" style="display:flex;gap:6px">
          ${[7,30,0].map(d => `<button class="btn btn-sm btn-secondary pd-hbtn ${d===7?'pd-hbtn-active':''}"
            data-days="${d}" onclick="_pdLoadHist(this.dataset.pid||'',${d})">
            ${d===0?'Tat ca':d+' ngay'}
          </button>`).join('')}
        </div>
      </div>
      <div id="pd-hist-body">
        <div class="loading-spinner" style="padding:30px"><div class="spinner"></div></div>
      </div>
    </div>`;
}

async function _pdLoadHist(pid, days) {
  // Find pid from URL if not passed
  if (!pid) {
    const hash = window.location.hash.replace('#people/','');
    pid = decodeURIComponent(hash);
  }

  qsa('.pd-hbtn').forEach(b => {
    b.classList.toggle('pd-hbtn-active', parseInt(b.dataset.days) === days);
  });

  const body = el('pd-hist-body');
  if (!body) return;
  body.innerHTML = '<div class="loading-spinner" style="padding:20px"><div class="spinner"></div></div>';

  try {
    const data = await API.get(`/people/${pid}/attendance?days=${days}`);
    const recs = data.records || [];

    if (!recs.length) {
      body.innerHTML = `<div class="empty-state" style="padding:28px">
        <p>Khong co lich su trong ${days||'toan bo'} ngay</p>
      </div>`;
      return;
    }

    body.innerHTML = `
      <div class="table-wrap" style="max-height:340px;overflow-y:auto">
        <table>
          <thead><tr>
            <th>Ngay</th><th>Check-In</th><th>Check-Out</th>
            <th>Trang thai</th><th>Similarity</th><th>Liveness</th>
          </tr></thead>
          <tbody>${recs.map(r => `
            <tr>
              <td class="td-strong">${r.date||r.check_in_time?.slice(0,10)||'?'}</td>
              <td class="td-muted td-time">${r.check_in_time?.slice(11,19)||'&ndash;'}</td>
              <td class="td-muted td-time">${r.check_out_time?.slice(11,19)||'&ndash;'}</td>
              <td>${fmt.badge(r.attendance_status||'CHECKED_IN')}</td>
              <td>${r.check_in_similarity ? fmt.simBar(parseFloat(r.check_in_similarity||0)) : '&ndash;'}</td>
              <td class="td-muted" style="font-size:12px">${r.check_in_liveness_status||'&ndash;'}</td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>`;
  } catch(e) {
    body.innerHTML = `<p style="color:var(--red);padding:12px">${e.message}</p>`;
  }
}

// ── Edit modal ────────────────────────────────────────────────
function _pmOpenEditModal(pid) {
  const all = el('pd-body') ? [el('pd-body')._person] : _pm.all;
  const p   = all.find ? all.find(x => x?.person_id === pid) : _pm.all.find(x => x.person_id === pid);
  if (!p) { Toast.error('Khong tim thay du lieu'); return; }

  const bodyEl = el('pd-edit-body') || el('pm-add-body');
  if (!bodyEl) return;
  const modalId = el('pd-edit-modal') ? 'pd-edit-modal' : 'pm-add-modal';

  bodyEl.innerHTML = `
    <form id="pm-edit-frm" onsubmit="return _pmSaveEdit(event,'${pid}')">
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Ho ten</label>
          <input class="form-input" id="pme-name"  value="${p.full_name    ||''}" />
        </div>
        <div class="form-group">
          <label class="form-label">Ma SV</label>
          <input class="form-input" id="pme-code"  value="${p.student_code ||''}" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Lop / Phong ban</label>
          <input class="form-input" id="pme-class" value="${p.class_name   ||''}" />
        </div>
        <div class="form-group">
          <label class="form-label">Trang thai</label>
          <select class="form-select" id="pme-status">
            <option value="active"   ${p.status==='active'  ?'selected':''}>Active</option>
            <option value="inactive" ${p.status==='inactive'?'selected':''}>Inactive</option>
          </select>
        </div>
      </div>
      <div class="btn-group" style="margin-top:4px">
        <button class="btn btn-primary" type="submit" id="pme-btn">Luu thay doi</button>
        <button class="btn btn-secondary" type="button"
                onclick="_pmModalClose(null,'${modalId}')">Huy</button>
      </div>
    </form>`;

  el(modalId).style.display = 'flex';
  if (el('pm-modal-title')) el('pm-modal-title').textContent = 'Chinh sua: ' + pid;
}

async function _pmSaveEdit(e, pid) {
  e.preventDefault();
  const btn = el('pme-btn');
  btn.disabled = true; btn.textContent = 'Dang luu...';
  try {
    await API.put(`/people/${pid}`, {
      full_name:    el('pme-name').value.trim(),
      student_code: el('pme-code').value.trim(),
      class_name:   el('pme-class').value.trim(),
      status:       el('pme-status').value,
    });
    Toast.success('Da luu thay doi');
    _pmModalClose(null, el('pd-edit-modal') ? 'pd-edit-modal' : 'pm-add-modal');
    renderPeopleDetail(pid);
  } catch(err) { Toast.error(err.message); }
  finally { btn.disabled=false; btn.textContent='Luu thay doi'; }
  return false;
}

// ── Add person modal (with face upload) ──────────────────────
let _addFiles = [];

function _pmOpenAdd() {
  _addFiles = [];
  const nums = _pm.all.map(p => { const m=p.person_id.match(/^person_(\d+)$/); return m?parseInt(m[1]):0; });
  const next = `person_${String((nums.length?Math.max(...nums):0)+1).padStart(3,'0')}`;

  el('pm-add-body').innerHTML = `
    <form id="pm-add-frm" onsubmit="return _pmSaveAdd(event)">
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Person ID *</label>
          <input class="form-input" id="pma-id" value="${next}" required />
        </div>
        <div class="form-group">
          <label class="form-label">Ho ten</label>
          <input class="form-input" id="pma-name" placeholder="Nguyen Van A" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Ma SV / Nhan vien</label>
          <input class="form-input" id="pma-code" placeholder="SV001" />
        </div>
        <div class="form-group">
          <label class="form-label">Lop / Phong ban</label>
          <input class="form-input" id="pma-class" placeholder="CNTT01" />
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Trang thai</label>
        <select class="form-select" id="pma-status">
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      <div class="pm-section-divider">
        <span>Dang ky khuon mat (tuy chon)</span>
      </div>
      <p style="font-size:12px;color:var(--text-muted);margin-bottom:10px">
        Upload hoac chup truc tiep. Co the bo qua va dang ky sau.
      </p>
      ${_cwCreate('pma')}

      <div class="btn-group" style="margin-top:16px">
        <button class="btn btn-primary" type="submit" id="pma-btn">Them nguoi</button>
        <button class="btn btn-secondary" type="button"
                onclick="_pmModalClose(null,'pm-add-modal')">Huy</button>
      </div>
    </form>`;

  el('pm-add-modal').style.display = 'flex';
  setTimeout(() => _cwInit('pma'), 50);
}

async function _pmSaveAdd(e) {
  e.preventDefault();
  const btn  = el('pma-btn');
  const pid  = el('pma-id').value.trim();
  if (!pid) { Toast.error('Person ID khong duoc rong'); return false; }
  btn.disabled = true; btn.textContent = 'Dang them...';

  try {
    await API.post('/people', {
      person_id:    pid,
      full_name:    el('pma-name').value.trim(),
      student_code: el('pma-code').value.trim(),
      class_name:   el('pma-class').value.trim(),
      status:       el('pma-status').value,
    });

    const files = _cwGetFiles('pma');
    if (files.length > 0) {
      btn.textContent = 'Dang tao template...';
      const fd = new FormData();
      fd.append('person_id',    pid);
      fd.append('full_name',    el('pma-name').value.trim());
      fd.append('student_code', el('pma-code').value.trim());
      fd.append('class_name',   el('pma-class').value.trim());
      files.forEach(f => fd.append('images', f, f.name));
      const res = await API.post('/face/register', fd);
      Toast.success(`Da them ${pid} + ${res.num_embeddings_created} anh khuon mat`);
    } else {
      Toast.success('Da them: ' + pid);
    }

    _cwClear('pma');
    _pmModalClose(null, 'pm-add-modal');
    _pmLoad();
  } catch(err) { Toast.error(err.message); }
  finally { btn.disabled = false; btn.textContent = 'Them nguoi'; }
  return false;
}

// ── Delete confirm ────────────────────────────────────────────
function _pmConfirmDel(pid, name) {
  el('pd-del-body').innerHTML = `
    <p style="margin-bottom:10px;font-size:14px">
      Xoa <strong style="color:var(--text-bright)">${name}</strong>?
    </p>
    <p style="font-size:12px;color:var(--text-muted);margin-bottom:20px;line-height:1.7">
      Hanh dong nay se xoa nguoi nay khoi <code style="color:var(--blue)">people.csv</code>
      va <code style="color:var(--blue)">person_templates.pkl</code>.<br>
      Lich su diem danh se duoc giu lai.
    </p>
    <div class="btn-group">
      <button class="btn btn-secondary" onclick="_pmModalClose(null,'pd-del-modal')">Huy</button>
      <button class="btn btn-danger" id="pd-del-ok" onclick="_pmDoDel('${pid}')">Xoa vinh vien</button>
    </div>`;
  el('pd-del-modal').style.display = 'flex';
}

async function _pmDoDel(pid) {
  const btn = el('pd-del-ok'); btn.disabled=true; btn.textContent='Dang xoa...';
  try {
    await API.delete(`/people/${pid}`);
    Toast.success('Da xoa: ' + pid);
    _pmModalClose(null,'pd-del-modal');
    _pmBack();
  } catch(err) {
    Toast.error(err.message);
    btn.disabled=false; btn.textContent='Xoa vinh vien';
  }
}

// ── Status ────────────────────────────────────────────────────
async function _pmSetStatus(pid, status) {
  try {
    await API.patch(`/people/${pid}/status`, {status});
    Toast.success(`${pid} → ${status}`);
    renderPeopleDetail(pid);
  } catch(e) { Toast.error(e.message); }
}

// ── Pagination ────────────────────────────────────────────────
function _pmPagerHTML(total, s, e) {
  const tp = Math.ceil(total / _pm.pageSize);
  const pages = tp<=7 ? Array.from({length:tp},(_,i)=>i+1) : (() => {
    const arr=[1];
    if(_pm.page>3) arr.push('…');
    for(let p=Math.max(2,_pm.page-1);p<=Math.min(tp-1,_pm.page+1);p++) arr.push(p);
    if(_pm.page<tp-2) arr.push('…');
    arr.push(tp); return arr;
  })();
  return `
    <span class="pm-pg-info">Hien thi ${s+1}&ndash;${e} / ${total} nguoi</span>
    <div class="pm-pg-controls">
      <button class="pm-pg-btn" onclick="_pmPage(${_pm.page-1})" ${_pm.page<=1?'disabled':''}>&#x2190;</button>
      ${pages.map(p=>p==='…'
        ?`<span class="pm-pg-ellipsis">&hellip;</span>`
        :`<button class="pm-pg-btn${p===_pm.page?' active':''}" onclick="_pmPage(${p})">${p}</button>`
      ).join('')}
      <button class="pm-pg-btn" onclick="_pmPage(${_pm.page+1})" ${_pm.page>=tp?'disabled':''}>&#x2192;</button>
    </div>
    <div class="pm-pg-sizes">
      ${[10,20,50].map(n=>`<button class="pm-pg-size-btn${_pm.pageSize===n?' active':''}" onclick="_pmPS(${n})">${n}</button>`).join('')}
    </div>`;
}
function _pmPage(p) {
  const mx=Math.ceil(_pm.filtered.length/_pm.pageSize);
  _pm.page=Math.max(1,Math.min(p,mx)); _pmRenderTable();
}
function _pmPS(n)   { _pm.pageSize=n; _pm.page=1; _pmRenderTable(); }

// ── Modals + nav ─────────────────────────────────────────────
function _pmModalClose(e, id) {
  if (e && e.target !== el(id)) return;
  const m = el(id); if(m) m.style.display='none';
  // Stop any running camera streams when modal closes
  if (id === 'pm-add-modal') _cwStop('pma');
  if (id === 'pd-edit-modal' || id === 'pm-add-modal') _cwStop('pdu');
}
function _pmBack() {
  history.pushState(null,'','#people');
  el('page-title').textContent='Quan ly nguoi';
  renderPeople();
}
function _pmLB(url, name) {
  const lb=document.createElement('div');
  lb.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.88);z-index:9999;display:flex;align-items:center;justify-content:center;cursor:zoom-out';
  lb.innerHTML=`<div onclick="event.stopPropagation()" style="text-align:center">
    <img src="${url}" style="max-width:90vw;max-height:85vh;border-radius:8px;display:block"/>
    <div style="color:rgba(255,255,255,.5);font-size:12px;margin-top:10px">${name}</div>
  </div>`;
  lb.addEventListener('click',()=>lb.remove());
  document.body.appendChild(lb);
}

// ── Filter / sort callbacks ───────────────────────────────────
function _pmOnSearch(v) { _pm.search=v; _pmApply(); _pmRenderTable(); }
function _pmFilter() {
  _pm.filterStatus=(el('pm-f-status')?.value||'');
  _pm.filterTemplate=(el('pm-f-tmpl')?.value||'');
  _pmApply(); _pmRenderTable();
}
function _pmSort(v) { _pm.sortVal=v; _pmApply(); _pmRenderTable(); }

// ── Helpers ───────────────────────────────────────────────────
function _t(s) { return s ? String(s).slice(0,19) : '&ndash;'; }
function _initials(name) {
  return name.split(/\s+/).slice(0,2).map(w=>w[0]||'').join('').toUpperCase()||'?';
}
