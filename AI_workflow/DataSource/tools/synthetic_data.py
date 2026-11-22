"""Hand-authored SYNTHETIC companion data for CampusMate testing.
NOTHING in this module is a Ganpat University fact."""

SYN = "synthetic"
AY = "2026-2027"
DISCLAIMER = "SYNTHETIC DATA — FOR CAMPUSMATE DEVELOPMENT AND TESTING ONLY. THIS DOCUMENT IS NOT AN OFFICIAL GANPAT UNIVERSITY DOCUMENT."
DOMAIN = "campusmate-demo.example"

def s(doc, **kw):
    d = {"source_type": SYN, "source_document": doc, "academic_year": AY}
    d.update(kw)
    return d

# ------------------------------------------------------------------ buildings / rooms
BUILDINGS = [
    {"building_id": "BLDG-DEMO-A", "name": "Demo Academic Block A", "code": "DA", "floors": 5,
     "description": "Fictional academic block used for CampusMate testing. Houses the IT department office, faculty cabins and most teaching laboratories."},
    {"building_id": "BLDG-DEMO-B", "name": "Demo Innovation Block B", "code": "DB", "floors": 3,
     "description": "Fictional block housing the seminar hall, hardware lab and innovation spaces."},
]
def room(rid, bid, floor, rtype, name):
    return {"room_id": rid, "room_number": rid.replace("ROOM-", ""), "building_id": bid, "floor": floor, "room_type": rtype, "label": name}
ROOMS = [
    room("ROOM-DA-201", "BLDG-DEMO-A", 2, "office", "IT Department Office & Student Help Desk"),
    room("ROOM-DA-202", "BLDG-DEMO-A", 2, "office", "Head of Department cabin"),
    room("ROOM-DA-205", "BLDG-DEMO-A", 2, "project_room", "Capstone Project Room"),
    room("ROOM-DA-206", "BLDG-DEMO-A", 2, "lounge", "Faculty Lounge"),
    room("ROOM-DA-207", "BLDG-DEMO-A", 2, "discussion_room", "Discussion Room 1"),
    room("ROOM-DA-208", "BLDG-DEMO-A", 2, "discussion_room", "Discussion Room 2"),
    room("ROOM-DA-209", "BLDG-DEMO-A", 2, "reading_room", "Department Reading Room"),
] + [room(f"ROOM-DA-{n}", "BLDG-DEMO-A", 2, "office", f"Faculty cabin {n}") for n in range(210, 220)] + [
    room("ROOM-DA-301", "BLDG-DEMO-A", 3, "laboratory", "AI & Machine Learning Lab"),
    room("ROOM-DA-302", "BLDG-DEMO-A", 3, "laboratory", "Natural Language Processing Lab"),
    room("ROOM-DA-303", "BLDG-DEMO-A", 3, "laboratory", "Database Systems Lab"),
    room("ROOM-DA-304", "BLDG-DEMO-A", 3, "laboratory", "Programming Lab"),
    room("ROOM-DA-305", "BLDG-DEMO-A", 3, "laboratory", "Systems & Software Engineering Lab"),
    room("ROOM-DA-401", "BLDG-DEMO-A", 4, "laboratory", "Networks & Security Lab"),
    room("ROOM-DA-402", "BLDG-DEMO-A", 4, "laboratory", "Cloud & Big Data Lab"),
    room("ROOM-DA-403", "BLDG-DEMO-A", 4, "laboratory", "Web & Mobile Development Lab"),
    room("ROOM-DA-404", "BLDG-DEMO-A", 4, "laboratory", "Vision & Graphics Lab"),
    room("ROOM-DA-405", "BLDG-DEMO-A", 4, "computing_facility", "GPU Computing Facility"),
    room("ROOM-DB-101", "BLDG-DEMO-B", 1, "laboratory", "IoT & Robotics Lab"),
    room("ROOM-DB-102", "BLDG-DEMO-B", 1, "innovation_centre", "Innovation & Incubation Centre"),
    room("ROOM-DB-103", "BLDG-DEMO-B", 1, "workspace", "Student Project Workspace"),
    room("ROOM-DB-201", "BLDG-DEMO-B", 2, "seminar_hall", "IT Seminar Hall"),
]

# ------------------------------------------------------------------ research areas
RESEARCH_AREAS = [
    ("RA-IT-001", "Artificial Intelligence & Machine Learning"),
    ("RA-IT-002", "Natural Language Processing"),
    ("RA-IT-003", "Databases & Data Engineering"),
    ("RA-IT-004", "Cyber Security & Cryptography"),
    ("RA-IT-005", "Cloud, Distributed & High Performance Computing"),
    ("RA-IT-006", "Internet of Things & Robotics"),
    ("RA-IT-007", "Computer Vision & Graphics"),
    ("RA-IT-008", "Software Engineering & Human-Computer Interaction"),
    ("RA-IT-009", "Theoretical Computer Science & Algorithms"),
    ("RA-IT-010", "Computer Networks"),
]

# ------------------------------------------------------------------ department
DEPARTMENT = s("DOC-DEPT-PROFILE-001",
    department_id="DEPT-IT-001",
    department_name="Department of Information Technology",
    short_name="IT",
    parent_org_unit_id="COLLEGE-UVPCE-001",
    parent_link_note="Synthetic assumption: the official syllabus lists B.TECH-IT and M.TECH-IT under U.V. Patel College of Engineering, Faculty of Engineering & Technology, but names no department. DEPT-IT-001 is a CampusMate demo entity.",
    university_id="UNIV-GUNI-001",
    head_faculty_id="FAC-IT-001",
    overview="The Department of Information Technology (DEPT-IT-001) is a synthetic demo department created for CampusMate testing. It hosts the B.Tech IT programme (PROG-BTECH-IT-001) and the M.Tech IT programme (PROG-MTECH-IT-001), whose curricula are taken from the official GUNI structured syllabus, and it operates ten demo laboratories and ten shared facilities in the fictional Demo Academic Block A and Demo Innovation Block B.",
    vision="To be a demo department whose teaching, laboratories and student services are fully discoverable through a trustworthy, citation-first AI assistant.",
    mission=["Deliver the B.Tech IT and M.Tech IT curricula with strong laboratory practice.",
             "Guide every capstone and major project through documented, fair evaluation.",
             "Keep policies, notices and schedules published as versioned, machine-readable records.",
             "Encourage applied research in AI, data, security, cloud and IoT."],
    focus_areas=["Applied AI and data systems", "Secure and scalable software", "Industry-ready capstone projects", "Research-led postgraduate study"],
    program_ids=["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"],
    research_area_ids=[r[0] for r in RESEARCH_AREAS],
    lab_ids=[f"LAB-IT-{i:03d}" for i in range(1, 11)],
    facility_ids=[f"FCL-IT-{i:03d}" for i in range(1, 11)],
    office_room_id="ROOM-DA-201",
    contact={"office_email": f"it-office@{DOMAIN}", "hod_office_email": f"it-hod@{DOMAIN}",
             "projects_email": f"it-projects@{DOMAIN}", "labs_email": f"it-labs@{DOMAIN}",
             "phone": "SYN-EXT-4000 (placeholder extension, not a real number)",
             "office_hours": "Monday–Friday 09:30–17:00 (synthetic)"},
    version="1.0", status="active")

# ------------------------------------------------------------------ faculty
# (id, name, designation, qualification, specialization, research areas, room, joining_year, courses[(code, role)])
_F = [
 ("FAC-IT-001", "Dr. Meera Datavala", "Professor & Head of Department", "Ph.D. (Computer Science)", "Database systems and data engineering", ["RA-IT-003"], "ROOM-DA-202", 2008,
  [("2CEIT303", "instructor"), ("3CEIT211", "instructor"), ("3CEIT202", "instructor")]),
 ("FAC-IT-002", "Dr. Arjun Tensorkar", "Professor", "Ph.D. (Artificial Intelligence)", "Machine learning and intelligent systems", ["RA-IT-001"], "ROOM-DA-210", 2010,
  [("2CEIT602", "instructor"), ("3CEIT101", "instructor"), ("2CEIT78PE1", "instructor")]),
 ("FAC-IT-003", "Dr. Nisha Tokenwala", "Associate Professor", "Ph.D. (Computational Linguistics)", "Natural language processing and information retrieval", ["RA-IT-002", "RA-IT-001"], "ROOM-DA-210", 2013,
  [("2CEIT78PE7", "instructor"), ("3CEIT307", "instructor"), ("3CEIT303", "instructor")]),
 ("FAC-IT-004", "Dr. Kabir Modelkar", "Associate Professor", "Ph.D. (Data Science)", "Applied machine learning and data science", ["RA-IT-001", "RA-IT-003"], "ROOM-DA-211", 2014,
  [("2CEIT602", "lab_instructor"), ("2CEIT6PE4", "instructor"), ("3CEIT309", "instructor")]),
 ("FAC-IT-005", "Prof. Riya Queryani", "Assistant Professor", "M.Tech (Information Technology)", "NoSQL and web-scale data management", ["RA-IT-003"], "ROOM-DA-211", 2018,
  [("2CEIT303", "lab_instructor"), ("2CEIT405", "instructor"), ("2CEIT78PE5", "instructor")]),
 ("FAC-IT-006", "Dr. Vikram Packetkar", "Associate Professor", "Ph.D. (Computer Networks)", "Wireless and software-defined networking", ["RA-IT-010"], "ROOM-DA-212", 2011,
  [("2CEIT503", "instructor"), ("3CEIT105", "instructor"), ("3CEIT106", "instructor"), ("3CEIT108", "instructor")]),
 ("FAC-IT-007", "Dr. Sana Cipherwala", "Associate Professor", "Ph.D. (Information Security)", "Applied cryptography and PKI", ["RA-IT-004"], "ROOM-DA-212", 2012,
  [("2CEIT6PE3", "instructor"), ("3CEIT103", "instructor"), ("3CEIT207", "instructor"), ("3CEIT310", "instructor")]),
 ("FAC-IT-008", "Prof. Dev Firewallani", "Assistant Professor", "M.Tech (Cyber Security)", "Ethical hacking, digital forensics and blockchain", ["RA-IT-004"], "ROOM-DA-213", 2019,
  [("2CEIT6PE7", "instructor"), ("2CEIT78PE8", "instructor"), ("2CEIT78PE2", "instructor")]),
 ("FAC-IT-009", "Dr. Aditi Cloudani", "Professor", "Ph.D. (Distributed Systems)", "Cloud computing and service-oriented architectures", ["RA-IT-005"], "ROOM-DA-213", 2009,
  [("2CEIT603", "instructor"), ("3CEIT203", "instructor"), ("3CEIT110", "instructor"), ("3CEIT111", "instructor"), ("2CEIT78PE10", "instructor")]),
 ("FAC-IT-010", "Dr. Harsh Clusterwala", "Associate Professor", "Ph.D. (High Performance Computing)", "Big data platforms and parallel computing", ["RA-IT-005", "RA-IT-003"], "ROOM-DA-214", 2015,
  [("2CEIT702", "instructor"), ("3CEIT306", "instructor"), ("2CEIT78PE12", "instructor"), ("3CEIT109", "instructor"), ("2CEIT78PE11", "instructor")]),
 ("FAC-IT-011", "Prof. Tanya Pixelani", "Assistant Professor", "M.Tech (Computer Vision)", "Image processing, computer vision and XR", ["RA-IT-007", "RA-IT-001"], "ROOM-DA-214", 2020,
  [("2CEIT5PE2", "instructor"), ("2CEIT78PE3", "instructor"), ("2CEIT78PE13", "instructor"), ("3CEIT201", "instructor"), ("2CEIT78PE6", "instructor")]),
 ("FAC-IT-012", "Prof. Ishaan Stackani", "Assistant Professor", "M.Tech (Computer Engineering)", "Programming languages and data structures", ["RA-IT-009"], "ROOM-DA-215", 2017,
  [("2CEIT302", "instructor"), ("2CEIT304", "instructor"), ("2CEIT5PE1", "instructor"), ("2CEIT5PE8", "instructor")]),
 ("FAC-IT-013", "Dr. Pooja Lambdani", "Associate Professor", "Ph.D. (Theoretical Computer Science)", "Automata, compilers and algorithms", ["RA-IT-009"], "ROOM-DA-215", 2012,
  [("2CEIT601", "instructor"), ("2CEIT701", "instructor"), ("3CEIT308", "instructor"), ("2CEIT402", "instructor"), ("3CEIT102", "instructor"), ("2CEIT78PE9", "instructor")]),
 ("FAC-IT-014", "Prof. Rohan Kernelwala", "Assistant Professor", "M.Tech (Computer Systems)", "Operating systems and computer architecture", ["RA-IT-005"], "ROOM-DA-216", 2018,
  [("2CEIT401", "instructor"), ("2CEIT501", "instructor"), ("3CEIT204", "instructor"), ("3CEIT205", "instructor"), ("3CEIT113", "instructor")]),
 ("FAC-IT-015", "Prof. Kavya Graphwala", "Assistant Professor", "M.Tech (Information Technology)", "Web and mobile application development", ["RA-IT-008"], "ROOM-DA-216", 2019,
  [("2CEIT6PE1", "instructor"), ("2CEIT5PE5", "instructor"), ("2CEIT403", "instructor"), ("3CEIT107", "instructor"), ("2CEIT78PE4", "instructor")]),
 ("FAC-IT-016", "Prof. Aman Circuitkar", "Assistant Professor", "M.Tech (Embedded Systems)", "IoT, robotics and digital systems", ["RA-IT-006"], "ROOM-DA-217", 2016,
  [("2CEIT301", "instructor"), ("2CEIT6PE6", "instructor"), ("2CEIT6PE9", "instructor"), ("3CEIT305", "instructor"), ("3CEIT208", "instructor")]),
 ("FAC-IT-017", "Dr. Neha Testani", "Associate Professor", "Ph.D. (Software Engineering)", "Software testing, architecture and design patterns", ["RA-IT-008"], "ROOM-DA-217", 2013,
  [("2CEIT502", "instructor"), ("2CEIT6PE2", "instructor"), ("3CEIT112", "instructor"), ("3CEIT206", "instructor"), ("2CEIT5PE4", "instructor")]),
 ("FAC-IT-018", "Prof. Yash Uxwala", "Assistant Professor", "M.Des (Interaction Design)", "User experience, HCI and game design", ["RA-IT-008"], "ROOM-DA-218", 2021,
  [("2CEIT604", "instructor"), ("2CEIT5PE6", "instructor"), ("2CEIT6PE5", "instructor"), ("2CEIT5PE7", "instructor")]),
 ("FAC-IT-019", "Dr. Farhan Pythonwala", "Assistant Professor", "Ph.D. (Applied Mathematics)", "Scientific Python, quantum computing and modelling", ["RA-IT-009", "RA-IT-001"], "ROOM-DA-218", 2020,
  [("2CEIT404", "instructor"), ("2CEIT5PE3", "instructor"), ("3CEIT209", "instructor"), ("3CEIT210", "instructor"), ("3CEIT304", "instructor")]),
 ("FAC-IT-020", "Dr. Leena Projectkar", "Associate Professor & Project Coordinator", "Ph.D. (Information Technology)", "Project-based learning and IT infrastructure management", ["RA-IT-008", "RA-IT-005"], "ROOM-DA-219", 2011,
  [("2CEIT504", "coordinator"), ("2CEIT605", "coordinator"), ("2CEIT703", "coordinator"), ("2CEIT801", "coordinator"),
   ("3CEIT301", "coordinator"), ("3CEIT302", "coordinator"), ("3CEIT401", "coordinator"), ("3CEIT104", "instructor"),
   ("2CEIT704", "instructor"), ("2CEIT6PE8", "instructor")]),
]

def faculty_records():
    out = []
    for fid, name, des, qual, spec, ras, room_id, jy, courses in _F:
        slug = name.split()[-1].lower()
        first = name.split()[1].lower()
        out.append(s("DOC-FACULTY-001", faculty_id=fid, name=name, designation=des, department_id="DEPT-IT-001",
            qualification=qual, specialization=spec, research_area_ids=ras,
            research_areas=[dict(RESEARCH_AREAS)[r] for r in ras],
            email=f"{first}.{slug}@{DOMAIN}", office_id=room_id,
            consultation_hours="Tuesday & Thursday 15:00–16:30 (synthetic)" if int(fid[-3:]) % 2 else "Monday & Wednesday 14:00–15:30 (synthetic)",
            courses_taught=[f"COURSE-{c}" for c, _ in courses], joining_year=jy,
            is_hod=(fid == "FAC-IT-001"), status="active", version="1.0",
            identity_note="Fictional demo identity. Not a real Ganpat University faculty member."))
    return out

def teaching_assignments(course_sem):
    out = []; n = 0
    for fid, *_rest in _F:
        for code, role in _rest[-1]:
            n += 1
            out.append(s("DOC-FACULTY-001", assignment_id=f"TA-SYN-{n:03d}", faculty_id=fid, course_id=f"COURSE-{code}",
                         semester_id=course_sem[f"COURSE-{code}"], role=role))
    return out

# ------------------------------------------------------------------ laboratories
_L = [
 ("LAB-IT-001", "AI & Machine Learning Lab", "ROOM-DA-301", 36, "FAC-IT-002",
  ["36 workstations (32 GB RAM, RTX-class GPU)", "Python/Jupyter, PyTorch, scikit-learn", "Shared model registry server"],
  ["2CEIT602", "2CEIT6PE4", "2CEIT78PE1", "3CEIT101", "3CEIT309"], "Mon–Sat 09:00–18:00"),
 ("LAB-IT-002", "Natural Language Processing Lab", "ROOM-DA-302", 30, "FAC-IT-003",
  ["30 workstations", "Local SLM inference server (8B-class models)", "Annotated corpora for Indic and English text", "Vector database sandbox"],
  ["2CEIT78PE7", "3CEIT307", "3CEIT303", "2CEIT78PE5"], "Mon–Fri 09:00–17:30"),
 ("LAB-IT-003", "Database Systems Lab", "ROOM-DA-303", 40, "FAC-IT-001",
  ["40 workstations", "PostgreSQL and MySQL servers", "MongoDB and Cassandra cluster", "ER-modelling tools"],
  ["2CEIT303", "2CEIT405", "3CEIT211", "3CEIT202"], "Mon–Sat 09:00–17:30"),
 ("LAB-IT-004", "Programming Lab", "ROOM-DA-304", 60, "FAC-IT-012",
  ["60 workstations", "JDK, .NET SDK, GCC, Python toolchains", "Online judge server"],
  ["2CEIT302", "2CEIT304", "2CEIT402", "2CEIT404", "2CEIT5PE1", "2CEIT5PE8", "2CEIT78PE9", "3CEIT102", "2CEIT5PE3", "3CEIT209", "3CEIT210", "3CEIT304"], "Mon–Sat 08:30–19:00"),
 ("LAB-IT-005", "Networks & Security Lab", "ROOM-DA-401", 32, "FAC-IT-007",
  ["Managed switches and routers", "Isolated penetration-testing network", "Packet capture appliances", "Wireless test bed"],
  ["2CEIT503", "2CEIT6PE3", "2CEIT6PE7", "2CEIT78PE8", "2CEIT78PE2", "3CEIT103", "3CEIT105", "3CEIT106", "3CEIT107", "3CEIT108", "3CEIT207", "3CEIT310", "3CEIT208"], "Mon–Fri 09:00–17:00"),
 ("LAB-IT-006", "Cloud & Big Data Lab", "ROOM-DA-402", 36, "FAC-IT-009",
  ["Private OpenStack cloud", "Hadoop/Spark cluster (8 nodes)", "Kubernetes sandbox"],
  ["2CEIT603", "2CEIT702", "2CEIT78PE10", "2CEIT78PE11", "2CEIT78PE12", "3CEIT109", "3CEIT110", "3CEIT111", "3CEIT203", "3CEIT306", "2CEIT6PE8"], "Mon–Sat 09:00–18:00"),
 ("LAB-IT-007", "IoT & Robotics Lab", "ROOM-DB-101", 24, "FAC-IT-016",
  ["Microcontroller and single-board computer kits", "Sensor and actuator sets", "Two mobile robot platforms", "Digital electronics trainer kits"],
  ["2CEIT301", "2CEIT6PE6", "2CEIT6PE9", "3CEIT305"], "Mon–Fri 10:00–17:00"),
 ("LAB-IT-008", "Web & Mobile Development Lab", "ROOM-DA-403", 40, "FAC-IT-015",
  ["40 workstations", "Android and iOS device farm", "Node.js/React toolchains", "Usability testing station"],
  ["2CEIT403", "2CEIT5PE5", "2CEIT5PE6", "2CEIT604", "2CEIT6PE1", "2CEIT78PE4", "2CEIT6PE5"], "Mon–Sat 09:00–18:00"),
 ("LAB-IT-009", "Vision & Graphics Lab", "ROOM-DA-404", 24, "FAC-IT-011",
  ["GPU workstations", "Stereo and depth cameras", "VR headsets"],
  ["2CEIT5PE2", "2CEIT78PE3", "2CEIT78PE6", "2CEIT78PE13", "3CEIT201"], "Mon–Fri 09:00–17:00"),
 ("LAB-IT-010", "Systems & Software Engineering Lab", "ROOM-DA-305", 40, "FAC-IT-014",
  ["40 Linux workstations", "Virtualisation host", "CI/CD and test-automation server", "Compiler construction toolkits"],
  ["2CEIT401", "2CEIT501", "2CEIT502", "2CEIT601", "2CEIT701", "2CEIT6PE2", "2CEIT5PE4", "3CEIT112", "3CEIT113", "3CEIT204", "3CEIT205", "3CEIT206", "3CEIT308"], "Mon–Sat 09:00–17:30"),
]
def lab_records(rooms):
    out = []
    for lid, name, rid, cap, fid, eq, courses, hrs in _L:
        r = rooms[rid]
        out.append(s("DOC-LABS-001", lab_id=lid, lab_name=name, department_id="DEPT-IT-001",
            building_id=r['building_id'], building=next(b['name'] for b in BUILDINGS if b['building_id'] == r['building_id']),
            floor=r['floor'], room_id=rid, room_number=r['room_number'], capacity=cap, equipment=eq,
            responsible_faculty_id=fid, related_courses=[f"COURSE-{c}" for c in courses],
            opening_hours=hrs + " (synthetic)", governing_policy_ids=["POLICY-002", "POLICY-003"],
            booking_contact=f"it-labs@{DOMAIN}", status="active", version="1.0"))
    return out

# ------------------------------------------------------------------ facilities
_FC = [
 ("FCL-IT-001", "IT Seminar Hall", "ROOM-DB-201", 180, "seminar_hall", "Tiered hall with projector, lecture capture and hybrid-meeting kit. Used for seminars, guest talks and capstone final presentations.", "Bookable Mon–Sat 09:00–18:00 via the department office (POLICY-009)."),
 ("FCL-IT-002", "Capstone Project Room", "ROOM-DA-205", 48, "project_room", "Team tables, whiteboards and lockable storage for B.Tech IT Capstone Project-I/II/III and M.Tech major project teams.", "Open Mon–Sat 08:30–20:00 to registered project teams."),
 ("FCL-IT-003", "Innovation & Incubation Centre", "ROOM-DB-102", 30, "innovation_centre", "Maker space with 3D printer, prototyping bench and mentoring corner for student start-up ideas.", "Mon–Fri 10:00–18:00; access after induction."),
 ("FCL-IT-004", "Faculty Lounge", "ROOM-DA-206", 20, "lounge", "Lounge and informal meeting space for IT faculty.", "Faculty only, Mon–Sat 08:30–18:30."),
 ("FCL-IT-005", "Discussion Room 1", "ROOM-DA-207", 8, "discussion_room", "Small room with display screen for group study and faculty consultations.", "Bookable in 1-hour slots, Mon–Sat 09:00–18:00."),
 ("FCL-IT-006", "Discussion Room 2", "ROOM-DA-208", 8, "discussion_room", "Small room with whiteboard for group study and project reviews.", "Bookable in 1-hour slots, Mon–Sat 09:00–18:00."),
 ("FCL-IT-007", "Student Project Workspace", "ROOM-DB-103", 60, "workspace", "Open-plan workspace with power, Wi-Fi and hot desks for any IT student project work.", "Open daily 08:00–21:00 during the semester."),
 ("FCL-IT-008", "GPU Computing Facility", "ROOM-DA-405", 12, "computing_facility", "Shared GPU servers for deep-learning, NLP and vision projects; access through a job scheduler.", "24x7 remote access for approved projects; room open Mon–Fri 09:00–17:00."),
 ("FCL-IT-009", "Department Reading Room", "ROOM-DA-209", 40, "reading_room", "Quiet reading room with reference books, past project reports and journals.", "Mon–Sat 09:00–19:00."),
 ("FCL-IT-010", "Department Office & Student Help Desk", "ROOM-DA-201", 10, "office", "Front office for certificates, forms, facility bookings and general queries.", "Mon–Fri 09:30–17:00, Sat 09:30–13:00."),
]
def facility_records(rooms):
    out = []
    for fid, name, rid, cap, ftype, desc, avail in _FC:
        r = rooms[rid]
        b = next(x['name'] for x in BUILDINGS if x['building_id'] == r['building_id'])
        out.append(s("DOC-FACILITIES-001", facility_id=fid, facility_name=name, facility_type=ftype,
            department_id="DEPT-IT-001", room_id=rid, location=f"{b}, Floor {r['floor']}, Room {r['room_number']}",
            description=desc, capacity=cap, availability=avail + " (synthetic)", status="active", version="1.0"))
    return out

# ------------------------------------------------------------------ policies
P_NOTE = "This is a synthetic policy created for CampusMate testing. It is not a Ganpat University regulation."
_P = [
 ("POLICY-001", "CM-SYN-POL-001", "Attendance Policy (Demo)", "attendance", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"], [], [], [],
  "Sets the demo minimum attendance expectation for IT courses.",
  ["Students are expected to attend at least 75% of lecture and 80% of laboratory sessions in each course (synthetic threshold).",
   "Attendance is reviewed at mid-semester (see calendar CAL-2026-27-006) and before the end-semester examinations.",
   "Students below threshold receive a written advisory from the course faculty and may be asked to meet the Head of Department (FAC-IT-001).",
   "Medical or institutional-duty absences must be reported to the Department Office (FCL-IT-010) within 7 days."]),
 ("POLICY-002", "CM-SYN-POL-002", "Laboratory Usage Policy (Demo)", "laboratory", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"], [], [f"LAB-IT-{i:03d}" for i in range(1, 11)], [],
  "Rules for using any of the ten IT department laboratories LAB-IT-001 to LAB-IT-010.",
  ["Students may use a laboratory only during scheduled practicals or after registering a lab slot with the responsible faculty member of that lab.",
   "Lab slot registration opens every Monday at 09:00 through the department office email it-labs@campusmate-demo.example.",
   "Personal software may not be installed on lab workstations; requests go to the lab's responsible faculty.",
   "Lab computers must be logged off and seats left clean at the end of each session.",
   "Repeated violations are reported to the Head of Department."]),
 ("POLICY-003", "CM-SYN-POL-003", "Laboratory Safety Policy (Demo)", "safety", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"], [], [f"LAB-IT-{i:03d}" for i in range(1, 11)], ["FCL-IT-003", "FCL-IT-008"],
  "Electrical, hardware and data-safety rules for laboratories and maker spaces.",
  ["Food and drinks are not permitted inside any laboratory.",
   "Hardware in LAB-IT-007 (IoT & Robotics Lab) and FCL-IT-003 (Innovation & Incubation Centre) may be operated only after a safety induction.",
   "Report damaged cables, overheating equipment or data breaches immediately to the responsible faculty member.",
   "Emergency exits and fire extinguishers must never be blocked.",
   "Students must not connect unknown USB devices to the isolated security test network in LAB-IT-005."]),
 ("POLICY-004", "CM-SYN-POL-004", "Capstone Project Submission Policy (Demo)", "project", ["PROG-BTECH-IT-001"], ["2CEIT504", "2CEIT605", "2CEIT703"], [], ["FCL-IT-002"],
  "How B.Tech IT Capstone Project-I, II and III deliverables are submitted.",
  ["Teams of 2–4 students register a project title with the Project Coordinator (FAC-IT-020) by the topic deadline in the academic calendar.",
   "Each submission must include a report (PDF), source-code repository link, and a 5-minute demo video.",
   "Final submissions are made through the demo project portal by 17:00 on the deadline date; late submissions lose 10% per day for up to 3 days.",
   "Similarity above 20% in the report requires a written explanation to the Project Coordinator.",
   "Printed copies are not required unless requested by the evaluation panel."]),
 ("POLICY-005", "CM-SYN-POL-005", "Project Evaluation Policy (Demo)", "project", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"], ["2CEIT504", "2CEIT605", "2CEIT703", "3CEIT301", "3CEIT401"], [], ["FCL-IT-001", "FCL-IT-002"],
  "Panel-based evaluation of capstone and major projects.",
  ["Every project is evaluated by a panel of at least two faculty members plus the guide.",
   "Evaluation happens in two stages: a mid-review and a final presentation in the IT Seminar Hall (FCL-IT-001).",
   "Demo rubric weights: problem definition 15%, design 20%, implementation 30%, testing 15%, report and presentation 20%.",
   "Panel scores are finalised within 5 working days and published on the notice board.",
   "Students may request a re-review within 3 working days of publication."]),
 ("POLICY-006", "CM-SYN-POL-006", "Industrial Training Policy (Demo)", "project", ["PROG-BTECH-IT-001"], ["2CEIT801"], [], [],
  "Rules for the Semester VIII INDUSTRIAL TRAINING course (2CEIT801).",
  ["Students must submit an offer letter from the host organisation to the Project Coordinator (FAC-IT-020) before the start of Semester VIII.",
   "Fortnightly progress reports are due every second Friday.",
   "A faculty guide is assigned to each student and conducts at least one remote review per month.",
   "The final training report and presentation are due on the date in the academic calendar (CAL-2026-27-020)."]),
 ("POLICY-007", "CM-SYN-POL-007", "Seminar Policy (Demo)", "seminar", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"], ["2HS102", "3CEIT302"], [], ["FCL-IT-001"],
  "Topic approval and delivery of seminar courses.",
  ["Seminar topics must be approved by the course faculty at least 3 weeks before the presentation.",
   "Each seminar is 15 minutes of presentation plus 5 minutes of questions.",
   "Slides and a 2-page abstract must be uploaded 48 hours before the talk.",
   "M.Tech SEMINAR (3CEIT302) talks are scheduled in the IT Seminar Hall (FCL-IT-001)."]),
 ("POLICY-008", "CM-SYN-POL-008", "Faculty Consultation Policy (Demo)", "student_services", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"], [], [], ["FCL-IT-005", "FCL-IT-006"],
  "How students meet faculty outside class.",
  ["Every faculty member publishes weekly consultation hours in the Faculty Directory (DOC-FACULTY-001).",
   "Students book a slot by emailing the faculty member at least 24 hours in advance.",
   "Consultations take place in the faculty cabin or in Discussion Room 1/2 (FCL-IT-005, FCL-IT-006).",
   "Urgent academic issues can be raised at the Department Office & Student Help Desk (FCL-IT-010)."]),
 ("POLICY-009", "CM-SYN-POL-009", "Facility Booking Policy (Demo)", "facilities", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"], [], [], ["FCL-IT-001", "FCL-IT-005", "FCL-IT-006", "FCL-IT-008"],
  "Booking rules for the seminar hall, discussion rooms and GPU facility.",
  ["The IT Seminar Hall (FCL-IT-001) must be booked at least 5 working days in advance through the Department Office.",
   "Discussion rooms (FCL-IT-005, FCL-IT-006) can be booked for a maximum of 2 hours per team per day.",
   "GPU Computing Facility (FCL-IT-008) access requires a faculty-approved project and is allocated in 24-hour job quotas.",
   "Bookings not used within 15 minutes of the start time are released."]),
 ("POLICY-010", "CM-SYN-POL-010", "M.Tech Major Project Policy (Demo)", "project", ["PROG-MTECH-IT-001"], ["3CEIT301", "3CEIT401"], [], ["FCL-IT-002", "FCL-IT-008"],
  "Supervision and submission of MAJOR PROJECT PART - I and PART - II.",
  ["Each M.Tech student is assigned a supervisor from the IT faculty by the Project Coordinator (FAC-IT-020).",
   "A research proposal is due by the end of week 4 of Semester III.",
   "Part - II requires a thesis and at least one paper-style manuscript submitted to the supervisor.",
   "Final thesis submission follows the date in the academic calendar (CAL-2026-27-021)."]),
 ("POLICY-011", "CM-SYN-POL-011", "Academic Integrity Policy (Demo)", "academic_integrity", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"], [], [], [],
  "Expectations on original work and use of AI tools.",
  ["All submitted work must be the student's own; sources and AI-tool assistance must be acknowledged.",
   "Code submissions may be checked with similarity tools.",
   "Suspected violations are reviewed by a panel of two faculty members appointed by the Head of Department."]),
]
def policy_records():
    out = []
    for pid, num, title, cat, progs, courses, labs, fcls, summary, clauses in _P:
        out.append(s("DOC-POLICIES-001", policy_id=pid, policy_number=num, title=title, category=cat,
            applies_to_department_ids=["DEPT-IT-001"], applies_to_program_ids=progs,
            related_course_ids=[f"COURSE-{c}" for c in courses], related_lab_ids=labs, related_facility_ids=fcls,
            owner_faculty_id="FAC-IT-020" if cat == "project" else "FAC-IT-001",
            summary=summary, clauses=clauses, synthetic_notice=P_NOTE,
            effective_from="2026-07-01", effective_to="2027-06-30", version="1.0", status="active"))
    return out

# ------------------------------------------------------------------ academic calendar
_C = [
 ("CAL-2026-27-001", "Registration period – odd semester", "registration", "2026-07-06", "2026-07-10", "odd", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-002", "Orientation for new B.Tech IT and M.Tech IT students", "orientation", "2026-07-13", "2026-07-15", "odd", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-003", "Odd semester teaching begins", "semester_start", "2026-07-16", "2026-07-16", "odd", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-004", "Capstone / major project topic registration deadline", "project_deadline", "2026-08-14", "2026-08-14", "odd", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-005", "Independence Day – holiday", "holiday", "2026-08-15", "2026-08-15", "odd", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-006", "Mid-semester examinations – odd semester", "examination", "2026-09-07", "2026-09-12", "odd", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-007", "Capstone Project mid-review", "project_evaluation", "2026-09-28", "2026-10-03", "odd", ["PROG-BTECH-IT-001"]),
 ("CAL-2026-27-008", "Autumn break", "holiday", "2026-11-02", "2026-11-14", "odd", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-009", "Capstone Project final submission (Capstone Project-I and III)", "project_deadline", "2026-11-18", "2026-11-18", "odd", ["PROG-BTECH-IT-001"]),
 ("CAL-2026-27-010", "Last teaching day – odd semester", "semester_end", "2026-11-20", "2026-11-20", "odd", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-011", "Practical and viva examinations – odd semester", "examination", "2026-11-23", "2026-11-28", "odd", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-012", "End-semester theory examinations – odd semester", "examination", "2026-11-30", "2026-12-12", "odd", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-013", "Winter break", "holiday", "2026-12-14", "2026-12-31", "odd", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-014", "Result publication – odd semester", "result", "2027-01-08", "2027-01-08", "odd", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-015", "Registration period – even semester", "registration", "2027-01-04", "2027-01-06", "even", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-016", "Even semester teaching begins", "semester_start", "2027-01-07", "2027-01-07", "even", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-017", "Republic Day – holiday", "holiday", "2027-01-26", "2027-01-26", "even", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-018", "Mid-semester examinations – even semester", "examination", "2027-02-22", "2027-02-27", "even", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-019", "Capstone Project-II final submission", "project_deadline", "2027-04-16", "2027-04-16", "even", ["PROG-BTECH-IT-001"]),
 ("CAL-2026-27-020", "Industrial Training (2CEIT801) final report and presentation", "project_deadline", "2027-04-30", "2027-04-30", "even", ["PROG-BTECH-IT-001"]),
 ("CAL-2026-27-021", "M.Tech Major Project Part - II thesis submission", "project_deadline", "2027-04-23", "2027-04-23", "even", ["PROG-MTECH-IT-001"]),
 ("CAL-2026-27-022", "Last teaching day – even semester", "semester_end", "2027-04-24", "2027-04-24", "even", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-023", "End-semester theory examinations – even semester", "examination", "2027-05-03", "2027-05-15", "even", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-024", "Summer vacation", "holiday", "2027-05-17", "2027-06-30", "even", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
 ("CAL-2026-27-025", "Result publication – even semester", "result", "2027-06-11", "2027-06-11", "even", ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"]),
]
def calendar_records():
    odd = {"PROG-BTECH-IT-001": ["SEM-BTECH-IT-01", "SEM-BTECH-IT-03", "SEM-BTECH-IT-05", "SEM-BTECH-IT-07"],
           "PROG-MTECH-IT-001": ["SEM-MTECH-IT-01", "SEM-MTECH-IT-03"]}
    even = {"PROG-BTECH-IT-001": ["SEM-BTECH-IT-02", "SEM-BTECH-IT-04", "SEM-BTECH-IT-06", "SEM-BTECH-IT-08"],
            "PROG-MTECH-IT-001": ["SEM-MTECH-IT-02", "SEM-MTECH-IT-04"]}
    special = {"CAL-2026-27-007": ["SEM-BTECH-IT-05", "SEM-BTECH-IT-07"], "CAL-2026-27-009": ["SEM-BTECH-IT-05", "SEM-BTECH-IT-07"],
               "CAL-2026-27-019": ["SEM-BTECH-IT-06"], "CAL-2026-27-020": ["SEM-BTECH-IT-08"], "CAL-2026-27-021": ["SEM-MTECH-IT-04"],
               "CAL-2026-27-002": ["SEM-BTECH-IT-01", "SEM-MTECH-IT-01"]}
    out = []
    for cid, title, etype, st, en, term, progs in _C:
        m = odd if term == "odd" else even
        sems = special.get(cid, [x for p in progs for x in m[p]])
        out.append(s("DOC-CALENDAR-001", event_id=cid, title=title, event_type=etype, start_date=st, end_date=en,
            term=f"{term.title()} semester {AY}", department_id="DEPT-IT-001", program_ids=progs, semester_ids=sems,
            synthetic_notice="Synthetic demo date — not an actual Ganpat University schedule.", status="active", version="1.0"))
    return out

# ------------------------------------------------------------------ notices
_N = [
 ("NOTICE-001", "2026-07-01", "orientation", "Orientation programme for new B.Tech IT and M.Tech IT students", ["students_new"], "2026-07-13", "2026-07-15",
  "All newly admitted students of PROG-BTECH-IT-001 (Semester I) and PROG-MTECH-IT-001 (Semester I) must attend the orientation programme from 13 to 15 July 2026 in the IT Seminar Hall (FCL-IT-001, Demo Innovation Block B, Room DB-201). Sessions cover the curriculum, laboratory rules (POLICY-002, POLICY-003) and student services.",
  {"calendar_ids": ["CAL-2026-27-002"], "facility_ids": ["FCL-IT-001"], "policy_ids": ["POLICY-002", "POLICY-003"]}),
 ("NOTICE-002", "2026-07-02", "registration", "Odd semester course registration window", ["students_all"], "2026-07-06", "2026-07-10",
  "Course registration for the odd semester of AY 2026-2027 is open from 6 to 10 July 2026. Semester V students must select one course each from ELECTIVE-I (EGRP-BTECH-IT-05-ELECTIVE-I) and ELECTIVE-II (EGRP-BTECH-IT-05-ELECTIVE-II). Queries: Department Office (FCL-IT-010).",
  {"calendar_ids": ["CAL-2026-27-001"], "facility_ids": ["FCL-IT-010"]}),
 ("NOTICE-003", "2026-07-08", "timetable", "Odd semester timetable published", ["students_all", "faculty"], "2026-07-16", "2026-11-20",
  "The odd semester timetable for B.Tech IT Semesters III, V and VII and M.Tech IT Semesters I and III is published. Practicals for 2CEIT303 DATABASE MANAGEMENT SYSTEM run in LAB-IT-003 (Room DA-303); practicals for 2CEIT503 COMPUTER NETWORKS run in LAB-IT-005 (Room DA-401).",
  {"course_ids": ["COURSE-2CEIT303", "COURSE-2CEIT503"], "lab_ids": ["LAB-IT-003", "LAB-IT-005"]}),
 ("NOTICE-004", "2026-07-20", "project", "Capstone project team formation and topic registration", ["students_sem5", "students_sem7"], "2026-07-20", "2026-08-14",
  "Students of 2CEIT504 CAPSTONE PROJECT-I (Semester V) and 2CEIT703 CAPSTONE PROJECT-III (Semester VII) must form teams of 2–4 and register titles with the Project Coordinator Dr. Leena Projectkar (FAC-IT-020) by 14 August 2026 as per POLICY-004.",
  {"course_ids": ["COURSE-2CEIT504", "COURSE-2CEIT703"], "faculty_ids": ["FAC-IT-020"], "policy_ids": ["POLICY-004"], "calendar_ids": ["CAL-2026-27-004"]}),
 ("NOTICE-005", "2026-08-10", "examination", "Mid-semester examination schedule – odd semester (version 1)", ["students_all"], "2026-09-07", "2026-09-12",
  "Mid-semester examinations for the odd semester will be held from 7 to 12 September 2026. Detailed paper-wise timetable is attached to this notice. This notice is SUPERSEDED by NOTICE-008.",
  {"calendar_ids": ["CAL-2026-27-006"], "superseded_by": "NOTICE-008"}),
 ("NOTICE-006", "2026-08-12", "holiday", "Independence Day holiday", ["students_all", "faculty", "staff"], "2026-08-15", "2026-08-15",
  "The department will remain closed on 15 August 2026 (CAL-2026-27-005). Laboratories LAB-IT-001 to LAB-IT-010 will be closed.",
  {"calendar_ids": ["CAL-2026-27-005"]}),
 ("NOTICE-007", "2026-08-18", "workshop", "Hands-on workshop: Retrieval-Augmented Generation with local SLMs", ["students_sem7", "students_mtech"], "2026-08-29", "2026-08-29",
  "A one-day workshop on retrieval-augmented generation, BM25 + vector hybrid search and local small language models will be conducted by Dr. Nisha Tokenwala (FAC-IT-003) in the Natural Language Processing Lab (LAB-IT-002, Room DA-302) on 29 August 2026. Recommended for students of 2CEIT78PE7 NATURAL LANGUAGE PROCESSING and 3CEIT307.",
  {"faculty_ids": ["FAC-IT-003"], "lab_ids": ["LAB-IT-002"], "course_ids": ["COURSE-2CEIT78PE7", "COURSE-3CEIT307"]}),
 ("NOTICE-008", "2026-08-28", "examination", "REVISED mid-semester examination schedule – odd semester (version 2)", ["students_all"], "2026-09-07", "2026-09-12",
  "This notice supersedes NOTICE-005. The mid-semester examination window remains 7 to 12 September 2026, but the 2CEIT602 ARTIFICIAL INTELLIGENCE paper for re-registered students moves to 12 September 2026 (Saturday) and all papers now start at 10:00 instead of 09:30.",
  {"calendar_ids": ["CAL-2026-27-006"], "supersedes": "NOTICE-005", "course_ids": ["COURSE-2CEIT602"]}),
 ("NOTICE-009", "2026-09-01", "laboratory", "Weekly lab slot registration opens for Database Systems Lab and Programming Lab", ["students_all"], "2026-09-07", "2026-11-20",
  "Extra practice slots in LAB-IT-003 (Database Systems Lab) and LAB-IT-004 (Programming Lab) can be registered every Monday from 09:00 by email to it-labs@campusmate-demo.example, as per POLICY-002.",
  {"lab_ids": ["LAB-IT-003", "LAB-IT-004"], "policy_ids": ["POLICY-002"]}),
 ("NOTICE-010", "2026-09-03", "seminar", "Guest seminar: Responsible AI in education", ["students_all", "faculty"], "2026-09-16", "2026-09-16",
  "A guest seminar on responsible AI in education will be held on 16 September 2026 at 11:00 in the IT Seminar Hall (FCL-IT-001). Coordinated by Dr. Arjun Tensorkar (FAC-IT-002).",
  {"faculty_ids": ["FAC-IT-002"], "facility_ids": ["FCL-IT-001"]}),
 ("NOTICE-011", "2026-09-08", "meeting", "Faculty meeting – capstone mid-review panels", ["faculty"], "2026-09-15", "2026-09-15",
  "All IT faculty members are requested to attend a meeting on 15 September 2026 at 15:00 in the Faculty Lounge (FCL-IT-004) to finalise panels for the capstone mid-review (CAL-2026-27-007) under POLICY-005. Convened by the Head of Department, Dr. Meera Datavala (FAC-IT-001).",
  {"faculty_ids": ["FAC-IT-001"], "facility_ids": ["FCL-IT-004"], "policy_ids": ["POLICY-005"], "calendar_ids": ["CAL-2026-27-007"]}),
 ("NOTICE-012", "2026-09-10", "project", "Capstone mid-review schedule", ["students_sem5", "students_sem7", "faculty"], "2026-09-28", "2026-10-03",
  "Capstone Project mid-reviews for 2CEIT504 and 2CEIT703 will run from 28 September to 3 October 2026 in the Capstone Project Room (FCL-IT-002, Room DA-205). Teams must upload an interim report 48 hours before their slot (POLICY-004, POLICY-005).",
  {"course_ids": ["COURSE-2CEIT504", "COURSE-2CEIT703"], "facility_ids": ["FCL-IT-002"], "policy_ids": ["POLICY-004", "POLICY-005"], "calendar_ids": ["CAL-2026-27-007"]}),
 ("NOTICE-013", "2026-09-14", "facility", "GPU Computing Facility maintenance", ["students_all", "faculty"], "2026-09-19", "2026-09-20",
  "The GPU Computing Facility (FCL-IT-008, Room DA-405) will be unavailable on 19–20 September 2026 for scheduled maintenance. Jobs queued before 18 September 18:00 will be resumed afterwards.",
  {"facility_ids": ["FCL-IT-008"]}),
 ("NOTICE-014", "2026-09-17", "timetable", "Timetable update: Cloud Computing and Big Data Analytics practicals", ["students_sem7"], "2026-09-21", "2026-11-20",
  "From 21 September 2026, practicals of 2CEIT702 BIG DATA ANALYTICS move from Wednesday to Friday 14:00–16:00 in LAB-IT-006 (Cloud & Big Data Lab, Room DA-402).",
  {"course_ids": ["COURSE-2CEIT702"], "lab_ids": ["LAB-IT-006"]}),
 ("NOTICE-015", "2026-06-15", "general", "Summer internship report submission (AY 2025-2026 carry-over)", ["students_sem5"], "2026-06-15", "2026-07-31",
  "Students who completed optional summer internships must submit a 2-page report to the Department Office (FCL-IT-010) by 31 July 2026. This notice has EXPIRED.",
  {"facility_ids": ["FCL-IT-010"]}),
 ("NOTICE-016", "2026-07-25", "laboratory", "Mandatory safety induction for IoT & Robotics Lab", ["students_sem6", "students_mtech"], "2026-08-03", "2026-08-07",
  "Students intending to take 2CEIT6PE6 ROBOTICS or 2CEIT6PE9 INTERNET OF THINGS, and M.Tech students of 3CEIT305, must complete the safety induction in LAB-IT-007 (Room DB-101) as per POLICY-003.",
  {"lab_ids": ["LAB-IT-007"], "policy_ids": ["POLICY-003"], "course_ids": ["COURSE-2CEIT6PE6", "COURSE-2CEIT6PE9", "COURSE-3CEIT305"]}),
 ("NOTICE-017", "2026-08-05", "project", "M.Tech Major Project Part - I supervisor allocation", ["students_mtech"], "2026-08-05", "2026-08-31",
  "Supervisor allocation for 3CEIT301 MAJOR PROJECT PART - I is published. Students must submit research proposals by the end of week 4 as per POLICY-010. Contact the Project Coordinator (FAC-IT-020).",
  {"course_ids": ["COURSE-3CEIT301"], "policy_ids": ["POLICY-010"], "faculty_ids": ["FAC-IT-020"]}),
 ("NOTICE-018", "2026-09-18", "examination", "End-semester examination form submission", ["students_all"], "2026-09-21", "2026-10-09",
  "Examination forms for the odd semester end-semester examinations (CAL-2026-27-012, 30 November to 12 December 2026) must be submitted between 21 September and 9 October 2026 via the Department Office (FCL-IT-010).",
  {"calendar_ids": ["CAL-2026-27-012"], "facility_ids": ["FCL-IT-010"]}),
 ("NOTICE-019", "2026-08-20", "general", "Department reading room extended hours", ["students_all"], "2026-08-24", "2026-12-12",
  "The Department Reading Room (FCL-IT-009, Room DA-209) will remain open until 21:00 on weekdays until the end of the odd semester examinations.",
  {"facility_ids": ["FCL-IT-009"]}),
 ("NOTICE-020", "2026-07-30", "seminar", "Seminar topic approval deadline for M.Tech SEMINAR (3CEIT302)", ["students_mtech"], "2026-07-30", "2026-08-21",
  "M.Tech Semester III students must get seminar topics approved by 21 August 2026 as per POLICY-007. Seminars will be delivered in the IT Seminar Hall (FCL-IT-001).",
  {"course_ids": ["COURSE-3CEIT302"], "policy_ids": ["POLICY-007"], "facility_ids": ["FCL-IT-001"]}),
]
def notice_records(today="2026-09-18"):
    out = []
    for nid, date, cat, title, aud, eff, exp, content, links in _N:
        status = "superseded" if links.get("superseded_by") else ("expired" if exp < today else "active")
        out.append(s("DOC-NOTICES-001", notice_id=nid, title=title, date=date, department_id="DEPT-IT-001",
            category=cat, target_audience=aud, content=content, effective_date=eff, expiry_date=exp,
            related_course_ids=links.get("course_ids", []), related_faculty_ids=links.get("faculty_ids", []),
            related_lab_ids=links.get("lab_ids", []), related_facility_ids=links.get("facility_ids", []),
            related_policy_ids=links.get("policy_ids", []), related_calendar_ids=links.get("calendar_ids", []),
            supersedes=links.get("supersedes"), superseded_by=links.get("superseded_by"),
            status=status, version="1.0"))
    return out

# ------------------------------------------------------------------ FAQ
_Q = [
 ("FAQ-001", "projects", "How do I submit my capstone project?", "Submit the report (PDF), repository link and 5-minute demo video through the demo project portal by 17:00 on the deadline in the academic calendar. Late submissions lose 10% per day for up to 3 days.", ["POLICY-004", "FAC-IT-020", "CAL-2026-27-009", "COURSE-2CEIT504", "COURSE-2CEIT605", "COURSE-2CEIT703"]),
 ("FAQ-002", "projects", "When are capstone project evaluations?", "The odd-semester mid-review runs 28 September–3 October 2026 (CAL-2026-27-007). Final presentations follow the submission deadlines in the calendar and are held in the IT Seminar Hall.", ["POLICY-005", "CAL-2026-27-007", "FCL-IT-001", "NOTICE-012"]),
 ("FAQ-003", "projects", "Who is the project coordinator?", "Dr. Leena Projectkar (FAC-IT-020), Associate Professor & Project Coordinator, cabin ROOM-DA-219. Email: leena.projectkar@campusmate-demo.example.", ["FAC-IT-020"]),
 ("FAQ-004", "projects", "How big can a capstone team be?", "Teams of 2 to 4 students, registered with the Project Coordinator by the topic deadline.", ["POLICY-004", "CAL-2026-27-004"]),
 ("FAQ-005", "projects", "How is my capstone project graded?", "A panel of at least two faculty plus the guide uses the demo rubric: problem definition 15%, design 20%, implementation 30%, testing 15%, report and presentation 20%.", ["POLICY-005"]),
 ("FAQ-006", "projects", "Can I request a re-review of my project marks?", "Yes. Request a re-review within 3 working days of the panel scores being published.", ["POLICY-005"]),
 ("FAQ-007", "projects", "What do I need before starting Industrial Training in Semester VIII?", "Submit an offer letter from the host organisation to the Project Coordinator before Semester VIII starts; then send fortnightly progress reports.", ["POLICY-006", "COURSE-2CEIT801", "FAC-IT-020"]),
 ("FAQ-008", "projects", "Where can my project team work?", "Use the Capstone Project Room (FCL-IT-002, Room DA-205) or the Student Project Workspace (FCL-IT-007, Room DB-103).", ["FCL-IT-002", "FCL-IT-007"]),
 ("FAQ-009", "faculty", "How can I contact a faculty member?", "Email the faculty member (addresses are in the Faculty Directory) at least 24 hours before their published consultation hours.", ["POLICY-008", "DOC-FACULTY-001"]),
 ("FAQ-010", "faculty", "Who is the Head of the IT department?", "Dr. Meera Datavala (FAC-IT-001), Professor & Head of Department, cabin ROOM-DA-202 (synthetic demo identity).", ["FAC-IT-001", "DEPT-IT-001"]),
 ("FAQ-011", "faculty", "Where do consultations take place?", "In the faculty member's cabin or in Discussion Room 1/2 (FCL-IT-005, FCL-IT-006).", ["POLICY-008", "FCL-IT-005", "FCL-IT-006"]),
 ("FAQ-012", "laboratories", "How can I register for a laboratory slot?", "Email it-labs@campusmate-demo.example; registration opens every Monday at 09:00 as per the Laboratory Usage Policy.", ["POLICY-002", "NOTICE-009"]),
 ("FAQ-013", "laboratories", "Where is the NLP laboratory?", "The Natural Language Processing Lab (LAB-IT-002) is in Demo Academic Block A, Floor 3, Room DA-302.", ["LAB-IT-002"]),
 ("FAQ-014", "laboratories", "Which lab is used for Database Management System practicals?", "LAB-IT-003 Database Systems Lab, Room DA-303, responsible faculty Dr. Meera Datavala (FAC-IT-001).", ["LAB-IT-003", "COURSE-2CEIT303", "FAC-IT-001"]),
 ("FAQ-015", "laboratories", "Can I eat or drink in the labs?", "No. Food and drinks are not permitted in any laboratory.", ["POLICY-003"]),
 ("FAQ-016", "laboratories", "Do I need training before using the IoT & Robotics Lab?", "Yes. A safety induction is mandatory before operating hardware in LAB-IT-007.", ["POLICY-003", "LAB-IT-007", "NOTICE-016"]),
 ("FAQ-017", "laboratories", "Can I install my own software on lab computers?", "No. Send installation requests to the responsible faculty of that lab.", ["POLICY-002"]),
 ("FAQ-018", "facilities", "Where is the project room?", "The Capstone Project Room (FCL-IT-002) is in Demo Academic Block A, Floor 2, Room DA-205.", ["FCL-IT-002"]),
 ("FAQ-019", "facilities", "How do I book the seminar hall?", "Book the IT Seminar Hall (FCL-IT-001) through the Department Office at least 5 working days in advance.", ["POLICY-009", "FCL-IT-001", "FCL-IT-010"]),
 ("FAQ-020", "facilities", "How do I get GPU access for my project?", "Ask your guide to approve the project; the GPU Computing Facility (FCL-IT-008) allocates 24-hour job quotas.", ["POLICY-009", "FCL-IT-008"]),
 ("FAQ-021", "facilities", "What are the Department Office hours?", "Monday–Friday 09:30–17:00 and Saturday 09:30–13:00, Room DA-201.", ["FCL-IT-010"]),
 ("FAQ-022", "seminars", "What is the process for seminar submission?", "Get your topic approved 3 weeks ahead, upload slides and a 2-page abstract 48 hours before the talk, then present for 15 minutes plus 5 minutes of questions.", ["POLICY-007", "COURSE-2HS102", "COURSE-3CEIT302"]),
 ("FAQ-023", "academics", "What courses are in Semester VI of B.Tech IT?", "Per the official syllabus: 2CEIT601 THEORY OF COMPUTATION, 2CEIT602 ARTIFICIAL INTELLIGENCE, 2CEIT603 CLOUD COMPUTING, 2CEIT604 USER EXPERIENCE DESIGN, 2CEIT605 CAPSTONE PROJECT-II, 2HS6101 APTITUDE SKILL BUILDING–II, plus one course each from ELECTIVE-III and ELECTIVE-IV.", ["SEM-BTECH-IT-06", "PROG-BTECH-IT-001"]),
 ("FAQ-024", "academics", "What is the grading scale?", "Per the official syllabus grade table: 90 and above A+ (10), 80–89 A (9), 70–79 B+ (8), 60–69 B (7), 50–59 C+ (6), 40–49 C (5), below 40 F (0).", ["GRADE-BAND-01", "PROG-BTECH-IT-001"]),
 ("FAQ-025", "academics", "How many credits is the B.Tech IT programme?", "174 credits across Semesters I–VIII, computed from the official semester totals (20+20+24+21+23+23+23+20).", ["PROG-BTECH-IT-001"]),
 ("FAQ-026", "academics", "What is the minimum attendance requirement?", "The demo Attendance Policy (POLICY-001) expects 75% of lectures and 80% of lab sessions. This is synthetic; the official GUNI documents supplied do not contain an attendance regulation.", ["POLICY-001"]),
 ("FAQ-027", "academics", "Are there prerequisites for Artificial Intelligence?", "The official syllabus does not list prerequisites. The synthetic advisory map recommends 2CEIT402 DESIGN AND ANALYSIS OF ALGORITHMS and 2BS3102 DISCRETE MATHEMATICS & PROBABILITY.", ["COURSE-2CEIT602", "COURSE-2CEIT402", "COURSE-2BS3102"]),
 ("FAQ-028", "academics", "Can I use AI tools for assignments?", "Only with acknowledgement; undisclosed use counts as an integrity violation under the demo Academic Integrity Policy.", ["POLICY-011"]),
 ("FAQ-029", "calendar", "When do odd-semester end-semester exams start?", "30 November 2026 (demo calendar CAL-2026-27-012, ends 12 December 2026).", ["CAL-2026-27-012"]),
 ("FAQ-030", "calendar", "When are odd-semester results published?", "8 January 2027 (demo calendar CAL-2026-27-014).", ["CAL-2026-27-014"]),
 ("FAQ-031", "services", "Where do I submit medical absence documents?", "At the Department Office & Student Help Desk (FCL-IT-010) within 7 days.", ["POLICY-001", "FCL-IT-010"]),
 ("FAQ-032", "services", "Where can I read past project reports?", "In the Department Reading Room (FCL-IT-009, Room DA-209).", ["FCL-IT-009"]),
]
def faq_records():
    return [s("DOC-FAQ-001", faq_id=q, category=c, question=qq, answer=a, related_entity_ids=ids,
              department_id="DEPT-IT-001", status="active", version="1.0",
              answer_basis="mixed: official curriculum facts cited from the GUNI syllabus; everything else synthetic" if any(x.startswith(("SEM-", "PROG-", "GRADE-")) for x in ids) else "synthetic")
            for q, c, qq, a, ids in _Q]

# ------------------------------------------------------------------ synthetic prerequisite map
_PR = [("2CEIT302", "2ES104"), ("2CEIT303", "2ES104"), ("2CEIT304", "2ES104"), ("2CEIT401", "2CEIT304"),
       ("2CEIT402", "2CEIT304"), ("2CEIT405", "2CEIT303"), ("2CEIT501", "2CEIT301"), ("2CEIT503", "2CEIT401"),
       ("2CEIT601", "2BS3102"), ("2CEIT602", "2CEIT402"), ("2CEIT602", "2BS3102"), ("2CEIT603", "2CEIT503"),
       ("2CEIT701", "2CEIT601"), ("2CEIT702", "2CEIT303"), ("2CEIT702", "2CEIT405"), ("2CEIT6PE4", "2CEIT404"),
       ("2CEIT6PE3", "2CEIT503"), ("2CEIT6PE7", "2CEIT503"), ("2CEIT78PE1", "2CEIT602"), ("2CEIT78PE7", "2CEIT602"),
       ("2CEIT78PE13", "2CEIT602"), ("2CEIT605", "2CEIT504"), ("2CEIT703", "2CEIT605"), ("3CEIT401", "3CEIT301")]
def prerequisite_records():
    return [s("DOC-COURSES-001", prerequisite_id=f"PREREQ-SYN-{i:03d}", course_id=f"COURSE-{a}",
              requires_course_id=f"COURSE-{b}", strength="recommended",
              synthetic_notice="Synthetic advisory prerequisite for CampusMate testing. The official GUNI syllabus pages used here do not specify prerequisites.")
            for i, (a, b) in enumerate(_PR, 1)]

# ------------------------------------------------------------------ synthetic course descriptions
DESC = {
 "2CEIT301": "Number systems, Boolean algebra, combinational and sequential logic design with hands-on trainer kits.",
 "2CEIT302": "Classes, objects, inheritance, polymorphism and exception handling with practical programming in an OO language.",
 "2CEIT303": "Relational model, ER modelling, SQL, normalisation, transactions and indexing, with practicals on PostgreSQL/MySQL.",
 "2CEIT304": "Arrays, stacks, queues, linked lists, trees, graphs, hashing, sorting and searching.",
 "2CEIT401": "Processes, threads, CPU scheduling, synchronisation, memory management and file systems.",
 "2CEIT402": "Asymptotic analysis, divide and conquer, greedy, dynamic programming, graph algorithms and NP-completeness.",
 "2CEIT403": "Modern application development toolchains, version control, build tools and rapid application frameworks.",
 "2CEIT404": "Python programming, data structures, modules, file handling and scientific libraries.",
 "2CEIT405": "Practical introduction to document, key-value, column-family and graph databases.",
 "2CEIT501": "Instruction sets, CPU organisation, pipelining, memory hierarchy and I/O.",
 "2CEIT502": "Software process models, requirements, design, testing and project management.",
 "2CEIT503": "Network layers, TCP/IP, routing, switching, transport protocols and socket programming.",
 "2CEIT504": "First stage of the capstone project: problem identification, literature survey and project proposal.",
 "2CEIT601": "Finite automata, regular languages, context-free grammars, pushdown automata and Turing machines.",
 "2CEIT602": "Search, knowledge representation, reasoning, planning and an introduction to machine learning, with lab exercises in Python.",
 "2CEIT603": "Virtualisation, cloud service and deployment models, cloud storage and containers.",
 "2CEIT604": "User research, personas, wireframing, prototyping and usability testing.",
 "2CEIT605": "Second stage of the capstone project: design and partial implementation.",
 "2CEIT701": "Lexical analysis, parsing, semantic analysis, intermediate code generation and optimisation.",
 "2CEIT702": "Hadoop, Spark, distributed storage and large-scale data processing pipelines.",
 "2CEIT703": "Final stage of the capstone project: complete implementation, testing, report and presentation.",
 "2CEIT704": "Communication, teamwork, interview and presentation skills for placement readiness.",
 "2CEIT801": "Semester-long industrial training in a host organisation with periodic reporting.",
 "2CEIT78PE7": "Text preprocessing, language models, embeddings, sequence labelling, transformers and retrieval-augmented generation.",
 "2CEIT6PE4": "Data wrangling, exploratory analysis, supervised and unsupervised learning, and model evaluation.",
 "2CEIT78PE1": "Neural networks, CNNs, RNNs, transformers and training practice on GPUs.",
 "3CEIT101": "Fuzzy systems, evolutionary algorithms, neural networks and swarm intelligence.",
 "3CEIT301": "First part of the M.Tech dissertation: problem formulation, literature review and research proposal.",
 "3CEIT401": "Second part of the M.Tech dissertation: implementation, experiments, thesis and publication.",
 "3CEIT307": "Advanced NLP: neural language models, information extraction, question answering and evaluation.",
}
def synthetic_description(code, name, ctype, group):
    if code in DESC: return DESC[code]
    if ctype == "elective": return f"Elective option in group {group}: a course on {name.title()} covering its core concepts, tools and a mini project. (Generic synthetic summary.)"
    return None
