/* Tarixchi Abdulloh — Telegram Mini App */
(() => {
'use strict';
const tg = window.Telegram && Telegram.WebApp;
const $ = (s, r = document) => r.querySelector(s);
const view = $('#view');
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const LET = ['A', 'B', 'C', 'D'];

/* ---------- Ikonkalar ---------- */
const P = {
  home:'<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  trophy:'<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/>',
  audio:'<path d="M3 14v-2a9 9 0 0 1 18 0v2"/><rect x="3" y="14" width="4" height="7" rx="1.5"/><rect x="17" y="14" width="4" height="7" rx="1.5"/>',
  books:'<rect x="4" y="3" width="5" height="18" rx="1"/><rect x="11" y="3" width="5" height="18" rx="1"/><path d="m17.5 5 3.5 15"/>',
  shield:'<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
  play:'<path d="M7 4.5v15l13-7.5z"/>', pause:'<rect x="6" y="4.5" width="4" height="15" rx="1"/><rect x="14" y="4.5" width="4" height="15" rx="1"/>',
  trash:'<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  edit:'<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>',
  plus:'<path d="M12 5v14M5 12h14"/>', upload:'<path d="M12 16V4m0 0-4 4m4-4 4 4M4 20h16"/>',
  chev:'<path d="m9 6 6 6-6 6"/>', back:'<path d="m15 6-6 6 6 6"/>',
  flame:'<path d="M12 3c1 4 5 5.5 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-5 1-9z"/>',
  check:'<path d="m5 12 5 5 9-10"/>', x:'<path d="M6 6l12 12M18 6 6 18"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  spark:'<path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8zM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
  refresh:'<path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5"/>', target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/>',
  file:'<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/>', db:'<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
  star:'<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
};
const ic = (n, cls = '') => `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true">${P[n] || ''}</svg>`;
const icf = n => ic(n, 'fill');

/* ---------- Holat ---------- */
const S = { cfg: {}, user: null, stats: null, tree: null, tab: 'home', nav: [], quiz: null, rating: { period: 'week' }, audios: [], books: [], playing: null };
const dev = new URLSearchParams(location.search).get('dev');

/* ---------- Yordamchilar ---------- */
function toast(msg, kind = '') {
  const t = $('#toast'); t.textContent = msg; t.className = 'show ' + kind;
  clearTimeout(toast.t); toast.t = setTimeout(() => t.className = '', 2600);
}
function haptic(kind) { try { kind === 'select' ? tg.HapticFeedback.selectionChanged() : tg.HapticFeedback.notificationOccurred(kind); } catch (e) {} }
async function api(path, opt = {}) {
  const headers = { 'X-Telegram-Init-Data': (tg && tg.initData) || '' };
  if (dev) headers['X-Dev-User'] = dev;
  if (opt.json) { headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(opt.json); }
  const r = await fetch(path, { method: opt.method || (opt.body ? 'POST' : 'GET'), headers, body: opt.body });
  let data = {}; try { data = await r.json(); } catch (e) {}
  if (!r.ok) throw new Error(data.error || 'Xatolik yuz berdi');
  return data;
}
function upload(path, fd, onProgress) {
  return new Promise((resolve, reject) => {
    const x = new XMLHttpRequest(); x.open('POST', path);
    x.setRequestHeader('X-Telegram-Init-Data', (tg && tg.initData) || ''); if (dev) x.setRequestHeader('X-Dev-User', dev);
    x.upload.onprogress = e => e.lengthComputable && onProgress && onProgress(e.loaded / e.total);
    x.onload = () => { let d = {}; try { d = JSON.parse(x.responseText); } catch (e) {} x.status < 300 ? resolve(d) : reject(new Error(d.error || 'Yuklashda xatolik')); };
    x.onerror = () => reject(new Error('Tarmoq xatosi'));
    x.send(fd);
  });
}
function ask(msg) {
  return new Promise(res => {
    if (tg && tg.showConfirm && tg.initData) tg.showConfirm(msg, ok => res(ok)); else res(confirm(msg));
  });
}
const fmt = n => (Math.round(n * 10) / 10).toString().replace('.', ',');
const fmtTime = s => { s = Math.max(0, s | 0); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
const size = b => b > 1048576 ? (b / 1048576).toFixed(1) + ' MB' : Math.round(b / 1024) + ' KB';
const initials = n => (n || '?').trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase();
const isAdmin = () => !!(S.user && S.user.is_admin);

/* ---------- Sheet (pastdan chiquvchi oyna) ---------- */
function openSheet(html, mount) {
  const root = $('#sheet-root');
  root.innerHTML = `<div class="ov"><div class="sheet"><div class="grip"></div>${html}</div></div>`;
  $('.ov', root).addEventListener('click', e => { if (e.target.classList.contains('ov')) closeSheet(); });
  mount && mount($('.sheet', root));
}
function closeSheet() {
  $('#sheet-root').innerHTML = '';
  if (S.quiz && S.quiz.active && !S.quiz.locked && !S.timerId) startTimer();   // tahrirlash oynasi yopilganda vaqt davom etadi
}

/* ---------- Navigatsiya ---------- */
function setBack(fn) {
  if (!tg || !tg.BackButton) return;
  try { tg.BackButton.offClick(setBack.h); } catch (e) {}
  if (fn) { setBack.h = fn; tg.BackButton.onClick(fn); tg.BackButton.show(); } else tg.BackButton.hide();
}
function go(renderFn) { S.nav.push(renderFn); renderFn(); syncBack(); }
function goBack() {
  if (S.quiz && S.quiz.active) return finishQuiz(true);
  S.nav.pop(); const f = S.nav[S.nav.length - 1];
  if (f) f(); else renderTab(); syncBack();
}
function syncBack() { setBack(S.nav.length ? goBack : null); }
function resetNav() { S.nav = []; syncBack(); }
const crumb = (title, back = true) => `<div class="crumb">${back ? `<button class="back" data-a="back">${ic('back')}</button>` : ''}<h2>${esc(title)}</h2></div>`;

/* ---------- Tab bar ---------- */
function tabs() {
  const t = [['home', 'Test', 'home'], ['rating', 'Reyting', 'trophy'], ['audio', 'Audiolar', 'audio']];
  if (S.cfg.has_books) t.push(['books', 'Kitoblar', 'books']);
  if (isAdmin()) t.push(['admin', 'Admin', 'shield']);
  return t;
}
function setQuizMode(on) { document.body.classList.toggle('in-quiz', on); $('#tabbar').classList.toggle('hide', on); }
function renderTabbar() {
  $('#tabbar').innerHTML = `<div class="tabs-in">${tabs().map(([id, label, icon]) => `<button class="tab ${S.tab === id ? 'on' : ''}" data-tab="${id}">${ic(icon)}${label}</button>`).join('')}</div>`;
}
function renderTab() {
  stopTimer(); S.quiz = null; setQuizMode(false);
  renderTabbar();
  ({ home: renderHome, rating: renderRating, audio: renderAudio, books: renderBooks, admin: renderAdmin }[S.tab] || renderHome)();
  window.scrollTo(0, 0);
}

/* ---------- BOSH SAHIFA ---------- */
async function refreshStats() { try { const d = await api('/api/me'); S.user = d.user; S.stats = d.stats; } catch (e) {} }
function renderHome() {
  const st = S.stats || {}, nl = st.next_level;
  const prev = [0, 25, 100, 250, 500].filter(v => v <= st.points).pop() || 0;
  const pct = nl ? Math.min(100, ((st.points - prev) / (nl.need - prev)) * 100) : 100;
  view.innerHTML = `
    <div class="hero row between">
      <div class="grow"><div class="hello">Assalomu alaykum,</div><h1 class="gold-grad">${esc(S.user.name)}</h1></div>
      ${isAdmin() ? `<span class="badge admin">${ic('shield')}Admin</span>` : ''}
    </div>
    <div class="card">
      <div class="row between" style="margin-bottom:12px">
        <span class="badge">${ic('star')}${esc(st.level)}</span>
        ${st.streak ? `<span class="badge" style="color:var(--amber);border-color:rgba(242,169,59,.4)">${ic('flame')}${st.streak} kunlik seriya</span>` : ''}
      </div>
      <div class="stats">
        <div class="stat"><b class="gold-grad">${fmt(st.points || 0)}</b><span>Ball</span></div>
        <div class="stat"><b>${st.correct || 0}</b><span>To'g'ri javob</span></div>
        <div class="stat"><b>${st.week_rank ? '#' + st.week_rank : '—'}</b><span>Haftalik o'rin</span></div>
      </div>
      <div class="level-bar"><i style="width:${pct}%"></i></div>
      <div class="muted" style="font-size:12px;margin-top:6px">${nl ? `${esc(nl.name)} darajasigacha ${fmt(Math.max(0, nl.need - st.points))} ball` : 'Eng yuqori darajaga erishdingiz!'}</div>
    </div>
    <div class="section-title">Bilimingizni sinang</div>
    <div class="stack">
      <div class="item gold-item" data-a="start">
        <div class="ico">${ic('target')}</div>
        <div class="grow"><div class="t">Testni boshlash</div><div class="s">Sinf, fan va mavzuni tanlang • har to'g'ri javob +${fmt(S.cfg.points)} ball</div></div>${ic('chev', 'chev')}
      </div>
      <div class="item" data-a="mistakes">
        <div class="ico">${ic('refresh')}</div>
        <div class="grow"><div class="t">Xatolar ustida ishlash</div><div class="s">${st.mistakes ? `Oxirgi xato qilgan ${st.mistakes} ta savolingizni takrorlang` : 'Hozircha xatolar yo\'q — ajoyib!'}</div></div>${ic('chev', 'chev')}
      </div>
    </div>
    <div class="orn" style="margin-top:22px">${ic('star')}</div>
    <p class="center muted" style="font-size:12.5px">${S.stats.tests || 0} ta test yakunlangan</p>`;
}

/* ---------- TEST OQIMI ---------- */
async function loadTree(force) { if (!S.tree || force) S.tree = (await api('/api/tree')).tree; return S.tree; }

function startFlow() {
  resetNav(); S.nav.push(() => renderTab());   // bosh sahifa
  view.innerHTML = `<div class="countdown"><div class="n" id="cd">3</div></div>`;
  let n = 3; haptic('select');
  const iv = setInterval(async () => {
    n--; const el = $('#cd');
    if (!el) return clearInterval(iv);
    if (n > 0) { el.textContent = n; el.style.animation = 'none'; void el.offsetWidth; el.style.animation = ''; haptic('select'); }
    else { clearInterval(iv); el.textContent = '🚀'; await loadTree(true).catch(e => toast(e.message, 'err')); setTimeout(() => go(() => showGrades('quiz')), 450); }
  }, 1000);
}
function showGrades(mode) {
  const manage = mode === 'manage';
  view.innerHTML = `${crumb(manage ? 'Savollar bazasi' : 'Sinfingizni tanlang')}
    <div class="stack">${(S.tree || []).map((g, i) => `
      <div class="item" data-a="grade" data-i="${i}" data-mode="${mode}">
        <div class="ico">${ic('books')}</div>
        <div class="grow"><div class="t">${esc(g.grade)}</div><div class="s">${g.count} ta savol</div></div>
        ${isAdmin() ? `<button class="icon-btn danger" data-a="delgrade" data-i="${i}" title="Sinfni o'chirish">${ic('trash')}</button>` : ''}
        ${ic('chev', 'chev')}
      </div>`).join('') || `<div class="empty"><div class="big">📜</div>Hozircha savollar yo'q.${isAdmin() ? '<br>Admin bo\'limidan savol qo\'shing.' : ''}</div>`}</div>`;
}
function showSubjects(gi, mode) {
  const g = S.tree[gi];
  view.innerHTML = `${crumb(g.grade + ' — fanni tanlang')}<div class="stack">${g.subjects.map((s, si) => `
    <div class="item" data-a="subject" data-gi="${gi}" data-si="${si}" data-mode="${mode}">
      <div class="ico">${ic('spark')}</div><div class="grow"><div class="t">${esc(s.subject)}</div><div class="s">${s.topics.length} ta mavzu • ${s.count} ta savol</div></div>${ic('chev', 'chev')}
    </div>`).join('')}</div>`;
}
function showTopics(gi, si, mode) {
  S.mode = mode; const g = S.tree[gi], s = g.subjects[si], manage = mode === 'manage';
  view.innerHTML = `${crumb(`${g.grade}, ${s.subject}`)}
    <p class="muted" style="margin:-4px 4px 12px">${manage ? 'Mavzuni tanlang' : 'Qaysi mavzudan sinov topshirasiz?'}</p>
    <div class="stack">
      ${manage ? '' : `<div class="item gold-item" data-a="topic" data-gi="${gi}" data-si="${si}" data-ti="-1"><div class="ico">${ic('spark')}</div><div class="grow"><div class="t">Barcha mavzular</div><div class="s">${s.count} ta savol aralash</div></div>${ic('chev', 'chev')}</div>`}
      ${s.topics.map((t, ti) => `
      <div class="item" data-a="${manage ? 'mtopic' : 'topic'}" data-gi="${gi}" data-si="${si}" data-ti="${ti}">
        <div class="ico">${ic('file')}</div>
        <div class="grow"><div class="t">${esc(t.topic)}</div><div class="s">${t.count} ta savol</div></div>
        ${isAdmin() ? `<button class="icon-btn danger" data-a="deltopic" data-gi="${gi}" data-si="${si}" data-ti="${ti}" title="Mavzuni o'chirish">${ic('trash')}</button>` : ''}
        ${ic('chev', 'chev')}
      </div>`).join('')}
    </div>`;
}
function showInfo(gi, si, ti) {
  const g = S.tree[gi], s = g.subjects[si], all = ti < 0, t = all ? null : s.topics[ti];
  const n = all ? s.count : t.count;
  S.pending = { grade: g.grade, subject: s.subject, topic: all ? '*' : t.topic, count: 0, total: n };
  view.innerHTML = `${crumb('Test ma\'lumoti')}
    <div class="card center">
      <div style="font-size:34px">🏛️</div>
      <h2 style="margin:8px 0 4px">${esc(all ? 'Barcha mavzular' : t.topic)}</h2>
      <div class="muted">${esc(g.grade)} — ${esc(s.subject)}</div>
      <div class="stats" style="margin:16px 0 6px">
        <div class="stat"><b id="qn">${n}</b><span>savol</span></div>
        <div class="stat"><b>${S.cfg.time}s</b><span>har biriga</span></div>
        <div class="stat"><b>+${fmt(S.cfg.points)}</b><span>ball / to'g'ri</span></div>
      </div>
      ${n > 20 ? `<div class="muted" style="font-size:12px;margin:14px 0 8px">Savollar soni</div><div class="chips" style="justify-content:center">${[10, 20, 30, 0].map(c => `<button class="chip ${c === 0 ? 'on' : ''}" data-a="cnt" data-c="${c}">${c || 'Hammasi'}</button>`).join('')}</div>` : ''}
      <button class="btn primary block" style="margin-top:18px" data-a="run">🏁 Boshlash</button>
    </div>`;
}
async function beginQuiz(payload) {
  try {
    view.innerHTML = '<div class="spinner" style="margin-top:30vh"></div>';
    const d = await api('/api/quiz/start', { json: payload });
    S.quiz = { sid: d.session_id, title: d.title, qs: d.questions, i: 0, ok: 0, bad: 0, skip: 0, time: d.time, left: d.time, locked: false, active: true };
    if (!S.nav.length) S.nav.push(() => renderTab());
    S.nav.push(() => {}); syncBack(); setQuizMode(true);
    showQuestion();
  } catch (e) { toast(e.message, 'err'); renderTab(); }
}
function stopTimer() { if (S.timerId) { clearInterval(S.timerId); S.timerId = null; } }
function startTimer() {
  stopTimer(); const q = S.quiz; q.left = q.left ?? q.time;
  tick();
  S.timerId = setInterval(() => { q.left--; tick(); if (q.left <= 0) { stopTimer(); answer(null); } }, 1000);
}
function tick() {
  const q = S.quiz; if (!q) return;
  const C = 2 * Math.PI * 22, el = $('.timer'); if (!el) return;
  $('.timer .fg').style.strokeDashoffset = C * (1 - Math.max(0, q.left) / q.time);
  $('.timer b').textContent = Math.max(0, q.left);
  el.className = 'timer' + (q.left <= 5 ? ' danger' : q.left <= 10 ? ' warn' : '');
}
function showQuestion() {
  const q = S.quiz;
  if (q.i >= q.qs.length) return finishQuiz(false);
  const cur = q.qs[q.i], C = 2 * Math.PI * 22; q.locked = false; q.left = q.time;
  view.innerHTML = `
    <div class="qtop">
      <div class="timer"><svg viewBox="0 0 54 54"><circle class="bg" cx="27" cy="27" r="22"/><circle class="fg" cx="27" cy="27" r="22" stroke-dasharray="${C}" stroke-dashoffset="0"/></svg><b>${q.time}</b></div>
      <div class="grow"><div class="muted" style="font-size:12px">${esc(q.title)}</div>
        <div class="counter"><span>${q.i + 1}/${q.qs.length}</span><span class="ok">✓ ${q.ok}</span><span class="bad">✕ ${q.bad}</span></div></div>
      <button class="btn sm danger" data-a="finish">Tugatish</button>
    </div>
    <div class="progress"><i style="width:${(q.i / q.qs.length) * 100}%"></i></div>
    <div class="card qcard">
      <div class="qnum">${q.i + 1}-savol</div>
      <div class="qtext">${esc(cur.question)}</div>
      <div class="options">${cur.options.map((o, k) => `<button class="opt" data-a="opt" data-v="${k}"><span class="k">${LET[k]}</span><span>${esc(o)}</span></button>`).join('')}</div>
      ${isAdmin() ? `<div class="admin-bar"><button class="btn sm" data-a="qedit">${ic('edit')}Tahrirlash</button><button class="btn sm danger" data-a="qdel">${ic('trash')}O'chirish</button></div>` : ''}
    </div>`;
  startTimer();
}
async function answer(idx) {
  const q = S.quiz; if (!q || q.locked) return; q.locked = true; stopTimer();
  const cur = q.qs[q.i], choice = idx === null ? null : cur.options[idx];
  try {
    const r = await api('/api/quiz/answer', { json: { session_id: q.sid, qid: cur.id, choice } });
    const opts = [...document.querySelectorAll('.opt')];
    opts.forEach((b, k) => { const isRight = cur.options[k] === r.answer; b.classList.add(isRight ? 'correct' : (k === idx ? 'wrong' : 'dim')); b.disabled = true; });
    if (r.status === 'correct') { q.ok++; haptic('success'); } else if (r.status === 'wrong') { q.bad++; haptic('error'); } else { q.skip++; haptic('warning'); }
    const cn = $('.counter'); if (cn) cn.innerHTML = `<span>${q.i + 1}/${q.qs.length}</span><span class="ok">✓ ${q.ok}</span><span class="bad">✕ ${q.bad}</span>`;
    q.i++; setTimeout(() => { if (S.quiz === q && q.active) showQuestion(); }, 1500);
  } catch (e) { toast(e.message, 'err'); q.locked = false; startTimer(); }
}
async function finishQuiz(early) {
  const q = S.quiz; if (!q) return; stopTimer(); q.active = false;
  view.innerHTML = '<div class="spinner" style="margin-top:30vh"></div>';
  try {
    const r = await api('/api/quiz/finish', { json: { session_id: q.sid } });
    S.stats = r.stats; S.quiz = null; S.nav = [() => renderTab()]; syncBack(); setQuizMode(false); renderTabbar();
    showResult(r);
  } catch (e) { toast(e.message, 'err'); renderTab(); }
}
function showResult(r) {
  const pct = r.total ? Math.round((r.correct / r.total) * 100) : 0, C = 2 * Math.PI * 64;
  const msg = pct >= 90 ? 'Ajoyib natija! 🏆' : pct >= 70 ? 'Juda yaxshi! 👏' : pct >= 50 ? 'Yomon emas, davom eting 💪' : 'Takrorlash foydali bo\'ladi 📚';
  view.innerHTML = `
    <div class="card center">
      <div class="muted" style="font-size:12px">${esc(r.title)}</div>
      <div class="ring"><svg viewBox="0 0 150 150"><circle class="bg" cx="75" cy="75" r="64"/><circle class="fg" cx="75" cy="75" r="64" stroke-dasharray="${C}" stroke-dashoffset="${C}" id="rf"/></svg><b class="gold-grad">${pct}%</b></div>
      <h2>${msg}</h2>
      <div class="badge" style="margin-top:10px">${ic('star')}+${fmt(r.points)} ball</div>
      <div class="res-grid">
        <div class="res g"><b>${r.correct}</b><span>To'g'ri</span></div>
        <div class="res r"><b>${r.wrong}</b><span>Xato</span></div>
        <div class="res a"><b>${r.skipped}</b><span>O'tkazib yuborilgan</span></div>
      </div>
      <div class="muted" style="font-size:13px">Jami: ${r.total} ta savol${r.stats.streak ? ` • 🔥 ${r.stats.streak} kunlik seriya` : ''}</div>
    </div>
    <div class="stack" style="margin-top:14px">
      <button class="btn primary block" data-a="start">🔁 Yana boshlash</button>
      <button class="btn block" data-a="home">Bosh sahifa</button>
    </div>
    ${r.detail.length ? `<div class="section-title">Batafsil natija</div><div class="card flat">${r.detail.map((d, i) => `
      <div class="detail"><div class="m ${d.status}">${ic(d.status === 'correct' ? 'check' : d.status === 'wrong' ? 'x' : 'clock')}</div>
      <div class="grow">${i + 1}. ${esc(d.question)}${d.status !== 'correct' ? `<small>To'g'ri javob: ${esc(d.answer)}</small>` : ''}</div></div>`).join('')}</div>` : ''}`;
  requestAnimationFrame(() => setTimeout(() => { const f = $('#rf'); if (f) f.style.strokeDashoffset = C * (1 - pct / 100); }, 60));
  haptic('success');
}

/* ---------- Savol shakli (qo'shish / tahrirlash) ---------- */
function questionForm({ q = null, withPath = false }) {
  const dl = (id, arr) => `<datalist id="${id}">${[...new Set(arr)].map(x => `<option value="${esc(x)}">`).join('')}</datalist>`;
  const tree = S.tree || [];
  const grades = tree.map(g => g.grade), subjects = tree.flatMap(g => g.subjects.map(s => s.subject)), topics = tree.flatMap(g => g.subjects.flatMap(s => s.topics.map(t => t.topic)));
  const opts = q ? q.options : ['', '', '', ''], ci = q ? q.options.indexOf(q.answer) : 0;
  return `${withPath ? `
    <label class="f">Sinf</label><input class="in" id="f-grade" list="dl-g" placeholder="masalan: 8-sinf">${dl('dl-g', grades)}
    <label class="f">Fan</label><input class="in" id="f-subject" list="dl-s" placeholder="masalan: O'zbekiston tarixi">${dl('dl-s', subjects)}
    <label class="f">Mavzu</label><input class="in" id="f-topic" list="dl-t" placeholder="masalan: Amir Temur davlati">${dl('dl-t', topics)}` : ''}
    <label class="f">Savol matni</label><textarea class="in" id="f-q">${esc(q ? q.question : '')}</textarea>
    <label class="f">Variantlar (to'g'ri javobni belgilang)</label>
    ${opts.map((o, k) => `<div class="optrow"><input type="radio" name="ci" value="${k}" ${k === ci ? 'checked' : ''}><span class="k">${LET[k]}</span><input class="in f-o" value="${esc(o)}" placeholder="${LET[k]} variant"></div>`).join('')}`;
}
function readForm(sheet, withPath) {
  const v = id => ($('#' + id, sheet)?.value || '').trim();
  const o = {
    question: v('f-q'), options: [...sheet.querySelectorAll('.f-o')].map(i => i.value.trim()),
    correct_index: +(sheet.querySelector('input[name=ci]:checked')?.value ?? -1),
  };
  if (withPath) Object.assign(o, { grade: v('f-grade'), subject: v('f-subject'), topic: v('f-topic') });
  return o;
}
function openAddQuestion() {
  loadTree().then(() => openSheet(`<h2>Savol qo'shish</h2>${questionForm({ withPath: true })}
    <button class="btn primary block" style="margin-top:16px" id="save">Saqlash</button>`, sh => {
    $('#save', sh).onclick = async () => {
      try { await api('/api/admin/question', { json: readForm(sh, true) }); S.tree = null; toast('Savol qo\'shildi ✓', 'good'); haptic('success'); closeSheet(); }
      catch (e) { toast(e.message, 'err'); }
    };
  }));
}
async function openEditQuestion(id, onSaved) {
  try {
    const q = await api('/api/admin/question/' + id);
    openSheet(`<h2>Savolni tahrirlash</h2>${questionForm({ q })}
      <button class="btn primary block" style="margin-top:16px" id="save">Saqlash</button>`, sh => {
      $('#save', sh).onclick = async () => {
        try { const r = await api('/api/admin/question/' + id, { method: 'PUT', json: readForm(sh, false) }); S.tree = null; closeSheet(); toast('Yangilandi ✓', 'good'); onSaved && onSaved(r); }
        catch (e) { toast(e.message, 'err'); }
      };
    });
  } catch (e) { toast(e.message, 'err'); }
}

/* ---------- REYTING ---------- */
async function renderRating() {
  const P3 = [['week', 'Haftalik'], ['month', '1 oylik'], ['quarter', '3 oylik']], per = S.rating.period;
  view.innerHTML = `<div class="hero"><h1 class="gold-grad">Reyting</h1><div class="muted">Har bir to'g'ri javob uchun +${fmt(S.cfg.points)} ball</div></div>
    <div class="seg">${P3.map(([k, l]) => `<button class="${k === per ? 'on' : ''}" data-per="${k}">${l}</button>`).join('')}</div><div id="rt"><div class="spinner"></div></div>`;
  try {
    const d = await api('/api/rating?period=' + per); if (S.tab !== 'rating') return;
    const top = d.top, me = S.user.id;
    const pod = [top[1], top[0], top[2]];
    $('#rt').innerHTML = `
      <div class="card me-card"><div class="me-rank gold-grad">${d.me ? '#' + d.me.rank : '—'}</div>
        <div class="grow"><div class="t" style="font-weight:600">Sizning o'rningiz</div><div class="muted" style="font-size:13px">${d.me ? `${fmt(d.me.points)} ball • ${d.participants} ishtirokchi ichida` : 'Bu davrda hali ball to\'plamagansiz'}</div></div></div>
      ${top.length ? `
      ${top.length >= 3 ? `<div class="podium">${pod.map((u, i) => { const r = [2, 1, 3][i]; return `<div class="pod p${r}"><div class="av">${esc(initials(u.name))}</div><div class="nm">${esc(u.name)}</div><div class="pt">${fmt(u.points)}</div><div class="medal">${r}-O'RIN</div></div>`; }).join('')}</div>` : ''}
      <div>${top.slice(top.length >= 3 ? 3 : 0).map(u => `<div class="rank-row ${u.id === me ? 'me' : ''}"><div class="no">${u.rank}</div><div class="grow"><div style="font-weight:600">${esc(u.name)}</div><div class="muted" style="font-size:12px">${u.answers} ta to'g'ri javob</div></div><div class="pts">${fmt(u.points)}</div></div>`).join('')}</div>`
      : `<div class="empty"><div class="big">🏆</div>Bu davrda hali hech kim ball to'plamagan.<br>Birinchi bo'ling!</div>`}
      <p class="center muted" style="font-size:12px;margin-top:10px">So'nggi ${d.days} kun natijalari</p>`;
  } catch (e) { $('#rt').innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
}

/* ---------- AUDIOLAR ---------- */
async function renderAudio() {
  view.innerHTML = `<div class="hero row between"><div><h1 class="gold-grad">Audiolar</h1><div class="muted">Tinglab o'rganing</div></div>
    ${isAdmin() ? `<button class="btn primary sm" data-a="addaudio">${ic('plus')}Audio</button>` : ''}</div><div id="al"><div class="spinner"></div></div>`;
  try {
    S.audios = (await api('/api/audios')).audios; if (S.tab !== 'audio') return;
    $('#al').innerHTML = S.audios.length ? `<div class="stack">${S.audios.map(a => `
      <div class="item audio-item" data-a="play" data-id="${a.id}">
        <div class="ico ${S.playing === a.id ? 'playing' : ''}">${icf(S.playing === a.id && !$('#audio').paused ? 'pause' : 'play')}</div>
        <div class="grow"><div class="t">${esc(a.title)}</div><div class="s">${[a.grade, a.topic].filter(Boolean).map(esc).join(' • ') || 'Audio'} • ${size(a.size)}</div></div>
        ${isAdmin() ? `<button class="icon-btn danger" data-a="delaudio" data-id="${a.id}">${ic('trash')}</button>` : ''}
      </div>`).join('')}</div>` : `<div class="empty"><div class="big">🎧</div>Hozircha audiolar yo'q.${isAdmin() ? '<br>«Audio» tugmasi orqali qo\'shing.' : ''}</div>`;
  } catch (e) { $('#al').innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
}
const au = $('#audio');
function renderPlayer() {
  const a = S.audios.find(x => x.id === S.playing); const box = $('#player');
  document.body.classList.toggle('has-player', !!a);
  if (!a) { box.innerHTML = ''; return; }
  box.innerHTML = `<div class="mini"><div class="row between"><div class="ttl grow">${esc(a.title)}</div>
    <button class="icon-btn" data-a="pclose">${ic('x')}</button></div>
    <input type="range" id="seek" min="0" max="1000" value="0"><div class="tm"><span id="t1">0:00</span><span id="t2">0:00</span></div>
    <div class="ctl"><button class="btn sm" data-a="pback">−15</button><button class="play" data-a="ptoggle" id="pbtn">${icf('pause')}</button><button class="btn sm" data-a="pfwd">+15</button>
    <button class="btn sm" data-a="pspeed" id="spd">${au.playbackRate}x</button></div></div>`;
  $('#seek').oninput = e => { if (au.duration) au.currentTime = (e.target.value / 1000) * au.duration; };
}
au.addEventListener('timeupdate', () => { const s = $('#seek'); if (!s || !au.duration) return; s.value = (au.currentTime / au.duration) * 1000; $('#t1').textContent = fmtTime(au.currentTime); $('#t2').textContent = fmtTime(au.duration); });
au.addEventListener('play', () => { const b = $('#pbtn'); if (b) b.innerHTML = icf('pause'); });
au.addEventListener('pause', () => { const b = $('#pbtn'); if (b) b.innerHTML = icf('play'); });
au.addEventListener('ended', () => { const b = $('#pbtn'); if (b) b.innerHTML = icf('play'); });
function playAudio(id) {
  const a = S.audios.find(x => x.id === id); if (!a) return;
  if (S.playing === id) { au.paused ? au.play() : au.pause(); return; }
  S.playing = id; au.src = a.url; au.play().catch(() => toast('Audioni ochib bo\'lmadi', 'err')); renderPlayer();
  if (S.tab === 'audio') renderAudio();
}
function openAudioUpload() {
  const grades = (S.tree || []).map(g => g.grade);
  openSheet(`<h2>Audio qo'shish</h2>
    <label class="f">Nomi</label><input class="in" id="a-title" placeholder="masalan: Amir Temur hayoti">
    <label class="f">Sinf (ixtiyoriy)</label><input class="in" id="a-grade" list="dl-ag" placeholder="8-sinf"><datalist id="dl-ag">${grades.map(g => `<option value="${esc(g)}">`).join('')}</datalist>
    <label class="f">Mavzu (ixtiyoriy)</label><input class="in" id="a-topic">
    <label class="f">Audio fayl (mp3, m4a, ogg, wav…)</label><input class="in" type="file" id="a-file" accept="audio/*">
    <div class="bar hide" id="bar" style="margin-top:14px"><i></i></div>
    <button class="btn primary block" style="margin-top:16px" id="save">${ic('upload')}Yuklash</button>`, sh => {
    $('#save', sh).onclick = async () => {
      const f = $('#a-file', sh).files[0]; if (!f) return toast('Audio fayl tanlang', 'err');
      const fd = new FormData(); fd.append('file', f); fd.append('title', $('#a-title', sh).value); fd.append('grade', $('#a-grade', sh).value); fd.append('topic', $('#a-topic', sh).value);
      $('#bar', sh).classList.remove('hide'); $('#save', sh).disabled = true;
      try { await upload('/api/admin/audio', fd, p => $('#bar i', sh).style.width = (p * 100) + '%'); closeSheet(); toast('Audio qo\'shildi ✓', 'good'); if (S.tab === 'audio') renderAudio(); }
      catch (e) { toast(e.message, 'err'); $('#save', sh).disabled = false; }
    };
  });
}

/* ---------- KITOBLAR ---------- */
async function renderBooks() {
  view.innerHTML = `<div class="hero row between"><div><h1 class="gold-grad">Kitoblar</h1><div class="muted">Foydali adabiyotlar</div></div>
    ${isAdmin() ? `<button class="btn primary sm" data-a="addbook">${ic('plus')}Kitob</button>` : ''}</div><div id="bl"><div class="spinner"></div></div>`;
  try {
    S.books = (await api('/api/books')).books; if (S.tab !== 'books') return;
    $('#bl').innerHTML = S.books.length ? `<div class="stack">${S.books.map(b => `
      <div class="card book">
        <div class="cover">${esc(b.title.slice(0, 28))}</div>
        <div class="grow"><div class="t" style="font:700 17px var(--font-head)">${esc(b.title)}</div>
          <div class="muted" style="font-size:13px">${esc(b.author) || 'Muallif ko\'rsatilmagan'}</div>
          ${b.description ? `<div style="font-size:13px;margin-top:6px">${esc(b.description)}</div>` : ''}
          <div class="row" style="margin-top:10px"><span class="pill">${esc(b.ext.toUpperCase())} • ${size(b.size)}</span><div class="grow"></div>
          <button class="btn sm primary" data-a="openbook" data-id="${b.id}">Ochish</button>
          ${isAdmin() ? `<button class="icon-btn danger" data-a="delbook" data-id="${b.id}">${ic('trash')}</button>` : ''}</div></div>
      </div>`).join('')}</div>` : `<div class="empty"><div class="big">📚</div>Hozircha kitoblar yo'q.</div>`;
  } catch (e) { $('#bl').innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
}
function openBookUpload() {
  openSheet(`<h2>Kitob qo'shish</h2>
    <label class="f">Kitob nomi</label><input class="in" id="b-title">
    <label class="f">Muallif (ixtiyoriy)</label><input class="in" id="b-author">
    <label class="f">Qisqa tavsif (ixtiyoriy)</label><textarea class="in" id="b-desc"></textarea>
    <label class="f">Fayl (pdf, epub, docx…)</label><input class="in" type="file" id="b-file">
    <div class="bar hide" id="bar" style="margin-top:14px"><i></i></div>
    <button class="btn primary block" style="margin-top:16px" id="save">${ic('upload')}Yuklash</button>`, sh => {
    $('#save', sh).onclick = async () => {
      const f = $('#b-file', sh).files[0], title = $('#b-title', sh).value.trim(); if (!f || !title) return toast('Nom va faylni kiriting', 'err');
      const fd = new FormData(); fd.append('file', f); fd.append('title', title); fd.append('author', $('#b-author', sh).value); fd.append('description', $('#b-desc', sh).value);
      $('#bar', sh).classList.remove('hide'); $('#save', sh).disabled = true;
      try {
        await upload('/api/admin/book', fd, p => $('#bar i', sh).style.width = (p * 100) + '%'); closeSheet(); toast('Kitob qo\'shildi ✓', 'good');
        S.cfg.has_books = true; renderTabbar(); if (S.tab === 'books') renderBooks();
      } catch (e) { toast(e.message, 'err'); $('#save', sh).disabled = false; }
    };
  });
}

/* ---------- ADMIN ---------- */
function renderAdmin() {
  view.innerHTML = `<div class="hero"><h1 class="gold-grad">Boshqaruv</h1><div class="muted">Faqat adminlar uchun</div></div>
    <div class="stack">
      <div class="item gold-item" data-a="aiimport"><div class="ico">${ic('spark')}</div><div class="grow"><div class="t">Sun'iy intellekt bilan fayldan qo'shish</div><div class="s">Word / PDF / TXT — sinf va mavzularni o'zi ajratadi${S.cfg.ai ? '' : ' (AI kaliti yo\'q — standart format)'}</div></div>${ic('chev', 'chev')}</div>
      <div class="item" data-a="addq"><div class="ico">${ic('plus')}</div><div class="grow"><div class="t">Savol qo'shish</div><div class="s">Bitta savolni qo'lda kiritish</div></div>${ic('chev', 'chev')}</div>
      <div class="item" data-a="manage"><div class="ico">${ic('db')}</div><div class="grow"><div class="t">Savollar bazasi</div><div class="s">Tahrirlash, o'chirish, sinf va mavzularni boshqarish</div></div>${ic('chev', 'chev')}</div>
      <div class="item" data-a="addaudio"><div class="ico">${ic('audio')}</div><div class="grow"><div class="t">Audio qo'shish</div><div class="s">«Audiolar» bo'limiga yangi audio</div></div>${ic('chev', 'chev')}</div>
      <div class="item" data-a="addbook"><div class="ico">${ic('books')}</div><div class="grow"><div class="t">Kitob qo'shish</div><div class="s">${S.cfg.has_books ? '«Kitoblar» bo\'limiga yangi kitob' : 'Birinchi kitob qo\'shilgach «Kitoblar» bo\'limi paydo bo\'ladi'}</div></div>${ic('chev', 'chev')}</div>
    </div>`;
}
function openImport() {
  openSheet(`<h2>Fayldan savollarni qo'shish</h2>
    <p class="muted" style="margin:6px 0 12px">Savollar yozilgan faylni yuklang. Bot sinf, fan va mavzularni o'zi ajratib oladi — qo'shishdan oldin natijani ko'rasiz.</p>
    <label class="drop"><input type="file" id="imp" accept=".docx,.txt,.pdf" hidden>${ic('upload')}<b>Faylni tanlang</b>.docx, .txt yoki .pdf</label><div id="imp-out"></div>`, sh => {
    $('#imp', sh).onchange = async e => {
      const f = e.target.files[0]; if (!f) return; const out = $('#imp-out', sh);
      out.innerHTML = `<div class="spinner"></div><div class="center muted">${S.cfg.ai ? 'AI tahlil qilmoqda…' : 'Fayl o\'qilmoqda…'}</div>`;
      const fd = new FormData(); fd.append('file', f);
      try {
        const p = await upload('/api/admin/import/preview', fd);
        out.innerHTML = `
          <div class="card flat" style="margin-top:14px"><b>${p.total} ta savol topildi</b>${p.skipped ? `<span class="muted"> • ${p.skipped} tasi to'liq emas (o'tkazildi)</span>` : ''}${p.used_ai ? ' <span class="pill">AI</span>' : ''}
          ${p.mixed ? '<div class="muted" style="font-size:12px;margin-top:4px">Faylda bir nechta sinf/fan aniqlandi — o\'z holicha joylanadi.</div>' : ''}</div>
          <div class="row" style="gap:10px"><div class="grow"><label class="f">Sinf</label><input class="in" id="i-g" value="${esc(p.grade || '')}" placeholder="${p.mixed ? 'avtomatik' : '8-sinf'}"></div>
          <div class="grow"><label class="f">Fan</label><input class="in" id="i-s" value="${esc(p.subject || '')}" placeholder="${p.mixed ? 'avtomatik' : 'Fan'}"></div></div>
          <div class="group-list">${p.groups.map(g => `<div><span>${esc(g.grade)} • ${esc(g.topic)}</span><b>${g.count}</b></div>`).join('')}</div>
          <label class="check"><input type="checkbox" id="i-r"><span>Shu sinf va fandagi <b>eski savollarni almashtirish</b> (o'chirilib, yangilari qo'yiladi)</span></label>
          <button class="btn primary block" style="margin-top:16px" id="i-ok">Bazaga qo'shish</button>`;
        $('#i-ok', sh).onclick = async () => {
          try {
            const r = await api('/api/admin/import/commit', { json: { token: p.token, grade: $('#i-g', sh).value, subject: $('#i-s', sh).value, replace: $('#i-r', sh).checked } });
            S.tree = null; closeSheet(); haptic('success');
            toast(`${r.added} ta savol qo'shildi${r.duplicates ? `, ${r.duplicates} ta takror` : ''}${r.removed ? `, ${r.removed} ta eskisi o'chirildi` : ''}`, 'good');
          } catch (er) { toast(er.message, 'err'); }
        };
      } catch (er) { out.innerHTML = `<div class="empty">${esc(er.message)}</div>`; }
    };
  });
}
async function showManageQuestions(gi, si, ti) {
  const g = S.tree[gi], s = g.subjects[si], t = s.topics[ti];
  view.innerHTML = `${crumb(t.topic)}<div class="spinner"></div>`;
  try {
    const d = await api(`/api/admin/questions?grade=${encodeURIComponent(g.grade)}&subject=${encodeURIComponent(s.subject)}&topic=${encodeURIComponent(t.topic)}`);
    const draw = () => {
      view.innerHTML = `${crumb(t.topic)}<p class="muted" style="margin:-4px 4px 12px">${g.grade} • ${esc(s.subject)} • ${d.questions.length} ta savol</p>
        <div class="stack">${d.questions.map((q, n) => `<div class="card qlist-item" data-id="${q.id}">
          <div class="qt">${n + 1}. ${esc(q.question)}</div>
          <ol>${q.options.map((o, k) => `<li class="${o === q.answer ? 'ans' : ''}">${LET[k]}) ${esc(o)}</li>`).join('')}</ol>
          <div class="admin-bar"><button class="btn sm" data-a="mq-edit" data-id="${q.id}">${ic('edit')}Tahrirlash</button><button class="btn sm danger" data-a="mq-del" data-id="${q.id}">${ic('trash')}O'chirish</button></div></div>`).join('') || '<div class="empty">Bu mavzuda savol qolmadi.</div>'}</div>`;
    };
    draw(); S.manage = { d, draw };
  } catch (e) { toast(e.message, 'err'); }
}

/* ---------- Hodisalar (event delegation) ---------- */
document.addEventListener('click', async e => {
  const tab = e.target.closest('[data-tab]');
  if (tab) { resetNav(); S.tab = tab.dataset.tab; await refreshStats(); return renderTab(); }
  const per = e.target.closest('[data-per]');
  if (per) { S.rating.period = per.dataset.per; return renderRating(); }
  const el = e.target.closest('[data-a]'); if (!el) return;
  const d = el.dataset, a = d.a; e.stopPropagation();
  const gi = +d.gi, si = +d.si, ti = +d.ti;
  switch (a) {
    case 'back': return goBack();
    case 'home': resetNav(); S.tab = 'home'; await refreshStats(); return renderTab();
    case 'start': return startFlow();
    case 'mistakes': if (!S.stats.mistakes) return toast('Xato qilingan savollar yo\'q 🎉', 'good'); return beginQuiz({ mode: 'mistakes' });
    case 'grade': return go(() => showSubjects(+d.i, d.mode));
    case 'subject': return go(() => showTopics(gi, si, d.mode));
    case 'topic': return go(() => showInfo(gi, si, ti));
    case 'mtopic': return go(() => showManageQuestions(gi, si, ti));
    case 'cnt': S.pending.count = +d.c; document.querySelectorAll('[data-a=cnt]').forEach(b => b.classList.toggle('on', b === el)); $('#qn').textContent = d.c > 0 ? Math.min(+d.c, S.pending.total) : S.pending.total; return;
    case 'run': return beginQuiz({ grade: S.pending.grade, subject: S.pending.subject, topic: S.pending.topic, count: S.pending.count });
    case 'opt': haptic('select'); return answer(+d.v);
    case 'finish': if (await ask('Testni tugatamizmi?')) finishQuiz(true); return;
    case 'qedit': {
      const q = S.quiz, cur = q.qs[q.i]; stopTimer();
      return openEditQuestion(cur.id, r => { cur.question = r.question; cur.options = [...r.options].sort(() => Math.random() - .5); showQuestion(); });
    }
    case 'qdel': {
      const q = S.quiz; stopTimer();
      if (!(await ask('Bu savol butunlay o\'chirilsinmi?'))) return startTimer();
      try { await api('/api/admin/question/' + q.qs[q.i].id, { method: 'DELETE' }); q.qs.splice(q.i, 1); S.tree = null; toast('Savol o\'chirildi', 'good'); showQuestion(); } catch (er) { toast(er.message, 'err'); startTimer(); }
      return;
    }
    case 'delgrade': { const g = S.tree[+d.i]; if (!(await ask(`${g.grade}dagi BARCHA savollar (${g.count} ta) o'chirilsinmi?`))) return;
      try { await api('/api/admin/delete-grade', { json: { grade: g.grade } }); await loadTree(true); toast('Sinf o\'chirildi', 'good'); showGrades(d.mode || 'quiz'); } catch (er) { toast(er.message, 'err'); } return; }
    case 'deltopic': { const g = S.tree[gi], s = g.subjects[si], t = s.topics[ti]; if (!(await ask(`«${t.topic}» mavzusi (${t.count} ta savol) o'chirilsinmi?`))) return;
      try { await api('/api/admin/delete-topic', { json: { grade: g.grade, subject: s.subject, topic: t.topic } }); await loadTree(true); toast('Mavzu o\'chirildi', 'good');
        const ng = S.tree.findIndex(x => x.grade === g.grade); const ns = ng < 0 ? -1 : S.tree[ng].subjects.findIndex(x => x.subject === s.subject);
        if (ns < 0) { S.nav.pop(); S.nav.pop(); ng < 0 ? (S.nav.pop(), S.nav[S.nav.length - 1]()) : S.nav[S.nav.length - 1](); } else showTopics(ng, ns, S.mode); syncBack(); } catch (er) { toast(er.message, 'err'); } return; }
    case 'mq-edit': return openEditQuestion(+d.id, async () => { const m = S.manage; const idx = m.d.questions.findIndex(q => q.id === +d.id); const fresh = await api('/api/admin/question/' + d.id); m.d.questions[idx] = fresh; m.draw(); });
    case 'mq-del': if (!(await ask('Bu savol o\'chirilsinmi?'))) return;
      try { await api('/api/admin/question/' + d.id, { method: 'DELETE' }); S.manage.d.questions = S.manage.d.questions.filter(q => q.id !== +d.id); S.tree = null; S.manage.draw(); toast('Savol o\'chirildi', 'good'); } catch (er) { toast(er.message, 'err'); } return;
    case 'aiimport': return openImport();
    case 'addq': return openAddQuestion();
    case 'manage': await loadTree(true); return go(() => showGrades('manage'));
    case 'addaudio': await loadTree().catch(() => {}); return openAudioUpload();
    case 'addbook': return openBookUpload();
    case 'play': return playAudio(+d.id);
    case 'delaudio': if (!(await ask('Audio o\'chirilsinmi?'))) return; await api('/api/admin/audio/' + d.id, { method: 'DELETE' }); if (S.playing === +d.id) { au.pause(); S.playing = null; renderPlayer(); } return renderAudio();
    case 'ptoggle': return au.paused ? au.play() : au.pause();
    case 'pback': au.currentTime = Math.max(0, au.currentTime - 15); return;
    case 'pfwd': au.currentTime = Math.min(au.duration || 1e9, au.currentTime + 15); return;
    case 'pspeed': { const sp = [1, 1.25, 1.5, 2, .75]; au.playbackRate = sp[(sp.indexOf(au.playbackRate) + 1) % sp.length]; el.textContent = au.playbackRate + 'x'; return; }
    case 'pclose': au.pause(); S.playing = null; renderPlayer(); if (S.tab === 'audio') renderAudio(); return;
    case 'openbook': { const b = S.books.find(x => x.id === +d.id); const url = location.origin + b.url; return tg && tg.openLink ? tg.openLink(url) : window.open(url, '_blank'); }
    case 'delbook': if (!(await ask('Kitob o\'chirilsinmi?'))) return; await api('/api/admin/book/' + d.id, { method: 'DELETE' });
      S.cfg = await api('/api/config'); renderTabbar(); if (!S.cfg.has_books) { S.tab = 'home'; return renderTab(); } return renderBooks();
  }
});

/* ---------- Boshlash ---------- */
async function boot() {
  if (tg) { try { tg.ready(); tg.expand(); tg.setHeaderColor('#050B18'); tg.setBackgroundColor('#050B18'); tg.disableVerticalSwipes && tg.disableVerticalSwipes(); } catch (e) {} }
  view.innerHTML = '<div class="spinner" style="margin-top:35vh"></div>';
  try {
    S.cfg = await api('/api/config');
    const a = await api('/api/auth', { method: 'POST', json: {} });
    S.user = a.user; S.stats = a.stats;
    if (isAdmin()) loadTree().catch(() => {});
    renderTab();
  } catch (e) {
    view.innerHTML = `<div class="empty" style="margin-top:25vh"><div class="big">🔒</div><h2>Kirish imkonsiz</h2><p>${esc(e.message)}</p></div>`;
  }
}
boot();
})();
