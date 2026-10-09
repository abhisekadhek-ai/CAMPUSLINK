// api.js — matches the routes actually exposed by main.py

function getCampusLinkBaseUrl() {
    if (typeof window !== "undefined") {
        // 1. Check custom saved server address (useful for file:/// or remote devices)
        const customUrl = localStorage.getItem("campuslink_backend_url");
        if (customUrl && customUrl.trim()) {
            return customUrl.trim().replace(/\/+$/, "");
        }

        // 2. If accessed via HTTP or HTTPS (e.g. http://192.168.x.x:8000 or http://localhost:8000)
        if (window.location && (window.location.protocol === "http:" || window.location.protocol === "https:")) {
            return window.location.origin;
        }
    }
    // 3. Fallback default
    return "http://127.0.0.1:8000";
}

let BASE_URL = getCampusLinkBaseUrl();

function setCampusLinkBaseUrl(url) {
    if (!url) return;
    url = url.trim().replace(/\/+$/, "");
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
        url = "http://" + url;
    }
    try {
        localStorage.setItem("campuslink_backend_url", url);
    } catch (_) {}
    BASE_URL = url;
    return url;
}

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

function wrapFetchError(error, path) {
    if (
        error &&
        (error.name === "TypeError" ||
         String(error.message || error).includes("Failed to fetch") ||
         String(error.message || error).includes("NetworkError"))
    ) {
        const currentUrl = BASE_URL;
        const err = new Error(
            `Cannot connect to CampusLink Backend at ${currentUrl}. ` +
            `If accessing from another system, check network connection or set the host server IP.`
        );
        err.isNetworkError = true;
        return err;
    }
    return error;
}

async function handleResponse(res, path) {
    if (res.ok) return res.json();

    let errorDetail = "";
    try {
        const errJson = await res.json();
        errorDetail = errJson.detail || errJson.message || "";
    } catch (_) {}

    // Token expired or invalid while logged in
    // -> back to that role's login page (skip if it was login attempt)
    if (
        res.status === 401 &&
        typeof getSession === "function" &&
        getSession() &&
        !path.includes("/auth/login")
    ) {
        const role = getSession().role;

        sessionStorage.removeItem(AUTH_KEY);

        location.replace("../login.html?role=" + role);
    }

    const err = new Error(errorDetail || `${path} failed: ${res.status}`);
    err.status = res.status;
    err.detail = errorDetail;
    throw err;
}


async function apiGet(path) {
    try {
        const res = await fetch(
            BASE_URL + path,
            {
                headers: authHeaders()
            }
        );
        return await handleResponse(res, path);
    } catch (err) {
        throw wrapFetchError(err, path);
    }
}


async function apiPost(path, body) {
    try {
        const res = await fetch(
            BASE_URL + path,
            {
                method: "POST",
                headers: authHeaders({
                    "Content-Type": "application/json"
                }),
                body: JSON.stringify(body),
            }
        );
        return await handleResponse(res, path);
    } catch (err) {
        throw wrapFetchError(err, path);
    }
}


async function apiPut(path, body) {
    try {
        const res = await fetch(
            BASE_URL + path,
            {
                method: "PUT",
                headers: authHeaders({
                    "Content-Type": "application/json"
                }),
                body: JSON.stringify(body),
            }
        );
        return await handleResponse(res, path);
    } catch (err) {
        throw wrapFetchError(err, path);
    }
}


// ==================================================
// PATCH
// Used by College Approval
// ==================================================

async function apiPatch(path, body) {
    try {
        const res = await fetch(
            BASE_URL + path,
            {
                method: "PATCH",
                headers: authHeaders({
                    "Content-Type": "application/json"
                }),
                body: JSON.stringify(body),
            }
        );
        return await handleResponse(res, path);
    } catch (err) {
        throw wrapFetchError(err, path);
    }
}


// ==================================================
// Students
// ==================================================

const getStudents =
    () => apiGet("/students");

const getStudent =
    (id) => apiGet(`/students/${id}`);

const getReadiness =
    (id) => apiGet(`/students/${id}/readiness`);

const getStudentMatches =
    (id) => apiGet(`/students/${id}/matches`);

const getStudentAiMatches =
    (id, topN) =>
        apiGet(
            `/students/${id}/ai-matches` +
            (topN ? `?top_n=${topN}` : "")
        );

const createStudent =
    (data) => apiPost("/students", data);


// ==================================================
// Recruiters
// Each row = one open role
// ==================================================

const getRecruiters =
    () => apiGet("/recruiters");

const getRecruiterRoles =
    () => apiGet("/recruiter/roles");

const createRecruiter =
    (data) => apiPost("/recruiters", data);

const getCandidates =
    (recruiterId) =>
        apiGet(
            `/recruiters/${recruiterId}/candidates`
        );

const shortlistStudent =
    (recruiterId, studentId) =>
        apiPost(
            `/recruiters/${recruiterId}/shortlist/${studentId}`,
            {}
        );


// ==================================================
// Drives
// ==================================================

const getDrives =
    () => apiGet("/drives");

const getDriveConflicts =
    () => apiGet("/drives/conflicts");

const checkDriveConflicts =
    (data) => apiPost("/drives/check-conflicts", data);

const createDrive =
    (data) => apiPost("/drives", data);

const getCollegeStudentDrives = (studentId = null, company = "") => {
    const params = new URLSearchParams();
    if (studentId) params.append("student_id", studentId);
    if (company) params.append("company", company);
    const qs = params.toString();
    return apiGet("/college/student-drives" + (qs ? `?${qs}` : ""));
};

const getCollegeStudents = () =>
    apiGet("/college/students");

const sendRecruiterEmailToStudent = (data) =>
    apiPost("/recruiter/send-email", data);

const getIndividualStudentDrives = (studentId) =>
    apiGet(`/students/${studentId}/drives`);

const updateStudentProfile =
    (studentId, data) =>
        apiPatch(
            `/students/${studentId}/profile`,
            data
        );



// ==================================================
// Offers
// ==================================================

const getOffers =
    () => apiGet("/offers");

const createOffer =
    (data) => apiPost("/offers", data);

const updateOfferStatus =
    (id, data) =>
        apiPut(
            `/offers/${id}/status`,
            data
        );


// ==================================================
// Job Application Tracking
// ==================================================

const getJobApplications =
    (studentId) =>
        apiGet(
            `/students/${studentId}/job-applications`
        );

const createJobApplication =
    (studentId, data) =>
        apiPost(
            `/students/${studentId}/job-applications`,
            data
        );

const getApprovedJobApplications = (company = "") =>
    apiGet("/recruiter/job-applicants" + (company ? `?company=${encodeURIComponent(company)}` : ""));

const updateJobApplicationStatus = (applicationId, status) =>
    apiPatch(`/job-applications/${applicationId}/status`, { status });

// ==================================================
// Student Resume Management
// ==================================================

async function uploadStudentResume(studentId, fileOrData) {
    const headers = authHeaders();
    let body;

    if (fileOrData instanceof FormData) {
        body = fileOrData;
        delete headers["Content-Type"];
    } else if (fileOrData instanceof File) {
        const formData = new FormData();
        formData.append("file", fileOrData);
        body = formData;
        delete headers["Content-Type"];
    } else if (typeof fileOrData === "string") {
        const formData = new FormData();
        formData.append("resume_url", fileOrData);
        body = formData;
        delete headers["Content-Type"];
    } else if (fileOrData && fileOrData.resume_url) {
        const formData = new FormData();
        formData.append("resume_url", fileOrData.resume_url);
        body = formData;
        delete headers["Content-Type"];
    }

    const res = await fetch(`${BASE_URL}/students/${studentId}/resume`, {
        method: "POST",
        headers,
        body,
    });
    return handleResponse(res, `/students/${studentId}/resume`);
}

const getStudentResume = (studentId) =>
    apiGet(`/students/${studentId}/resume`);

// ==================================================
// College & Placement Cell
// ==================================================

const getColleges = () => apiGet("/colleges");

const getCollegeJobApplications = () => apiGet("/college/job-applications");

const updateCollegeApproval =
    (applicationId, approval) =>
        apiPatch(
            `/job-applications/${applicationId}/college-approval`,
            {
                college_approval: approval
            }
        );


// ==================================================
// Analytics
// ==================================================

const getAnalytics =
    () => apiGet("/analytics/dashboard");


// ==================================================
// Automated Communication & Notification System
// ==================================================

const getNotifications = (params = {}) => {
    const query = new URLSearchParams();
    if (params.category) query.append("category", params.category);
    if (params.unread_only) query.append("unread_only", "true");
    if (params.limit) query.append("limit", params.limit);
    const qs = query.toString();
    return apiGet("/notifications" + (qs ? `?${qs}` : ""));
};

const markNotificationRead = (notificationId) =>
    apiPatch(`/notifications/${notificationId}/read`);

const markAllNotificationsRead = () =>
    apiPost("/notifications/mark-all-read", {});

const sendDocumentDeadline = (data) =>
    apiPost("/notifications/document-deadline", data);

const scheduleInterviewRound = (data) =>
    apiPost("/notifications/schedule-interview", data);

const getDispatchLog = () =>
    apiGet("/notifications/dispatch-log");

const seedSampleAutomation = () =>
    apiPost("/notifications/seed-sample-automation", {});

// Shared helpers
// ==================================================

function badgeClass(label) {

    const map = {

        "Not Ready": "notready",

        "Developing": "developing",

        "Ready": "ready",

        "Highly Employable": "highly",

        "Shortlisted": "shortlisted",

        "Below Threshold": "below",

        "Not Eligible": "noteligible",

        "Issued": "issued",

        "Accepted": "accepted",

        "Joined": "joined",

        "Deferred": "deferred",

        "Withdrawn": "withdrawn",

        "Scheduled": "scheduled",

        "Cancelled": "cancelled",

        "Rescheduled": "developing",

    };

    return map[label] || "developing";
}


function escapeHtml(str) {

    const div =
        document.createElement("div");

    div.textContent =
        str ?? "";

    return div.innerHTML;
}


function csv(list) {

    return (list || [])
        .map(
            s =>
                `<span class="tag">
                    ${escapeHtml(s)}
                </span>`
        )
        .join("");
}

// ==================================================
// MULTI-SOURCE INTEGRATION ENGINE HELPERS
// ==================================================
async function getMultiSourceEngineStatus() {
    return apiGet("/api/integration/engine/status");
}

async function getStudentMultiSourceProfile(studentId) {
    return apiGet(`/api/integration/analyze/student/${studentId}`);
}

async function getJobMatchMultiSource(studentId, recruiterId) {
    return apiGet(`/api/integration/analyze/job-match/${studentId}/${recruiterId}`);
}

async function getHistoricalPlacementTrends() {
    return apiGet("/api/integration/historical-trends");
}

async function getDriveCalendarMatrix() {
    return apiGet("/api/integration/drive-calendar");
}

async function getStudentAssessments(studentId) {
    return apiGet(`/api/integration/assessments/${studentId}`);
}

async function recordAssessment(data) {
    return apiPost("/api/integration/assessments", data);
}

async function recordMockInterview(data) {
    return apiPost("/api/integration/mock-interviews", data);
}

async function parseResumeData(studentId, data) {
    return apiPost(`/api/integration/parse-resume/${studentId}`, data);
}