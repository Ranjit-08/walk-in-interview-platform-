// api.js — Centralised API client
// All HTTP calls go through this module.
// Automatically attaches JWT token and handles errors.

const API_BASE = 'https://your-api-gateway-url.execute-api.ap-south-1.amazonaws.com/prod';

/**
 * Core fetch wrapper.
 * Attaches Authorization header, parses JSON, throws on non-2xx.
 */
async function apiRequest(method, path, body = null, requiresAuth = true) {
  const headers = { 'Content-Type': 'application/json' };

  if (requiresAuth) {
    const token = Auth.getToken();
    if (!token) {
      Auth.logout();
      window.location.href = '/pages/login.html';
      return;
    }
    headers['Authorization'] = `Bearer ${token}`;
  }

  const options = { method, headers };
  if (body) options.body = JSON.stringify(body);

  const response = await fetch(`${API_BASE}${path}`, options);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const err = new Error(data.message || 'Request failed');
    err.status = response.status;
    err.data   = data;
    throw err;
  }

  return data;
}

// ── Convenience methods ────────────────────────────────────────────
const api = {
  get:    (path, auth = true)         => apiRequest('GET',    path, null, auth),
  post:   (path, body, auth = true)   => apiRequest('POST',   path, body, auth),
  put:    (path, body, auth = true)   => apiRequest('PUT',    path, body, auth),
  delete: (path, auth = true)         => apiRequest('DELETE', path, null, auth),

  // ── Auth ──────────────────────────────────────────────────────
  auth: {
    registerUser:    (data) => api.post('/api/auth/register/user',    data, false),
    registerCompany: (data) => api.post('/api/auth/register/company', data, false),
    confirm:         (data) => api.post('/api/auth/confirm',          data, false),
    login:           (data) => api.post('/api/auth/login',            data, false),
    logout:          ()     => api.post('/api/auth/logout',           null, true),
    forgotPassword:  (data) => api.post('/api/auth/forgot-password',  data, false),
    resetPassword:   (data) => api.post('/api/auth/reset-password',   data, false),
    me:              ()     => api.get('/api/auth/me'),
  },

  // ── Jobs ──────────────────────────────────────────────────────
  jobs: {
    list:   (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return api.get(`/api/jobs${qs ? '?' + qs : ''}`, false);
    },
    get:    (id)   => api.get(`/api/jobs/${id}`, false),
    create: (data) => api.post('/api/jobs', data),
    delete: (id)   => api.delete(`/api/jobs/${id}`),
  },

  // ── Bookings ──────────────────────────────────────────────────
  bookings: {
    create:  (data) => api.post('/api/bookings', data),
    my:      ()     => api.get('/api/bookings/my'),
    active:  ()     => api.get('/api/bookings/active'),
    cancel:  (id)   => api.delete(`/api/bookings/${id}`),
    getByCode: (code) => api.get(`/api/bookings/${code}`, false),
  },

  // ── Company ───────────────────────────────────────────────────
  company: {
    dashboard:    ()      => api.get('/api/company/dashboard'),
    jobs:         ()      => api.get('/api/company/jobs'),
    jobBookings:  (jobId) => api.get(`/api/company/jobs/${jobId}/bookings`),
    updateStatus: (jobId, status) =>
      api.put(`/api/company/jobs/${jobId}/status`, { status }),
  },

  // ── Interview ─────────────────────────────────────────────────
  interview: {
    start:      (jobId)  => api.post('/api/interview/start', { job_id: jobId }),
    chat:       (data)   => api.post('/api/interview/chat', data),
    sessions:   ()       => api.get('/api/interview/sessions'),
    getSession: (id)     => api.get(`/api/interview/sessions/${id}`),
  },
};