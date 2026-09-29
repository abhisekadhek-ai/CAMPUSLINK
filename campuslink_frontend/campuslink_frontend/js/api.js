// api.js — matches the routes actually exposed by main.py
const BASE_URL = "http://127.0.0.1:8000";

async function apiGet(path) {
  const res = await fetch(BASE_URL + path);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}
async function apiPost(path, body) {
  const res = await fetch(BASE_URL + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}
async function apiPut(path, body) {
  const res = await fetch(BASE_URL + path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
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
