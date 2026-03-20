// auth.js — Authentication state management
// Handles token storage, user session, and Cognito flow helpers

const Auth = (() => {
  const TOKEN_KEY   = 'wip_access_token';
  const USER_KEY    = 'wip_user';
  const ROLE_KEY    = 'wip_role';

  return {
    // ── Token ────────────────────────────────────────────────
    setToken(token) { localStorage.setItem(TOKEN_KEY, token); },
    getToken()      { return localStorage.getItem(TOKEN_KEY); },

    // ── User ─────────────────────────────────────────────────
    setUser(user) { localStorage.setItem(USER_KEY, JSON.stringify(user)); },
    getUser()     {
      try { return JSON.parse(localStorage.getItem(USER_KEY)); }
      catch { return null; }
    },

    // ── Role ─────────────────────────────────────────────────
    setRole(role) { localStorage.setItem(ROLE_KEY, role); },
    getRole()     { return localStorage.getItem(ROLE_KEY) || 'user'; },

    // ── Login ─────────────────────────────────────────────────
    saveSession(tokens, profile) {
      this.setToken(tokens.access_token);
      this.setUser(profile);
      this.setRole(profile?.role || 'user');
    },

    // ── Logout ────────────────────────────────────────────────
    logout() {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem(ROLE_KEY);
    },

    // ── Guards ────────────────────────────────────────────────
    isLoggedIn()   { return !!this.getToken(); },
    isCompany()    { return this.getRole() === 'company'; },
    isUser()       { return this.getRole() === 'user'; },

    requireAuth() {
      if (!this.isLoggedIn()) {
        window.location.href = '/pages/login.html?redirect=' + encodeURIComponent(location.href);
        return false;
      }
      return true;
    },

    requireRole(role) {
      if (!this.isLoggedIn())      { window.location.href = '/pages/login.html'; return false; }
      if (this.getRole() !== role) { window.location.href = '/pages/login.html'; return false; }
      return true;
    },

    // ── Navbar helper ─────────────────────────────────────────
    updateNavbar() {
      const user = this.getUser();
      if (!user) return;

      const nameEl   = document.getElementById('nav-username');
      const avatarEl = document.getElementById('nav-avatar');

      if (nameEl)   nameEl.textContent   = user.full_name || user.company_name || 'Account';
      if (avatarEl) avatarEl.textContent = (user.full_name || user.company_name || 'U')[0].toUpperCase();
    },
  };
})();


// ── Toast Notification System ──────────────────────────────────────

const Toast = {
  show(message, type = 'info', duration = 3500) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }

    const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || icons.info}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'fadeOut 0.4s ease forwards';
      setTimeout(() => toast.remove(), 400);
    }, duration);
  },

  success: (msg) => Toast.show(msg, 'success'),
  error:   (msg) => Toast.show(msg, 'error'),
  warning: (msg) => Toast.show(msg, 'warning'),
  info:    (msg) => Toast.show(msg, 'info'),
};


// ── Loading Button Utility ─────────────────────────────────────────

function setLoading(btn, loading, text = '') {
  if (loading) {
    btn.disabled          = true;
    btn.dataset.origText  = btn.innerHTML;
    btn.innerHTML         = `<div class="spinner"></div>${text ? ' ' + text : ''}`;
  } else {
    btn.disabled  = false;
    btn.innerHTML = btn.dataset.origText || text;
  }
}


// ── Date Formatter ─────────────────────────────────────────────────

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric'
  });
}

function formatTime(timeStr) {
  if (!timeStr) return '—';
  const [h, m] = timeStr.split(':');
  const hour   = parseInt(h);
  const ampm   = hour >= 12 ? 'PM' : 'AM';
  return `${hour % 12 || 12}:${m} ${ampm}`;
}