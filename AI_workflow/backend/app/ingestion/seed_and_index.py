import json
import uuid
import re
from pathlib import Path

def build_knowledge_base():
    root = Path(__file__).resolve().parents[3]
    data_dir = root / "data" / "structured"
    output_file = root / "storage" / "knowledge_base.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    chunks = []

    def make_chunk(doc_id, title, category, text, source_type="official", metadata=None):
        c_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_id}:{len(chunks)}:{title[:30]}"))
        meta = {
            "doc_id": doc_id,
            "title": title,
            "category": category,
            "source_type": source_type,
            **(metadata or {})
        }
        return {
            "id": c_id,
            "title": title,
            "category": category,
            "source_type": source_type,
            "text": text.strip(),
            "metadata": meta
        }

    # 1. Courses
    courses_path = data_dir / "courses.json"
    if courses_path.exists():
        with open(courses_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for r in data.get("records", []):
                code = r.get("course_code") or r.get("course_id", "")
                name = r.get("course_name", "")
                credits = r.get("credits", 0)
                cs = r.get("credit_scheme") or {}
                prereq = r.get("prerequisites") or "None"
                desc = r.get("description") or ""
                sec = r.get("source_section") or ""
                pg = r.get("source_page")
                st = r.get("source_type", "official")
                sem_ids = r.get("semester_ids") or ([r.get("semester_id")] if r.get("semester_id") else [])
                course_type = r.get("course_type") or ""
                egrp = r.get("elective_group_id") or ""
                prog_id = r.get("program_id") or ""

                text = f"""Course Code: {code}
Course Name: {name}
Credits: {credits} (Theory: {cs.get('credit_th', 0)}, Practical: {cs.get('credit_pr', 0)}, Contact Hours: {cs.get('contact_hours', 0)})
Total Marks: {cs.get('total_marks', 100)}
Course Type: {course_type}
Prerequisites: {prereq}
Section / Curriculum: {sec}
Page: {pg}
Description & Syllabus Outline:
{desc if desc else f'Course offering in {sec}. Covers core academic concepts and practical lab assessments.'}
"""
                chunks.append(make_chunk(
                    f"COURSE-{code}",
                    f"Course: {code} - {name}",
                    "curriculum",
                    text,
                    st,
                    {
                        "code": code,
                        "page": pg,
                        "program_id": prog_id,
                        "semester_id": r.get("semester_id") or "",
                        "semester_ids": ",".join(s for s in sem_ids if s),
                        "course_type": course_type,
                        "elective_group_id": egrp,
                    },
                ))

    # 2. Faculty
    faculty_path = data_dir / "faculty.json"
    if faculty_path.exists():
        with open(faculty_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for r in data.get("records", []):
                name = r.get("name", "")
                fid = r.get("faculty_id", "")
                desig = r.get("designation", "")
                dept = r.get("department_id", "")
                qual = r.get("qualification", "")
                spec = r.get("specialization", "")
                areas = ", ".join(r.get("research_areas", []))
                email = r.get("email", "")
                office = r.get("office_id", "")
                hours = r.get("consultation_hours", "")
                is_hod = r.get("is_hod", False)
                courses = ", ".join(r.get("courses_taught", []))
                st = r.get("source_type", "synthetic")

                text = f"""Faculty Name: {name} ({'Head of Department (HOD)' if is_hod else desig})
Faculty ID: {fid}
Designation: {desig} {'[Head of Department - HOD]' if is_hod else ''}
Department: {dept}
Qualification: {qual}
Specialization: {spec}
Research Areas: {areas}
Email Address: {email}
Office / Cabin Location: {office}
Consultation Hours: {hours}
Courses Taught: {courses}
"""
                chunks.append(make_chunk(fid, f"Faculty: {name} ({'HOD' if is_hod else desig})", "faculty", text, st, {"faculty_id": fid, "is_hod": is_hod, "email": email, "office": office, "department_id": dept}))

    # 3. Academic Calendar
    cal_path = data_dir / "academic_calendar.json"
    if cal_path.exists():
        with open(cal_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for r in data.get("records", []):
                title = r.get("title", "")
                eid = r.get("event_id", "")
                etype = r.get("event_type", "")
                sdate = r.get("start_date", "")
                edate = r.get("end_date", "")
                term = r.get("term", "")
                st = r.get("source_type", "synthetic")

                text = f"""Event: {title}
Event ID: {eid}
Event Type: {etype}
Term / Academic Year: {term}
Start Date: {sdate}
End Date: {edate}
Description: Academic calendar schedule (demo) for {title}. Applies to relevant departments and semesters.
"""
                chunks.append(make_chunk(eid, f"Calendar: {title}", "calendar", text, st, {"event_type": etype, "start_date": sdate, "end_date": edate}))

    # 4. Policies
    pol_path = data_dir / "policies.json"
    if pol_path.exists():
        with open(pol_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for r in data.get("records", []):
                pid = r.get("policy_id", "")
                title = r.get("title", "")
                cat = r.get("category", "")
                summary = r.get("summary", "")
                clauses = "\n- ".join(r.get("clauses", []))
                st = r.get("source_type", "synthetic")

                text = f"""Policy Title: {title}
Policy ID: {pid}
Category: {cat}
Summary: {summary}
Official Policy Clauses:
- {clauses}
Effective Duration: {r.get('effective_from', '')} to {r.get('effective_to', '')}
"""
                chunks.append(make_chunk(pid, f"Policy: {title}", "policy", text, st, {"policy_id": pid, "category": cat}))

    # 5. Notices
    notices_path = data_dir / "notices.json"
    if notices_path.exists():
        with open(notices_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for r in data.get("records", []):
                nid = r.get("notice_id", "")
                title = r.get("title", "")
                cat = r.get("category", "")
                body = r.get("content", "")
                date = r.get("date", "")
                st = r.get("source_type", "synthetic")

                status = r.get("status", "")
                text = f"""Notice: {title}
Notice ID: {nid}
Category: {cat}
Status: {status}
Date Published: {date}
Content:
{body}
"""
                chunks.append(make_chunk(nid, f"Notice: {title}", "notice", text, st, {"notice_id": nid, "date": date, "status": status}))

    # 6. FAQs
    faq_path = data_dir / "faq.json"
    if faq_path.exists():
        with open(faq_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for r in data.get("records", []):
                fid = r.get("faq_id", "")
                cat = r.get("category", "")
                q = r.get("question", "")
                a = r.get("answer", "")
                st = r.get("source_type", "synthetic")

                text = f"""Frequently Asked Question: {q}
Category: {cat}
Answer:
{a}
"""
                chunks.append(make_chunk(fid, f"FAQ: {q}", "faq", text, st, {"faq_id": fid, "category": cat}))

    # 7. Laboratories & Facilities
    labs_path = data_dir / "laboratories.json"
    if labs_path.exists():
        with open(labs_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for r in data.get("records", []):
                lid = r.get("lab_id", "")
                name = r.get("lab_name") or r.get("name", "Department Lab")
                room = r.get("room_number") or r.get("room_id", "")
                incharge = r.get("responsible_faculty_id") or r.get("incharge_faculty_id", "")
                equip = ", ".join(r.get("equipment", []))
                st = r.get("source_type", "synthetic")

                text = f"""Laboratory: {name}
Lab ID: {lid}
Location / Room: {room}
Responsible Faculty In-charge: {incharge}
Key Equipment & Toolchains: {equip}
Capacity: {r.get('capacity', 36)} workstations
Opening Hours: {r.get('opening_hours', 'Mon-Sat 09:00-18:00')}
"""
                chunks.append(make_chunk(lid, f"Lab: {name}", "facility", text, st, {"lab_id": lid, "room": room}))

    facilities_path = data_dir / "facilities.json"
    if facilities_path.exists():
        with open(facilities_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for r in data.get("records", []):
                fcid = r.get("facility_id", "")
                name = r.get("facility_name", "")
                ftype = r.get("facility_type", "")
                loc = r.get("location", "") or r.get("room_id", "")
                desc = r.get("description", "")
                avail = r.get("availability", "")
                st = r.get("source_type", "synthetic")

                text = f"""Facility: {name}
Facility ID: {fcid}
Type: {ftype}
Location: {loc}
Capacity: {r.get('capacity', '')}
Availability / Hours: {avail}
Description: {desc}
"""
                chunks.append(make_chunk(fcid, f"Facility: {name}", "facility", text, st, {"facility_id": fcid, "room": r.get("room_id", "")}))

    # 8. Grading Scheme & Evaluation Policy
    grading_path = data_dir / "grading_scheme.json"
    if grading_path.exists():
        with open(grading_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            grades_summary = []
            for r in data.get("records", []):
                reg = r.get("grade_regular", "")
                gp = r.get("grade_point_regular", "")
                mr = r.get("marks_range", "")
                grades_summary.append(f"- Grade {reg}: Grade Point {gp} (Marks Range: {mr}%)")
            text = "Official University Grading Scheme & Grade Point Scale:\n" + "\n".join(grades_summary) + "\n\nStandard 10-point scale applied to SGPA and CGPA computation for all B.Tech and M.Tech programs."
            chunks.append(make_chunk("GRADING-SCHEME-001", "University Grading Scheme & Evaluation Criteria", "academic", text, "official"))

    # 9. Departments & Programs & Semesters
    dept_path = data_dir / "departments.json"
    if dept_path.exists():
        with open(dept_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for r in data.get("records", []):
                did = r.get("department_id", "")
                name = r.get("department_name") or r.get("name", "")
                short_name = r.get("short_name", "")
                hod = r.get("head_faculty_id") or r.get("hod_faculty_id", "")
                office = r.get("office_room_id") or r.get("building_id", "")
                contact = r.get("contact") or {}
                overview = r.get("overview") or "Offers B.Tech and M.Tech accredited degrees with laboratories and capstone projects."
                st = r.get("source_type", "synthetic")

                text = f"""Department: {name} ({short_name})
Department ID: {did}
Head of Department Faculty ID: {hod}
Department Office Room: {office}
Office Hours: {contact.get('office_hours', '')}
Office Email: {contact.get('office_email', '')}
HOD Office Email: {contact.get('hod_office_email', '')}
Overview: {overview}
"""
                chunks.append(make_chunk(did, f"Department: {name}", "department", text, st, {"department_id": did, "short_name": short_name, "hod": hod, "office": office}))

    programs_path = data_dir / "programs.json"
    if programs_path.exists():
        with open(programs_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for r in data.get("records", []):
                pid = r.get("program_id", "")
                pname = r.get("program_name", "")
                sname = r.get("short_name", "")
                dur = r.get("duration", "")
                tot_cr = r.get("total_credits", "")
                sems = r.get("number_of_semesters", "")
                desc = r.get("program_description") or r.get("synthetic_program_description") or ""
                st = r.get("source_type", "official")

                text = f"""Programme: {pname} ({sname})
Program ID: {pid}
Degree Type: {r.get('degree_type', '')}
Duration: {dur} ({sems} semesters)
Total Credits Required: {tot_cr}
Effective Year: {r.get('effective_year', '')}
Overview: {desc}
"""
                chunks.append(make_chunk(pid, f"Programme: {sname} - {pname}", "curriculum", text, st, {"program_id": pid, "short_name": sname}))

    semesters_path = data_dir / "semesters.json"
    if semesters_path.exists():
        with open(semesters_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for r in data.get("records", []):
                sid = r.get("semester_id", "")
                pid = r.get("program_id", "")
                sname = r.get("semester_name", "")
                snum = r.get("semester_number", "")
                tot_cr = r.get("total_credits", "")
                tot_th = r.get("total_credits_th", "")
                tot_pr = r.get("total_credits_pr", "")
                tot_hrs = r.get("total_contact_hours", "")
                tot_marks = r.get("total_marks", "")
                tot_courses = r.get("total_course", "")
                prog_label = "B.TECH-IT" if "BTECH" in pid else "M.TECH-IT"
                st = r.get("source_type", "official")

                text = f"""Semester Summary: {prog_label} {sname} (Semester {snum})
Semester ID: {sid}
Program ID: {pid}
Total Courses: {tot_courses} (Regular: {r.get('total_regular_course', 0)}, Elective: {r.get('total_elective_course', 0)}, Audit: {r.get('total_audit_course', 0)})
Total Credits: {tot_cr} (Theory: {tot_th}, Practical: {tot_pr})
Total Contact Hours: {tot_hrs}
Total Marks: {tot_marks}
Source Section: {r.get('source_section', '')}
"""
                chunks.append(make_chunk(sid, f"Semester: {prog_label} {sname}", "curriculum", text, st, {"semester_id": sid, "program_id": pid, "semester_number": snum}))

    # 10. Specific syllabus unit breakdown
    text = """Course Code: 2CEIT78PE4
Course Name: Mobile Computing (Elective IV - Semester VII)
Credits: 4 Credits (Theory: 3, Practical: 2, Total Marks: 150)
Unit Breakdown & Syllabus Content:
1. Unit 1: Wireless Transmission & Cellular Basics — Frequencies, Antennas, Cellular Systems & Handover mechanisms.
2. Unit 2: Medium Access Control (MAC) — SDMA, FDMA, TDMA, CDMA protocols.
3. Unit 3: Telecommunications & Satellite Systems — GSM Architecture, DECT, TETRA, Satellite Routing & Broadcast Systems.
4. Unit 4: Mobile Network & Transport Layer — Mobile IP, DHCP, Mobile TCP, Indirect TCP & Snooping TCP.
5. Unit 5: Mobile Ecosystems & Security — Android/iOS Architecture, WAP, Mobile Application Security & Emerging Trends.
"""
    chunks.append(make_chunk("COURSE-2CEIT78PE4", "Course: 2CEIT78PE4 - Mobile Computing Syllabus", "curriculum", text, "official", {"code": "2CEIT78PE4"}))

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)

    return chunks

if __name__ == "__main__":
    recs = build_knowledge_base()
    print(f"Built knowledge base with {len(recs)} records.")
