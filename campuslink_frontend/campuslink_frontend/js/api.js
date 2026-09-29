// api.js — matches the routes actually exposed by main.py
const BASE_URL = "http://127.0.0.1:8000";

// Sends the login token (if any) with every request so the backend knows who is asking.
function authHeaders(extra = {}) {
    const headers = { ...extra };

    try {
        const session = JSON.parse(
            sessionStorage.getItem("campuslink_session") || "null"
        );

        if (session && session.token) {
            headers["Authorization"] = `Bearer ${session.token}`;
        }
    } catch (error) {
        console.error("Could not read login session:", error);
    }

    return headers;
}


async function handleResponse(res, path) {
  if (res.ok) return res.json();
  // Token expired or invalid while logged in -> back to that role's login page
  if (res.status === 401 && typeof getSession === "function" && getSession()) {
    const role = getSession().role;
    sessionStorage.removeItem(AUTH_KEY);
    location.replace("../login.html?role=" + role);
  }
  throw new Error(`${path} failed: ${res.status}`);
}

async function apiGet(path) {
  const res = await fetch(BASE_URL + path, { headers: authHeaders() });
  return handleResponse(res, path);
}
async function apiPost(path, body) {
  const res = await fetch(BASE_URL + path, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  return handleResponse(res, path);
}
async function apiPut(path, body) {
  const res = await fetch(BASE_URL + path, {
    method: "PUT",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  return handleResponse(res, path);
}

// Students
const getStudents        = () => apiGet("/students");
const getStudent         = (id) => apiGet(`/students/${id}`);
const getReadiness       = (id) => apiGet(`/students/${id}/readiness`);
const getStudentMatches  = (id) => apiGet(`/students/${id}/matches`);
const getStudentAiMatches = (id, topN) => apiGet(`/students/${id}/ai-matches` + (topN ? `?top_n=${topN}` : ""));
const createStudent      = (data) => apiPost("/students", data);

// Recruiters (each row = one open role)
const getRecruiters      = () => apiGet("/recruiters");
const createRecruiter    = (data) => apiPost("/recruiters", data);
const getCandidates      = (recruiterId) => apiGet(`/recruiters/${recruiterId}/candidates`);
const shortlistStudent   = (recruiterId, studentId) => apiPost(`/recruiters/${recruiterId}/shortlist/${studentId}`, {});

// Drives
const getDrives          = () => apiGet("/drives");
const getDriveConflicts  = () => apiGet("/drives/conflicts");
const createDrive        = (data) => apiPost("/drives", data);

// Offers
const getOffers          = () => apiGet("/offers");
const createOffer        = (data) => apiPost("/offers", data);
const updateOfferStatus  = (id, data) => apiPut(`/offers/${id}/status`, data);

// Analytics
const getAnalytics       = () => apiGet("/analytics/dashboard");

// Shared helpers
function badgeClass(label) {
  const map = {
    "Not Ready": "notready", "Developing": "developing", "Ready": "ready",
    "Highly Employable": "highly", "Shortlisted": "shortlisted",
    "Below Threshold": "below", "Not Eligible": "noteligible",
    "Issued": "issued", "Accepted": "accepted", "Joined": "joined",
    "Deferred": "deferred", "Withdrawn": "withdrawn",
    "Scheduled": "scheduled", "Cancelled": "cancelled", "Rescheduled": "developing",
  };
  return map[label] || "developing";
}
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
function csv(list) {
  return (list || []).map(s => `<span class="tag">${escapeHtml(s)}</span>`).join("");
}
