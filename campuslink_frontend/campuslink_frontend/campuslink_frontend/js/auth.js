// auth.js — keeps each visitor inside their own portal (student / recruiter / admin).
//
// The password check and the real access rules now live in the BACKEND
// (POST /auth/login gives back a signed token, and every API route checks it).
// This file only remembers who is logged in for this browser tab and sends
// people who aren't logged in to the right login page.
const AUTH_KEY = "campuslink_session";

const ROLE_HOME = {
  student:   "student/dashboard.html",
  recruiter: "recruiter/dashboard.html",
  admin:     "admin/dashboard.html",
};

function getSession() {
  try { return JSON.parse(sessionStorage.getItem(AUTH_KEY)); } catch (e) { return null; }
}

function saveSession(session) {
  sessionStorage.setItem(AUTH_KEY, JSON.stringify(session));
}

// Call at the top of a dashboard. Returns the session, or sends the visitor to
// the login page for that role (and hides the page so nothing flashes).
function requireRole(role) {
  const s = getSession();
  if (s && s.role === role && s.token) return s;
  document.documentElement.style.visibility = "hidden";
  location.replace("../login.html?role=" + role);
  return null;
}

function logout() {
  sessionStorage.removeItem(AUTH_KEY);
  location.href = "../index.html";
}
