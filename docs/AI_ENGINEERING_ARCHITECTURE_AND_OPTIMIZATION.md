# CampusMate 2.0 — Super-Senior AI Engineering Audit & Upgrade Blueprint
> **Role:** Principal / Staff AI Systems Engineer (Code & Benchmark Audit)  
> **Scope:** Full verification of `AI_workflow/backend/app/retrieval/hybrid_engine.py`, `AI_workflow/backend/app/api/routes/chat_bypass.py`, `AI_workflow/backend/app/`, `server/routes/chat.js`, `src/components/chat/ChatContainer.jsx`, and empirical results in `AI_workflow/evaluation/results/RETRIEVAL.md` & `ANSWERS.md`.

*(Synchronized mirror of [AI_ENGINEERING_ARCHITECTURE_AND_OPTIMIZATION.md](../AI_ENGINEERING_ARCHITECTURE_AND_OPTIMIZATION.md) — see workspace root copy for direct relative links.)*

---

## 1. The Unfiltered Verdict: Does It Actually Need Improvement?

**Short Answer: Yes — significantly.**

The previous version of this document rated the project **8.8 / 10**. Reviewing what **actually executes at runtime today** rather than what architecture diagrams imply shows that score was **optimistic by nearly 4 points**.

When we inspected live code, `.env` settings, unused modules, and executed all 22 in-scope queries + 12 edge-case/negative queries directly against `HybridRAGEngine.get_instance()`, we found a sharp gap between **Strong Retrieval Foundations** and **Incomplete/Rule-Driven Execution in Generation, Routing, Multi-Turn Memory, and Guardrails**.

### Reality vs. Target Engineering Scorecard

| Engineering Dimension | Previous Claimed Score | **Honest Runtime Score** | What Is Actually Happening Right Now | Realistic Post-Fix Score |
| :--- | :---: | :---: | :--- | :---: |
| **Hybrid Retrieval** (Dense + Sparse + RRF) | 9.2 / 10 | **7.2 / 10** | BGE-small + Chroma + BM25 + RRF (`k=60`) works genuinely and preserves code matching (`2CEIT601`, `LAB-IT-001`), **but** ignores `EntityResolver` / metadata routing (`RETRIEVAL.md` shows routed MRR@10 `0.710` vs hybrid `0.581`), uses uncalibrated `k1=1.5, b=0.75`, and doesn't embed uploaded PDFs into Chroma. | **9.3 / 10** |
| **Generative LLM Synthesis** | 8.5 / 10 | **2.5 / 10** | **No live LLM is running.** `backend/.env` sets `GENERATION_PROVIDER=extractive` and neither `GROQ_API_KEY` nor `OPENAI_API_KEY` is configured. `_generate_answer()` falls back 100% of the time to `if/elif/else` Python formatters (`Branches A–E`) with static templates. | **9.0 / 10** |
| **Grounding & Guardrails** | 9.5 / 10 | **5.5 / 10** | Good outsider block on politics/jokes/code (`Who is the PM?`, `2 + 2`), **but** `\bcalculate` falsely blocks valid SGPA/CGPA grading queries, `"CS50 at Harvard"` leaks `2IT503`, `"library"/"wifi"` bypasses to Lab Safety Policy, and `grounding.py` was weakened to log warnings instead of rejecting bad numbers. | **9.2 / 10** |
| **Multi-Turn Memory & Routing** | *(unrated)* | **2.0 / 10** | `ChatContainer.jsx` sends `history` and `model` (`direct`/`groq`/`n8n`), **but** `BypassRequest` in `chat_bypass.py` drops `history` completely and ignores `model`. Every follow-up query (*"What are its credits?"*) is stateless and blind. | **8.8 / 10** |
| **Ingestion & Knowledge Hygiene** | 8.8 / 10 | **4.5 / 10** | `seed_and_index.py` reads wrong JSON keys for `departments.json` (`name` instead of `department_name`), emitting blank `Department: ` chunks; runtime PDF upload via `_do_ingest()` only updates volatile RAM BM25 (never ChromaDB or disk JSON). | **8.7 / 10** |
| **OVERALL VERDICT** | ~~8.8 / 10~~ | **4.8 / 10 (Working Hybrid Prototype)** | **Genuine retrieval exists, but answer synthesis is currently template-bound and brittle.** Fixing P0–P1 unlocks a real **9.0+ / 10** production RAG system. | **9.0 / 10** |

---

## 2. Forensic Audit: 8 Real Flaws Verified Directly in Code & Execution

1. **Zero LLM Synthesis Executing (`GENERATION_PROVIDER=extractive`, Missing API Keys):** `if groq_key:` in `hybrid_engine.py#L361` is always `False`; `openai_key` (`L358`) is never used; `chat_bypass.py#L24-L60` ignores `model` and omits `history`; UI model selection in `ChatInput.jsx` is cosmetic (`server/routes/chat.js#L152` also aliases `n8n` to `hybrid_engine`).
2. **Hardcoded Rule-Based Templates Still Exist:** `hybrid_engine.py#L505-L511` (Branch C) ignores retrieved documents and emits a static 3-bullet attendance template (breaking *"What is the procedure for submitting medical leaves?"*); `ChatContainer.jsx#L302-L314` hardcodes wrong mock facts (`Distributed Computing`, `Room 204`) as client fail-safes.
3. **Heuristic Routing Collisions & Regex Bugs (`Branches A–D`):** `"starting"` triggers Calendar Branch D; `\d{4}-\d{2}-\d{2}` parses `CAL-2026-27-006` into `"2026-27-00"`; `"professor"` and `"office"` hijack Consultation & Office-Hours FAQs (`Branch A`); FAQ `"course"` overwrites `Course: 2CEIT601` (`Branch B`).
4. **Guardrail False Positives & False Negatives:** `\bcalculate` (`hybrid_engine.py#L61`) blocks SGPA/CGPA grading queries; `any(...)` at line `418` lets `"CS50 at Harvard"` leak `2IT503`; `"library"`/`"wifi"` in `CAMPUS_DOMAIN_TERMS` (`L42`) leak `Laboratory Safety Policy`; line `344` labels internal abstentions as `answer_type: "answered"`.
5. **Existing `app/` Modules Bypassed & `grounding.py` Weakened:** `OpenAICompatibleProvider`, `RemoteOpenModelProvider`, `prompt.py`, and `ExtractiveProvider` sit unused, while `grounding.py#L83-L107` downgraded validation errors from `report.issues` to `report.warnings` (`report.passed` always `True`).
6. **`RETRIEVAL.md` Proves Reranking on CPU Hurts Latency Without Significance — While `routed` Wins:** `hybrid_rerank_minilm12` added **`4,434.7 ms`** p50 latency with **`sign-test p = 0.701`** (not significant vs. hybrid), whereas **`routed`** jumped `Hit@1` from `0.442 -> 0.615` and `MRR@10` from `0.581 -> 0.710` at **`52.0 ms`** (`p = 0.022`). Meanwhile, **HyDE** risks poisoning exact course-code queries and **Redis semantic caching** is premature at 237 chunks and unsafe across stateful multi-turn pronouns.
7. **Ingestion Bugs:** `seed_and_index.py#L216-L226` drops `department_name`/`head_faculty_id`/`office_room_id`; `_do_ingest()` in `chat_bypass.py#L116-L123` never embeds uploaded PDFs into ChromaDB; `runPythonDirectQuery` (`chat.js#L114`) cold-starts FastEmbed per fallback call.
8. **Hyperparameter Drift & Eval Gap:** `hybrid_engine.py#L190` and `bm25.py#L25` still set `k1=1.5, b=0.75` instead of `k1=1.2, b=0.65`, and `ANSWERS.md` shows `extractive-v1` scored `0.143` answered rate on semantic queries (`C_semantic`).

---

## 3. Prioritized Engineering Roadmap (P0 -> P1 -> P2)

* **P0 (Critical):** Configure live Groq (`llama-3.3-70b-versatile`) / Ollama (`qwen2.5:7b`) via `RemoteOpenModelProvider` / `OpenAICompatibleProvider` + `prompt.py`; thread `history[-4:]` & `model` end-to-end; delete Branch C static bullets, Branches A–D hijackers (use `ExtractiveProvider` strictly on outage), and fake `ChatContainer.jsx` mock strings; fix `\bcalculate`, date regex `\b20\d{2}-...\b`, unindexed `"library"/"wifi"`, and `"answer_type": "abstained"`.
* **P1 (Precision & Grounding):** Add in-memory entity/metadata routing (`Course`/`Faculty`/`Lab` exact boosts + unknown named-entity abstention for traps like `CS50`/`Harvard`); restore strict `report.issues` enforcement in `grounding.py`; fix `departments.json` mapping in `seed_and_index.py`; chunk & upsert admin PDF uploads into persistent ChromaDB + `knowledge_base.json`; update BM25 to `k1=1.2, b=0.65`.
* **P2 (Fluency & Verification):** Add contextual coreference rewriting (`history > 0`, `T=0.0`); implement SSE token streaming (`/api/v1/chat/stream`) replacing fake frontend `setTimeout` steps; automate regression checks using `app.evaluation` metrics (`Hit@5 >= 0.85`, `0%` unanswerable leak rate) + `Top Vector < 0.70` / entity gate calibrated against `RETRIEVAL.md` (`0.7006` unanswerable vs `0.7079` answerable vector scores).
