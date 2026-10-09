import urllib.request
import urllib.parse
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def request(method, path, data=None, token=None):
    url = BASE_URL + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except:
            return e.code, err_body

def run_tests():
    print("====================================================================")
    print("STEP 1: Verify 5 Recruiter Logins")
    print("====================================================================")
    recruiters = [
        ("tcs@campuslink.com", "tcs123", "TCS"),
        ("infosys@campuslink.com", "infosys123", "Infosys"),
        ("wipro@campuslink.com", "wipro123", "Wipro"),
        ("google@campuslink.com", "google123", "Google"),
        ("amazon@campuslink.com", "amazon123", "Amazon"),
    ]

    tokens = {}
    for email, pwd, comp in recruiters:
        code, res = request("POST", "/auth/login", {"email": email, "password": pwd, "role": "recruiter"})
        assert code == 200, f"Login failed for {email}: {res}"
        assert res.get("role") == "recruiter", f"Expected role 'recruiter' for {email}, got {res.get('role')}"
        tokens[comp] = res["token"]
        print(f"  [PASS] {comp:8} -> Logged in successfully ({email})")

    print("\n====================================================================")
    print("STEP 2: Verify College Placement Officer Login")
    print("====================================================================")
    code, college_res = request("POST", "/auth/login", {"college_id": "COL0001", "password": "college123", "role": "college"})
    assert code == 200, f"College login failed: {college_res}"
    college_token = college_res["token"]
    print(f"  [PASS] College Placement Officer (COL0001) logged in successfully")

    print("\n====================================================================")
    print("STEP 3: Verify Student Login & Application Creation to 'Google'")
    print("====================================================================")
    code, student_res = request("POST", "/auth/login", {"student_id": 1001, "password": "student123", "role": "student"})
    assert code == 200, f"Student login failed: {student_res}"
    student_token = student_res["token"]
    student_id = student_res.get("student_id") or 1001
    print(f"  [PASS] Student #{student_id} logged in successfully")

    import time
    ts = int(time.time())
    unique_job = f"AI Cloud Architect {ts}"
    apply_payload = {
        "job_title": unique_job,
        "company": "Google",
        "college": "KIT",
        "job_url": f"https://careers.google.com/jobs/results/ai-{ts}",
        "source": "Student Portal Manual Apply"
    }
    code, app_data = request("POST", f"/students/{student_id}/job-applications", apply_payload, token=student_token)
    assert code in (200, 201), f"Apply failed: {app_data}"
    app_id = app_data["id"]
    print(f"  [PASS] Application #{app_id} created for company '{app_data['company']}'")
    print(f"         College Approval initial state: '{app_data.get('college_approval')}'")
    assert app_data.get("college_approval") == "Pending", "College approval must start as 'Pending'!"

    print("\n====================================================================")
    print("STEP 4: Verify Recruiter Isolation (Pending is HIDDEN from Recruiter)")
    print("====================================================================")
    code, google_apps = request("GET", "/recruiter/job-applicants", token=tokens["Google"])
    assert code == 200
    google_app_ids = [a["id"] for a in google_apps]
    assert app_id not in google_app_ids, f"Error: Application #{app_id} should NOT be visible to Google recruiter before college approval!"
    print(f"  [PASS] Google recruiter cannot see application #{app_id} while Pending college approval.")

    print("\n====================================================================")
    print("STEP 5: College Placement Officer Reviews & Approves Application")
    print("====================================================================")
    code, col_apps = request("GET", "/college/job-applications", token=college_token)
    assert code == 200
    found_in_college = any(a["id"] == app_id for a in col_apps)
    assert found_in_college, f"Application #{app_id} must appear in College Placement Section!"
    print(f"  [PASS] Application #{app_id} is present in College Placement Section.")

    # College approves the application
    code, approve_res = request("PATCH", f"/job-applications/{app_id}/college-approval", {"college_approval": "Approved"}, token=college_token)
    assert code == 200, f"Approval failed: {approve_res}"
    print(f"  [PASS] College Placement Officer APPROVED application #{app_id}!")

    print("\n====================================================================")
    print("STEP 6: Verify Specific Recruiter Visibility & Cross-Recruiter Privacy")
    print("====================================================================")
    code, google_apps2 = request("GET", "/recruiter/job-applicants", token=tokens["Google"])
    assert code == 200
    google_app_ids2 = [a["id"] for a in google_apps2]
    assert app_id in google_app_ids2, f"Application #{app_id} must be visible to Google recruiter after approval!"
    print(f"  [PASS] Application #{app_id} is NOW VISIBLE to Google recruiter.")

    # Other recruiters must NOT see it!
    for other_comp in ["Amazon", "TCS", "Infosys", "Wipro"]:
        code, other_apps = request("GET", "/recruiter/job-applicants", token=tokens[other_comp])
        assert code == 200
        other_app_ids = [a["id"] for a in other_apps]
        assert app_id not in other_app_ids, f"Privacy breach: Google application #{app_id} visible to {other_comp}!"
        print(f"  [PASS] Verified {other_comp} recruiter CANNOT see Google's application #{app_id}.")

    print("\n====================================================================")
    print("STEP 7: Verify College Placement Drive Option (Date & Location for Individual Students)")
    print("====================================================================")
    code, drives_data = request("GET", f"/college/student-drives?student_id={student_id}", token=college_token)
    assert code == 200, f"Drives endpoint failed: {drives_data}"
    assert len(drives_data) > 0, "Expected at least one drive entry for student"
    sample_drive = drives_data[0]
    print(f"  [PASS] Retrieved {len(drives_data)} drive records for student #{student_id}:")
    print(f"         - Company:       {sample_drive.get('company')}")
    print(f"         - Date:          {sample_drive.get('date')}")
    print(f"         - Location:      {sample_drive.get('location') or sample_drive.get('venue')}")
    print(f"         - Time Slot:     {sample_drive.get('time_slot')}")
    print(f"         - Stage:         {sample_drive.get('routing_stage')}")
    assert "date" in sample_drive and sample_drive["date"], "Drive record must contain date"
    assert ("location" in sample_drive or "venue" in sample_drive), "Drive record must contain location/venue"

    print("\n====================================================================")
    print(">>> ALL 7 WORKFLOW TESTS PASSED SUCCESSFULLY! <<<")
    print("====================================================================")

if __name__ == "__main__":
    run_tests()
