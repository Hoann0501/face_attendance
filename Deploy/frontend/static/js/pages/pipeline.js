/* Pipeline / Workflow Report */

function renderPipeline() {
  setContent(`
  <div class="pipeline-page">

    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
      <div>
        <h2 style="font-size:20px;font-weight:700;color:var(--text-bright)">Pipeline &amp; Workflow Report</h2>
        <p style="font-size:13px;color:var(--text-muted);margin-top:4px">
          Face Recognition Attendance System with Anti-Spoofing &mdash; Technical Overview
        </p>
      </div>
      <button class="btn btn-secondary" onclick="window.print()">Print / Export PDF</button>
    </div>

    <!-- 01 Executive Summary -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">01</span> Executive Summary</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px">
        ${[
          { label:'Project name',    value:'Face Recognition Attendance System with Anti-Spoofing', accent:'blue' },
          { label:'Objective',       value:'Automated face-based attendance · liveness detection · check-in / check-out · report export · face captures', accent:'green' },
          { label:'Core components', value:'FastAPI Backend · HTML/JS SPA Frontend · Camera App · AI Models · Local CSV/JSON/Pickle Storage', accent:'purple' },
          { label:'Status',          value:'POC — all core functions operational and integrated', accent:'yellow' },
        ].map(c=>`
          <div class="summary-card" style="border-color:var(--${c.accent})">
            <div class="summary-card-label">${c.label}</div>
            <div class="summary-card-value" style="color:var(--${c.accent})">${c.value}</div>
          </div>`).join('')}
      </div>
    </div>

    <!-- 02 Requirement Mapping -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">02</span> Requirement Mapping</div>
      <div class="card" style="padding:0">
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th style="width:28px">#</th>
              <th>Requirement</th>
              <th>Implemented Module</th>
              <th>Components / Output</th>
              <th>Status</th>
            </tr></thead>
            <tbody>
              ${[
                ['1','Quan ly CSDL khuon mat','People management &middot; Face registration (merged)',
                  `${_cp('people.csv','blue')} &middot; ${_cp('person_templates.pkl','green')} &middot; enroll images &middot; ${_cp('/people','muted')} &middot; ${_cp('/face/register','muted')}`,
                  'Done'],
                ['2','Phan tich hinh anh khuon mat','Face analysis &middot; Attribute model',
                  `InsightFace detector &middot; MobileNetV3 attribute &middot; bbox, landmark, emb_dim, gender, age, age_group`,
                  'Done'],
                ['3','Tim kiem khuon mat','Face search 1-to-N',
                  `ArcFace embedding &middot; Cosine similarity &middot; Top-K &middot; ${_cp('/face/search','muted')}`,
                  'Done'],
                ['4','Chong gia mao sinh trac hoc','Liveness detection',
                  `MobileNetV3-small &middot; face crop + full frame &middot; temporal voting win=7 &middot; sharp-frame buffer`,
                  'Done'],
                ['5','Xac minh khuon mat','Verification 1-to-1',
                  `ArcFace &middot; Cosine threshold 0.35 &middot; VERIFIED / UNKNOWN &middot; ${_cp('/face/verify','muted')}`,
                  'Done'],
                ['6','Check-in / Check-out','Attendance service + Camera app',
                  `${_cp('attendance_YYYY-MM-DD.csv','green')} &middot; ${_cp('recent_events.json','yellow')} &middot; OpenCV camera`,
                  'Extended'],
                ['7','Face captures','Auto-save face photo on attendance',
                  `${_cp('face_captures/YYYY-MM-DD/checkin|checkout/','orange')} &middot; Sharp-frame selection &middot; Unsharp mask`,
                  'Extended'],
              ].map(([n,req,mod,comp,st])=>`
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

    <!-- 03 Architecture -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">03</span> System Architecture</div>
      <div class="card">
        <div class="ach">

          <!-- CLIENTS -->
          <div class="ach-band">
            <div class="ach-lbl">Clients</div>
            <div class="ach-row">
              <div class="ach-box ach-default">Admin / User<span class="ach-sub">Web browser</span></div>
              <div class="ach-flex"></div>
              <div class="ach-box ach-default">Camera Operator<span class="ach-sub">Terminal</span></div>
            </div>
          </div>

          <!-- dual → converging arrows -->
          <div class="ach-gap ach-gap-2">
            <svg width="100%" height="36" preserveAspectRatio="none" viewBox="0 0 500 36">
              <line x1="125" y1="0" x2="125" y2="18" stroke="#30363d" stroke-width="1.2"/>
              <line x1="375" y1="0" x2="375" y2="18" stroke="#30363d" stroke-width="1.2"/>
              <line x1="125" y1="18" x2="250" y2="18" stroke="#30363d" stroke-width="1.2"/>
              <line x1="375" y1="18" x2="250" y2="18" stroke="#30363d" stroke-width="1.2"/>
              <line x1="250" y1="18" x2="250" y2="32" stroke="#30363d" stroke-width="1.2"/>
              <polygon points="245,29 255,29 250,36" fill="#30363d"/>
            </svg>
          </div>

          <!-- APPLICATIONS -->
          <div class="ach-band">
            <div class="ach-lbl ach-lbl-blue">Apps</div>
            <div class="ach-row">
              <div class="ach-box ach-blue">Web Frontend<span class="ach-sub">HTML / CSS / JS (SPA)</span></div>
              <div class="ach-flex"></div>
              <div class="ach-box ach-blue">Camera App<span class="ach-sub">Python + OpenCV</span></div>
            </div>
          </div>

          <!-- single center arrow -->
          <div class="ach-gap ach-gap-1">
            <svg width="2" height="28" viewBox="0 0 2 28">
              <line x1="1" y1="0" x2="1" y2="22" stroke="#30363d" stroke-width="1.2"/>
              <polygon points="-2,19 2,19 0,26" fill="#30363d" transform="translate(1,0)"/>
            </svg>
          </div>

          <!-- API LAYER -->
          <div class="ach-band">
            <div class="ach-lbl ach-lbl-purple">API</div>
            <div class="ach-row">
              <div class="ach-box ach-purple" style="flex:1;justify-content:center">
                <div style="font-size:14px;font-weight:700;margin-bottom:10px">FastAPI Backend</div>
                <div style="display:flex;gap:7px;flex-wrap:wrap;justify-content:center">
                  ${['/people','/face/register','/face/search','/face/verify','/face/analyze','/attendance','/attendance/captures','/health'].map(r=>`<span class="arch-chip">${r}</span>`).join('')}
                </div>
              </div>
            </div>
          </div>

          <!-- single center arrow -->
          <div class="ach-gap ach-gap-1">
            <svg width="2" height="28" viewBox="0 0 2 28">
              <line x1="1" y1="0" x2="1" y2="22" stroke="#30363d" stroke-width="1.2"/>
              <polygon points="-2,19 2,19 0,26" fill="#30363d" transform="translate(1,0)"/>
            </svg>
          </div>

          <!-- AI SERVICES -->
          <div class="ach-band">
            <div class="ach-lbl ach-lbl-green">AI Services</div>
            <div class="ach-row">
              <div class="ach-box ach-green ach-sm">Anti-Spoof<span class="ach-sub">MobileNetV3-small</span></div>
              <div class="ach-box ach-green ach-sm">Face Verifier<span class="ach-sub">InsightFace ArcFace</span></div>
              <div class="ach-box ach-green ach-sm">Face Attribute<span class="ach-sub">MobileNetV3 multi-task</span></div>
              <div class="ach-box ach-green ach-sm">Attendance Service<span class="ach-sub">Check-in / Check-out</span></div>
            </div>
          </div>

          <!-- single center arrow -->
          <div class="ach-gap ach-gap-1">
            <svg width="2" height="28" viewBox="0 0 2 28">
              <line x1="1" y1="0" x2="1" y2="22" stroke="#30363d" stroke-width="1.2"/>
              <polygon points="-2,19 2,19 0,26" fill="#30363d" transform="translate(1,0)"/>
            </svg>
          </div>

          <!-- STORAGE -->
          <div class="ach-band">
            <div class="ach-lbl ach-lbl-yellow">Storage</div>
            <div class="ach-row">
              <div class="ach-box ach-yellow ach-sm" style="font-family:monospace;font-size:12px">people.csv</div>
              <div class="ach-box ach-yellow ach-sm" style="font-family:monospace;font-size:12px">attendance_<br>YYYY-MM-DD.csv</div>
              <div class="ach-box ach-yellow ach-sm" style="font-family:monospace;font-size:12px">recent_events.json</div>
              <div class="ach-box ach-yellow ach-sm" style="font-family:monospace;font-size:12px">person_templates.pkl</div>
              <div class="ach-box ach-yellow ach-sm" style="font-family:monospace;font-size:12px">face_captures/</div>
              <div class="ach-box ach-yellow ach-sm" style="font-family:monospace;font-size:12px">Trained Models</div>
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- 04 AI Pipeline -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">04</span> AI Pipeline</div>
      <div class="two-col">
        <div class="card">
          <div class="card-title" style="margin-bottom:20px">Processing Flow</div>
          <div class="flow2">
            <div class="flow2-node flow2-blue">Input: Camera frame or uploaded image</div>
            <div class="flow2-arrow"></div>
            <div class="flow2-node">Face Detection<div class="flow2-note">InsightFace / Haar cascade</div></div>
            <div class="flow2-arrow"></div>
            <div class="flow2-node">Liveness / Anti-Spoofing
              <div class="flow2-note">MobileNetV3-small &middot; face crop + full frame &middot; temporal voting (win=7) &middot; sharp-frame buffer</div>
            </div>
            <div class="flow2-arrow"></div>
            <div class="flow2-branch-label">
              <span class="flow2-bad">FAKE_OR_SUSPECT</span>
              <span style="color:var(--text-muted)"> &mdash; </span>
              <span class="flow2-good">REAL_ATTENDANCE_OK</span>
            </div>
            <div class="flow2-fork">
              <div class="flow2-fork-bad">
                <div class="flow2-node flow2-red">Reject<div class="flow2-note">No record, no capture</div></div>
              </div>
              <div class="flow2-fork-good">
                <div class="flow2-node">ArcFace Embedding<div class="flow2-note">InsightFace buffalo_l &mdash; 512-dim</div></div>
                <div class="flow2-arrow"></div>
                <div class="flow2-node">Cosine Similarity<div class="flow2-note">Compare templates &mdash; threshold 0.35</div></div>
                <div class="flow2-arrow"></div>
                <div class="flow2-branch-label">
                  <span class="flow2-bad">sim &lt; 0.35</span>
                  <span style="color:var(--text-muted)"> &mdash; </span>
                  <span class="flow2-good">Verified</span>
                </div>
                <div class="flow2-fork">
                  <div class="flow2-fork-bad"><div class="flow2-node flow2-yellow">Unknown<div class="flow2-note">No record</div></div></div>
                  <div class="flow2-fork-good">
                    <div class="flow2-node flow2-green">Write Attendance + Save Face Capture<div class="flow2-note">CSV record + JPEG photo (sharpest frame)</div></div>
                  </div>
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
              ['Input','Face crop (224x224) + Full frame (224x224)'],
              ['Classes','fake = 0 / real = 1'],
              ['Threshold (face crop)','0.75'],
              ['Threshold (full frame)','0.55'],
              ['Window size','7 frames'],
              ['Min real votes','5 / 7'],
              ['Sharp-frame buffer','20 frames — Laplacian variance'],
              ['Test accuracy','~ 94.1 %'],
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
              ['POC sample','45 pairs (15 pos / 30 neg)'],
              ['POC accuracy','100 % (small sample)'],
            ])}
          </div>
        </div>
      </div>
    </div>

    <!-- 05 Training Pipeline -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">05</span> Training Pipeline</div>
      <div class="card">
        <div class="timeline">
          ${[
            { color:'var(--blue)', phase:'Phase 1', title:'Chuan bi du lieu Anti-Spoofing',
              items:[
                `Dataset: ${_cp('data_face/Image/','blue')} &ndash; live / not_live`,
                `Cau truc: ${_cp('train_photo/{live,not_live}','orange')} + ${_cp('test_photo/{live,not_live}','orange')}`,
                `Tien xu ly: Haar cascade crop mat, resize 224x224, split train/test`,
                `Notebook: ${_cp('02_train_face_crop_model.ipynb','blue')}`,
              ]},
            { color:'var(--green)', phase:'Phase 2', title:'Train Anti-Spoofing Model',
              items:[
                `Model: MobileNetV3-small (classification head 2 classes)`,
                `Output: ${_cp('vfa_mobilenetv3_small_best.pth','green')}`,
                `Test accuracy: ~94.1%`,
                `Deploy threshold: 0.90 offline; webcam temporal voting face=0.75, full=0.55`,
                `Notebook: ${_cp('02_train_face_crop_model.ipynb','blue')}`,
              ]},
            { color:'var(--purple)', phase:'Phase 3', title:'Face Verification POC',
              items:[
                `Enrolled ${_cp('person_001','purple')}, ${_cp('person_002','purple')}, ${_cp('person_003','purple')} using InsightFace buffalo_l ArcFace`,
                `Template = mean-normalized embedding across enroll images`,
                `Luu vao ${_cp('person_templates.pkl','green')}`,
                `Threshold 0.35 tren 45-pair evaluation; 100% accuracy on POC sample`,
                `Notebook: ${_cp('03_face_verification_poc.ipynb','blue')}`,
              ]},
            { color:'var(--yellow)', phase:'Phase 4', title:'Train Face Attribute Model',
              items:[
                `Dataset: UTKFace (gender + age labels)`,
                `Model: MobileNetV3-small multi-task (gender_head + age_group_head + age_head)`,
                `Age normalization: label / 100.0 trong training; decode x 100.0 khi predict`,
                `Results: gender acc ~92.2%, age_group acc ~79.7%, age MAE ~6.5 years`,
                `Output: ${_cp('face_attribute_mobilenetv3_best.pth','yellow')}`,
                `Notebook: ${_cp('04_train_face_attribute_model.ipynb','blue')}`,
              ]},
            { color:'var(--green)', phase:'Phase 5', title:'Tich hop Deploy',
              items:[
                `Copy models vao ${_cp('Deploy/models/','green')}`,
                `Copy enroll images vao ${_cp('Deploy/data/enroll_images/','green')}`,
                `Module split: ${_cp('core/','blue')} &middot; ${_cp('backend/','blue')} &middot; ${_cp('frontend/','blue')} &middot; ${_cp('camera_app/','blue')}`,
                `Storage: local CSV/JSON/pickle — khong SQL/SQLite`,
                `Gop dang ky khuon mat vao quan ly nguoi (single nav item)`,
                `Them face captures: tu luu anh sau check-in/out thanh cong`,
                `Script: ${_cp('init_deploy.py','green')} de migrate du lieu cu`,
              ]},
          ].map(t=>`
            <div class="timeline-item">
              <div class="timeline-dot" style="background:${t.color}"></div>
              <div class="timeline-phase" style="color:${t.color}">${t.phase}</div>
              <div class="timeline-title">${t.title}</div>
              <div class="timeline-body"><ul>${t.items.map(i=>`<li>${i}</li>`).join('')}</ul></div>
            </div>`).join('')}
        </div>
      </div>
    </div>

    <!-- 06 Runtime Workflow -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">06</span> Runtime Attendance Workflow</div>
      <div class="two-col">
        <div class="card">
          <div class="card-title" style="color:var(--green);margin-bottom:18px">Check-In Flow</div>
          ${_step([
            ['Camera detects face (Haar cascade)',               'default'],
            ['Sharp-frame buffer accumulates frames',            'default'],
            ['Anti-spoofing temporal voting',                    'default'],
            ['FAKE_OR_SUSPECT -> reject, no record, no capture', 'bad'],
            ['REAL_ATTENDANCE_OK -> extract ArcFace embedding',  'good'],
            ['Cosine similarity < 0.35 -> UNKNOWN, no record',   'bad'],
            ['Verified -> check person status',                  'default'],
            ['Inactive -> INACTIVE USER, no record',             'bad'],
            ['Already checked in today -> ALREADY CHECKED IN',   'warn'],
            ['First check-in: write CSV row, save face capture JPEG', 'good'],
          ])}
        </div>
        <div class="card">
          <div class="card-title" style="color:var(--blue);margin-bottom:18px">Check-Out Flow</div>
          ${_step([
            ['Camera detects face',                              'default'],
            ['Anti-spoofing + face verification (same as check-in)','default'],
            ['No check-in record today -> error, no record',     'bad'],
            ['Already checked out -> ALREADY CHECKED OUT',       'warn'],
            ['Checked in but not out: update CSV row + save face capture', 'good'],
          ])}
          <div style="margin-top:20px">
            <div class="card-title" style="margin-bottom:12px">Data Rules</div>
            ${_kv([
              ['1 row per person per day', `${_cp('attendance_YYYY-MM-DD.csv','green')}`],
              ['Check-in',       'Create row / status = CHECKED_IN'],
              ['Duplicate check-in', 'Blocked / ALREADY_CHECKED_IN'],
              ['Check-out',      'Update row / status = CHECKED_OUT'],
              ['Face capture',   'JPEG saved to face_captures/date/mode/'],
              ['Delete record',  'Cascades: CSV row + face capture images'],
              ['Camera cooldown','4 s between writes'],
            ])}
          </div>
        </div>
      </div>
    </div>

    <!-- 07 Data Storage -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">07</span> Data Storage Layout</div>
      <div class="card" style="padding-bottom:0">
        <div class="ds-grid">
          ${[
            { name:'people.csv',                  color:'var(--blue)',
              tag:'CSV',
              fields:[['person_id','TEXT, Primary Key'],['full_name','TEXT'],['student_code','TEXT'],['class_name','TEXT'],['status','active / inactive'],['created_at / updated_at','TIMESTAMP']],
              note:'Master list of registered users' },
            { name:'attendance_YYYY-MM-DD.csv',   color:'var(--green)',
              tag:'CSV / day',
              fields:[['person_id','TEXT'],['check_in_time','TIMESTAMP'],['check_out_time','TIMESTAMP'],['check_in_similarity','REAL'],['face_real_score','REAL'],['attendance_status','CHECKED_IN / CHECKED_OUT']],
              note:'One file per calendar day. One row per person.' },
            { name:'recent_events.json',          color:'var(--yellow)',
              tag:'JSON',
              fields:[['event_type','CHECK_IN / CHECK_OUT'],['event_time','TIMESTAMP'],['person_id','TEXT'],['full_name','TEXT'],['similarity','REAL'],['liveness_status','TEXT']],
              note:'Sliding window of last 50 events. Polled by frontend every 5 s.' },
            { name:'person_templates.pkl',        color:'var(--purple)',
              tag:'Pickle',
              fields:[['type','dict[str, np.ndarray]'],['key','person_id'],['value','float32 (512,)'],['method','Mean-normalized ArcFace embedding'],['update','On /face/register call']],
              note:'Re-loaded from disk on each identity search.' },
            { name:'enroll_images/{person_id}/',  color:'var(--blue)',
              tag:'JPEG',
              fields:[['naming','enroll_NN_YYYYMMDD_HHMMSS.jpg'],['quality','JPEG 92'],['written by','/face/register endpoint'],['used for','Display in People detail page'],['backup','Manual']],
              note:'Saved automatically on every face registration call.' },
            { name:'face_captures/{date}/{mode}/',color:'var(--orange)',
              tag:'JPEG',
              fields:[['naming','{person_id}_{date}_{time}_{mode}.jpg'],['quality','JPEG 95 + unsharp mask'],['selection','Sharpest frame (Laplacian variance)'],['written by','Camera app on success'],['cascade delete','Yes — with attendance record']],
              note:'Auto-saved on successful check-in or check-out.' },
            { name:'models/',                     color:'var(--text-muted)',
              tag:'PTH / JSON',
              fields:[['anti_spoof/','vfa_mobilenetv3_small_best.pth'],['attribute/','face_attribute_mobilenetv3_best.pth'],['verification/','face_verification_config.json + person_templates.pkl'],['access','Read-only at inference']],
              note:'Copied from project root during init_deploy.py.' },
          ].map(f=>`
            <div class="ds-card">
              <div class="ds-card-top">
                <code class="ds-name" style="color:${f.color}">${f.name}</code>
                <span class="ds-tag" style="border-color:${f.color};color:${f.color}">${f.tag}</span>
              </div>
              <div class="ds-fields">
                ${f.fields.map(([k,v])=>`
                  <div class="ds-field">
                    <span class="ds-fk">${k}</span>
                    <span class="ds-fv">${v}</span>
                  </div>`).join('')}
              </div>
              <div class="ds-note">${f.note}</div>
            </div>`).join('')}
        </div>
        <div class="ds-footer">
          No SQL / SQLite &mdash; all data stored as plain files. Easy to inspect, back up, and move. The entire Deploy folder is self-contained.
        </div>
      </div>
    </div>

    <!-- 08 Web Navigation -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">08</span> Web Management Navigation</div>
      <div class="card">
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px">
          ${[
            { page:'Dashboard',            desc:'Metrics hom nay, recent events feed, auto-refresh 5s',                     color:'var(--blue)' },
            { page:'Quan ly nguoi',        desc:'Danh sach + tim kiem + phan trang + detail page (thong tin / anh / lich su / actions) + them nguoi co upload anh', color:'var(--green)' },
            { page:'Tim kiem / Xac minh', desc:'Face search top-K (1-to-N) + verification 1-to-1',                          color:'var(--purple)' },
            { page:'Phan tich anh',        desc:'Detect faces + bbox + gender + age + age_group + embedding dim',            color:'var(--purple)' },
            { page:'Bao cao diem danh',    desc:'Filter + sort + export CSV/Excel + xoa record (cascade images)',            color:'var(--yellow)' },
            { page:'  Face Captures',      desc:'Xem anh khuon mat da chup khi check-in/out, lightbox, download',           color:'var(--orange)' },
            { page:'Pipeline Report',      desc:'Trang bao cao ky thuat nay',                                                color:'var(--text-muted)' },
          ].map(n=>`
            <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;padding:14px;border-left:3px solid ${n.color}">
              <div style="font-size:13px;font-weight:700;color:${n.color};margin-bottom:6px">${n.page}</div>
              <div style="font-size:12px;color:var(--text-muted)">${n.desc}</div>
            </div>`).join('')}
        </div>
      </div>
    </div>

    <!-- 09 Results -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">09</span> Results</div>
      <div class="res-grid">
        ${[
          { title:'Anti-Spoofing', color:'var(--green)', stats:[
            ['Model','MobileNetV3-small'],
            ['Test accuracy','94.1 %'],
            ['Sharp-frame buffer','20 frames / Laplacian variance'],
            ['Webcam output','REAL / FAKE'],
            ['Voting','Temporal window = 7'],
          ]},
          { title:'Face Verification', color:'var(--blue)', stats:[
            ['Backend','InsightFace / ArcFace'],
            ['Threshold','0.35'],
            ['POC sample','45 pairs (15 pos / 30 neg)'],
            ['POC accuracy','100 %'],
            ['Embedding dim','512'],
          ]},
          { title:'Face Attribute', color:'var(--purple)', stats:[
            ['Gender accuracy','92.2 %'],
            ['Age-group accuracy','79.7 %'],
            ['Age MAE','~ 6.5 years'],
            ['Output','gender / age / age_group'],
            ['Dataset','UTKFace'],
          ]},
          { title:'Attendance System', color:'var(--yellow)', stats:[
            ['Check-in / out','Operational'],
            ['Dedup per day','1 row / person'],
            ['Report modes','PRESENT / ABSENT / CHECKED_OUT'],
            ['Export','CSV / Excel'],
            ['Delete','Cascade: CSV row + face captures'],
          ]},
          { title:'Face Captures', color:'var(--orange)', stats:[
            ['Trigger','Successful check-in or check-out'],
            ['Storage','face_captures/{date}/{mode}/'],
            ['Filename','{person_id}_{datetime}_{mode}.jpg'],
            ['Quality','JPEG 95 + unsharp mask'],
            ['View','Web: Captures tab + lightbox'],
          ]},
          { title:'System', color:'var(--text-muted)', stats:[
            ['Backend','FastAPI + Uvicorn'],
            ['Frontend','HTML / CSS / JS (SPA)'],
            ['Camera app','Python + OpenCV'],
            ['Storage','Local CSV / JSON / pickle'],
            ['Nav pages','5 main + Pipeline report'],
          ]},
        ].map(c=>`
          <div class="res-card">
            <div class="res-card-head" style="border-color:${c.color}">
              <span class="res-card-title" style="color:${c.color}">${c.title}</span>
            </div>
            <div class="res-card-body">
              ${c.stats.map(([k,v])=>`
                <div class="res-row">
                  <span class="res-key">${k}</span>
                  <span class="res-val">${v}</span>
                </div>`).join('')}
            </div>
          </div>`).join('')}
      </div>
    </div>

    <!-- 10 Demo Guide -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">10</span> Demo Guide</div>
      <div class="card">
        <ul class="checklist">
          ${[
            ['Initialize data',           _cp('python scripts/init_deploy.py','green'),        'Run once — seeds DB, migrates old logs, copies enroll images'],
            ['Start backend + frontend',  _cp('scripts\\\\run_backend.bat','yellow'),          `API + Frontend at ${_cp('http://127.0.0.1:8000','blue')}`],
            ['Demo Quan ly nguoi',        'Sidebar > Quan ly nguoi',                           'Browse list, click a row to open detail page'],
            ['Demo them nguoi + anh',     'Click "+ Them nguoi moi"',                          'Fill info + upload face images in one modal'],
            ['Demo cap nhat khuon mat',   'Detail page > tab "Anh dang ky"',                  'Upload zone + register button inline'],
            ['Demo lich su diem danh',    'Detail page > tab "Lich su diem danh"',             'Filter 7 / 30 / all days'],
            ['Demo Tim kiem / Xac minh', 'Sidebar > Tim kiem',                                'Upload query image, view top-K + 1-to-1 verify'],
            ['Demo Phan tich anh',        'Sidebar > Phan tich anh',                           'Upload image, see bbox + gender + age + age_group'],
            ['Demo Camera Check-in',      _cp('scripts\\\\run_camera_checkin.bat','yellow'),   'Startup menu selects mode + camera, press 1/2/Q'],
            ['Demo Camera Check-out',     _cp('scripts\\\\run_camera_checkout.bat','yellow'),  'Check-out logic + saves face capture'],
            ['Demo Bao cao + export',     'Sidebar > Bao cao diem danh',                      'Filter, export CSV/Excel, delete record (cascade)'],
            ['Demo Face Captures',        'Bao cao > tab "Face Captures"',                    'View photos, lightbox, download per image'],
            ['Demo Pipeline Report',      'Sidebar > Pipeline Report',                         'This page — full technical overview'],
          ].map(([title,code,note],i)=>`
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

    <!-- 11 Limitations -->
    <div class="pipeline-section">
      <div class="pipeline-section-title"><span class="sec-num">11</span> Limitations &amp; Next Steps</div>
      <div class="limit-grid">
        <div class="limit-card warn">
          <div class="limit-card-title">Current Limitations</div>
          <ul class="limit-list">
            ${[
              'POC local file storage — not a multi-user production server',
              'Anti-spoofing does not cover advanced attacks (3D masks, deepfakes)',
              'Face verification validated on a small POC sample only',
              'Age estimation is approximate (MAE ~ 6.5 years)',
              'Camera app runs locally — no distributed camera support',
              'No role-based access control (admin / user)',
              'No automatic data backup',
              'Face captures quality depends on camera and lighting conditions',
            ].map(t=>`<li>${t}</li>`).join('')}
          </ul>
        </div>
        <div class="limit-card next">
          <div class="limit-card-title">Recommended Next Steps</div>
          <ul class="limit-list">
            ${[
              'Collect real-environment spoof samples to retrain anti-spoofing model',
              'Expand face verification dataset to 50-100+ identities',
              'Add JWT-based authentication and role management',
              'Implement scheduled data backup',
              'Add system-level audit logging',
              'Migrate to database server for multi-site deployment',
              'Containerise with Docker or package as internal installer',
              'Add support for multiple simultaneous cameras',
              'Build mobile-friendly version of the web frontend',
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

/* ── helpers ── */
function _cp(text, color='blue') {
  const m={blue:'var(--blue)',green:'var(--green)',yellow:'var(--yellow)',orange:'var(--orange)',purple:'var(--purple)',red:'var(--red)',muted:'var(--text-muted)'};
  return `<code style="color:${m[color]||m.blue};font-family:'Cascadia Code','Fira Code',monospace;font-size:12.5px;background:rgba(255,255,255,.05);padding:1px 5px;border-radius:3px">${text}</code>`;
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
  return `<div style="display:flex;flex-direction:column;gap:0">${steps.map(([text,type],i)=>{
    const c={good:'var(--green)',bad:'var(--red)',warn:'var(--yellow)',default:'var(--border)'};
    const bg={good:'var(--green-bg)',bad:'var(--red-bg)',warn:'var(--yellow-bg)',default:'var(--bg-surface)'};
    const tc={good:'var(--green)',bad:'var(--red)',warn:'var(--yellow)',default:'var(--text)'};
    return `
      <div style="display:flex;align-items:stretch;gap:0">
        <div style="display:flex;flex-direction:column;align-items:center;width:28px;flex-shrink:0">
          <div style="width:10px;height:10px;border-radius:50%;background:${c[type]};margin-top:12px;flex-shrink:0;border:2px solid var(--bg)"></div>
          ${i<steps.length-1?`<div style="width:2px;flex:1;background:var(--border);margin:2px 0"></div>`:''}
        </div>
        <div style="padding:8px 0 ${i<steps.length-1?'8px':'0'} 12px">
          <div style="font-size:13px;color:${tc[type]};background:${type!=='default'?bg[type]:'transparent'};
               ${type!=='default'?'padding:4px 10px;border-radius:5px;display:inline-block':''}">${text}</div>
        </div>
      </div>`;
  }).join('')}</div>`;
}
