/* Face Search and Verify page */

function renderFaceSearch() {
  setContent(`
    <div class="tabs" id="fs-tabs">
      <div class="tab active" data-tab="search">Search (1-to-N)</div>
      <div class="tab" data-tab="verify">Verify (1-to-1)</div>
    </div>

    <!-- Search tab -->
    <div class="tab-content active" id="tc-search">
      <div class="two-col">
        <div>
          <div class="card">
            <div class="card-title">Query Image</div>
            <div class="upload-zone">
              <input type="file" id="search-file" accept="image/*" onchange="_onSearchFileChange()" />
              <div class="upload-icon-placeholder"></div>
              <div class="upload-text"><strong>Choose image</strong> to search against</div>
            </div>
            <img id="search-preview" style="display:none;margin-top:12px;border-radius:8px;max-height:280px;width:100%;object-fit:contain" />
            <div class="form-group" style="margin-top:14px">
              <label class="form-label">Top K</label>
              <div style="display:flex;align-items:center;gap:12px">
                <input type="range" id="search-topk" min="1" max="10" value="5"
                       oninput="el('topk-val').textContent=this.value"
                       style="flex:1;cursor:pointer" />
                <span id="topk-val" style="color:var(--blue);font-weight:700;min-width:20px">5</span>
              </div>
            </div>
            <button class="btn btn-primary" onclick="_doSearch()">Search</button>
          </div>
        </div>
        <div>
          <div class="card">
            <div class="card-title">Top-K Results</div>
            <div id="search-results">
              <div class="empty-state"><p>Upload an image to search</p></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Verify tab -->
    <div class="tab-content" id="tc-verify">
      <div class="two-col">
        <div>
          <div class="card">
            <div class="card-title">Verification</div>
            <div class="form-group">
              <label class="form-label">Select person *</label>
              <select class="form-select" id="verify-person"></select>
            </div>
            <div class="form-group">
              <label class="form-label">Query image</label>
              <div class="upload-zone">
                <input type="file" id="verify-file" accept="image/*" onchange="_onVerifyFileChange()" />
                <div class="upload-icon-placeholder"></div>
                <div class="upload-text"><strong>Choose image</strong> to verify</div>
              </div>
              <img id="verify-preview" style="display:none;margin-top:12px;border-radius:8px;max-height:280px;width:100%;object-fit:contain" />
            </div>
            <button class="btn btn-primary" onclick="_doVerify()">Verify</button>
          </div>
        </div>
        <div>
          <div class="card">
            <div class="card-title">Result</div>
            <div id="verify-results">
              <div class="empty-state"><p>Select a person and upload an image</p></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `);

  // Tabs
  const tabs = qsa('.tab', el('fs-tabs'));
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      qsa('.tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      el('tc-' + tab.dataset.tab).classList.add('active');
    });
  });

  _loadVerifyPeople();
}

function _onSearchFileChange() {
  const f = el('search-file').files[0]; if (!f) return;
  const p = el('search-preview'); p.src = URL.createObjectURL(f); p.style.display = 'block';
}

function _onVerifyFileChange() {
  const f = el('verify-file').files[0]; if (!f) return;
  const p = el('verify-preview'); p.src = URL.createObjectURL(f); p.style.display = 'block';
}

async function _doSearch() {
  const fileInput = el('search-file');
  if (!fileInput.files[0]) { Toast.warning('Select an image first'); return; }

  const topk   = el('search-topk').value;
  const fd     = new FormData();
  fd.append('image', fileInput.files[0]);

  const resEl  = el('search-results');
  resEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';

  try {
    const data      = await API.post(`/face/search?top_k=${topk}`, fd);
    const results   = data.results || [];
    const threshold = 0.35;

    if (!results.length) {
      resEl.innerHTML = '<div class="empty-state"><p>No results found</p></div>';
      return;
    }

    const best    = results[0];
    const isMatch = best.similarity >= threshold;

    resEl.innerHTML = `
      <div style="margin-bottom:16px;padding:14px;border-radius:8px;
           background:${isMatch ? 'var(--green-bg)' : 'var(--red-bg)'};
           border:1px solid ${isMatch ? 'var(--green)' : 'var(--red)'}">
        <div style="font-size:15px;font-weight:700;color:${isMatch ? 'var(--green)' : 'var(--red)'}">
          ${isMatch ? 'MATCH' : 'NO MATCH / UNKNOWN'}
        </div>
        <div style="font-size:13px;margin-top:4px;color:var(--text-muted)">
          Best: <strong style="color:var(--text)">${best.full_name || best.person_id}</strong>
          &nbsp;&bull;&nbsp; similarity = ${Number(best.similarity).toFixed(4)}
          &nbsp;&bull;&nbsp; threshold = ${threshold}
        </div>
      </div>

      <p style="font-size:11px;color:var(--text-muted);margin-bottom:10px;text-transform:uppercase;
                font-weight:600;letter-spacing:.05em">
        ${data.num_faces || 0} face(s) detected &nbsp;&bull;&nbsp; Top ${results.length} results
      </p>

      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>#</th><th>Person ID</th><th>Full Name</th><th>Code</th><th>Class</th>
            <th>Status</th><th>Similarity</th>
          </tr></thead>
          <tbody>${results.map((r, i) => `
            <tr style="${r.similarity >= threshold ? 'background:rgba(63,185,80,.05)' : ''}">
              <td class="td-muted">${i+1}</td>
              <td class="td-mono">${r.person_id}</td>
              <td class="td-strong">${r.full_name || '&ndash;'}</td>
              <td class="td-muted">${r.student_code || '&ndash;'}</td>
              <td class="td-muted">${r.class_name || '&ndash;'}</td>
              <td>${r.status ? fmt.badge(r.status) : '&ndash;'}</td>
              <td>${fmt.simBar(r.similarity, threshold)}</td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>`;
  } catch(e) {
    Toast.error(e.message);
    resEl.innerHTML = `<p style="color:var(--red)">${e.message}</p>`;
  }
}

async function _loadVerifyPeople() {
  try {
    const people = await API.get('/people');
    const sel    = el('verify-person');
    if (!sel) return;
    sel.innerHTML = people.length
      ? people.map(p => `<option value="${p.person_id}">${p.person_id} — ${p.full_name || ''}</option>`).join('')
      : '<option>No people found</option>';
  } catch {}
}

async function _doVerify() {
  const pid  = el('verify-person')?.value;
  const file = el('verify-file')?.files[0];
  if (!pid)  { Toast.warning('Select a person first'); return; }
  if (!file) { Toast.warning('Select an image first'); return; }

  const resEl = el('verify-results');
  resEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';

  const fd = new FormData();
  fd.append('person_id', pid);
  fd.append('image', file);

  try {
    const r        = await API.post('/face/verify', fd);
    const verified = r.is_verified;
    const sim      = Number(r.similarity || 0);

    resEl.innerHTML = `
      <div style="text-align:center;padding:28px 0">
        <div style="font-size:13px;font-weight:700;letter-spacing:.08em;
             color:${verified ? 'var(--green)' : 'var(--red)'};margin-bottom:8px">
          ${verified ? 'VERIFIED' : 'NOT VERIFIED'}
        </div>
        <div style="display:inline-block;width:80px;height:80px;border-radius:50%;
             border:3px solid ${verified ? 'var(--green)' : 'var(--red)'};
             line-height:80px;font-size:32px;color:${verified ? 'var(--green)' : 'var(--red)'}">
          ${verified ? '&#x2713;' : '&#x2715;'}
        </div>

        <div style="margin-top:24px;display:grid;grid-template-columns:1fr 1fr 1fr;
                    gap:12px;max-width:360px;margin-inline:auto">
          <div class="face-metric-item">
            <div class="face-metric-label">Similarity</div>
            <div class="face-metric-val" style="font-size:20px;color:${verified?'var(--green)':'var(--red)'}">
              ${sim.toFixed(4)}</div>
          </div>
          <div class="face-metric-item">
            <div class="face-metric-label">Threshold</div>
            <div class="face-metric-val" style="font-size:20px">${r.threshold}</div>
          </div>
          <div class="face-metric-item">
            <div class="face-metric-label">Person</div>
            <div style="font-size:12px;font-weight:600;color:var(--blue);margin-top:4px;
                        font-family:monospace">${pid}</div>
          </div>
        </div>
        <div style="margin-top:16px;max-width:360px;margin-inline:auto">${fmt.simBar(sim, r.threshold)}</div>
      </div>`;
  } catch(e) {
    Toast.error(e.message);
    resEl.innerHTML = `<p style="color:var(--red)">${e.message}</p>`;
  }
}
