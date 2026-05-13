/* Pipeline / Workflow Report – professional layout, no emoji */

function renderPipeline() {
  setContent(`
  <div class="pipeline-page">

    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
      <div>
        <h2 style="font-size:20px;font-weight:700;color:var(--text-bright)">Pipeline &amp; Workflow Report</h2>
        <p style="font-size:13px;color:var(--text-muted);margin-top:4px">Face Recognition Attendance System with Anti-Spoofing &mdash; Technical Overview</p>
      </div>
      <button class="btn btn-secondary" onclick="window.print()">Print / Export PDF</button>
    </div>

    <!-- 1. Executive Summary -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">01</span> Executive Summary</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px">
        ${[
          { label: 'Project name',    value: 'Face Recognition Attendance System with Anti-Spoofing', accent: 'blue' },
          { label: 'Objective',       value: 'Automated face-based attendance, liveness detection, check-in / check-out, report export', accent: 'green' },
          { label: 'Core components', value: 'FastAPI Backend  ·  HTML/JS Frontend  ·  Camera App  ·  AI Models  ·  Local CSV Storage', accent: 'purple' },
          { label: 'Status',          value: 'POC complete — all core functions operational', accent: 'yellow' },
        ].map(c => `
          <div class="summary-card" style="border-color:var(--${c.accent})">
            <div class="summary-card-label">${c.label}</div>
            <div class="summary-card-value" style="color:var(--${c.accent})">${c.value}</div>
          </div>`).join('')}
      </div>
    </div>

    <!-- 2. Requirement Mapping -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">02</span> Requirement Mapping</div>
      <div class="card" style="padding:0">
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th style="width:30px">#</th>
              <th>Requirement</th>
              <th>Implemented Module</th>
              <th>Components / Output</th>
              <th>Status</th>
            </tr></thead>
            <tbody>
              ${[
                ['1','Database management','People management &middot; Face registration',`${_cp('people.csv','blue')} &middot; ${_cp('person_templates.pkl','green')} &middot; ${_cp('/people','muted')} &middot; ${_cp('/face/register','muted')}`,'Done'],
                ['2','Face image analysis','Face analysis &middot; Attribute model',`InsightFace detector &middot; MobileNetV3 attribute &middot; bbox, landmark, emb_dim, gender, age, age_group`,'Done'],
                ['3','Face search','Face search 1-to-N',`ArcFace embedding &middot; Cosine similarity &middot; Top-K &middot; ${_cp('/face/search','muted')}`,'Done'],
                ['4','Anti-spoofing / Liveness','Liveness detection',`MobileNetV3-small &middot; face crop + full frame &middot; temporal voting win=7`,'Done'],
                ['5','Face verification','Verification 1-to-1',`ArcFace &middot; Cosine threshold 0.35 &middot; VERIFIED / UNKNOWN &middot; ${_cp('/face/verify','muted')}`,'Done'],
                ['6','Check-in / Check-out','Attendance service + Camera app',`${_cp('attendance_YYYY-MM-DD.csv','green')} &middot; ${_cp('recent_events.json','yellow')} &middot; OpenCV camera app`,'Extended'],
              ].map(([n,req,mod,comp,st]) => `
                <tr>
                  <td class="td-muted" style="font-weight:600">${n}</td>
                  <td class="td-strong">${req}</td>
                  <td>${mod}</td>
                  <td style="font-size:12px;color:var(--text-muted)">${comp}</td>
                  <td><span class="badge ${st==='Done'?'badge-green':'badge-blue'}">${st}</span></td>
                </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 3. Architecture -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">03</span> System Architecture</div>
      <div class="card">
        <div class="arch-v2">

          <!-- Row: Clients -->
          <div class="arch-v2-row">
            <div class="arch-v2-box arch-client">Admin / User<br><span class="arch-sub">Web browser</span></div>
            <div class="arch-v2-spacer"></div>
            <div class="arch-v2-box arch-client">Camera Operator<br><span class="arch-sub">Terminal</span></div>
          </div>
          <div class="arch-v2-arrows"><div class="arch-down-arrow"></div><div class="arch-down-arrow"></div></div>

          <!-- Row: Apps -->
          <div class="arch-v2-row">
            <div class="arch-v2-box arch-blue">Web Frontend<br><span class="arch-sub">HTML / CSS / JS (SPA)</span></div>
            <div class="arch-v2-spacer"></div>
            <div class="arch-v2-box arch-blue">Camera App<br><span class="arch-sub">Python + OpenCV</span></div>
          </div>
          <div class="arch-v2-arrows"><div class="arch-down-arrow"></div><div class="arch-down-arrow"></div></div>

          <!-- Row: API (full width) -->
          <div class="arch-v2-row arch-v2-full">
            <div class="arch-v2-box arch-purple arch-wide">
              FastAPI Backend
              <div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-top:6px">
                ${['/people','/face/register','/face/search','/face/verify','/face/analyze','/attendance','/health'].map(r =>
                  `<span class="arch-chip">${r}</span>`).join('')}
              </div>
            </div>
          </div>
          <div class="arch-v2-arrows arch-v2-center"><div class="arch-down-arrow"></div></div>

          <!-- Row: Core AI -->
          <div class="arch-v2-row arch-v2-wrap">
            <div class="arch-v2-box arch-green arch-sm">Anti-Spoof Service<br><span class="arch-sub">MobileNetV3-small</span></div>
            <div class="arch-v2-box arch-green arch-sm">Face Verifier<br><span class="arch-sub">InsightFace ArcFace</span></div>
            <div class="arch-v2-box arch-green arch-sm">Face Attribute<br><span class="arch-sub">MobileNetV3 multi-task</span></div>
            <div class="arch-v2-box arch-green arch-sm">Attendance Service<br><span class="arch-sub">Check-in / Check-out</span></div>
          </div>
          <div class="arch-v2-arrows arch-v2-center"><div class="arch-down-arrow"></div></div>

          <!-- Row: Storage -->
          <div class="arch-v2-row arch-v2-wrap">
            <div class="arch-v2-box arch-yellow arch-sm">people.csv</div>
            <div class="arch-v2-box arch-yellow arch-sm">attendance_<br>YYYY-MM-DD.csv</div>
            <div class="arch-v2-box arch-yellow arch-sm">recent_events.json</div>
            <div class="arch-v2-box arch-yellow arch-sm">person_templates.pkl</div>
            <div class="arch-v2-box arch-yellow arch-sm">Trained Models</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 4. AI Pipeline -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">04</span> AI Pipeline</div>
      <div class="two-col">

        <div class="card">
          <div class="card-title" style="margin-bottom:20px">Processing Flow</div>
          <div class="flow2">
            <div class="flow2-node flow2-blue">Input: Camera frame or uploaded image</div>
            <div class="flow2-arrow"></div>
            <div class="flow2-node">Face Detection<div class="flow2-note">InsightFace / Haar cascade — produces bbox</div></div>
            <div class="flow2-arrow"></div>
            <div class="flow2-node">Liveness / Anti-Spoofing<div class="flow2-note">MobileNetV3-small · face crop + full frame · temporal voting (window=7)</div></div>
            <div class="flow2-arrow"></div>
            <div class="flow2-branch-label">
              <span class="flow2-bad">FAKE_OR_SUSPECT</span>
              <span style="color:var(--text-muted)"> &mdash; </span>
              <span class="flow2-good">REAL_ATTENDANCE_OK</span>
            </div>
            <div class="flow2-fork">
              <div class="flow2-fork-bad">
                <div class="flow2-node flow2-red">Reject<div class="flow2-note">No attendance record written</div></div>
              </div>
              <div class="flow2-fork-good">
                <div class="flow2-node">ArcFace Embedding<div class="flow2-note">InsightFace buffalo_l — 512-dim vector</div></div>
                <div class="flow2-arrow"></div>
                <div class="flow2-node">Cosine Similarity Search<div class="flow2-note">Compare against all templates — threshold 0.35</div></div>
                <div class="flow2-arrow"></div>
                <div class="flow2-branch-label">
                  <span class="flow2-bad">sim &lt; 0.35</span>
                  <span style="color:var(--text-muted)"> &mdash; </span>
                  <span class="flow2-good">Verified</span>
                </div>
                <div class="flow2-fork">
                  <div class="flow2-fork-bad"><div class="flow2-node flow2-yellow">Unknown<div class="flow2-note">No record written</div></div></div>
                  <div class="flow2-fork-good"><div class="flow2-node flow2-green">Check-in / Check-out<div class="flow2-note">Write attendance CSV</div></div></div>
                </div>
              </div>
            </div>
            <div class="flow2-arrow"></div>
            <div class="flow2-node flow2-blue">Dashboard / Report update<div class="flow2-note">Frontend polling every 5s</div></div>
          </div>
        </div>

        <div>
          <div class="card" style="margin-bottom:16px">
            <div class="card-title">Anti-Spoofing Parameters</div>
            ${_kv([
              ['Model','MobileNetV3-small'],
              ['Input','Face crop (224×224) + Full frame (224×224)'],
              ['Classes','fake = 0 / real = 1'],
              ['Threshold (face crop)','0.75'],
              ['Threshold (full frame)','0.55'],
              ['Window size','7 frames'],
              ['Min real votes','5 / 7'],
              ['Test accuracy','≈ 94.1 %'],
            ])}
          </div>
          <div class="card">
            <div class="card-title">Face Verification Parameters</div>
            ${_kv([
              ['Model','InsightFace buffalo_l'],
              ['Algorithm','ArcFace'],
              ['Embedding dim','512'],
              ['Distance metric','Cosine similarity'],
              ['Threshold','0.35'],
              ['POC sample','45 pairs (15 positive, 30 negative)'],
              ['POC accuracy','100 % (small sample)'],
            ])}
          </div>
        </div>
      </div>
    </div>

    <!-- 5. Training Timeline -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">05</span> Training Pipeline</div>
      <div class="card">
        <div class="timeline">
          ${[
            { color:'var(--blue)', phase:'Phase 1', title:'Chuẩn bị dữ liệu Anti-Spoofing',
              items:[
                `Dataset: ${_cp('data_face/Image/', 'blue')} &ndash; live / not_live`,
                `Cấu trúc: ${_cp('train_photo/{live,not_live}', 'orange')} + ${_cp('test_photo/{live,not_live}', 'orange')}`,
                `Tiền xử lý: scan ảnh, Haar cascade crop mặt, resize 224&times;224, split train/test`,
                `Notebook: ${_cp('01_prepare_data.ipynb', 'blue')}`,
              ]},
            { color:'var(--green)', phase:'Phase 2', title:'Train Anti-Spoofing Model',
              items:[
                `Model: MobileNetV3-small (classification head 2 classes)`,
                `Output: ${_cp('vfa_mobilenetv3_small_best.pth', 'green')}`,
                `Test accuracy: ~94.1% (argmax)`,
                `Deploy threshold: 0.90 offline; webcam dùng temporal voting với face=0.75, full=0.55`,
                `Notebook: ${_cp('02_train_face_crop_model.ipynb', 'blue')}`,
              ]},
            { color:'var(--purple)', phase:'Phase 3', title:'Face Verification POC',
              items:[
                `Tạo enroll/query cho ${_cp('person_001', 'purple')}, ${_cp('person_002', 'purple')}, ${_cp('person_003', 'purple')}`,
                `Dùng InsightFace buffalo_l extract ArcFace embedding (512-dim)`,
                `Tạo ${_cp('person_templates.pkl', 'green')} (mean embedding per person)`,
                `Chọn threshold 0.35 trên 45 pairs; đạt 100% POC sample`,
                `Notebook: ${_cp('03_face_verification_poc.ipynb', 'blue')}`,
              ]},
            { color:'var(--yellow)', phase:'Phase 4', title:'Train Face Attribute Model',
              items:[
                `Dataset: UTKFace (gender + age)`,
                `Model: MobileNetV3-small multi-task (gender head + age_group head + age regression head)`,
                `Age normalize: age / 100.0 &rarr; decode &times; 100.0 khi predict`,
                `Test gender acc: ~92.2% &nbsp;&bull;&nbsp; Test age_group acc: ~79.7% &nbsp;&bull;&nbsp; Age MAE: ~6.5 năm`,
                `Output: ${_cp('face_attribute_mobilenetv3_best.pth', 'yellow')}`,
                `Notebook: ${_cp('04_train_face_attribute_model.ipynb', 'blue')}`,
              ]},
            { color:'var(--green)', phase:'Phase 5', title:'Tích hợp Deploy',
              items:[
                `Copy models vào ${_cp('Deploy/models/', 'green')}`,
                `Tách module: ${_cp('core/', 'blue')} &middot; ${_cp('backend/', 'blue')} &middot; ${_cp('frontend/', 'blue')} &middot; ${_cp('camera_app/', 'blue')}`,
                `Storage: local CSV/JSON/pickle &ndash; không dùng SQL/SQLite`,
                `Check-in/check-out logic: 1 dòng/người/ngày`,
                `Script: ${_cp('init_deploy.py', 'green')} để migrate dữ liệu cũ`,
              ]},
          ].map(t => `
            <div class="timeline-item">
              <div class="timeline-dot" style="background:${t.color}"></div>
              <div class="timeline-phase" style="color:${t.color}">${t.phase}</div>
              <div class="timeline-title">${t.title}</div>
              <div class="timeline-body"><ul>${t.items.map(i => `<li>${i}</li>`).join('')}</ul></div>
            </div>`).join('')}
        </div>
      </div>
    </div>

    <!-- 6. Runtime Workflow -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">06</span> Runtime Attendance Workflow</div>
      <div class="two-col">
        <div class="card">
          <div class="card-title" style="color:var(--green);margin-bottom:18px">Check-In Flow</div>
          ${_step([
            ['Camera detects face (Haar cascade)',        'default'],
            ['Anti-spoofing temporal voting',             'default'],
            ['FAKE_OR_SUSPECT → reject, no record',       'bad'],
            ['REAL_ATTENDANCE_OK → extract ArcFace embedding', 'good'],
            ['Cosine similarity &lt; 0.35 → UNKNOWN, no record', 'bad'],
            ['Verified → check person status',            'default'],
            ['Inactive → INACTIVE USER, no record',       'bad'],
            ['Already checked in today → ALREADY CHECKED IN', 'warn'],
            ['First check-in today → write check_in_time, status = CHECKED_IN', 'good'],
          ])}
        </div>
        <div class="card">
          <div class="card-title" style="color:var(--blue);margin-bottom:18px">Check-Out Flow</div>
          ${_step([
            ['Camera detects face',                       'default'],
            ['Anti-spoofing + face verification (same as check-in)', 'default'],
            ['No check-in record today → error, no record', 'bad'],
            ['Already checked out → ALREADY CHECKED OUT', 'warn'],
            ['Checked in but not yet out → write check_out_time, status = CHECKED_OUT', 'good'],
          ])}
          <div style="margin-top:20px">
            <div class="card-title" style="margin-bottom:12px">Data Rules</div>
            ${_kv([
              ['1 row per person per day','attendance_YYYY-MM-DD.csv'],
              ['Check-in','Create row · status = CHECKED_IN'],
              ['Duplicate check-in','Blocked · ALREADY_CHECKED_IN'],
              ['Check-out','Update row · status = CHECKED_OUT'],
              ['Duplicate check-out','Blocked · ALREADY_CHECKED_OUT'],
              ['Camera cooldown','4 s between consecutive writes'],
            ])}
          </div>
        </div>
      </div>
    </div>

    <!-- 7. Data Storage -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">07</span> Data Storage Layout</div>
      <div class="card">
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px">
          ${[
            { name:'people.csv',              color:'var(--blue)',   fields:['person_id &nbsp;&middot;&nbsp; full_name &nbsp;&middot;&nbsp; student_code','class_name &nbsp;&middot;&nbsp; status &nbsp;&middot;&nbsp; created_at &nbsp;&middot;&nbsp; updated_at'],             note:'Master list of registered users'},
            { name:'attendance_YYYYMMDD.csv', color:'var(--green)',  fields:['person_id &nbsp;&middot;&nbsp; check_in_time &nbsp;&middot;&nbsp; check_out_time','check_in_similarity &nbsp;&middot;&nbsp; check_out_similarity','face_real_score &nbsp;&middot;&nbsp; attendance_status'],  note:'One file per day &bull; one row per person'},
            { name:'recent_events.json',      color:'var(--yellow)', fields:['event_type &nbsp;&middot;&nbsp; event_time &nbsp;&middot;&nbsp; person_id','full_name &nbsp;&middot;&nbsp; similarity &nbsp;&middot;&nbsp; liveness_status'],                   note:'Last 50 events &bull; polled every 5 s'},
            { name:'person_templates.pkl',    color:'var(--purple)', fields:['dict: person_id &rarr; np.ndarray(512,)','mean-normalized ArcFace embedding'],                           note:'Updated on face registration'},
            { name:'models/',                 color:'var(--orange)', fields:['anti_spoof/vfa_mobilenetv3_small_best.pth','attribute/face_attribute_mobilenetv3_best.pth','verification/face_verification_config.json'], note:'Read-only at inference time'},
          ].map(f => `
            <div style="background:var(--bg-card);border:1px solid ${f.color};border-radius:8px;padding:14px">
              <code style="font-size:12px;font-weight:700;color:${f.color};font-family:'Cascadia Code','Fira Code',monospace;word-break:break-all;display:block;margin-bottom:8px">${f.name}</code>
              <ul style="list-style:none;font-size:11px;color:var(--text-muted);line-height:2">
                ${f.fields.map(x => `<li style="display:flex;gap:6px;align-items:baseline"><span style="color:var(--border);flex-shrink:0">&#x2013;</span><span>${x}</span></li>`).join('')}
              </ul>
              <p style="font-size:11px;color:var(--text-muted);margin-top:8px;border-top:1px solid var(--border-soft);padding-top:6px;font-style:italic">${f.note}</p>
            </div>`).join('')}
        </div>
        <div style="margin-top:14px;padding:12px 14px;background:var(--bg-surface);border-radius:6px;font-size:13px;color:var(--text-muted)">
          No SQL / SQLite — all data stored as plain files. Easy to inspect, back up, and move. The entire Deploy folder is self-contained.
        </div>
      </div>
    </div>

    <!-- 8. Results -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">08</span> Results</div>
      <div class="result-cards">
        ${[
          { title:'Anti-Spoofing', stats:[['Model','MobileNetV3-small'],['Test accuracy','94.1 %'],['Webcam output','REAL / FAKE'],['Voting','Temporal, window=7']] },
          { title:'Face Verification', stats:[['Backend','InsightFace / ArcFace'],['Threshold','0.35'],['POC pairs','45 (15 pos, 30 neg)'],['POC accuracy','100 %']] },
          { title:'Face Attribute', stats:[['Gender accuracy','92.2 %'],['Age-group accuracy','79.7 %'],['Age MAE','≈ 6.5 years'],['Output','gender · age · age_group']] },
          { title:'Attendance System', stats:[['Check-in / out','Operational'],['Dedup per day','1 row / person'],['Report modes','PRESENT / ABSENT / CHECKED_OUT'],['Export','CSV · Excel']] },
          { title:'System', stats:[['Backend','FastAPI'],['Frontend','HTML/CSS/JS (SPA)'],['Camera app','Python OpenCV'],['Storage','Local CSV / JSON / pickle']] },
        ].map(c => `
          <div class="result-card">
            <div class="result-card-header"><span class="result-card-title">${c.title}</span></div>
            ${c.stats.map(([k,v]) => `
              <div class="result-stat"><span class="result-stat-label">${k}</span><span class="result-stat-value green">${v}</span></div>`).join('')}
          </div>`).join('')}
      </div>
    </div>

    <!-- 9. Demo Guide -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">09</span> Demo Guide</div>
      <div class="card">
        <ul class="checklist">
          ${[
            ['Initialize data',          _cp('python scripts/init_deploy.py',  'green'),  'Run once to seed database and migrate old logs'],
            ['Start backend',            _cp('scripts\\\\run_backend.bat',      'yellow'), `Serves API + Frontend at ${_cp('http://127.0.0.1:8000', 'blue')}`],
            ['Open web management',      _cp('http://127.0.0.1:8000',          'blue'),   'All pages available in sidebar'],
            ['Demo people management',   'People page',                                    'Add / edit / activate / deactivate'],
            ['Demo face registration',   'Face Registration page',                         'Upload 2–5 clear face images'],
            ['Demo face search/verify',  'Search / Verify page',                           'Upload query image, view top-K results'],
            ['Demo face analysis',       'Analysis page',                                  'Detect bbox, gender, age, age_group'],
            ['Demo camera check-in',     _cp('scripts\\\\run_camera_checkin.bat', 'yellow'), 'Press 1 / 2 / Q to control mode'],
            ['Demo camera check-out',    _cp('scripts\\\\run_camera_checkout.bat','yellow'), 'Automatic check-out logic'],
            ['Demo report &amp; export', 'Attendance Report page',                         'Pick date, filter, export CSV / Excel'],
          ].map(([title, code, note], i) => `
            <li>
              <span class="check-num">${i+1}</span>
              <div>
                <div style="font-weight:600;margin-bottom:3px">${title}</div>
                <div style="margin-top:2px">${code}</div>
                <span style="font-size:12px;color:var(--text-muted)">${note}</span>
              </div>
            </li>`).join('')}
        </ul>
      </div>
    </div>

    <!-- 10. Limitations -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">10</span> Limitations &amp; Next Steps</div>
      <div class="limit-grid">
        <div class="limit-card warn">
          <div class="limit-card-title">Current Limitations</div>
          <ul class="limit-list">
            ${['POC local file storage — not a multi-user production server',
               'Anti-spoofing does not cover advanced attacks (3D masks, deepfakes)',
               'Face verification validated on a small POC sample only',
               'Age estimation is approximate (MAE ≈ 6.5 years)',
               'Camera app is local — no distributed camera support',
               'No role-based access control (admin / user)',
               'No automatic data backup',
            ].map(t=>`<li>${t}</li>`).join('')}
          </ul>
        </div>
        <div class="limit-card next">
          <div class="limit-card-title">Recommended Next Steps</div>
          <ul class="limit-list">
            ${['Collect real-environment spoof samples to retrain anti-spoofing model',
               'Expand face verification dataset to 50–100+ identities',
               'Add JWT-based authentication and role management',
               'Implement scheduled data backup',
               'Add system-level audit logging',
               'Migrate to a proper database server for multi-site deployment',
               'Containerise with Docker or package as an internal installer',
               'Add support for multiple simultaneous cameras',
            ].map(t=>`<li>${t}</li>`).join('')}
          </ul>
        </div>
      </div>
    </div>

    <div style="text-align:center;padding:24px 0 4px;color:var(--text-muted);font-size:12px;border-top:1px solid var(--border)">
      Face Recognition Attendance System &mdash; Technical Report &mdash; ${new Date().toLocaleDateString('en-GB')}
    </div>
  </div>
  `);
}

/* ---- helpers ---- */

/** Colored inline code span. color: blue | green | yellow | orange | purple | red */
function _cp(text, color = 'blue') {
  const map = {
    blue:   'var(--blue)',
    green:  'var(--green)',
    yellow: 'var(--yellow)',
    orange: 'var(--orange)',
    purple: 'var(--purple)',
    red:    'var(--red)',
    muted:  'var(--text-muted)',
  };
  const col = map[color] || map.blue;
  return `<code style="color:${col};font-family:'Cascadia Code','Fira Code',monospace;font-size:12.5px;background:rgba(255,255,255,.05);padding:1px 5px;border-radius:3px">${text}</code>`;
}

function _kv(pairs) {
  return `<div style="display:grid;gap:6px">${pairs.map(([k,v])=>`
    <div style="display:flex;justify-content:space-between;align-items:baseline;
         padding:7px 10px;background:var(--bg-surface);border-radius:6px;font-size:13px;gap:12px">
      <span style="color:var(--text-muted);white-space:nowrap">${k}</span>
      <span style="font-weight:600;color:var(--text-bright);text-align:right">${v}</span>
    </div>`).join('')}</div>`;
}

function _step(steps) {
  return `<div style="display:flex;flex-direction:column;gap:0">${steps.map(([text, type], i) => {
    const colors = { good:'var(--green)', bad:'var(--red)', warn:'var(--yellow)', default:'var(--border)' };
    const bgColors = { good:'var(--green-bg)', bad:'var(--red-bg)', warn:'var(--yellow-bg)', default:'var(--bg-surface)' };
    const textColors = { good:'var(--green)', bad:'var(--red)', warn:'var(--yellow)', default:'var(--text)' };
    const c = colors[type] || colors.default;
    return `
      <div style="display:flex;align-items:stretch;gap:0">
        <div style="display:flex;flex-direction:column;align-items:center;width:28px;flex-shrink:0">
          <div style="width:10px;height:10px;border-radius:50%;background:${c};margin-top:12px;flex-shrink:0;border:2px solid var(--bg)"></div>
          ${i < steps.length-1 ? `<div style="width:2px;flex:1;background:var(--border);margin:2px 0"></div>` : ''}
        </div>
        <div style="padding:8px 0 ${i < steps.length-1 ? '8px' : '0'} 12px">
          <div style="font-size:13px;color:${textColors[type]||textColors.default};background:${bgColors[type]||'transparent'};
               ${type!=='default'?'padding:4px 10px;border-radius:5px;display:inline-block':''}">${text}</div>
        </div>
      </div>`;
  }).join('')}</div>`;
}
