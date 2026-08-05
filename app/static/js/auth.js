/* ==========================================================
   Ezitech Internship Analytics — shared auth helpers
   Loaded by every page. Handles:
   - calling POST /auth/login
   - storing the session (token, role, name, linked_id)
   - guarding role-specific pages (redirects to /login if missing)
   - attaching the Authorization header to every API fetch
   ========================================================== */

const AUTH_STORAGE_KEY = "ezitech_session";

function saveSession(session) {
  // sessionStorage (not localStorage): clears when the tab closes,
  // which is the right default for a shared/lab machine demo.
  sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

function getSession() {
  const raw = sessionStorage.getItem(AUTH_STORAGE_KEY);
  return raw ? JSON.parse(raw) : null;
}

function clearSession() {
  sessionStorage.removeItem(AUTH_STORAGE_KEY);
}

function logout() {
  clearSession();
  window.location.href = "/login";
}

/**
 * Call this at the top of every dashboard page's script.
 * requiredRole: "admin" | "mentor" | "student"
 * Redirects to /login if there's no session or the wrong role.
 */
function requireSession(requiredRole) {
  const session = getSession();
  if (!session || !session.access_token) {
    window.location.href = "/login";
    return null;
  }
  if (requiredRole && session.role !== requiredRole) {
    // Logged in, but as the wrong role — send them to their own dashboard
    // instead of silently showing nothing.
    window.location.href = `/${session.role}`;
    return null;
  }
  return session;
}

/**
 * Wrapper around fetch() that attaches the bearer token and handles
 * an expired/invalid token by bouncing back to /login.
 */
async function apiFetch(path, options = {}) {
  const session = getSession();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (session && session.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const response = await fetch(path, { ...options, headers });

  if (response.status === 401) {
    clearSession();
    window.location.href = "/login";
    throw new Error("Session expired");
  }

  return response;
}

/**
 * Performs login against the API. Returns the session object on
 * success, throws with a readable message on failure.
 */
async function login(email, password) {
  const response = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Incorrect email or password.");
    }
    throw new Error("Something went wrong logging in. Please try again.");
  }

  const session = await response.json();
  saveSession(session);
  return session;
}

/** Redirects a logged-in user to the dashboard matching their role. */
function redirectToDashboard(role) {
  window.location.href = `/${role}`;
}

/**
 * Registers a new student account. Returns the session object (role
 * is always "student") on success, throws with a readable message
 * on failure — mirrors login() above.
 */
async function register(name, email, password, technology, batch) {
  const response = await fetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password, technology, batch: batch || null }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    if (response.status === 409) {
      throw new Error("An account with this email already exists. Try signing in instead.");
    }
    if (response.status === 422) {
      throw new Error(body.detail || "Please check the form and try again.");
    }
    throw new Error(body.detail || "Something went wrong creating your account. Please try again.");
  }

  const data = await response.json();
  const session = { access_token: data.access_token, role: "student", name: data.name, linked_id: data.linked_id };
  saveSession(session);
  return session;
}
