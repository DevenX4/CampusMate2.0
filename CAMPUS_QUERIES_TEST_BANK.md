# CampusMate 2.0 — Audited Question & Answer Test Bank + Rule-Based Cross-Check

> **Brutal-Honesty Cross-Check Report:** Audited directly against [`hybrid_engine.py`](CampusMate_2-main/AI_workflow/backend/app/retrieval/hybrid_engine.py), [`knowledge_base.json`](CampusMate_2-main/AI_workflow/storage/knowledge_base.json) (`237` indexed records), [`backend/.env`](CampusMate_2-main/AI_workflow/backend/.env), and [`ChatContainer.jsx`](CampusMate_2-main/src/components/chat/ChatContainer.jsx).

---

## Cross-Check Verdict: Are These Answers Hardcoded / Pre-Added in the System?

To ensure **CampusMate 2.0 is NOT a rule-based chatbot**, we audited every query in this file across both code and storage. Here is the exact, unvarnished truth:

| Question | Answer | Evidence in Codebase |
| :--- | :---: | :--- |
| **1. Are these Q&A answers pre-written as question-to-answer pairs in the chatbot?** | **NO** | All `237` records are structured academic records (`curriculum`, `faculty`, `calendar`, `policy`, `faq`, `facility`, `notice`, `academic`, `department`) ingested from JSON datasets via [`seed_and_index.py`](CampusMate_2-main/AI_workflow/backend/app/ingestion/seed_and_index.py) into BM25 + ChromaDB (`BAAI/bge-small-en-v1.5`). |
| **2. Is a live generative LLM (Groq / OpenAI / Ollama) synthesizing the answers right now?** | **NO** | [`backend/.env`](CampusMate_2-main/AI_workflow/backend/.env) sets `GENERATION_PROVIDER=extractive` and neither `GROQ_API_KEY` nor `OPENAI_API_KEY` is configured. `_generate_answer()` skips Groq on every request and enters Python `if/elif/else` template formatting (`Branches A–E`). |
| **3. Do ANY hardcoded/static rule-based shortcuts still exist in code?** | **YES (3 Places)** | **Must be cleaned up** so synthesis is 100% evidence-driven (see table below). |

### Exact Places Where Static / Rule-Based Logic Still Exists Today

| Location | Lines | What It Currently Does (And Why It Breaks Real RAG) |
| :--- | :---: | :--- |
| [`hybrid_engine.py`](CampusMate_2-main/AI_workflow/backend/app/retrieval/hybrid_engine.py#L505-L511) | `505–511` | **Branch C (Attendance & Policies):** Completely **ignores the retrieved document text** and outputs a hardcoded 3-bullet string (`75% attendance...`). **Proven failure:** *"What is the procedure for submitting medical leaves?"* retrieved the right FAQ (`FCL-IT-010`, within 7 days), then Branch C threw it away and printed the static attendance bullets! |
| [`hybrid_engine.py`](CampusMate_2-main/AI_workflow/backend/app/retrieval/hybrid_engine.py#L425-L522) | `425–522` | **Branches A, B, D (Local Template Formatters):** Keyword `if/elif` matching overrides RAG ranking — `"starting"` triggers Calendar dates (`Branch D`), `CAL-2026-27-006` corrupts into date `2026-27-00`, `"professor"` / `"office"` overrides consultation & office-hour FAQs (`Branch A`), and FAQ `"course"` overwrites specific course `2CEIT601` (`Branch B`). |
| [`ChatContainer.jsx`](CampusMate_2-main/src/components/chat/ChatContainer.jsx#L291-L318) | `291–318` | **Client-Side Tertiary Fail-Safe:** Only runs when *both* Node Express and FastAPI are unreachable, **but** contains 3 hardcoded `if/else` keyword answers (`Semester 6`, `Attendance`, `HOD`) with **stale wrong facts** (`Distributed Computing` instead of `THEORY OF COMPUTATION`; `Room 204` instead of `ROOM-DA-202`). |

### 5 Factual Mismatches Found & Fixed in This Test Bank vs. `knowledge_base.json`
The earlier draft of this document contained 5 inaccurate descriptions carried over from stale mock text:
1. **`2CEIT601`** in `knowledge_base.json` is **`THEORY OF COMPUTATION`** (`4.0` credits, `150` marks), *not* `Distributed Computing & Cloud Infrastructure`.
2. **Semester VI Electives** in `knowledge_base.json` are **`2CEIT6PE1` – `2CEIT6PE9`** (`WEB TECHNOLOGY`, `CRYPTOGRAPHY AND NETWORK SECURITY`, `DATA SCIENCES AND MACHINE LEARNING`, `ROBOTICS`, `ETHICAL HACKING`, `INTERNET OF THINGS`, etc.), *not* `Deep Learning / Cloud Native DevOps / Blockchain`.
3. **HOD Cabin & Email**: `FAC-IT-001` (`Dr. Meera Datavala`) is **`ROOM-DA-202`** (`meera.datavala@campusmate-demo.example`), *not* `Room 204` / `hod.it@gnu.ac.in`.
4. **`2CEIT304` & `2CEIT401` Units**: `knowledge_base.json` stores credit breakdown, contact hours, total marks (`150`), and curriculum section for `2CEIT304` / `2CEIT401` — only **`2CEIT78PE4 - Mobile Computing`** has full Unit 1–5 syllabus text indexed!
5. **Library & Campus WiFi**: `knowledge_base.json` has **0 chunks** mentioning `"library"` or `"wifi"`. Previously listed in Section 6, it actually leaked `Policy: Laboratory Safety Policy (Demo)` instead of abstaining — it is now properly classified under **Section 7 (Abstention Tests)** and replaced in Section 6 with real indexed facilities (`Database Systems Lab`, `Department Office hours`).

---

## Quick Test Index
- [Section 1: Course Curriculum & Credits (Sem 1 – 8)](#section-1-course-curriculum--credits-sem-1--8)
- [Section 2: Faculty, HOD & Consultation Records](#section-2-faculty-hod--consultation-records)
- [Section 3: Attendance, Detention & Grading Policies](#section-3-attendance-detention--grading-policies)
- [Section 4: Academic Calendar, Exam Dates & Deadlines](#section-4-academic-calendar-exam-dates--deadlines)
- [Section 5: Capstone Project & Industrial Training Guidelines](#section-5-capstone-project--industrial-training-guidelines)
- [Section 6: Department Labs & Campus Facilities](#section-6-department-labs--campus-facilities)
- [Section 7: Out-of-KB University Queries (Abstention Tests)](#section-7-out-of-kb-university-queries-abstention-tests)
- [Section 8: Strict Outsider Questions (Domain Guardrail Tests)](#section-8-strict-outsider-questions-domain-guardrail-tests)

---

## Section 1: Course Curriculum & Credits (Sem 1 – 8)

### Query 1.1: Semester 6 Course Catalog
* **Audit Status:** `PASS` (Hits `FAQ: What courses are in Semester VI of B.Tech IT?`)
* **Copy Query:**
  ```text
  What courses and subjects are offered in Semester 6 B.Tech IT?
  ```
* **Verified KB Ground Truth:**
  Lists `2CEIT601 THEORY OF COMPUTATION`, `2CEIT602 ARTIFICIAL INTELLIGENCE`, `2CEIT603 CLOUD COMPUTING`, `2CEIT604 USER EXPERIENCE DESIGN`, `2CEIT605 CAPSTONE PROJECT-II`, `2HS6101 APTITUDE SKILL BUILDING–II`, plus Elective-III and Elective-IV.

### Query 1.2: Specific Course Code & Credits (`2CEIT601`)
* **Audit Status:** `BUG EXPOSED (Branch B Overwrite)` — Retrieval ranks `Course: 2CEIT601 - THEORY OF COMPUTATION` #1, then Branch B (`hybrid_engine.py#L458`) replaces it with the Sem VI FAQ!
* **Copy Query:**
  ```text
  What is 2CEIT601 and what are its credits?
  ```
* **Verified KB Ground Truth:**
  `Course: 2CEIT601 - THEORY OF COMPUTATION`, **`4.0` credits** (`Theory: 3.0`, `Practical: 1.0`, `Contact Hours: 5.0`), **`150` Total Marks**, Prerequisites: `None`, Section: `B.TECH-IT Semester VI – course table`.

### Query 1.3: Detailed 5-Unit Syllabus Breakdown (`2CEIT78PE4` Mobile Computing)
* **Audit Status:** `PASS` (Only course in KB with full Unit 1–5 syllabus outline)
* **Copy Query:**
  ```text
  What is the syllabus and unit breakdown for Mobile Computing (2CEIT78PE4)?
  ```
* **Verified KB Ground Truth:**
  `2CEIT78PE4 - Mobile Computing (Elective IV - Semester VII)`, `4 Credits (Theory: 3, Practical: 2, Total Marks: 150)`, Units 1–5 covering Cellular Basics & Handover, MAC (`SDMA/FDMA/TDMA/CDMA`), GSM/DECT/TETRA/Satellite, Mobile IP/TCP, and Mobile Ecosystems & Security.

### Query 1.4: Course Credits & Total Marks (`2CEIT304` & `2CEIT401`)
* **Audit Status:** `PASS`
* **Copy Query:**
  ```text
  What are the credits, contact hours, and total marks for 2CEIT304 Data Structures?
  ```
  ```text
  What are the prerequisites and total marks for 2CEIT401 Operating Systems?
  ```
* **Verified KB Ground Truth:**
  * `2CEIT304 - DATA STRUCTURES` (`Semester III`): **`5.0` credits** (`Theory: 3.0`, `Practical: 2.0`, `7.0` contact hours), **`150` marks**, Prerequisites: `None`.
  * `2CEIT401 - OPERATING SYSTEMS` (`Semester IV`): **`4.0` credits** (`Theory: 3.0`, `Practical: 1.0`, `5.0` contact hours), **`150` marks**, Prerequisites: `None`.

### Query 1.5: Semester 6 Elective Offerings
* **Audit Status:** `PARTIAL` (Returns top single elective `2CEIT6PE6 - ROBOTICS` in local mode; needs LLM + metadata list to enumerate all `2CEIT6PE1–6PE9`)
* **Copy Query:**
  ```text
  What elective subjects can I choose in Semester 6 B.Tech IT?
  ```
* **Verified KB Ground Truth:**
  Department Electives indexed for Sem VI include `2CEIT6PE1 WEB TECHNOLOGY`, `2CEIT6PE2 SOFTWARE VALIDATION & TESTING`, `2CEIT6PE3 CRYPTOGRAPHY AND NETWORK SECURITY`, `2CEIT6PE4 DATA SCIENCES AND MACHINE LEARNING`, `2CEIT6PE5 GAME DESIGN & DEVELOPMENT`, `2CEIT6PE6 ROBOTICS`, `2CEIT6PE7 ETHICAL HACKING`, `2CEIT6PE8 IT INFRASTRUCTURE & MANAGEMENT`, and `2CEIT6PE9 INTERNET OF THINGS`.

---

## Section 2: Faculty, HOD & Consultation Records

### Query 2.1: Head of Department (HOD)
* **Audit Status:** `PASS` (Hits `Faculty: Dr. Meera Datavala (HOD)`)
* **Copy Query:**
  ```text
  Who is the HOD of Information Technology?
  ```
* **Verified KB Ground Truth:**
  **Dr. Meera Datavala** (`FAC-IT-001`), Professor & Head of Department, Cabin: **`ROOM-DA-202`**, Email: `meera.datavala@campusmate-demo.example`, Consultation Hours: `Tuesday & Thursday 15:00–16:30 (synthetic)`.

### Query 2.2: Specific Faculty Cabin & Consultation Hours
* **Audit Status:** `PASS`
* **Copy Query:**
  ```text
  What is Dr. Arjun Tensorkar's cabin location and consultation hours?
  ```
* **Verified KB Ground Truth:**
  **Dr. Arjun Tensorkar** (`FAC-IT-002`, Professor, AI/ML), Cabin: **`ROOM-DA-210`**, Email: `arjun.tensorkar@campusmate-demo.example`, Consultation Hours: `Monday & Wednesday 14:00–15:30 (synthetic)`.

### Query 2.3: Cryptography & Security Faculty
* **Audit Status:** `PASS`
* **Copy Query:**
  ```text
  Which professor teaches Cryptography and Information Security?
  ```
* **Verified KB Ground Truth:**
  **Dr. Sana Cipherwala** (`FAC-IT-007`, Associate Professor), Cabin: **`ROOM-DA-212`**, Email: `sana.cipherwala@campusmate-demo.example`, Specialization: Applied cryptography and PKI.

### Query 2.4: Faculty Consultation Procedure
* **Audit Status:** `BUG EXPOSED (Branch A Hijack)` — Keyword `"professor"` triggers Branch A and prints a single random faculty card (`Prof. Riya Queryani`) instead of `FAQ: How can I contact a faculty member?` & `Policy: Faculty Consultation Policy (Demo)`.
* **Copy Query:**
  ```text
  How can I schedule a consultation with a professor?
  ```
* **Verified KB Ground Truth:**
  Email the faculty member at least **24 hours before** their published consultation hours; meetings happen in the faculty cabin or **Discussion Room 1/2 (`FCL-IT-005`, `FCL-IT-006`)**.

---

## Section 3: Attendance, Detention & Grading Policies

### Query 3.1: Minimum Attendance Rule
* **Audit Status:** `HARDCODED SHORTCUT EXPOSED (Branch C)` — Matches KB numbers, but synthesized via static Branch C string instead of reading `POLICY-001`!
* **Copy Query:**
  ```text
  What is the 75% attendance rule for semester exams?
  ```
* **Verified KB Ground Truth:**
  `Policy: Attendance Policy (Demo)` (`POLICY-001`): **75% minimum in lectures** and **80% in laboratory sessions** (synthetic threshold), reviewed at mid-semester and before end-semester exams.

### Query 3.2: Below-75% Attendance Consequences
* **Audit Status:** `HARDCODED SHORTCUT EXPOSED (Branch C)`
* **Copy Query:**
  ```text
  What happens if my attendance drops below 75 percent?
  ```
* **Verified KB Ground Truth:**
  Students below threshold receive a **written advisory** from the course faculty and may be asked to meet the **Head of Department (`FAC-IT-001`)**.

### Query 3.3: Medical Leave Submission
* **Audit Status:** `BUG EXPOSED (Branch C Overwrite)` — Retrieval finds `FAQ: Where do I submit medical absence documents?`, **but Branch C ignores it** and outputs generic attendance text!
* **Copy Query:**
  ```text
  What is the procedure for submitting medical leaves?
  ```
* **Verified KB Ground Truth:**
  Report medical or institutional-duty absences to the **Department Office & Student Help Desk (`FCL-IT-010`)** **within 7 days**.

### Query 3.4: University Grading Scale & Grade Points
* **Audit Status:** `FALSELY BLOCKED (Guardrail Bug)` — First query is rejected by `\bcalculate` in `_OUT_OF_SCOPE_RE` (`hybrid_engine.py#L61`), even though `GRADING-SCHEME-001` & `FAQ: What is the grading scale?` exist in the KB!
* **Copy Query (Reworded version works today; original exposes bug):**
  ```text
  How are SGPA and CGPA calculated under the evaluation policy?
  ```
  ```text
  What is the official university grading scale and grade point criteria?
  ```
* **Verified KB Ground Truth:**
  10-point grading scale: `90+` = `A+ (10)`, `80–89` = `A (9)`, `70–79` = `B+ (8)`, `60–69` = `B (7)`, `50–59` = `C+ (6)`, `40–49` = `C (5)`, `<40` = `F (0)`.

---

## Section 4: Academic Calendar, Exam Dates & Deadlines

### Query 4.1: Mid-Semester Exam Dates
* **Audit Status:** `PARTIAL / REGEX BUG` — Correctly finds `CAL-2026-27-006`, **but** Branch D regex parses Event ID into `2026-27-00 to 2026-09-07 to 2026-09-12`.
* **Copy Query:**
  ```text
  When are the mid semester examinations scheduled?
  ```
* **Verified KB Ground Truth:**
  Odd semester: **`2026-09-07` to `2026-09-12`** (`CAL-2026-27-006`). Even semester: **`2027-02-22` to `2027-02-27`** (`CAL-2026-27-018`).

### Query 4.2: Capstone Topic Registration Deadline
* **Audit Status:** `PASS`
* **Copy Query:**
  ```text
  What is the deadline for capstone project topic registration?
  ```
* **Verified KB Ground Truth:**
  `Calendar: Capstone / major project topic registration deadline` (`CAL-2026-27-004`): **`2026-08-14`** (Odd semester 2026-2027).

### Query 4.3: Odd Semester Start & Autumn Break
* **Audit Status:** `PARTIAL / REGEX BUG` (Same `2026-27-00` ID regex leak)
* **Copy Query:**
  ```text
  When does odd semester teaching begin and when is autumn break?
  ```
* **Verified KB Ground Truth:**
  Odd semester teaching begins: **`2026-07-16`** (`CAL-2026-27-003`). Autumn break: **`2026-11-02` to `2026-11-14`** (`CAL-2026-27-008`).

---

## Section 5: Capstone Project & Industrial Training Guidelines

### Query 5.1: Capstone Team Size
* **Audit Status:** `PASS` (Hits `FAQ: How big can a capstone team be?`)
* **Copy Query:**
  ```text
  How many students can be in a capstone project team?
  ```
* **Verified KB Ground Truth:**
  Teams of **2 to 4 students**, registered with the Project Coordinator by the topic deadline (`CAL-2026-27-004`).

### Query 5.2: Capstone Evaluation & Rubric
* **Audit Status:** `PASS` (Hits `FAQ: How is my capstone project graded?`)
* **Copy Query:**
  ```text
  How is my capstone project graded and evaluated?
  ```
* **Verified KB Ground Truth:**
  Evaluated by a panel of at least two faculty plus the guide using the demo rubric: **problem definition 15%, design 20%, implementation 30%, testing 15%, report & presentation 20%**.

### Query 5.3: Industrial Training Requirements (Sem VIII)
* **Audit Status:** `BUG EXPOSED (Branch D Hijack)` — Matches `"start"` inside `"starting"` on line 514, replacing the retrieved FAQ text with a blank calendar header!
* **Copy Query:**
  ```text
  What do I need before starting Industrial Training in Semester VIII?
  ```
* **Verified KB Ground Truth:**
  `FAQ` & `POLICY-006`: Submit an **offer letter from the host organisation** to the Project Coordinator (`FAC-IT-020`) before Semester VIII starts, then send **fortnightly progress reports** (every second Friday); final report/presentation due `2027-04-30` (`CAL-2026-27-020`).

---

## Section 6: Department Labs & Campus Facilities

### Query 6.1: AI & Machine Learning Lab
* **Audit Status:** `PASS` (Hits `Lab: AI & Machine Learning Lab`)
* **Copy Query:**
  ```text
  Where is the AI & Machine Learning Lab and what hardware is available?
  ```
* **Verified KB Ground Truth:**
  `LAB-IT-001`, Room **`DA-301`**, Faculty In-charge: `FAC-IT-002` (Dr. Arjun Tensorkar), **36 workstations (32 GB RAM, RTX-class GPU)**, Python/Jupyter, PyTorch, scikit-learn, Shared model registry server.

### Query 6.2: Networks & Security Lab
* **Audit Status:** `PASS` (Hits `Lab: Networks & Security Lab`)
* **Copy Query:**
  ```text
  What equipment and tools are in the Networks & Security Lab?
  ```
* **Verified KB Ground Truth:**
  `LAB-IT-005`, Room **`DA-401`**, Faculty In-charge: `FAC-IT-007`, **32 workstations**, managed switches/routers, isolated penetration-testing network, packet capture appliances, wireless test bed; Mon–Fri `09:00–17:00`.

### Query 6.3: Database Systems Lab
* **Audit Status:** `PASS` (Replaced non-existent Library/WiFi query with verified indexed facility)
* **Copy Query:**
  ```text
  Where is the Database Systems Lab and what tools does it have?
  ```
* **Verified KB Ground Truth:**
  `LAB-IT-003`, Room **`DA-303`**, Faculty In-charge: `FAC-IT-001`, **40 workstations**, PostgreSQL, MySQL, MongoDB & Cassandra cluster, ER-modelling tools; Mon–Sat `09:00–17:30`.

### Query 6.4: Department Office Hours & Room
* **Audit Status:** `BUG EXPOSED (Branch A Hijack)` — Keyword `"office"` triggers Branch A (Faculty profile) instead of answering `FAQ: What are the Department Office hours?`.
* **Copy Query:**
  ```text
  What are the Department Office hours?
  ```
* **Verified KB Ground Truth:**
  `FAQ: What are the Department Office hours?`: **Monday–Friday `09:30–17:00` and Saturday `09:30–13:00`, Room `DA-201`**.

---

## Section 7: Out-of-KB University Queries (Abstention Tests)

> **Expected Behavior:** The knowledge base contains **zero records** for Stanford, Civil Engineering, Harvard CS50, Campus Library hours, or Campus WiFi credentials. Every query below **must abstain cleanly**.

### Query 7.1: Other University Syllabus (`PASS` — Correctly Abstains)
```text
What is the syllabus for aerospace engineering semester 8 at Stanford?
```

### Query 7.2: Unverified Department HOD (`PASS` — Correctly Abstains)
```text
Who is the HOD of Civil Engineering?
```

### Query 7.3: External Course Code Trap (`BUG EXPOSED` — Currently Leaks `2IT503`)
* **Current Reality:** Fails abstention because `"computer"` and `"science"` overlap corpus tokens in line 418 `any(...)`, falsely returning `2IT503 COMPUTER SYSTEM ARCHITECTURE`.
```text
What are the prerequisites for CS50 Introduction to Computer Science at Harvard?
```

### Query 7.4: Unindexed Campus Services Trap (`BUG EXPOSED` — Currently Leaks Lab Safety Policy)
* **Current Reality:** `library` and `wifi` exist in `CAMPUS_DOMAIN_TERMS` (`hybrid_engine.py#L42`) even though `knowledge_base.json` has `0` records for both! Currently returns `Policy: Laboratory Safety Policy (Demo)` instead of abstaining.
```text
What are the library hours and how do I connect to campus WiFi?
```

---

## Section 8: Strict Outsider Questions (Domain Guardrail Tests)

> **Expected Behavior:** Blocked **before retrieval** (`route = "out_of_scope"`, `answer_type = "abstained"`). All 5 verified passing on live test!

* **Query 8.1 (`PASS`):** `Who is the PM?`
* **Query 8.2 (`PASS`):** `What is 2 + 2?`
* **Query 8.3 (`PASS`):** `How to lose weight in 30 days?`
* **Query 8.4 (`PASS`):** `Write python code to reverse a string`
* **Query 8.5 (`PASS`):** `Tell me a funny joke`
