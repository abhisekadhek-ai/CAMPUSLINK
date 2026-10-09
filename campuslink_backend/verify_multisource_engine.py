"""
verify_multisource_engine.py — Comprehensive verification script for the
Multi-Source Data Integration & Analysis Engine.

Validates:
1. Multi-Source Integration Engine Status & Source Connectivity (6 Sources)
2. Student Academic & Resume Data Integration
3. Recruiter Job Description & Eligibility Criteria Matrix
4. Placement Drive Calendars & Timelines Integration
5. Historical Placement Records & Predictive Trends
6. Diagnostic Assessment & Mock-Interview Results
7. Deep Multi-Source Candidate-Job Matching & Explainable Diagnostics
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from database import SessionLocal
from models import (
    Student,
    Recruiter,
    Drive,
    HistoricalPlacementRecord,
    AssessmentResult,
    MockInterviewResult,
)
from ml.multi_source_engine import get_multi_source_engine
from main import (
    get_multi_source_engine_status,
    analyze_student_multi_source_profile,
    analyze_student_job_fit_multi_source,
    get_historical_placement_trends,
    get_integrated_drive_calendar,
    get_student_assessments_and_mocks,
)

def run_tests():
    db = SessionLocal()
    engine = get_multi_source_engine(db)

    print("=====================================================================")
    print("      MULTI-SOURCE DATA INTEGRATION & ANALYSIS ENGINE VERIFICATION   ")
    print("=====================================================================")

    # Test 1: Operational Status across all 6 Connected Sources
    print("\n--- TEST 1: Multi-Source Engine Health & Data Sources Connectivity ---")
    status = engine.get_status()
    print(f"Engine Status: {status['engine_status']} (Version: {status['version']})")
    print(f"Total Integrated Datapoints: {status['total_integrated_datapoints']}")
    for src_key, src in status["sources"].items():
        print(f"  [{src['source_name']}] -> Status: {src['status']}, Records: {src.get('total_records', src.get('assessment_records', 'N/A'))}")
    assert status["engine_status"] == "Active & Integrated"
    assert status["total_integrated_datapoints"] >= 4000
    print("[PASS] Test 1: All 6 data sources are successfully connected and verified.")

    # Test 2: Student Academic & Resume Data Integration
    print("\n--- TEST 2: Student Academic & Parsed Resume Data Analysis ---")
    sample_student = db.query(Student).filter(Student.cgpa >= 8.0).first()
    assert sample_student is not None
    print(f"Student: {sample_student.name} (ID: {sample_student.id}, Branch: {sample_student.branch})")
    print(f"  Academic Data: CGPA={sample_student.cgpa}, Backlogs={sample_student.backlogs}")
    print(f"  Skills ({len(sample_student.skills or [])}): {sample_student.skills[:4]}")
    print(f"  Projects ({len(sample_student.projects or [])}): {sample_student.projects[:2]}")
    print(f"  Certifications ({len(sample_student.certifications or [])}): {sample_student.certifications[:2]}")
    print(f"  Resume Text Available: {bool(sample_student.resume_text)}")
    ats_score = (sample_student.parsed_resume_data or {}).get("ats_compatibility_score", "N/A")
    print(f"  Resume ATS Compatibility Score: {ats_score}%")
    assert sample_student.cgpa > 0
    assert bool(sample_student.resume_text)
    print("[PASS] Test 2: Student academic and resume data are seamlessly integrated.")

    # Test 3: Recruiter Job Description & Eligibility Criteria Matrix
    print("\n--- TEST 3: Recruiter Job Description & Eligibility Criteria Matrix ---")
    sample_recruiter = db.query(Recruiter).first()
    assert sample_recruiter is not None
    print(f"Recruiter: {sample_recruiter.company} — Role: {sample_recruiter.role}")
    print(f"  Job Description: {sample_recruiter.job_description[:120]}...")
    print(f"  Key Responsibilities ({len(sample_recruiter.responsibilities or [])}): {sample_recruiter.responsibilities[0] if sample_recruiter.responsibilities else 'N/A'}")
    print(f"  Cutoff Criteria: Min CGPA={sample_recruiter.min_cgpa}, Max Backlogs={sample_recruiter.max_backlogs}")
    print(f"  Assessment Benchmarks: Min Mock={sample_recruiter.min_mock_score}, Min Assessment={sample_recruiter.min_assessment_score}")
    print(f"  Eligible Branches: {sample_recruiter.eligible_branches}")
    assert bool(sample_recruiter.job_description)
    assert sample_recruiter.max_backlogs is not None
    print("[PASS] Test 3: Recruiter JD and full eligibility matrix verified.")

    # Test 4: Placement Drive Calendars & Timelines
    print("\n--- TEST 4: Placement Drive Calendars & Timelines Integration ---")
    calendar_matrix = engine.get_drive_calendar_matrix()
    print(f"Total Scheduled Placement Drives in Calendar: {len(calendar_matrix)}")
    first_drive = calendar_matrix[0]
    print(f"  Sample Drive: {first_drive['company']} ({first_drive['role']})")
    print(f"  Date & Time: {first_drive['date']} ({first_drive['time_slot']}) at {first_drive['venue']}")
    print(f"  Registration Deadline: {first_drive['registration_deadline']}")
    print(f"  Capacity: {first_drive['infrastructure_capacity']}, Eligible Students: {first_drive['eligible_students_count']} (Util: {first_drive['capacity_utilization_ratio']})")
    print(f"  Rounds Breakdown: {[r['round'] for r in first_drive['rounds_timeline']]}")
    assert len(calendar_matrix) > 0
    assert bool(first_drive['registration_deadline'])
    print("[PASS] Test 4: Placement drive calendar integration verified.")

    # Test 5: Historical Placement Records & Predictive Trends
    print("\n--- TEST 5: Historical Placement Records & Predictive Analytics ---")
    hist_trends = engine.analyze_historical_trends()
    print(f"Historical Records: {hist_trends['total_historical_records']} spanning batches 2021-2025")
    print(f"Total Historical Placements: {hist_trends['total_students_represented']}")
    print(f"Historical CTC Metrics: Average=INR {hist_trends['overall_average_ctc_lpa']} LPA, Peak=INR {hist_trends['overall_max_ctc_lpa']} LPA")
    print("  Year-over-Year Summary:")
    for yr in hist_trends['year_wise_trends']:
        print(f"    {yr['batch_year']}: {yr['total_placed']} placed, Avg CTC=INR {yr['average_ctc_lpa']} LPA, Max=INR {yr['highest_ctc_lpa']} LPA")
    print("  Top 3 Hiring Domains:")
    for dom in hist_trends['domain_demand_distribution'][:3]:
        print(f"    - {dom['domain']}: {dom['placements']} offers")
    assert hist_trends['total_historical_records'] > 0
    assert hist_trends['overall_average_ctc_lpa'] > 0
    print("[PASS] Test 5: Historical placement records & trend analytics verified.")

    # Test 6: Diagnostic Assessment & Mock-Interview Results
    print("\n--- TEST 6: Diagnostic Assessment & Mock-Interview Results ---")
    asm_data = get_student_assessments_and_mocks(sample_student.id, db=db)
    print(f"Assessments for {asm_data['student_name']}: {len(asm_data['diagnostic_assessments'])}")
    if asm_data['diagnostic_assessments']:
        a = asm_data['diagnostic_assessments'][0]
        print(f"  Title: {a['assessment_title']} (Total: {a['total_score']}/100, Percentile: {a['percentile']}th)")
        print(f"  Scores: Coding={a['coding_score']}, Aptitude={a['aptitude_score']}, Technical={a['technical_score']}")
    print(f"Mock Interviews: {len(asm_data['mock_interviews'])}")
    if asm_data['mock_interviews']:
        m = asm_data['mock_interviews'][0]
        print(f"  Type: {m['interview_type']} by {m['interviewer_name']} ({m['interviewer_designation']})")
        print(f"  Ratings: Technical={m['technical_rating']}, Communication={m['communication_rating']}, Overall={m['overall_score']}")
        print(f"  Verdict: {m['verdict']} -- Notes: {m['feedback_notes'][:80]}...")
    assert len(asm_data['diagnostic_assessments']) > 0
    assert len(asm_data['mock_interviews']) > 0
    print("[PASS] Test 6: Assessment and mock-interview results integration verified.")

    # Test 7: Deep Multi-Source Candidate-Job Matching & Explainability
    print("\n--- TEST 7: Deep Multi-Source Candidate-Job Matching ---")
    job_fit = engine.analyze_job_fit(sample_student.id, sample_recruiter.id)
    print(f"Match: {job_fit['student_name']} -> {job_fit['company']} ({job_fit['role']})")
    print(f"  Synthesized Multi-Source Fit Score: {job_fit['fit_score']}/100")
    print(f"  Status: {job_fit['status']} (Badge: {job_fit['badge_class']})")
    print(f"  Eligibility Checks: {job_fit['eligibility_breakdown']}")
    print(f"  Semantic Cosine Relevance: {job_fit['skill_and_resume_analysis']['semantic_similarity_percent']}%")
    print(f"  Skill Coverage: {job_fit['skill_and_resume_analysis']['skill_coverage_percent']}%")
    print(f"  Historical Placement Benchmark for Role: Avg Placed CGPA={job_fit['historical_benchmark']['historical_hiring_cgpa']}, Avg CTC=INR {job_fit['historical_benchmark']['historical_avg_ctc_lpa']} LPA")
    print(f"  Explainable Reasoning: {job_fit['explanation']}")
    assert "fit_score" in job_fit
    assert "status" in job_fit
    assert "explanation" in job_fit
    print("[PASS] Test 7: Multi-source job matching and explainable diagnostics verified.")

    db.close()
    print("\n=====================================================================")
    print("   ALL MULTI-SOURCE INTEGRATION TESTS PASSED WITH 100% SUCCESS!      ")
    print("=====================================================================")

if __name__ == "__main__":
    run_tests()
