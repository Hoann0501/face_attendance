/* Face analysis page */

function renderFaceAnalysis() {
  setContent(`
    <div class="two-col-lg">
      <div>
        <div class="card">
          <div class="card-title">Upload Image</div>
          <div class="upload-zone" id="fa-zone">
            <input type="file" id="fa-file" accept="image/*" onchange="_onFaFile()" />
            <div class="upload-icon-placeholder"></div>
            <div class="upload-text">
              <strong>Choose image</strong> &mdash; detects bbox, gender, age, age_group
            </div>
          </div>
          <div id="fa-canvas-wrap" style="margin-top:14px;display:none">
            <canvas id="fa-canvas" style="border-radius:8px;max-width:100%"></canvas>
          </div>
        </div>
      </div>

      <div>
        <div id="fa-results">
          <div class="empty-state" style="padding:60px 20px">
            <p>Upload an image to begin analysis</p>
          </div>
        </div>
      </div>
    </div>
  `);
}

let _faImageObj = null;

function _onFaFile() {
  const file = el('fa-file').files[0]; if (!file) return;
  _faImageObj = new Image();
  _faImageObj.onload = () => _doAnalyze(file);
  _faImageObj.src = URL.createObjectURL(file);
}

async function _doAnalyze(file) {
  const resEl = el('fa-results');
  resEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';

  const fd = new FormData();
  fd.append('image', file);

  try {
    const data  = await API.post('/face/analyze', fd);
    const faces = data.faces || [];

    if (!faces.length) {
      resEl.innerHTML = '<div class="empty-state"><p>No faces detected</p></div>';
      _drawAnnotated([], _faImageObj);
      return;
    }

    _drawAnnotated(faces, _faImageObj);

    resEl.innerHTML = `
      <p style="font-size:13px;color:var(--text-muted);margin-bottom:14px">
        Detected <strong style="color:var(--blue)">${faces.length}</strong> face(s)
      </p>
      <div class="face-cards">
        ${faces.map(f => {
          const bbox = f.bbox || [];
          const bboxStr = bbox.length === 4
            ? `(${bbox[0].toFixed(0)}, ${bbox[1].toFixed(0)}) &rarr; (${bbox[2].toFixed(0)}, ${bbox[3].toFixed(0)})`
            : '&ndash;';
          const gConf  = f.gender_conf  != null ? (f.gender_conf  * 100).toFixed(1) + '%' : '&ndash;';
          const agConf = f.age_group_conf != null ? (f.age_group_conf * 100).toFixed(1) + '%' : '&ndash;';

          return `<div class="face-card">
            <div class="face-card-header">
              <span class="face-card-id">Face #${f.face_id}</span>
              <span class="badge badge-blue">det&nbsp;${f.det_score?.toFixed(3)}</span>
            </div>
            <div class="face-metrics">
              <div class="face-metric-item">
                <div class="face-metric-label">Gender</div>
                <div class="face-metric-val" style="font-size:16px">${f.gender || '&ndash;'}</div>
                <div style="font-size:11px;color:var(--text-muted)">${gConf}</div>
              </div>
              <div class="face-metric-item">
                <div class="face-metric-label">Age</div>
                <div class="face-metric-val" style="color:var(--yellow)">${f.age != null ? Math.round(f.age) : '&ndash;'}</div>
              </div>
              <div class="face-metric-item" style="grid-column:span 2">
                <div class="face-metric-label">Age Group</div>
                <div style="font-size:14px;font-weight:600;color:var(--purple)">
                  ${f.age_group || '&ndash;'}
                  <span style="font-size:11px;color:var(--text-muted);font-weight:400">&nbsp;${agConf}</span>
                </div>
              </div>
              <div class="face-metric-item" style="grid-column:span 2">
                <div class="face-metric-label">Bounding Box</div>
                <div style="font-size:12px;font-family:monospace;color:var(--text-muted)">${bboxStr}</div>
              </div>
              <div class="face-metric-item">
                <div class="face-metric-label">Emb dim</div>
                <div style="font-size:13px;color:var(--text-muted)">${f.embedding_dim || '&ndash;'}</div>
              </div>
              <div class="face-metric-item">
                <div class="face-metric-label">Landmarks</div>
                <div style="font-size:12px;color:var(--text-muted)">${f.landmarks ? f.landmarks.length + ' pts' : '&ndash;'}</div>
              </div>
            </div>
          </div>`;
        }).join('')}
      </div>
    `;
  } catch(e) {
    Toast.error(e.message);
    resEl.innerHTML = `<p style="color:var(--red)">${e.message}</p>`;
  }
}

function _drawAnnotated(faces, imgObj) {
  const wrap   = el('fa-canvas-wrap');
  const canvas = el('fa-canvas');
  if (!wrap || !canvas || !imgObj) return;

  wrap.style.display = 'block';

  const MAX_W = wrap.clientWidth || 600;
  const scale = Math.min(1, MAX_W / imgObj.naturalWidth);
  canvas.width  = imgObj.naturalWidth  * scale;
  canvas.height = imgObj.naturalHeight * scale;

  const ctx = canvas.getContext('2d');
  ctx.drawImage(imgObj, 0, 0, canvas.width, canvas.height);

  const colors = ['#3fb950','#58a6ff','#bc8cff','#e3b341','#f85149'];

  faces.forEach((f, i) => {
    const bbox = f.bbox || []; if (bbox.length < 4) return;
    const [x1, y1, x2, y2] = bbox.map(v => v * scale);
    const w = x2 - x1, h = y2 - y1;
    const col = colors[i % colors.length];

    ctx.strokeStyle = col; ctx.lineWidth = 2;
    ctx.strokeRect(x1, y1, w, h);

    const label = `#${f.face_id}  ${f.det_score?.toFixed(2)}`;
    ctx.font = `bold ${Math.max(11, 13 * scale)}px monospace`;
    const tw = ctx.measureText(label).width;
    ctx.fillStyle = 'rgba(0,0,0,.75)';
    ctx.fillRect(x1, y1 - 20 * scale, tw + 10, 20 * scale);
    ctx.fillStyle = col;
    ctx.fillText(label, x1 + 5, y1 - 5 * scale);

    if (f.gender || f.age != null) {
      const gl = [f.gender || '', f.age != null ? Math.round(f.age) + ' yr' : ''].filter(Boolean).join('  ');
      ctx.font = `${Math.max(10, 12 * scale)}px sans-serif`;
      const gw = ctx.measureText(gl).width;
      ctx.fillStyle = 'rgba(0,0,0,.7)';
      ctx.fillRect(x1, y2 + 1, gw + 10, 18 * scale);
      ctx.fillStyle = '#e3b341';
      ctx.fillText(gl, x1 + 5, y2 + 14 * scale);
    }
  });
}
