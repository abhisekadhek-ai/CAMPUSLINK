const AUTH_KEY = "campuslink_session";


/* =========================
   GET LOGIN SESSION
========================= */

function getSession() {

    try {

        const raw =
            sessionStorage.getItem(AUTH_KEY);

        if (!raw) {
            return null;
        }

        return JSON.parse(raw);

    } catch (error) {

        console.error(
            "Error reading CampusLink session:",
            error
        );

        return null;
    }
}


/* =========================
   SAVE LOGIN SESSION
========================= */

function saveSession(session) {

    sessionStorage.setItem(
        AUTH_KEY,
        JSON.stringify(session)
    );
}


/* =========================
   ROLE HOME
========================= */

const ROLE_HOME = {

    student:
        "student/dashboard.html",

    recruiter:
        "recruiter/dashboard.html",

    admin:
        "admin/dashboard.html",

    college: 
        "college/dashboard.html"    

};


/* =========================
   REQUIRE ROLE
========================= */

function requireRole(role) {

    const session =
        getSession();


    if (
        session &&
        session.role === role &&
        session.token
    ) {

        return session;

    }


    document.documentElement.style.visibility =
        "hidden";


    location.replace(
        "../login.html?role=" + role
    );


    return null;
}


/* =========================
   LOGOUT
========================= */

function logout() {

    sessionStorage.removeItem(
        AUTH_KEY
    );

    location.href =
        "../index.html";
}