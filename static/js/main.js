/* MARLO CMS — main.js
   Handles: like toggle, comment submit, mobile nav, dashboard sidebar */

const MARLO = window.MARLO || {};

// ── Utility: authorised fetch ────────────────────────────────
function apiFetch(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  if (MARLO.jwtToken) {
    headers['Authorization'] = `Bearer ${MARLO.jwtToken}`;
  }
  if (MARLO.csrfToken && ['POST', 'PUT', 'PATCH', 'DELETE'].includes((options.method || 'GET').toUpperCase())) {
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

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        console.error('Like failed:', err);
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
      } else {
        btn.classList.remove('liked');
        if (icon) icon.setAttribute('fill', 'none');
        if (labelEl) labelEl.textContent = 'Like';
      }

      if (countEl) countEl.textContent = data.like_count;

    } catch (err) {
      console.error('Like request error:', err);
    } finally {
      btn.disabled = false;
    }
  });
}

// ── Comment submit ────────────────────────────────────────────
function initCommentForm() {
  const submitBtn = document.getElementById('comment-submit');
  const textarea  = document.getElementById('comment-input');
  const statusEl  = document.getElementById('comment-status');
  const listEl    = document.getElementById('comments-list');
  const noMsg     = document.getElementById('no-comments-msg');

  if (!submitBtn || !textarea) return;

  submitBtn.addEventListener('click', async () => {
    const body = textarea.value.trim();

    if (!MARLO.jwtToken) {
      window.location.href = '/login/?next=' + window.location.pathname;
      return;
    }
    if (!body || body.length < 2) {
      showStatus(statusEl, 'Please write something first.', 'error');
      return;
    }

    const slug = submitBtn.dataset.slug;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Posting...';

    try {
      const res = await apiFetch(`/api/comments/post/${slug}/`, {
        method: 'POST',
        body: JSON.stringify({ body }),
      });

      if (res.status === 201) {
        textarea.value = '';
        showStatus(statusEl, 'Comment submitted for review. It will appear once approved.', 'success');
      } else if (res.status === 400) {
        const err = await res.json().catch(() => ({}));
        const msg = err.body ? err.body.join(', ') : 'Invalid comment.';
        showStatus(statusEl, msg, 'error');
      } else {
        showStatus(statusEl, 'Could not submit comment. Try again.', 'error');
      }
    } catch (err) {
      console.error('Comment submit error:', err);
      showStatus(statusEl, 'Network error. Please try again.', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Post comment';
    }
  });

  // Allow Ctrl+Enter to submit
  textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      submitBtn.click();
    }
  });
}

function showStatus(el, message, type) {
  if (!el) return;
  el.textContent = message;
  el.style.color = type === 'error' ? 'var(--red, #dc2626)' : 'var(--sky-700, #0369a1)';
  // Clear message after 5 seconds
  setTimeout(() => { el.textContent = ''; }, 5000);
}

// ── Mobile navbar toggle ─────────────────────────────────────
function initNavToggle() {
  const toggle = document.getElementById('navToggle');
  const links  = document.getElementById('navLinks');
  if (!toggle || !links) return;

  toggle.addEventListener('click', () => {
    links.classList.toggle('open');
  });

  // Close when clicking a link
  links.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => links.classList.remove('open'));
  });

  // Close on outside click
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

  if (openBtn) {
    openBtn.addEventListener('click', () => sidebar.classList.add('open'));
  }
  if (closeBtn) {
    closeBtn.addEventListener('click', () => sidebar.classList.remove('open'));
  }

  // Close on outside click (mobile)
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

// ── Alert auto-dismiss ───────────────────────────────────────
function initAlerts() {
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.4s';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });
}

// ── Boot ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initLikeButton();
  initCommentForm();
  initNavToggle();
  initSidebarToggle();
  initAlerts();
});
