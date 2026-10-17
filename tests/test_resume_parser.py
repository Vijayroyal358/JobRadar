"""Test resume parser skill detection, title extraction, and role suggestion."""
from app.resume_parser import parse_resume, guess_title, guess_name, estimate_years


SAMPLE_RESUME = """T SURYA PRAKASH
HR / L&D OPERATIONS | TRAINING COORDINATION | EMPLOYEE DEVELOPMENT | ADMINISTRATION
Tirupati, Andhra Pradesh | +91-9398436303 | suryaprakash41550@gmail.com
PROFESSIONAL SUMMARY
MBA – Human Resource Management graduate with 1.5 Yrs experience in L&D Operations and Backend banking operations. Looking forward to associating with an organization where I can utilize my skills to contribute to organizational goals and grow along with the company.
CORE HR / L&D COMPETENCIES
Training Need Analysis (TNA) • Skill Gap Analysis • Training and logistics Coordination • Vendor Management • Training Calendar Design • LMS Administration • Induction • Learning Effectiveness • Training MIS and Documentation • Excel Reporting • Stakeholder Coordination.
HR / L&D EXPERIENCE
Amara Raja Group – Mangal Industries Limited | L&D Intern | Apr 2024 – Apr 2025 | 1 Year
Carry out Training Need Analysis (TNA) and identification of skill gaps.
Design Training calendar for assigned businesses and plants.
Execute the training programs as per plan by coordinating with internal business teams, and by arranging Trainer and training logistics.
Accommodation booking and vendor coordination for training programs.
LMS administration: Mandatory e-learning and Support LMS activities including course uploads, assessments, surveys, and learning records. E-Induction support for new joiners and completion tracking.
Track training schedules, attendance/completion records, feedback, and required documentation. Prepare monthly reports, training records, and documentation, submit the same Head Office.
EXPERIENCE – INFOSYS BPM, Bangalore | Senior Process Executive – Banking Sector | 5 Months
Transaction processing and case handling.
Data verification and quality checks. Documentation and record maintenance.
SOP and process adherence.
US financial services process support. Exception identification and escalation.
Regular reporting of the transactions.
EDUCATION
MBA – Human Resource Management | Siddartha Educational Group of Institutions, Tirupati | 2021–2023
B.Com – Computer Applications | Marga Dharashini Degree College, Piler | 2018–2021
TECHNICAL SKILLS
MS Excel: Basic reporting, sorting/filtering, documentation and tracking and MS Word
SOFT SKILLS
Interpersonal Skills • Teamwork • Process Discipline • Attitude to learn • Trustworthy
ACADEMIC PROJECT
A Study on Recruitment & Selection | AP Southern Power Distribution Company Limited | 45 days | Tirupati
"""


def test_resume_parser_hr_ld():
    res = parse_resume("test_resume.txt", SAMPLE_RESUME.encode("utf-8"))

    # 1. Name, Title, and Experience assertions
    assert res["name"] == "T Surya Prakash", f"Expected 'T Surya Prakash', got {res['name']}"
    assert res["current_title"] != "PROFESSIONAL SUMMARY", "Title must not be a section header"
    assert "HR" in res["current_title"] or "L&D" in res["current_title"], f"Expected HR/L&D title, got {res['current_title']}"
    assert res["years_experience"] == 1.5, f"Expected 1.5 years, got {res['years_experience']}"

    # 2. Skill auto-detection assertions
    skills = res["skills"]
    assert len(skills) >= 15, f"Expected at least 15 skills, got {len(skills)}: {skills}"

    expected_skills = [
        "Excel",
        "Microsoft Word",
        "Human Resources (HR)",
        "Learning & Development (L&D)",
        "Training Coordination",
        "Training Needs Analysis (TNA)",
        "Skill Gap Analysis",
        "LMS Administration",
        "Employee Onboarding / Induction",
        "Vendor Management",
        "Stakeholder Management",
        "Interpersonal Skills",
        "Trustworthy",
    ]
    for exp in expected_skills:
        assert exp in skills, f"Expected '{exp}' to be in detected skills, but was missing"

    # 3. Suggested roles
    roles = res["suggested_roles"]
    assert any("L&D" in r or "HR" in r or "Operations" in r for r in roles), f"Expected HR/L&D roles, got {roles}"

    print("Resume parser HR/L&D self-checks passed!")


if __name__ == "__main__":
    test_resume_parser_hr_ld()
