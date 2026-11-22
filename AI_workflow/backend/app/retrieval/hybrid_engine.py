"""Production Hybrid RAG Engine for CampusMate AI.
Combines:
  1. Contextual Coreference Rewriter (resolved over bounded conversation history[-4:])
  2. Strict Two-Gate Domain & Unknown-Entity Guardrail (regex + corpus/code coverage + dense gate)
  3. Lightweight Entity & Metadata Router + Hybrid Retrieval (BGE-small ChromaDB + BM25 k1=1.2, b=0.65)
  4. Reciprocal Rank Fusion (RRF, k=60)
  5. Real LLM Synthesis via OpenAI-Compatible / Remote Open Model (T=0.15, top_p=0.90)
     with deterministic Extractive Evidence Assembler fallback (zero hardcoded templates)
  6. Strict Grounding Validation (app.chat.grounding.validate)
"""

import hashlib
import json
import logging
import math
import os
import re
import time
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from app.chat.grounding import validate as validate_grounding
from app.generation.base import ContextBlock, GenerationError, GenerationRequest
from app.generation.extractive import ExtractiveProvider, _term as _extractive_stem
from app.generation.openai_compatible import OpenAICompatibleProvider
from app.generation.remote_open_model import RemoteOpenModelProvider

logger = logging.getLogger("campusmate.hybrid")

# Configuration paths - AI_workflow is parents[3]
AI_WORKFLOW_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = AI_WORKFLOW_DIR / "storage"
MODEL_CACHE_DIR = AI_WORKFLOW_DIR / "model_cache"
KB_PATH = STORAGE_DIR / "knowledge_base.json"
CHROMA_PATH = STORAGE_DIR / "chroma"
KB_HASH_PATH = STORAGE_DIR / "chroma_kb.sha256"

# Read backend .env / repo .env into a local lookup dict without mutating os.environ
def _read_env_defaults() -> Dict[str, str]:
    values: Dict[str, str] = {}
    for env_path in (BACKEND_DIR / ".env", AI_WORKFLOW_DIR / ".env"):
        if not env_path.exists():
            continue
        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                key = k.strip()
                val = v.strip().strip('"').strip("'")
                if key and key not in values:
                    values[key] = val
        except Exception as exc:
            logger.debug("Could not parse %s: %s", env_path, exc)
    return values

_ENV_DEFAULTS = _read_env_defaults()


def _get_setting(key: str, default: str = "") -> str:
    return os.environ.get(key) or _ENV_DEFAULTS.get(key) or default

# Indexed University & Academic Campus Domain terms (strictly aligned with corpus coverage)
CAMPUS_DOMAIN_TERMS = frozenset([
    "course", "courses", "syllabus", "subject", "subjects", "credit", "credits", "unit", "units",
    "curriculum", "prerequisite", "prerequisites", "elective", "electives", "semester", "sem",
    "btech", "mtech", "engineering", "it", "ict",
    "theory", "practical", "lab", "laboratory", "labs", "laboratories", "tutorial", "hours", "marks",
    "grade", "grades", "grading", "sgpa", "cgpa", "evaluation", "exam", "exams", "examination",
    "examinations", "midsem", "endsem", "viva", "rubric", "remedial",
    "faculty", "teacher", "professor", "prof", "hod", "head", "coordinator", "mentor", "cabin",
    "office", "email", "contact", "consultation", "department", "desk", "helpdesk", "discussion",
    "attendance", "policy", "policies", "rule", "rules", "regulation", "regulations", "75", "80",
    "absent", "absence", "leave", "leaves", "medical", "duty", "advisory", "detain", "detention",
    "eligibility", "eligible", "malpractice", "seminar", "equipment", "workstations",
    "internship", "training", "industrial", "project", "capstone", "guidelines", "deadline",
    "deadlines", "submission", "schedule", "scheduled", "timetable", "calendar", "break", "autumn",
    "orientation", "registration", "ganpat", "guni", "uvpce", "campus", "university", "college",
    "student", "portal", "notice", "notices", "event", "programme", "program", "facility",
    "meera", "datavala", "arjun", "tensorkar", "sana", "cipherwala",
])

# Out-of-scope non-campus detector (arithmetic/calculus blocked, valid academic SGPA/CGPA allowed)
_OUT_OF_SCOPE_RE = re.compile(
    r"\b(who is (the )?(pm|prime minister|president|cm|chief minister|governor|monarch|king|queen))\b|"
    r"\b(capital of|currency of|population of|weather in|who is narendra modi|who won the)\b|"
    r"\b(cricket|football|ipl|fifa|world cup|actor|actress|bollywood|hollywood|movie|cinema|songs|music)\b|"
    r"\b(recipe|recipes|cook|cooking|baking|restaurant|pizza|burger|food|dish|cake)\b|"
    r"\b(joke|jokes|funny|sing a song|write a poem|riddle|story|tell me a joke)\b|"
    r"\b(write a python|write python code|write c\+\+|write code|program in|solve this math|integral of|derivative of)\b|"
    r"\b(bitcoin|cryptocurrency|stock market|share price|crypto|forex|investing)\b|"
    r"\b(photosynthesis|quantum mechanics|speed of light|solar system|planets|mars|moon|astronomy)\b|"
    r"\b(lose weight|weight loss|body weight|diet|fitness|calories|workout|exercise|gym|bodybuilding)\b|"
    r"\b(hack|hacking|crack password|steal|bypass|phishing|ransomware)\b|"
    # Arithmetic only: "2026-27" is an academic year and "what is 75% attendance" is a campus question.
    r"(\b\d+\s*[\+\*\/]\s*\d+\b|\b\d+\s+-\s+\d+\b|\bwhat is \d+(?:\.\d+)?\s*(?:[\+\-\*\/x]|plus|minus|times|divided)|"
    r"\bcalculate \d+\b|\bsolve (?:for|this equation|the equation)\b)",
    re.IGNORECASE,
)

# The knowledge base only holds the IT department's head of department.
_HOD_QUERY_RE = re.compile(r"\b(hod|head of (?:the )?(?:\w+\s+){0,3}department|head of)\b", re.IGNORECASE)
_OTHER_DEPARTMENT_RE = re.compile(
    r"\b(computer engineering|computer science|cse?|mechanical|electrical|electronics|civil|chemical|"
    r"biomedical|automobile|aerospace|ece|eee|mba|pharmacy|commerce)\b",
    re.IGNORECASE,
)
_FOLLOW_UP_RE = re.compile(r"^\s*(and|also|what about|how about)\b", re.IGNORECASE)
_CAMPUS_LIFE_RE = re.compile(
    r"\b(hostels?|fees?|tuition|placements?|scholarships?|admissions?|vice[- ]chancellor|chancellor|dean|"
    r"principal|registrar|canteen|library|transport|bus)\b",
    re.IGNORECASE,
)

# Topics a question can name that need their own records. They stop being refused as soon as
# the word appears in the knowledge base, so adding real data unlocks them automatically.
_UNCOVERED_TOPICS = frozenset(
    "phone whatsapp fee fees tuition hostel hostels placement placements scholarship scholarships "
    "admission admissions admitted library wifi bus transport canteen cafeteria dean chancellor "
    "registrar principal naac nirf accreditation ranking salary passport passing actual "
    "aerospace civil mechanical chemical biomedical automobile mba pharmacy commerce".split()
)
_REAL_INFO_RE = re.compile(
    r"\b(?:real|actual)\s+(?:phone|mobile|room|head|hod|email|contact)\b|"
    r"\bpersonal\s+(?:mobile|phone|number|email)\b",
    re.IGNORECASE,
)
_TEACH_RE = re.compile(
    r"\b(?:who|which\s+(?:faculty|professor|teacher|instructor))\b.*\b(?:teach(?:es)?|taught)\b",
    re.IGNORECASE,
)
_ACADEMIC_YEAR_RE = re.compile(r"\b(20\d\d)\s*[-/]\s*(?:20)?(\d\d)\b")
_QUERY_ALIASES = {
    "AI": "artificial intelligence",
    "ML": "machine learning",
    "NLP": "natural language processing",
    "DBMS": "database management systems",
    "OS": "operating systems",
    "IoT": "internet of things",
}


def _expand_aliases(question: str) -> str:
    """Spell out standard course abbreviations so both search methods can match them."""
    found = [full for short, full in _QUERY_ALIASES.items() if re.search(rf"\b{short}\b", question)]
    return f"{question} ({', '.join(found)})" if found else question

# Generic conversational / inquiry words excluded from unknown-entity checking
_GENERIC_QUERY_WORDS = frozenset(
    "what which who when where why how tell show list give explain describe know details info information "
    "about are can could would should does did has have had was were will been being this that these those "
    "there their they them his her she he its our your please need needed requires require required "
    "requirement requirements procedure process method way step steps guideline guidelines policy policies "
    "rule rules regulation regulations criterion criteria scale scheme calculate calculated calculation "
    "compute computed offered offer offering offerings available availability choose pick select option "
    "options breakdown overview summary topic topics unit units credit credits hour hours mark marks "
    "percent percentage schedule scheduled date dates timeline deadline deadlines starting start begin "
    "begins end ends drop drops below happen happens become becomes submit submitting submitted report "
    "reported apply applies applicable eligible eligibility contact email office cabin room location "
    "floor building teach teaches teaching faculty professor prof teacher head department hod college "
    "university campus student students equipment tools toolchains hardware software capacity opening "
    "hours big many team teams graded evaluated evaluation under official demo verify verified find "
    "any current latest recent upcoming new".split()
)

ABSTAIN_UNKNOWN_MESSAGE = (
    "I could not find verified documentation in the campus knowledge base for this query. "
    "As CampusMate AI, I strictly answer from verified university records to prevent misinformation. "
    "Please check with your department administrative office or the official student portal."
)
ABSTAIN_OUT_OF_SCOPE_MESSAGE = (
    "As CampusMate AI, I am strictly designed to assist with university academics, course syllabus, "
    "faculty details, attendance policies, exam schedules, and campus notices. "
    "I cannot assist with queries outside of university academics. Please ask a question related to your university curriculum or regulations."
)

CAPABILITIES_MESSAGE = (
    "I am **CampusMate AI**, your dedicated academic and campus assistant. Here is what I can do for you:\n\n"
    "• **Course Curriculum & Syllabus**: Look up course codes, credit schemes, theory/practical units, and reference textbooks.\n"
    "• **Faculty & Department Details**: Find faculty designations, cabin locations, contact emails, and HODs.\n"
    "• **Academic Policies & Regulations**: Verify the 75% attendance rule, condonation policies, detention criteria, and grading systems (SGPA/CGPA).\n"
    "• **Exams & Academic Schedules**: Check term dates, examination schedules, and academic deadlines.\n"
    "• **Campus Facilities & Labs**: Locate classrooms, specialized computing laboratories, and departmental facilities.\n\n"
    "How can I assist you with your academics today?"
)

_CAPABILITIES_RE = re.compile(
    r"^\s*(?:what\s+(?:can|do)\s+you\s+do(?:\s+for\s+me)?|how\s+can\s+you\s+help(?:\s+me)?|what\s+are\s+your\s+capabilities|who\s+are\s+you|what\s+do\s+you\s+know|help(?:\s+me)?)\s*[\!\.\?]*\s*$",
    re.IGNORECASE,
)

STOPWORDS = frozenset(
    "a an and are as at be by can do does for from has have how i in is it its me my of on or "
    "our the their there this to under was what when where which who whom why will with you your".split()
)
_TOKEN = re.compile(r"[a-z0-9]+")
_ISO_DATE = re.compile(r"\b(20\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))\b")
_EXPLICIT_CODE = re.compile(r"\b(?:\d[A-Z]{2,6}\d[A-Z0-9]*|[A-Z]{2,6}\d{2,4}[A-Z0-9]*)\b")
_EXPLICIT_ENTITY_ID = re.compile(
    r"\b(?:COURSE|FAC|LAB|FCL|POLICY|NOTICE|FAQ|CAL|PROG|SEM|DEPT|RA|ROOM|EGRP|GRADE)-[A-Z0-9]+(?:-[A-Z0-9]+)*\b"
)
# Case-sensitive on purpose: "IT" is the department, "it" is a pronoun.
_PRONOUN_RE = re.compile(r"\b(?:[Ii]t|[Ii]ts|[Tt]hey|[Tt]heir|[Tt]hem|[Hh]e|[Hh]is|[Ss]he|[Hh]er|[Tt]his|[Tt]hose|[Ss]ame)\b")
_ROMAN_TO_NUM = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8}
_SEMESTER_RE = re.compile(
    r"\bsem(?:ester)?\s*(\d{1,2}|viii|vii|vi|iv|v|iii|ii|i)\b|"
    r"\b(\d)(?:st|nd|rd|th)\s+sem(?:ester)?\b",
    re.IGNORECASE,
)


def tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]


def _normalize_stem(tok: str) -> str:
    """Light morphological normalization so valid inflections match indexed roots."""
    t = _extractive_stem(tok)
    for suffix, rep in (("ating", "ate"), ("ting", "t"), ("ing", ""), ("ied", "y"), ("ed", "")):
        if len(t) > len(suffix) + 3 and t.endswith(suffix):
            return t[:-len(suffix)] + rep
    return t


class HybridRAGEngine:
    _instance: Optional["HybridRAGEngine"] = None

    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.chunk_by_id: Dict[str, Dict[str, Any]] = {}
        self.chunk_ids: List[str] = []

        # BM25 index components (calibrated k1=1.2, b=0.65)
        self.postings: Dict[str, Dict[int, int]] = defaultdict(dict)
        self.lengths: List[int] = []
        self.avgdl: float = 0.0
        self.N: int = 0

        # Lightweight Entity, Metadata & Vocabulary Indexes
        self.title_tokens: set[str] = set()
        self.corpus_tokens: set[str] = set()
        self.corpus_norm_tokens: set[str] = set()
        self.known_codes: set[str] = set()
        self.course_by_code: Dict[str, Dict[str, Any]] = {}
        self.chunks_by_entity_id: Dict[str, Dict[str, Any]] = {}
        self.courses_by_semester: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.hod_chunks: List[Dict[str, Any]] = []
        self.faculty_surnames: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Chroma components
        self.embedder = None
        self.chroma_collection = None

        self.initialized = False
        self._initialize()

    @classmethod
    def get_instance(cls) -> "HybridRAGEngine":
        if cls._instance is None:
            cls._instance = HybridRAGEngine()
        return cls._instance

    def _initialize(self):
        try:
            logger.info("Initializing Hybrid RAG Engine...")
            if not KB_PATH.exists():
                logger.warning("Knowledge base not found at %s. Building default structured data...", KB_PATH)
                from app.ingestion.seed_and_index import build_knowledge_base
                build_knowledge_base()

            if KB_PATH.exists():
                with open(KB_PATH, "r", encoding="utf-8") as f:
                    self.chunks = json.load(f)
                self._rebuild_in_memory_indexes()

            self._init_chroma()
            self.initialized = True
            logger.info("Hybrid RAG Engine active with %d knowledge records.", len(self.chunks))
        except Exception as e:
            logger.error("Failed to initialize Hybrid RAG Engine: %s", e, exc_info=True)

    def _rebuild_in_memory_indexes(self):
        self.chunk_by_id = {c["id"]: c for c in self.chunks}
        self.chunk_ids = [c["id"] for c in self.chunks]
        self._build_bm25_index()
        self._build_entity_indexes()
        self.known_academic_years = {
            (y, s) for c in self.chunks for y, s in _ACADEMIC_YEAR_RE.findall(c.get("text", ""))
        }

    def _courses_named(self, question: str) -> List[str]:
        """Course codes named in a question, by code or by full course title."""
        codes = [c for c in _EXPLICIT_CODE.findall(question.upper()) if c in self.course_by_code]
        if codes:
            return codes
        q_tokens = set(tokenize(question))
        named = []
        for code, chunk in self.course_by_code.items():
            title_tokens = set(tokenize(chunk.get("title", "").split(" - ", 1)[-1])) - STOPWORDS
            if len(title_tokens) >= 2 and title_tokens <= q_tokens:
                named.append(code)
        return named

    def _faculty_for_course(self, code: str) -> List[Dict[str, Any]]:
        return [c for c in self.chunks if c.get("category") == "faculty" and f"COURSE-{code}" in c.get("text", "")]

    def _build_bm25_index(self):
        self.postings = defaultdict(dict)
        self.lengths = []
        self.title_tokens = set()
        self.corpus_tokens = set()
        self.corpus_norm_tokens = set()

        for idx, c in enumerate(self.chunks):
            title = c.get("title", "")
            text = c.get("text", "")
            self.title_tokens.update(
                t for t in tokenize(title) if not t.isdigit() and len(t) > 2
            )
            tokens = tokenize(f"{title} {text}")
            self.corpus_tokens.update(tokens)
            self.corpus_norm_tokens.update(_normalize_stem(t) for t in tokens)
            self.lengths.append(len(tokens))
            for t, count in Counter(tokens).items():
                self.postings[t][idx] = count
        self.avgdl = sum(self.lengths) / len(self.lengths) if self.lengths else 0.0
        self.N = len(self.chunks)

    def _build_entity_indexes(self):
        self.known_codes = set()
        self.course_by_code = {}
        self.chunks_by_entity_id = {}
        self.courses_by_semester = defaultdict(list)
        self.hod_chunks = []
        self.faculty_surnames = defaultdict(list)

        for c in self.chunks:
            meta = c.get("metadata") or {}
            title = c.get("title", "")
            text = c.get("text", "")
            doc_id = str(meta.get("doc_id") or "").upper()
            if doc_id:
                self.known_codes.add(doc_id)
                self.chunks_by_entity_id[doc_id] = c

            code = str(meta.get("code") or "").upper()
            if code:
                self.known_codes.add(code)
                self.known_codes.add(f"COURSE-{code}")
                self.course_by_code[code] = c

            for pat_match in _EXPLICIT_CODE.findall(f"{title} {text}"):
                self.known_codes.add(pat_match.upper())
            for eid_match in _EXPLICIT_ENTITY_ID.findall(f"{title} {text}"):
                self.known_codes.add(eid_match.upper())

            sem_str = meta.get("semester_ids") or meta.get("semester_id") or ""
            for s in str(sem_str).split(","):
                s = s.strip()
                if s:
                    self.courses_by_semester[s].append(c)

            if c.get("category") == "faculty":
                if meta.get("is_hod"):
                    self.hod_chunks.append(c)
                # Extract faculty name & surname for fast entity matching
                first_line = text.splitlines()[0] if text else ""
                m_name = re.search(r"Faculty Name:\s*(.+?)(?:\s*\(|$)", first_line)
                if m_name:
                    parts = [p.lower() for p in re.findall(r"[A-Za-z]+", m_name.group(1)) if len(p) > 2]
                    if parts:
                        self.faculty_surnames[parts[-1]].append(c)

    def _kb_sha256(self) -> str:
        if not KB_PATH.exists():
            return ""
        return hashlib.sha256(KB_PATH.read_bytes()).hexdigest()

    def _init_chroma(self):
        try:
            from fastembed import TextEmbedding
            import chromadb

            self.embedder = TextEmbedding(
                model_name="BAAI/bge-small-en-v1.5",
                cache_dir=str(MODEL_CACHE_DIR),
            )
            client = chromadb.PersistentClient(
                path=str(CHROMA_PATH),
                settings=chromadb.Settings(anonymized_telemetry=False),
            )
            self.chroma_collection = client.get_or_create_collection(
                name="campusmate_chunks",
                metadata={"hnsw:space": "cosine", "embedding_model": "BAAI/bge-small-en-v1.5", "dimension": 384},
            )

            current_hash = self._kb_sha256()
            stored_hash = KB_HASH_PATH.read_text(encoding="utf-8").strip() if KB_HASH_PATH.exists() else ""
            needs_rebuild = (
                self.chunks
                and (self.chroma_collection.count() == 0 or self.chroma_collection.count() != len(self.chunks) or current_hash != stored_hash)
            )
            if needs_rebuild:
                logger.info("Refreshing ChromaDB index (%d chunks)...", len(self.chunks))
                if self.chroma_collection.count() > 0:
                    client.delete_collection("campusmate_chunks")
                    self.chroma_collection = client.get_or_create_collection(
                        name="campusmate_chunks",
                        metadata={"hnsw:space": "cosine", "embedding_model": "BAAI/bge-small-en-v1.5", "dimension": 384},
                    )
                self._index_chunks_to_chroma(self.chunks)
                if current_hash:
                    KB_HASH_PATH.write_text(current_hash, encoding="utf-8")
        except Exception as e:
            logger.warning("Chroma initialization error (falling back to lexical BM25): %s", e)

    def _index_chunks_to_chroma(self, chunks_to_index: List[Dict[str, Any]]):
        if not self.embedder or not self.chroma_collection or not chunks_to_index:
            return
        texts = [f"{c['title']}\n{c['text']}" for c in chunks_to_index]
        vectors = [v.tolist() for v in self.embedder.embed(texts, batch_size=32)]

        batch_size = 100
        for i in range(0, len(chunks_to_index), batch_size):
            batch_chunks = chunks_to_index[i : i + batch_size]
            batch_vecs = vectors[i : i + batch_size]
            ids = [c["id"] for c in batch_chunks]
            docs = [c["text"] for c in batch_chunks]
            metas = []
            for c in batch_chunks:
                m = c.get("metadata", {}).copy()
                cleaned_m = {k: v if isinstance(v, (str, int, float, bool)) else str(v) for k, v in m.items()}
                cleaned_m["title"] = c.get("title", "")
                cleaned_m["category"] = c.get("category", "general")
                cleaned_m["source_type"] = c.get("source_type", "official")
                metas.append(cleaned_m)
            self.chroma_collection.upsert(ids=ids, embeddings=batch_vecs, documents=docs, metadatas=metas)
        logger.info("ChromaDB now holds %d indexed chunks.", self.chroma_collection.count())

    def add_chunks_and_persist(self, new_chunks: List[Dict[str, Any]]) -> int:
        """Persist newly ingested document chunks to memory, BM25, ChromaDB, and disk JSON."""
        if not new_chunks:
            return 0
        existing_ids = {c["id"] for c in self.chunks}
        deduped = [c for c in new_chunks if c["id"] not in existing_ids]
        # Replace if re-uploading same file id
        replace_ids = {c["id"] for c in new_chunks} - {c["id"] for c in deduped}
        if replace_ids:
            self.chunks = [c for c in self.chunks if c["id"] not in replace_ids]
        self.chunks.extend(new_chunks)
        self._rebuild_in_memory_indexes()
        try:
            self._index_chunks_to_chroma(new_chunks)
        except Exception as exc:
            logger.warning("Failed incremental ChromaDB upsert: %s", exc)
        try:
            KB_PATH.parent.mkdir(parents=True, exist_ok=True)
            KB_PATH.write_text(json.dumps(self.chunks, indent=2), encoding="utf-8")
            KB_HASH_PATH.write_text(self._kb_sha256(), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed persisting updated knowledge_base.json: %s", exc)
        return len(new_chunks)

    # ── Retrieval Primitives ──────────────────────────────────────────────────
    def bm25_search(self, query: str, k: int = 12) -> List[tuple[str, float]]:
        if not self.chunks or self.N == 0 or self.avgdl == 0:
            return []
        k1, b = 1.2, 0.65
        scores: Dict[int, float] = defaultdict(float)
        for t in sorted(set(tokenize(query))):
            n = len(self.postings.get(t, {}))
            if n == 0:
                continue
            idf = math.log(1 + (self.N - n + 0.5) / (n + 0.5))
            for idx, freq in self.postings[t].items():
                norm = k1 * (1 - b + b * self.lengths[idx] / self.avgdl)
                scores[idx] += idf * freq * (k1 + 1) / (freq + norm)
        ranked = sorted(scores.items(), key=lambda x: (-x[1], self.chunk_ids[x[0]]))[:k]
        return [(self.chunk_ids[idx], score) for idx, score in ranked]

    def vector_search(self, query: str, k: int = 12) -> List[tuple[str, float]]:
        if not self.chroma_collection or not self.embedder or self.chroma_collection.count() == 0:
            return []
        try:
            instruction = "Represent this sentence for searching relevant passages: "
            q_vec = next(iter(self.embedder.embed([instruction + query]))).tolist()
            res = self.chroma_collection.query(
                query_embeddings=[q_vec],
                n_results=min(k, self.chroma_collection.count()),
                include=["metadatas", "distances"],
            )
            ids = res.get("ids", [[]])[0]
            dists = res.get("distances", [[]])[0]
            return [(cid, 1.0 - float(dist)) for cid, dist in zip(ids, dists)]
        except Exception as e:
            logger.warning("Vector search failed: %s", e)
            return []

    def hybrid_search(self, query: str, k: int = 6) -> List[Dict[str, Any]]:
        bm25_hits = self.bm25_search(query, k=15)
        vector_hits = self.vector_search(query, k=15)

        rrf_k = 60
        fused: Dict[str, float] = defaultdict(float)
        details: Dict[str, Dict[str, Any]] = defaultdict(dict)

        for rank, (cid, score) in enumerate(bm25_hits, 1):
            fused[cid] += 1.0 / (rrf_k + rank)
            details[cid]["bm25_rank"] = rank
            details[cid]["bm25_score"] = round(score, 3)

        for rank, (cid, score) in enumerate(vector_hits, 1):
            fused[cid] += 1.0 / (rrf_k + rank)
            details[cid]["vector_rank"] = rank
            details[cid]["vector_score"] = round(score, 3)

        ranked = sorted(fused.items(), key=lambda x: -x[1])[:k]
        results = []
        for cid, rrf_score in ranked:
            if cid in self.chunk_by_id:
                results.append(self._format_hit(self.chunk_by_id[cid], round(rrf_score, 4), details[cid]))
        return results

    def _format_hit(self, chunk: Dict[str, Any], score: float, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "id": chunk["id"],
            "title": chunk.get("title", "Campus Document"),
            "category": chunk.get("category", "general"),
            "source_type": chunk.get("source_type", "official"),
            "metadata": chunk.get("metadata") or {},
            "score": score,
            "details": details or {},
            "text": chunk.get("text", ""),
        }

    def routed_hybrid_search(self, query: str, k: int = 6) -> tuple[List[Dict[str, Any]], str]:
        """Entity/metadata-aware hybrid retrieval matching RETRIEVAL.md's routed edge."""
        hybrid_hits = self.hybrid_search(query, k=max(k, 8))
        by_id = {h["id"]: h for h in hybrid_hits}
        boosted_ids: List[str] = []
        route = "hybrid_rag"
        q_lower = query.lower()

        # 1. Exact course codes & explicit entity IDs
        for code in _EXPLICIT_CODE.findall(query.upper()):
            if code in self.course_by_code:
                cid = self.course_by_code[code]["id"]
                boosted_ids.append(cid)
                route = "routed_entity"
        for eid in _EXPLICIT_ENTITY_ID.findall(query.upper()):
            if eid in self.chunks_by_entity_id:
                boosted_ids.append(self.chunks_by_entity_id[eid]["id"])
                route = "routed_entity"

        # 2. Faculty surname exact resolution
        for tok in tokenize(query):
            if tok in self.faculty_surnames:
                for fc in self.faculty_surnames[tok]:
                    boosted_ids.append(fc["id"])
                    route = "routed_entity"

        # 2b. HOD / Head of Department explicit resolution
        if re.search(r"\b(hod|head of (the )?department)\b", q_lower):
            hod_chunk = self.chunks_by_entity_id.get("FAC-IT-001")
            if hod_chunk:
                boosted_ids.append(hod_chunk["id"])
                route = "routed_entity"

        # 2c. Notice questions are answered from notices: best text matches first, then newest
        if re.search(r"\b(notices?|announcements?)\b", q_lower):
            matched = [h["id"] for h in hybrid_hits if h.get("category") == "notice"]
            newest = sorted(
                (c for c in self.chunks if c.get("category") == "notice"),
                key=lambda c: (
                    (c.get("metadata") or {}).get("status") == "active",
                    (c.get("metadata") or {}).get("date", ""),
                ),
                reverse=True,
            )
            wants_current = bool(re.search(r"\b(current|latest|active|recent|new)\b", q_lower))
            ordered_notices = (
                [c["id"] for c in newest] if wants_current
                else matched + [c["id"] for c in newest if c["id"] not in matched]
            )
            if ordered_notices:
                boosted_ids.extend(ordered_notices[:k])
                route = "routed_metadata"

        # 2d. "Who teaches X": the faculty records that list X answer it, not the course record
        if _TEACH_RE.search(query):
            for code in self._courses_named(query):
                for fc in self._faculty_for_course(code):
                    boosted_ids.insert(0, fc["id"])
                    route = "routed_entity"

        # 3. Semester / Elective enumeration lookup
        is_elective_query = bool(re.search(r"\belectives?\b", q_lower))
        is_course_list_query = bool(re.search(r"\b(courses?|subjects?|offered|choose)\b", q_lower))
        sem_matches = _SEMESTER_RE.findall(query)
        sem_nums: List[int] = []
        for g1, g2 in sem_matches:
            raw = (g1 or g2).lower()
            num = _ROMAN_TO_NUM.get(raw) or (int(raw) if raw.isdigit() else 0)
            if 1 <= num <= 8:
                sem_nums.append(num)

        target_sem_ids: List[str] = []
        if sem_nums:
            want_mtech = bool(re.search(r"\bm\.?\s?tech\b", q_lower))
            want_btech = bool(re.search(r"\bb\.?\s?tech\b", q_lower)) or not want_mtech
            for n in sem_nums:
                if want_btech:
                    target_sem_ids.append(f"SEM-BTECH-IT-{n:02d}")
                if want_mtech and n <= 4:
                    target_sem_ids.append(f"SEM-MTECH-IT-{n:02d}")

        if target_sem_ids and (is_elective_query or is_course_list_query) and not boosted_ids:
            # Prefer specific FAQ first if it directly answers semester courses, then attach elective records
            for sid in target_sem_ids:
                for c in self.courses_by_semester.get(sid, []):
                    ctype = (c.get("metadata") or {}).get("course_type", "")
                    if is_elective_query and ctype == "elective":
                        boosted_ids.append(c["id"])
                        route = "routed_metadata"
                    elif not is_elective_query and (c.get("category") == "curriculum"):
                        boosted_ids.append(c["id"])
                        route = "routed_metadata"

        # Assemble final ranked list without discarding high-scoring hybrid/FAQ hits
        ordered: List[Dict[str, Any]] = []
        seen: set[str] = set()

        # If query explicitly asks an exact code ("What is 2CEIT601..."), put exact course first
        for cid in boosted_ids:
            if cid not in seen and cid in self.chunk_by_id:
                existing = by_id.get(cid)
                if existing:
                    ordered.append(existing)
                else:
                    ordered.append(self._format_hit(self.chunk_by_id[cid], 0.032, {"routed_exact": True}))
                seen.add(cid)

        for h in hybrid_hits:
            if h["id"] not in seen:
                ordered.append(h)
                seen.add(h["id"])

        # An expired or replaced notice must not outrank a current record unless notices were asked for.
        if not re.search(r"\b(notices?|announcements?|revised)\b", q_lower):
            def is_stale(hit: Dict[str, Any]) -> bool:
                meta = hit.get("metadata") or self.chunk_by_id.get(hit["id"], {}).get("metadata") or {}
                return hit.get("category") == "notice" and meta.get("status") in ("expired", "superseded")
            ordered = [h for h in ordered if not is_stale(h)] + [h for h in ordered if is_stale(h)]

        limit = max(k, 9) if (is_elective_query and target_sem_ids) else k
        return ordered[:limit], route

    # ── Guardrails & Context Rewriting ────────────────────────────────────────
    def _is_valid_campus_query(self, query: str) -> bool:
        clean_q = query.strip()
        if _OUT_OF_SCOPE_RE.search(clean_q):
            return False

        # A campus topic with no records must get "not found", not "this is outside campus".
        if _CAMPUS_LIFE_RE.search(clean_q):
            return True

        if _CAPABILITIES_RE.match(clean_q):
            return True

        if re.match(
            r"^\s*(hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening|greetings|howdy)\s*[\!\.\?]*\s*$",
            clean_q,
            re.IGNORECASE,
        ):
            return True

        tokens = tokenize(clean_q)
        if not tokens or all(t.isdigit() for t in tokens):
            return False

        if any(t in CAMPUS_DOMAIN_TERMS for t in tokens):
            return True
        if any(_normalize_stem(t) in CAMPUS_DOMAIN_TERMS for t in tokens):
            return True

        title_toks = getattr(self, "title_tokens", set())
        if any(t in title_toks for t in tokens):
            return True

        # Allow explicit course codes / entity IDs through to Gate 2 so unknown-code traps abstain cleanly
        if _EXPLICIT_CODE.search(clean_q.upper()) or _EXPLICIT_ENTITY_ID.search(clean_q.upper()):
            return True

        return False

    def _detect_unknown_reference(self, question: str) -> Optional[str]:
        """Detect unknown external codes, IDs, or non-generic nouns absent from the KB."""
        if _HOD_QUERY_RE.search(question) and _OTHER_DEPARTMENT_RE.search(question):
            return "Head of a department that is not in the knowledge base"

        # Gate A: Uppercase course codes & entity IDs not in indexed catalog
        for code in _EXPLICIT_CODE.findall(question):
            cu = code.upper()
            if cu not in self.known_codes and f"COURSE-{cu}" not in self.known_codes:
                return f"Unknown code: {code}"

        for eid in _EXPLICIT_ENTITY_ID.findall(question):
            if eid.upper() not in self.known_codes:
                return f"Unknown entity ID: {eid}"

        if _REAL_INFO_RE.search(question):
            return "Asks for real personal or contact details"

        for year, suffix in _ACADEMIC_YEAR_RE.findall(question):
            if (year, suffix) not in self.known_academic_years:
                return f"Academic year not in the knowledge base: {year}-{suffix}"

        # A teaching question about a known course needs a faculty record that lists that course.
        if _TEACH_RE.search(question):
            courses = self._courses_named(question)
            if courses and not any(self._faculty_for_course(code) for code in courses):
                return "No faculty record lists this course"

        # Gate B: refuse only when the missing word names a subject. An ordinary word such as
        # "carry" or "want" being absent from the records says nothing about the answer.
        missing = {
            t for t in tokenize(question)
            if t not in _GENERIC_QUERY_WORDS
            and t not in CAMPUS_DOMAIN_TERMS
            and _normalize_stem(t) not in CAMPUS_DOMAIN_TERMS
            and not t.isdigit()
            and len(t) > 2
            and t not in self.corpus_tokens
            and _normalize_stem(t) not in self.corpus_norm_tokens
        }
        if topics := missing & _UNCOVERED_TOPICS:
            return f"Unindexed topic(s): {', '.join(sorted(topics)[:4])}"

        # A capitalised word after the first is a name (a subject, an institution). If the
        # records do not contain it, retrieval could only return something else.
        for word in re.findall(r"[A-Za-z][A-Za-z0-9&'-]*", question)[1:]:
            if word[0].isupper() and word not in _QUERY_ALIASES and set(tokenize(word)) & missing:
                return f"Unindexed name: {word}"

        return None

    def _rewrite_with_history(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]],
    ) -> tuple[str, List[Dict[str, str]]]:
        """Resolve pronouns/follow-ups using bounded conversation history[-4:] (max ~1,200 chars)."""
        if not history:
            return question, []

        bounded: List[Dict[str, str]] = []
        char_budget = 1200
        for turn in reversed(history[-6:]):
            role = turn.get("role", "user")
            content = (turn.get("content") or "").strip()
            if not content or role not in ("user", "assistant"):
                continue
            clipped = content[:450]
            if char_budget - len(clipped) < 0 and bounded:
                break
            bounded.append({"role": role, "content": clipped})
            char_budget -= len(clipped)
            if len(bounded) >= 4:
                break
        bounded.reverse()

        q_clean = question.strip()
        names_its_own_subject = bool(_EXPLICIT_CODE.search(q_clean.upper())) or any(
            t in self.faculty_surnames for t in tokenize(q_clean)
        )
        needs_resolution = not names_its_own_subject and bool(
            _PRONOUN_RE.search(q_clean) or _FOLLOW_UP_RE.search(q_clean)
        )
        if not needs_resolution or not bounded:
            return q_clean, bounded

        # Extract most recent entity (course code, entity ID, or faculty name) from newest history turn
        for turn in reversed(bounded):
            txt = turn["content"]
            codes = [c for c in _EXPLICIT_CODE.findall(txt.upper()) if c in self.course_by_code]
            if codes:
                code = codes[0]
                cname = self.course_by_code[code].get("title", code)
                return f"{q_clean} ({cname})", bounded
            eids = [e for e in _EXPLICIT_ENTITY_ID.findall(txt.upper()) if e in self.chunks_by_entity_id]
            if eids:
                chunk = self.chunks_by_entity_id[eids[0]]
                return f"{q_clean} ({chunk.get('title', eids[0])})", bounded
            for tok in tokenize(txt):
                if tok in self.faculty_surnames:
                    fc = self.faculty_surnames[tok][0]
                    return f"{q_clean} ({fc.get('title', tok)})", bounded

        return q_clean, bounded

    # ── Provider Resolution ───────────────────────────────────────────────────
    def _resolve_llm_provider(self, model_choice: Optional[str] = None):
        """Return an active OpenAI-compatible/Remote LLM provider if configured, else None."""
        choice = (model_choice or "").strip().lower()
        groq_key = _get_setting("GROQ_API_KEY").strip()
        openai_key = _get_setting("OPENAI_API_KEY").strip()
        gen_provider = _get_setting("GENERATION_PROVIDER", "extractive").strip().lower()
        gen_model = (_get_setting("GENERATION_MODEL") or _get_setting("LLM_MODEL")).strip()
        gen_key = (_get_setting("GENERATION_API_KEY") or _get_setting("LLM_API_KEY")).strip()
        gen_base = (_get_setting("GENERATION_BASE_URL") or _get_setting("LLM_BASE_URL")).strip()

        # "extractive" means no question or campus record ever leaves this machine.
        if gen_provider == "extractive":
            return None, None

        if choice == "groq":
            if groq_key:
                return RemoteOpenModelProvider(
                    base_url="https://api.groq.com/openai/v1",
                    model=_get_setting("GROQ_MODEL", "llama-3.3-70b-versatile"),
                    api_key=groq_key,
                    timeout=25.0,
                    provider_name="groq",
                ), None
            return None, "Extractive Grounded Fallback (GROQ_API_KEY not set)"

        if gen_provider in ("openai_compatible", "remote_open_model", "openrouter", "huggingface") and gen_model and gen_model != "extractive":
            base = gen_base or (
                "https://openrouter.ai/api/v1" if gen_provider == "openrouter"
                else "https://router.huggingface.co/hf-inference/v1" if gen_provider == "huggingface"
                else "http://127.0.0.1:11434/v1"
            )
            if gen_provider == "openai_compatible":
                return OpenAICompatibleProvider(base_url=base, model=gen_model, api_key=gen_key or None, timeout=30.0), None
            return RemoteOpenModelProvider(base_url=base, model=gen_model, api_key=gen_key or None, timeout=30.0, provider_name=gen_provider), None

        if groq_key:
            return RemoteOpenModelProvider(
                base_url="https://api.groq.com/openai/v1",
                model=_get_setting("GROQ_MODEL", "llama-3.3-70b-versatile"),
                api_key=groq_key,
                timeout=25.0,
                provider_name="groq",
            ), None

        if openai_key:
            return RemoteOpenModelProvider(
                base_url="https://api.openai.com/v1",
                model=_get_setting("OPENAI_MODEL", "gpt-4o-mini"),
                api_key=openai_key,
                timeout=25.0,
                provider_name="openai",
            ), None

        return None, None

    # ── Evidence Block Construction & Deterministic Grounded Assembler ─────────
    @staticmethod
    def _to_context_blocks(hits: List[Dict[str, Any]]) -> List[ContextBlock]:
        blocks: List[ContextBlock] = []
        for idx, h in enumerate(hits, 1):
            cat = h.get("category", "general")
            kind = "structured" if cat in ("curriculum", "academic", "department") else "document"
            blocks.append(
                ContextBlock(
                    ref=idx,
                    kind=kind,
                    source_type=h.get("source_type", "official"),
                    label=h.get("title", f"Source {idx}"),
                    text=h.get("text", ""),
                )
            )
        return blocks

    @staticmethod
    def _assemble_grounded_extractive(question: str, hits: List[Dict[str, Any]], blocks: List[ContextBlock]) -> Dict[str, Any]:
        """Purely evidence-driven deterministic answer assembly (ZERO hardcoded answers, ZERO ignored hits)."""
        primary = hits[0]
        q_lower = question.lower()

        # Check multi-item calendar schedule (only when top hit is ACTUALLY a calendar record!)
        if primary.get("category") == "calendar" and any(h.get("category") == "calendar" for h in hits):
            cal_hits = [(idx, h) for idx, h in enumerate(hits, 1) if h.get("category") == "calendar"][:4]
            lines = ["### Academic calendar and exam dates [1]", ""]
            for idx, h in cal_hits:
                dates = _ISO_DATE.findall(h["text"])
                term_m = re.search(r"Term\s*/\s*Academic Year:\s*(.+)", h["text"])
                term_str = f" ({term_m.group(1).strip()})" if term_m else ""
                if len(dates) >= 2 and dates[0] != dates[1]:
                    date_str = f": **{dates[0]}** to **{dates[1]}**"
                elif dates:
                    date_str = f": **{dates[0]}**"
                else:
                    date_str = ""
                lines.append(f"- **{h['title']}**{term_str}{date_str} [{idx}]")
            answer = "\n".join(lines)
        # Check multi-course / elective enumeration (e.g. Semester 6 electives)
        elif (
            len(hits) > 1
            and sum(1 for h in hits if (h.get("metadata") or {}).get("course_type") == "elective") >= 2
            and re.search(r"\belectives?\b", q_lower)
        ):
            lines = []
            # If an authoritative FAQ summary exists in hits, lead with it
            faq_pairs = [(idx, h) for idx, h in enumerate(hits, 1) if h.get("category") == "faq"]
            if faq_pairs:
                f_idx, faq_h = faq_pairs[0]
                ans_part = faq_h["text"].split("Answer:", 1)[1].strip() if "Answer:" in faq_h["text"] else faq_h["text"].strip()
                lines.append(f"### {faq_h['title']} [{f_idx}]")
                lines.append("")
                lines.append(f"{ans_part} [{f_idx}]")
                lines.append("")
            lines.append("**Indexed elective offerings:**")
            for idx, h in enumerate(hits, 1):
                if (h.get("metadata") or {}).get("course_type") == "elective":
                    lines.append(f"- **{h['title']}** [{idx}]")
            answer = "\n".join(lines)
        # Authoritative FAQ hit ranked #1
        elif primary.get("category") == "faq":
            text = primary["text"]
            ans_part = text.split("Answer:", 1)[1].strip() if "Answer:" in text else text.strip()
            lines = [f"### {primary['title']} [1]", "", f"{ans_part} [1]"]
            if len(hits) > 1 and hits[1].get("score", 0) >= 0.015:
                ref_lines = [l.strip() for l in hits[1]["text"].splitlines() if l.strip() and not l.strip().startswith("Frequently Asked Question:")]
                snippet = " | ".join(ref_lines[:3])
                if snippet:
                    lines.append("")
                    lines.append(f"**Supporting reference: {hits[1]['title']} [2]:**")
                    lines.append(f"- {snippet} [2]")
            answer = "\n".join(lines)
        # Structured / Policy / Course / Faculty / Lab / Facility / Department / Grading / Uploaded Doc
        else:
            lines = [f"### {primary['title']} [1]", ""]
            raw_lines = [l.strip() for l in primary["text"].splitlines() if l.strip()]
            for ln in raw_lines[:14]:
                if ln.startswith("- "):
                    lines.append(f"{ln} [1]")
                elif ":" in ln and not re.match(r"^\d+\.", ln):
                    k_part, v_part = ln.split(":", 1)
                    if v_part.strip():
                        lines.append(f"- **{k_part.strip()}**: {v_part.strip()} [1]")
                    else:
                        lines.append(f"**{k_part.strip()}:**")
                else:
                    lines.append(f"- {ln} [1]")
            if len(hits) > 1 and hits[1].get("score", 0) >= 0.015:
                sec_lines = [l.strip() for l in hits[1]["text"].splitlines() if l.strip()][:3]
                if sec_lines:
                    lines.append("")
                    lines.append(f"**Related campus record: {hits[1]['title']} [2]:**")
                    for sl in sec_lines:
                        lines.append(f"- {sl} [2]")
            answer = "\n".join(lines)

        # Ensure synthetic disclosure matches repo policy when synthetic records are cited
        report = validate_grounding(answer, blocks)
        final_text = report.answer if report.passed else answer
        if not final_text:
            final_text = ExtractiveProvider().generate(GenerationRequest(question=question, context=blocks)).text

        # Every answer that uses a sample record says so, whatever the record's title looks like.
        used_refs = {int(n) for n in re.findall(r"\[(\d+)\]", final_text)}
        demo_refs = [b.ref for b in blocks if b.ref in used_refs and (b.source_type == "synthetic" or "[synthetic]" in b.text)]
        if demo_refs and "not official GUNI information" not in final_text:
            marks = ", ".join(f"[{r}]" for r in demo_refs)
            final_text = (
                f"{final_text.rstrip()}\n\n**Demo data:** {marks} comes from sample records, not official GUNI "
                "information. Please confirm with your department office."
            )

        sources_out = [
            {"title": h["title"], "content": h["text"][:380], "score": h["score"], "cited": True}
            for h in hits
        ]
        return {
            "answer": final_text.strip(),
            "sources": sources_out,
            "grounding": {
                "passed": report.passed,
                "issues": report.issues,
                "warnings": report.warnings,
                "contains_demo_data": bool(demo_refs),
            },
        }

    def _generate_answer(
        self,
        question: str,
        hits: List[Dict[str, Any]],
        history: List[Dict[str, str]],
        model_choice: Optional[str] = None,
    ) -> Dict[str, Any]:
        blocks = self._to_context_blocks(hits)
        provider, fallback_label = self._resolve_llm_provider(model_choice)

        if provider is not None:
            try:
                req = GenerationRequest(
                    question=question,
                    context=blocks,
                    max_tokens=650,
                    temperature=0.15,
                    top_p=0.90,
                    history=history,
                )
                gen = provider.generate(req)
                report = validate_grounding(gen.text, blocks)

                if report.abstained:
                    return {
                        "answer": ABSTAIN_UNKNOWN_MESSAGE,
                        "answer_type": "abstained",
                        "provider": f"{provider.name} ({provider.model})",
                        "sources": [],
                        "grounding": {"passed": True, "issues": [], "warnings": report.warnings},
                    }

                if report.passed:
                    cited_set = set(report.cited)
                    sources_out = [
                        {
                            "title": h["title"],
                            "content": h["text"][:380],
                            "score": h["score"],
                            "cited": (idx in cited_set) if cited_set else True,
                        }
                        for idx, h in enumerate(hits, 1)
                    ]
                    return {
                        "answer": report.answer.strip(),
                        "answer_type": "answered",
                        "provider": f"{provider.name} ({provider.model})",
                        "sources": sources_out,
                        "grounding": {"passed": True, "issues": [], "warnings": report.warnings},
                    }

                logger.warning("LLM answer rejected by grounding check (%s); falling back to extractive evidence.", report.issues)
                fallback_label = f"Extractive Grounded Fallback (rejected LLM: {', '.join(report.issues[:2])})"
            except GenerationError as exc:
                logger.warning("LLM provider failed (%s); falling back to extractive evidence.", exc)
                fallback_label = f"Extractive Grounded Fallback ({provider.name} unavailable)"
            except Exception as exc:
                logger.warning("Unexpected LLM generation error (%s); falling back.", exc)

        assembled = self._assemble_grounded_extractive(question, hits, blocks)
        return {
            "answer": assembled["answer"],
            "answer_type": "answered",
            "provider": fallback_label or "CampusMate Extractive Evidence Synthesizer",
            "sources": assembled["sources"],
            "grounding": assembled["grounding"],
        }

    # ── Public Execution Entrypoints ──────────────────────────────────────────
    def answer_query(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        started = time.perf_counter()
        clean_q = question.strip()
        conv_uuid = conversation_id or str(uuid.uuid4())

        # 0. Contextual Co-reference Rewriting over bounded history[-4:]
        rewritten_q, bounded_history = self._rewrite_with_history(clean_q, history)
        rewritten_q = _expand_aliases(rewritten_q)

        # 1. Greeting check (fast natural response)
        greeting_match = re.match(
            r"^\s*(hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening|greetings|howdy)\s*[\!\.\?]*\s*$",
            clean_q,
            re.IGNORECASE,
        )
        if greeting_match:
            import datetime
            hour = datetime.datetime.now().hour
            tod = "Good morning!" if hour < 12 else ("Good afternoon!" if hour < 17 else "Good evening!")
            return {
                "answer": f"{tod} I am **CampusMate AI**, your intelligent campus companion. How can I assist you with your courses, faculty, exam schedules, or university policies today?",
                "sources": [],
                "route": "greeting",
                "answer_type": "answered",
                "query_id": str(uuid.uuid4()),
                "conversation_id": conv_uuid,
                "provider": "CampusMate Natural Dialogue",
                "timings_ms": {"total": round((time.perf_counter() - started) * 1000)},
            }

        # 1b. Capabilities inquiry check (what can you do for me, etc.)
        if _CAPABILITIES_RE.match(clean_q):
            return {
                "answer": CAPABILITIES_MESSAGE,
                "sources": [],
                "route": "capabilities",
                "answer_type": "answered",
                "query_id": str(uuid.uuid4()),
                "conversation_id": conv_uuid,
                "provider": "CampusMate Natural Dialogue",
                "timings_ms": {"total": round((time.perf_counter() - started) * 1000)},
            }

        # 2. Scope Guardrail: Refuse out-of-scope non-campus outsider questions
        if not self._is_valid_campus_query(rewritten_q):
            return {
                "answer": ABSTAIN_OUT_OF_SCOPE_MESSAGE,
                "sources": [],
                "route": "out_of_scope",
                "answer_type": "abstained",
                "query_id": str(uuid.uuid4()),
                "conversation_id": conv_uuid,
                "provider": "CampusMate Domain Guardrail",
                "timings_ms": {"total": round((time.perf_counter() - started) * 1000)},
            }

        # 3. Unknown Entity / Unindexed Topic Guardrail (CS50, Harvard, Library/WiFi, etc.)
        unknown_reason = self._detect_unknown_reference(rewritten_q)
        if unknown_reason:
            logger.info("Abstaining early before generation: %s", unknown_reason)
            return {
                "answer": ABSTAIN_UNKNOWN_MESSAGE,
                "sources": [],
                "route": "unknown_abstain",
                "answer_type": "abstained",
                "query_id": str(uuid.uuid4()),
                "conversation_id": conv_uuid,
                "provider": "CampusMate Grounding Guardrail",
                "timings_ms": {"total": round((time.perf_counter() - started) * 1000)},
            }

        # 4. Routed Hybrid RAG retrieval
        t_retrieval_start = time.perf_counter()
        hits, route_name = self.routed_hybrid_search(rewritten_q, k=6)
        retrieval_ms = round((time.perf_counter() - t_retrieval_start) * 1000)

        max_vector = max((h.get("details", {}).get("vector_score", 0) for h in hits), default=0)
        max_bm25 = max((h.get("details", {}).get("bm25_score", 0) for h in hits), default=0)
        has_exact_boost = any(h.get("details", {}).get("routed_exact") for h in hits)

        if not hits or (not has_exact_boost and max_bm25 == 0 and max_vector < 0.70):
            return {
                "answer": ABSTAIN_UNKNOWN_MESSAGE,
                "sources": [],
                "route": "unknown_abstain",
                "answer_type": "abstained",
                "query_id": str(uuid.uuid4()),
                "conversation_id": conv_uuid,
                "provider": "CampusMate Grounding Guardrail",
                "timings_ms": {"retrieval": retrieval_ms, "total": round((time.perf_counter() - started) * 1000)},
            }

        # 5. Synthesis & Strict Grounding Verification
        t_gen_start = time.perf_counter()
        gen_result = self._generate_answer(rewritten_q, hits, bounded_history, model_choice=model)
        generation_ms = round((time.perf_counter() - t_gen_start) * 1000)
        total_ms = round((time.perf_counter() - started) * 1000)

        is_abstained = gen_result.get("answer_type") == "abstained"
        return {
            "answer": gen_result["answer"],
            "sources": gen_result["sources"],
            "route": "unknown_abstain" if is_abstained else route_name,
            "answer_type": "abstained" if is_abstained else "answered",
            "query_id": str(uuid.uuid4()),
            "conversation_id": conv_uuid,
            "provider": gen_result.get("provider", "CampusMate Hybrid Engine"),
            "grounding": gen_result.get("grounding"),
            "timings_ms": {
                "retrieval": retrieval_ms,
                "generation": generation_ms,
                "total": total_ms,
            },
        }

    def answer_query_stream(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Yield real pipeline stage events, incremental tokens, and final verified payload for SSE."""
        started = time.perf_counter()
        clean_q = question.strip()
        conv_uuid = conversation_id or str(uuid.uuid4())

        yield {"event": "stage", "data": {"step": 0, "label": "Resolving query context & guardrails..."}}
        rewritten_q, bounded_history = self._rewrite_with_history(clean_q, history)
        rewritten_q = _expand_aliases(rewritten_q)

        greeting_match = re.match(
            r"^\s*(hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening|greetings|howdy)\s*[\!\.\?]*\s*$",
            clean_q,
            re.IGNORECASE,
        )
        if greeting_match or _CAPABILITIES_RE.match(clean_q) or not self._is_valid_campus_query(rewritten_q) or self._detect_unknown_reference(rewritten_q):
            res = self.answer_query(question, conversation_id=conv_uuid, history=history, model=model)
            yield {"event": "token", "data": {"delta": res["answer"]}}
            yield {"event": "done", "data": res}
            return

        yield {"event": "stage", "data": {"step": 1, "label": "Scanning BM25 sparse index & Chroma vector store..."}}
        t_ret = time.perf_counter()
        hits, route_name = self.routed_hybrid_search(rewritten_q, k=6)
        retrieval_ms = round((time.perf_counter() - t_ret) * 1000)

        yield {"event": "stage", "data": {"step": 2, "label": f"Fusing evidence via RRF k=60 ({retrieval_ms}ms)..."}}
        max_vector = max((h.get("details", {}).get("vector_score", 0) for h in hits), default=0)
        max_bm25 = max((h.get("details", {}).get("bm25_score", 0) for h in hits), default=0)
        has_exact_boost = any(h.get("details", {}).get("routed_exact") for h in hits)

        if not hits or (not has_exact_boost and max_bm25 == 0 and max_vector < 0.70):
            res = {
                "answer": ABSTAIN_UNKNOWN_MESSAGE,
                "sources": [],
                "route": "unknown_abstain",
                "answer_type": "abstained",
                "query_id": str(uuid.uuid4()),
                "conversation_id": conv_uuid,
                "provider": "CampusMate Grounding Guardrail",
                "timings_ms": {"retrieval": retrieval_ms, "total": round((time.perf_counter() - started) * 1000)},
            }
            yield {"event": "token", "data": {"delta": res["answer"]}}
            yield {"event": "done", "data": res}
            return

        yield {"event": "stage", "data": {"step": 3, "label": "Synthesizing grounded answer with citations..."}}
        blocks = self._to_context_blocks(hits)
        provider, fallback_label = self._resolve_llm_provider(model)
        t_gen = time.perf_counter()

        # Stream real tokens if live LLM provider is configured
        if provider is not None and hasattr(provider, "generate_stream"):
            req = GenerationRequest(
                question=rewritten_q,
                context=blocks,
                max_tokens=650,
                temperature=0.15,
                top_p=0.90,
                history=bounded_history,
            )
            streamed_parts: List[str] = []
            try:
                for delta in provider.generate_stream(req):
                    streamed_parts.append(delta)
                    yield {"event": "token", "data": {"delta": delta}}
                raw_text = "".join(streamed_parts).strip()
                report = validate_grounding(raw_text, blocks)
                generation_ms = round((time.perf_counter() - t_gen) * 1000)
                total_ms = round((time.perf_counter() - started) * 1000)

                if report.abstained:
                    final_payload = {
                        "answer": ABSTAIN_UNKNOWN_MESSAGE,
                        "sources": [],
                        "route": "unknown_abstain",
                        "answer_type": "abstained",
                        "query_id": str(uuid.uuid4()),
                        "conversation_id": conv_uuid,
                        "provider": f"{provider.name} ({provider.model})",
                        "grounding": {"passed": True, "issues": [], "warnings": report.warnings},
                        "timings_ms": {"retrieval": retrieval_ms, "generation": generation_ms, "total": total_ms},
                    }
                    yield {"event": "done", "data": final_payload}
                    return

                if report.passed:
                    cited_set = set(report.cited)
                    sources_out = [
                        {"title": h["title"], "content": h["text"][:380], "score": h["score"], "cited": (idx in cited_set) if cited_set else True}
                        for idx, h in enumerate(hits, 1)
                    ]
                    final_payload = {
                        "answer": report.answer.strip(),
                        "sources": sources_out,
                        "route": route_name,
                        "answer_type": "answered",
                        "query_id": str(uuid.uuid4()),
                        "conversation_id": conv_uuid,
                        "provider": f"{provider.name} ({provider.model})",
                        "grounding": {"passed": True, "issues": [], "warnings": report.warnings},
                        "timings_ms": {"retrieval": retrieval_ms, "generation": generation_ms, "total": total_ms},
                    }
                    yield {"event": "done", "data": final_payload}
                    return
                fallback_label = f"Extractive Grounded Fallback (rejected LLM: {', '.join(report.issues[:2])})"
            except GenerationError as exc:
                logger.warning("Streaming LLM failed (%s); falling back cleanly.", exc)
                fallback_label = f"Extractive Grounded Fallback ({provider.name} unavailable)"

        # Grounded Extractive fallback / non-LLM execution
        assembled = self._assemble_grounded_extractive(rewritten_q, hits, blocks)
        generation_ms = round((time.perf_counter() - t_gen) * 1000)
        total_ms = round((time.perf_counter() - started) * 1000)
        answer_text = assembled["answer"]

        # Stream line/word tokens smoothly
        for chunk in re.findall(r"\S+\s*", answer_text):
            yield {"event": "token", "data": {"delta": chunk}}

        final_payload = {
            "answer": answer_text,
            "sources": assembled["sources"],
            "route": route_name,
            "answer_type": "answered",
            "query_id": str(uuid.uuid4()),
            "conversation_id": conv_uuid,
            "provider": fallback_label or "CampusMate Extractive Evidence Synthesizer",
            "grounding": assembled["grounding"],
            "timings_ms": {"retrieval": retrieval_ms, "generation": generation_ms, "total": total_ms},
        }
        yield {"event": "done", "data": final_payload}
