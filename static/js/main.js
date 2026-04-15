/* MARLO CMS — main.js
   Handles: toast notifications, like toggle, comment submit, mobile nav, sidebar */

const MARLO = window.MARLO || {};

// ── Toast system ──────────────────────────────────────────────
function showToast(message, type = 'info', duration = 4500) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-msg">${message}</span>
    <button class="toast-close" aria-label="Dismiss">&#x2715;</button>
  `;

  toast.querySelector('.toast-close').addEventListener('click', () => dismissToast(toast));
  container.appendChild(toast);

  // Trigger CSS transition
  requestAnimationFrame(() => {
    requestAnimationFrame(() => toast.classList.add('toast-show'));
  });

  const timer = setTimeout(() => dismissToast(toast), duration);
  toast._timer = timer;
}

function dismissToast(toast) {
  clearTimeout(toast._timer);
  toast.classList.remove('toast-show');
  setTimeout(() => toast.remove(), 300);
}

// ── Utility: authorised fetch ────────────────────────────────
function apiFetch(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  if (MARLO.jwtToken) {
    headers['Authorization'] = `Bearer ${MARLO.jwtToken}`;
  }
  if (
    MARLO.csrfToken &&
    ['POST', 'PUT', 'PATCH', 'DELETE'].includes((options.method || 'GET').toUpperCase())
  ) {
    headers['X-CSRFToken'] = MARLO.csrfToken;
  }
  return fetch(url, { ...options, headers });
}

// ── Like / Unlike ────────────────────────────────────────────
function initLikeButton() {
  const btn = document.getElementById('like-btn');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    if (!MARLO.jwtToken) {
      window.location.href = '/login/?next=' + window.location.pathname;
      return;
    }

    const slug = btn.dataset.slug;
    btn.disabled = true;

    try {
      const res = await apiFetch(`/api/interactions/like/${slug}/`, { method: 'POST' });

      if (res.status === 401) {
        showToast('Please log in to like this post.', 'info');
        btn.disabled = false;
        return;
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || 'Could not process like. Try again.', 'error');
        btn.disabled = false;
        return;
      }

      const data = await res.json();
      const icon = document.getElementById('like-icon');
      const countEl = document.getElementById('like-count');
      const labelEl = document.getElementById('like-label');

      if (data.liked) {
        btn.classList.add('liked');
        if (icon) icon.setAttribute('fill', 'currentColor');
        if (labelEl) labelEl.textContent = 'Liked';
        showToast('Post liked!', 'success', 2000);
      } else {
        btn.classList.remove('liked');
        if (icon) icon.setAttribute('fill', 'none');
        if (labelEl) labelEl.textContent = 'Like';
        showToast('Like removed.', 'info', 2000);
      }

      if (countEl) countEl.textContent = data.like_count;

    } catch (err) {
      console.error('[MARLO] Like request error:', err);
      showToast('Network error. Please check your connection.', 'error');
    } finally {
      btn.disabled = false;
    }
  });
}

// ── Comment submit ────────────────────────────────────────────
function initCommentForm() {
  const submitBtn = document.getElementById('comment-submit');
  const textarea  = document.getElementById('comment-input');
  if (!submitBtn || !textarea) return;

  submitBtn.addEventListener('click', async () => {
    if (!MARLO.jwtToken) {
      window.location.href = '/login/?next=' + window.location.pathname + '#comments';
      return;
    }

    const body = textarea.value.trim();

    if (!body) {
      showToast('Please write something before posting.', 'warning');
      textarea.focus();
      return;
    }

    if (body.length < 2) {
      showToast('Comment is too short — write at least 2 characters.', 'warning');
      return;
    }

    if (body.length > 2000) {
      showToast(`Comment is too long (${body.length}/2000 characters).`, 'warning');
      return;
    }

    const slug = submitBtn.dataset.slug;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Posting…';

    try {
      const res = await apiFetch(`/api/comments/post/${slug}/`, {
        method: 'POST',
        body: JSON.stringify({ body }),
      });

      if (res.status === 201) {
        textarea.value = '';
        showToast('Comment submitted! It will appear once approved by a moderator.', 'success', 6000);
      } else if (res.status === 400) {
        const err = await res.json().catch(() => ({}));
        const msg = err.body ? err.body.join(', ') : 'Invalid comment. Please check your input.';
        showToast(msg, 'error');
      } else if (res.status === 401) {
        showToast('Your session expired. Please log in again.', 'info');
      } else {
        showToast('Could not submit comment. Please try again.', 'error');
      }
    } catch (err) {
      console.error('[MARLO] Comment submit error:', err);
      showToast('Network error. Please check your connection and try again.', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Post comment';
    }
  });

  // Ctrl+Enter / Cmd+Enter shortcut
  textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      submitBtn.click();
    }
  });

  // Live character counter hint
  textarea.addEventListener('input', () => {
    const len = textarea.value.length;
    if (len > 1800) {
      const statusEl = document.getElementById('comment-status');
      if (statusEl) {
        statusEl.textContent = `${len}/2000 characters`;
        statusEl.style.color = len > 2000 ? 'var(--red)' : 'var(--amber)';
      }
    }
  });
}

// ── Mobile navbar toggle ─────────────────────────────────────
function initNavToggle() {
  const toggle = document.getElementById('navToggle');
  const links  = document.getElementById('navLinks');
  if (!toggle || !links) return;

  toggle.addEventListener('click', () => links.classList.toggle('open'));

  links.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => links.classList.remove('open'));
  });

  document.addEventListener('click', (e) => {
    if (!toggle.contains(e.target) && !links.contains(e.target)) {
      links.classList.remove('open');
    }
  });
}

// ── Dashboard sidebar toggle (mobile) ───────────────────────
function initSidebarToggle() {
  const openBtn  = document.getElementById('sidebarToggle');
  const closeBtn = document.getElementById('sidebarClose');
  const sidebar  = document.getElementById('sidebar');
  if (!sidebar) return;

  if (openBtn) openBtn.addEventListener('click', () => sidebar.classList.add('open'));
  if (closeBtn) closeBtn.addEventListener('click', () => sidebar.classList.remove('open'));

  document.addEventListener('click', (e) => {
    if (
      sidebar.classList.contains('open') &&
      !sidebar.contains(e.target) &&
      openBtn && !openBtn.contains(e.target)
    ) {
      sidebar.classList.remove('open');
    }
  });
}

// ── Django flash messages → toasts ──────────────────────────
// Convert any server-rendered .alert elements into toasts on load
function initServerAlerts() {
  document.querySelectorAll('.alert').forEach(alert => {
    const text = alert.querySelector('.alert-msg')?.textContent
               || alert.textContent.replace('×', '').trim();

    let type = 'info';
    if (alert.classList.contains('alert-success')) type = 'success';
    else if (alert.classList.contains('alert-error')) type = 'error';
    else if (alert.classList.contains('alert-warning')) type = 'warning';

    if (text) showToast(text, type);

    // Hide the inline alert since we've converted it to a toast
    alert.style.display = 'none';
  });
}

// ── Boot ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initLikeButton();
  initCommentForm();
  initNavToggle();
  initSidebarToggle();
  initServerAlerts();
});