// ── API helper ───────────────────────────────────────────────────────────
async function api(url, { method = 'GET', body = null } = {}) {
  const opts = {
    method,
    headers: {},
    credentials: 'same-origin',
  };
  if (body !== null) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  let data;
  try { data = await res.json(); } catch { data = {}; }
  if (!res.ok) {
    const err = new Error(data.error || 'Хатогии сервер');
    err.data = data;
    throw err;
  }
  return data;
}

async function apiUpload(url, formData) {
  const res = await fetch(url, { method: 'POST', body: formData, credentials: 'same-origin' });
  let data;
  try { data = await res.json(); } catch { data = {}; }
  if (!res.ok) {
    const err = new Error(data.error || 'Хатогии сервер');
    throw err;
  }
  return data;
}

// ── Toast ────────────────────────────────────────────────────────────────
function toast(msg, type = '') {
  let el = document.getElementById('toast-container');
  if (!el) { el = document.createElement('div'); el.id = 'toast-container'; document.body.appendChild(el); }
  const t = document.createElement('div');
  const icons = { success: '✅', danger: '❌', '': 'ℹ️' };
  t.className = `toast ${type}`;
  t.innerHTML = `<span>${icons[type] || icons['']}</span> ${msg}`;
  el.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── Modal helpers ─────────────────────────────────────────────────────────
function openModal(id) { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }
function closeAllModals() { document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('open')); }

document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) closeAllModals();
  if (e.target.classList.contains('modal-close')) closeAllModals();
});

// ── Auth guard for protected pages ─────────────────────────────────────────
async function requireAuth(role = null) {
  try {
    const data = await api('/api/auth/me');
    if (!data.user) { window.location.href = '/login'; return null; }
    if (role && data.user.role !== role) {
      window.location.href = data.user.role === 'admin' ? '/admin' : '/pupil';
      return null;
    }
    return data.user;
  } catch {
    window.location.href = '/login';
    return null;
  }
}

async function logout() {
  await api('/api/auth/logout', { method: 'POST' });
  window.location.href = '/login';
}

function fmtDate(d) {
  return new Date(d).toLocaleDateString('tg-TJ', { day: '2-digit', month: 'short', year: 'numeric' });
}
