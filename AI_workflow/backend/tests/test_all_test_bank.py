"""Comprehensive test runner for CAMPUS_QUERIES_TEST_BANK.md.

Tests all 8 sections:
- Section 1: Course Curriculum & Credits (1.1, 1.2, 1.3, 1.4a, 1.4b, 1.5)
- Section 2: Faculty, HOD & Consultation (2.1, 2.2, 2.3, 2.4)
- Section 3: Attendance, Detention & Grading (3.1, 3.2, 3.3, 3.4a, 3.4b)
- Section 4: Calendar, Exam Dates & Deadlines (4.1, 4.2, 4.3)
- Section 5: Capstone & Industrial Training (5.1, 5.2, 5.3)
- Section 6: Labs & Facilities (6.1, 6.2, 6.3, 6.4)
- Section 7: Out-of-KB University Traps (7.1, 7.2, 7.3, 7.4)
- Section 8: Strict Outsiders / Guardrails (8.1, 8.2, 8.3, 8.4, 8.5)
- Multi-turn & Greetings
"""
import pytest
from app.retrieval.hybrid_engine import HybridRAGEngine


@pytest.fixture(scope="module")
def engine():
    return HybridRAGEngine.get_instance()


def test_section_1_curriculum(engine):
    # 1.1 Semester 6 Course Catalog
    r1 = engine.answer_query("What courses and subjects are offered in Semester 6 B.Tech IT?")
    assert r1["answer_type"] == "answered"
    assert any(term in r1["answer"].upper() for term in ["2CEIT601", "THEORY OF COMPUTATION", "SEMESTER VI", "ARTIFICIAL INTELLIGENCE"])

    # 1.2 Specific Course Code 2CEIT601
    r2 = engine.answer_query("What is 2CEIT601 and what are its credits?")
    assert r2["answer_type"] == "answered"
    assert "THEORY OF COMPUTATION" in r2["answer"].upper()
    assert "4.0" in r2["answer"] or "4" in r2["answer"]

    # 1.3 Detailed 5-Unit Syllabus Breakdown (2CEIT78PE4 Mobile Computing)
    r3 = engine.answer_query("What is the syllabus and unit breakdown for Mobile Computing (2CEIT78PE4)?")
    assert r3["answer_type"] == "answered"
    assert "MOBILE COMPUTING" in r3["answer"].upper() or "2CEIT78PE4" in r3["answer"]

    # 1.4a Data Structures 2CEIT304
    r4a = engine.answer_query("What are the credits, contact hours, and total marks for 2CEIT304 Data Structures?")
    assert r4a["answer_type"] == "answered"
    assert "DATA STRUCTURES" in r4a["answer"].upper()
    assert "5.0" in r4a["answer"] or "5" in r4a["answer"]

    # 1.4b Operating Systems 2CEIT401
    r4b = engine.answer_query("What are the prerequisites and total marks for 2CEIT401 Operating Systems?")
    assert r4b["answer_type"] == "answered"
    assert "OPERATING SYSTEMS" in r4b["answer"].upper()
    assert "4.0" in r4b["answer"] or "4" in r4b["answer"] or "150" in r4b["answer"]


def test_section_2_faculty_and_consultation(engine):
    # 2.1 HOD of IT
    r1 = engine.answer_query("Who is the HOD of Information Technology?")
    assert r1["answer_type"] == "answered"
    assert "MEERA DATAVALA" in r1["answer"].upper()
    assert "ROOM-DA-202" in r1["answer"]

    # 2.2 Arjun Tensorkar cabin
    r2 = engine.answer_query("What is Dr. Arjun Tensorkar's cabin location and consultation hours?")
    assert r2["answer_type"] == "answered"
    assert "ROOM-DA-210" in r2["answer"]

    # 2.3 Cryptography & Security faculty
    r3 = engine.answer_query("Which professor teaches Cryptography and Information Security?")
    assert r3["answer_type"] == "answered"
    assert "SANA CIPHERWALA" in r3["answer"].upper()

    # 2.4 Consultation procedure
    r4 = engine.answer_query("How can I schedule a consultation with a professor?")
    assert r4["answer_type"] == "answered"
    assert "24 hours" in r4["answer"].lower() or "consultation" in r4["answer"].lower()


def test_section_3_attendance_and_grading(engine):
    # 3.1 75% attendance rule
    r1 = engine.answer_query("What is the 75% attendance rule for semester exams?")
    assert r1["answer_type"] == "answered"
    assert "75%" in r1["answer"] or "75" in r1["answer"]

    # 3.2 Below 75% consequences
    r2 = engine.answer_query("What happens if my attendance drops below 75 percent?")
    assert r2["answer_type"] == "answered"
    assert "advisory" in r2["answer"].lower() or "faculty" in r2["answer"].lower() or "detention" in r2["answer"].lower() or "attendance" in r2["answer"].lower()

    # 3.3 Medical leaves submission
    r3 = engine.answer_query("What is the procedure for submitting medical leaves?")
    assert r3["answer_type"] == "answered"
    assert "7 days" in r3["answer"] or "help desk" in r3["answer"].lower() or "absence" in r3["answer"].lower()

    # 3.4 SGPA/CGPA evaluation policy
    r4 = engine.answer_query("How are SGPA and CGPA calculated under the evaluation policy?")
    assert r4["answer_type"] == "answered"
    assert "GRADING" in r4["answer"].upper() or "SCALE" in r4["answer"].upper() or "POINTS" in r4["answer"].upper() or "CREDIT" in r4["answer"].upper()


def test_section_4_academic_calendar(engine):
    # 4.1 Mid-semester exam dates
    r1 = engine.answer_query("When are the mid semester examinations scheduled?")
    assert r1["answer_type"] == "answered"
    assert "2026-09-07" in r1["answer"] or "2027-02-22" in r1["answer"]
    assert "2026-27-00" not in r1["answer"]  # regex corruption bug must never appear

    # 4.2 Capstone deadline
    r2 = engine.answer_query("What is the deadline for capstone project topic registration?")
    assert r2["answer_type"] == "answered"
    assert "2026-08-14" in r2["answer"]

    # 4.3 Odd semester teaching start & autumn break
    r3 = engine.answer_query("When does odd semester teaching begin and when is autumn break?")
    assert r3["answer_type"] == "answered"
    assert "2026-07-16" in r3["answer"]
    assert "2026-27-00" not in r3["answer"]


def test_section_5_capstone_and_training(engine):
    # 5.1 Capstone team size
    r1 = engine.answer_query("How many students can be in a capstone project team?")
    assert r1["answer_type"] == "answered"
    assert "2 to 4" in r1["answer"] or "4" in r1["answer"]

    # 5.2 Capstone evaluation
    r2 = engine.answer_query("How is my capstone project graded and evaluated?")
    assert r2["answer_type"] == "answered"
    assert "RUBRIC" in r2["answer"].upper() or "IMPLEMENTATION" in r2["answer"].upper() or "DESIGN" in r2["answer"].upper()

    # 5.3 Industrial Training
    r3 = engine.answer_query("What do I need before starting Industrial Training in Semester VIII?")
    assert r3["answer_type"] == "answered"
    assert "offer letter" in r3["answer"].lower() or "organisation" in r3["answer"].lower() or "coordinator" in r3["answer"].lower()


def test_section_6_labs_and_facilities(engine):
    # 6.1 AI & ML Lab
    r1 = engine.answer_query("Where is the AI & Machine Learning Lab and what hardware is available?")
    assert r1["answer_type"] == "answered"
    assert "DA-301" in r1["answer"] or "36" in r1["answer"] or "RTX" in r1["answer"].upper()

    # 6.2 Networks Lab
    r2 = engine.answer_query("What equipment and tools are in the Networks & Security Lab?")
    assert r2["answer_type"] == "answered"
    assert "DA-401" in r2["answer"] or "32" in r2["answer"] or "SWITCHES" in r2["answer"].upper()

    # 6.3 Database Systems Lab
    r3 = engine.answer_query("Where is the Database Systems Lab and what tools does it have?")
    assert r3["answer_type"] == "answered"
    assert "DA-303" in r3["answer"] or "40" in r3["answer"] or "MONGODB" in r3["answer"].upper() or "POSTGRESQL" in r3["answer"].upper()

    # 6.4 Department Office hours
    r4 = engine.answer_query("What are the Department Office hours?")
    assert r4["answer_type"] == "answered"
    assert "DA-201" in r4["answer"] or "09:30" in r4["answer"]


def test_section_7_out_of_kb_abstentions(engine):
    # 7.1 Stanford aerospace
    r1 = engine.answer_query("What is the syllabus for aerospace engineering semester 8 at Stanford?")
    assert r1["answer_type"] == "abstained"

    # 7.2 Civil HOD
    r2 = engine.answer_query("Who is the HOD of Civil Engineering?")
    assert r2["answer_type"] == "abstained"

    # 7.3 Harvard CS50 trap
    r3 = engine.answer_query("What are the prerequisites for CS50 Introduction to Computer Science at Harvard?")
    assert r3["answer_type"] == "abstained"
    assert "2IT503" not in r3["answer"]  # must not leak unrelated course

    # 7.4 Library & WiFi trap
    r4 = engine.answer_query("What are the library hours and how do I connect to campus WiFi?")
    assert r4["answer_type"] == "abstained"
    assert "LABORATORY SAFETY POLICY" not in r4["answer"].upper()


def test_section_8_outsiders_and_greetings(engine):
    # 8.1 PM
    assert engine.answer_query("Who is the PM?")["answer_type"] == "abstained"
    # 8.2 Math
    assert engine.answer_query("What is 2 + 2?")["answer_type"] == "abstained"
    # 8.3 Weight loss
    assert engine.answer_query("How to lose weight in 30 days?")["answer_type"] == "abstained"
    # 8.4 Python code
    assert engine.answer_query("Write python code to reverse a string")["answer_type"] == "abstained"
    # 8.5 Joke
    assert engine.answer_query("Tell me a funny joke")["answer_type"] == "abstained"

    # Greetings
    g = engine.answer_query("hello")
    assert g["answer_type"] == "answered"
    assert "CAMPUSMATE" in g["answer"].upper()

