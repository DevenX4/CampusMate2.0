"""Generation providers, with no model and no network: the extractive provider is pure Python,
and the OpenAI-compatible provider talks to a fake server (httpx.MockTransport)."""

import json
import logging
import re

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.generation import runtime
from app.generation.base import ABSTAIN_MESSAGE, ContextBlock, GenerationError, GenerationRequest
from app.generation.extractive import (
    MAX_SENTENCE_CHARS, SYNTHETIC_NOTE, SYNTHETIC_PREFIX, ExtractiveProvider, sentences, terms,
)
from app.generation.openai_compatible import OpenAICompatibleProvider, display_url, is_local
from app.generation.prompt import SYSTEM_PROMPT, render_messages

CONTEXT = [
    ContextBlock(1, "structured", "official", "Syllabus p.15",
                 "2CEIT602 ARTIFICIAL INTELLIGENCE: 4 credits (theory 3 + practical/TW 1), 150 total marks."),
    ContextBlock(2, "document", "synthetic", "Faculty profiles",
                 "Dr. Example teaches ARTIFICIAL INTELLIGENCE. The department picnic is in March."),
    ContextBlock(3, "document", "official", "Academic calendar", "Term-end examinations start in May."),
]
SECRET_KEY = "sk-test-SECRET-123"


def ask(question: str, context=CONTEXT) -> str:
    return ExtractiveProvider().generate(GenerationRequest(question, context)).text


# --- extractive -------------------------------------------------------------------------------

def test_extractive_answer_is_copied_from_the_cited_sources():
    answer = ask("How many credits does ARTIFICIAL INTELLIGENCE carry, and who teaches it?")
    cited = re.findall(r"\s*(?:\(Synthetic[^)]*\) )?(.*?) \[(\d)\]\.", answer)
    assert [ref for _, ref in cited] == ["1", "2"]  # structured fact first, then the passage
    for text, ref in cited:
        assert text in CONTEXT[int(ref) - 1].text  # nothing that is not in its source
    assert "picnic" not in answer and "May" not in answer  # irrelevant sentences are left out


def test_sentences_do_not_split_after_titles_or_initials():
    assert sentences("Dr. A. Patel (Prof. of IT) heads it, e.g. the lab. Next one!\nLine two") == [
        "Dr. A. Patel (Prof. of IT) heads it, e.g. the lab.", "Next one!", "Line two"]


def test_a_wrapped_line_is_never_quoted_on_its_own():
    # Half of a wrapped sentence can say the opposite of the whole sentence.
    text = ("All dates are synthetic and are not\nan actual Ganpat University schedule.\nOdd semester 2026-2027\n"
            "source_type: synthetic\n2CEIT601 THEORY OF COMPUTATION (4 cr)")
    assert sentences(text) == ["All dates are synthetic and are not an actual Ganpat University schedule.",
                               "Odd semester 2026-2027", "source_type: synthetic", "2CEIT601 THEORY OF COMPUTATION (4 cr)"]


def test_graph_facts_are_quoted_clause_by_clause_and_questions_never():
    graph = ContextBlock(1, "graph", "official", "Knowledge graph",
                         "AI (Course COURSE-X, official). credits: 4. Relationships: practicals_in: LAB-1 (AI Lab) "
                         "[synthetic]; taught_by: FAC-1 (Dr. Rao) [synthetic]")
    faq = ContextBlock(2, "document", "synthetic", "FAQ", "Where are the AI practicals held?")
    answer = ask("Where are the practicals of AI held?", [graph, faq])
    # The course is official, the lab is not: the quoted clause carries the synthetic label, and
    # its subject, so it cannot be read as a fact about another course.
    assert answer == f"{SYNTHETIC_PREFIX} AI: practicals_in: LAB-1 (AI Lab) [synthetic] [1]. {SYNTHETIC_NOTE}"


def test_a_neighbour_s_relationship_names_its_own_subject():
    # Found in the UI: asked for the AI lab, the answer quoted "practicals_in: LAB-IT-004" from the
    # graph item of another course (a neighbour), as if it were the AI lab.
    other = ContextBlock(2, "graph", "official", "Knowledge graph",
                         "2CEIT402 ALGORITHMS (Course COURSE-2CEIT402, official). Relationships: practicals_in: LAB-4 [synthetic]")
    assert "2CEIT402 ALGORITHMS: practicals_in: LAB-4" in ask("Which lab hosts the practicals?", [other])


def test_matching_normalises_numerals_and_plurals():
    assert terms("official electives in Semester VII, facilities, credits") >= {"elective", "semester", "7", "facility", "credit"}
    semester = ContextBlock(1, "structured", "official", "Syllabus", "B.Tech IT Semester VII: ELECTIVE-V, choose one of: A, B.")
    assert ask("What are the official electives in semester 7?", [semester]).endswith("[1].")


def test_extractive_labels_synthetic_evidence():
    assert f"{SYNTHETIC_PREFIX} Dr. Example teaches ARTIFICIAL INTELLIGENCE [2]." in ask("Who teaches ARTIFICIAL INTELLIGENCE?")


@pytest.mark.parametrize("question,context", [
    ("Who teaches ARTIFICIAL INTELLIGENCE?", []),                    # no evidence at all
    ("What is the hostel curfew time?", CONTEXT),                      # evidence about something else
])
def test_extractive_abstains(question, context):
    assert ask(question, context) == ABSTAIN_MESSAGE


def test_extractive_keeps_structured_facts_whole_and_is_deterministic():
    course_list = "; ".join(f"2CEIT6{i:02d} COURSE NUMBER {i} (4 cr)" for i in range(30))
    context = [ContextBlock(1, "structured", "official", "Syllabus", f"B.Tech IT Semester VI courses: {course_list}")]
    assert len(context[0].text) > MAX_SENTENCE_CHARS
    answer = ask("Which courses are in Semester VI?", context)
    assert course_list in answer and answer == ask("Which courses are in Semester VI?", context)


def test_after_a_structured_fact_a_passage_is_used_only_for_another_part_of_the_question():
    context = [
        ContextBlock(1, "structured", "official", "Syllabus p.15", "B.Tech IT Semester VI courses: 2CEIT602 ARTIFICIAL INTELLIGENCE (4 cr)."),
        ContextBlock(2, "document", "synthetic", "Catalogue", "Semester VI course table also in B.Tech IT syllabus."),
        ContextBlock(3, "document", "synthetic", "Labs", "Semester VI practicals of B.Tech IT are held in the AI lab."),
    ]
    assert ask("Which courses are in Semester VI of B.Tech IT?", context) == \
        "B.Tech IT Semester VI courses: 2CEIT602 ARTIFICIAL INTELLIGENCE (4 cr) [1]."
    both = ask("Which courses are in Semester VI of B.Tech IT, and where are its practicals held?", context)
    assert "[1]." in both and f"{SYNTHETIC_PREFIX} Semester VI practicals of B.Tech IT are held in the AI lab [3]." in both


# --- prompt -------------------------------------------------------------------------------------

def test_prompt_carries_rules_trust_labels_and_question():
    system, user = render_messages(GenerationRequest("Who teaches AI?", CONTEXT))
    assert system == {"role": "system", "content": SYSTEM_PROMPT} and ABSTAIN_MESSAGE in SYSTEM_PROMPT
    assert "[1] (official; Syllabus p.15)" in user["content"]
    assert "[2] (SYNTHETIC demo data; Faculty profiles)" in user["content"]
    assert user["content"].endswith("Question: Who teaches AI?")


# --- OpenAI-compatible server ------------------------------------------------------------------

def fake_server(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def completion(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": content}}],
                                     "usage": {"prompt_tokens": 321, "completion_tokens": 12}})


def test_openai_compatible_request_and_response():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(url=str(request.url), auth=request.headers.get("authorization"), body=json.loads(request.content))
        return completion("<think>the user wants credits</think>\nIt carries 4 credits [1].")

    provider = OpenAICompatibleProvider("https://llm.example/v1", "some-model", SECRET_KEY, transport=fake_server(handler))
    result = provider.generate(GenerationRequest("Credits of AI?", CONTEXT, max_tokens=50, temperature=0.0))
    assert seen["url"] == "https://llm.example/v1/chat/completions"
    assert seen["auth"] == f"Bearer {SECRET_KEY}"
    assert seen["body"] == {"model": "some-model", "messages": render_messages(GenerationRequest("Credits of AI?", CONTEXT)),
                            "temperature": 0.0, "max_tokens": 50, "stream": False}
    assert result.text == "It carries 4 credits [1]."  # the reasoning block is not part of the answer
    assert (result.provider, result.model, result.prompt_tokens, result.completion_tokens) == (
        "openai_compatible", "some-model", 321, 12)


def test_local_server_gets_no_authorization_header():
    headers = []
    provider = OpenAICompatibleProvider("http://127.0.0.1:11434/v1", "m", transport=fake_server(
        lambda request: headers.append(request.headers.get("authorization")) or completion("ok")))
    provider.generate(GenerationRequest("q", CONTEXT))
    assert headers == [None]


@pytest.mark.parametrize("handler,message", [
    (lambda r: httpx.Response(500, text="model crashed"), "HTTP 500: model crashed"),
    (lambda r: httpx.Response(200, json={"choices": []}), "unexpected response"),
    (lambda r: httpx.Response(200, text="<html>proxy</html>"), "did not return JSON"),
    (lambda r: (_ for _ in ()).throw(httpx.ConnectError("refused")), "is the model server running?"),
    (lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("slow")), "within the timeout"),
])
def test_server_failures_become_generation_errors_without_the_key(handler, message):
    provider = OpenAICompatibleProvider("https://user:pw@llm.example/v1", "m", SECRET_KEY, transport=fake_server(handler))
    with pytest.raises(GenerationError, match=re.escape(message)) as error:
        provider.generate(GenerationRequest("q", CONTEXT))
    assert SECRET_KEY not in str(error.value) and "pw@" not in str(error.value)


def test_check_confirms_the_model_is_served():
    models = fake_server(lambda r: httpx.Response(200, json={"data": [{"id": "qwen-small"}, {"id": "other"}]}))
    assert "qwen-small" in OpenAICompatibleProvider("http://localhost:8080/v1", "qwen-small", transport=models).check()
    with pytest.raises(GenerationError, match="has: qwen-small, other"):
        OpenAICompatibleProvider("http://localhost:8080/v1", "missing", transport=models).check()


def test_url_helpers():
    assert is_local("http://127.0.0.1:11434/v1") and is_local("http://localhost:8080/v1")
    assert not is_local("https://api.example.com/v1")
    assert display_url("https://user:pw@api.example.com/v1") == "https://api.example.com/v1"


# --- configuration ------------------------------------------------------------------------------

def test_llm_provider_needs_a_model_and_the_error_shows_no_secrets():
    with pytest.raises(ValidationError, match="GENERATION_MODEL is required") as error:
        Settings(_env_file=None, db_password="db-SECRET-pw", generation_provider="openai_compatible",
                 generation_api_key=SECRET_KEY)
    assert "db-SECRET-pw" not in str(error.value) and SECRET_KEY not in str(error.value)


def test_provider_is_chosen_by_configuration(monkeypatch, caplog):
    def configured(**env):
        monkeypatch.setattr(runtime, "get_settings", lambda: Settings(_env_file=None, db_password="x", **env))
        runtime.get_generator.cache_clear()
        return runtime.get_generator()

    try:
        assert isinstance(configured(), ExtractiveProvider)  # the default: no model needed
        with caplog.at_level(logging.WARNING):
            remote = configured(generation_provider="openai_compatible", generation_model="m",
                                generation_base_url="https://api.example.com/v1", generation_api_key=SECRET_KEY)
        assert isinstance(remote, OpenAICompatibleProvider) and remote.model == "m"
        assert "not on this machine" in caplog.text and SECRET_KEY not in caplog.text

        # Test remote_open_model provider configuration
        remote_open = configured(generation_provider="remote_open_model", generation_model="meta-llama/Llama-3.1-8B-Instruct",
                                 generation_base_url="https://router.huggingface.co/hf-inference/v1", generation_api_key=SECRET_KEY)
        assert isinstance(remote_open, RemoteOpenModelProvider) and remote_open.model == "meta-llama/Llama-3.1-8B-Instruct"
    finally:
        runtime.get_generator.cache_clear()


def test_llm_env_aliases():
    settings = Settings(_env_file=None, db_password="x", LLM_PROVIDER="openrouter", LLM_MODEL="qwen/qwen-2.5-72b-instruct",
                        LLM_API_KEY="sk-or-123", LLM_BASE_URL="https://openrouter.ai/api/v1")
    assert settings.generation_provider == "openrouter"
    assert settings.generation_model == "qwen/qwen-2.5-72b-instruct"
    assert settings.generation_api_key.get_secret_value() == "sk-or-123"
    assert settings.generation_base_url == "https://openrouter.ai/api/v1"


# --- Remote open model provider tests --------------------------------------------------------

from app.generation.remote_open_model import RemoteOpenModelProvider


def test_remote_open_model_provider_success():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(url=str(request.url), auth=request.headers.get("authorization"),
                    referer=request.headers.get("http-referer"), body=json.loads(request.content))
        return completion("Artificial Intelligence is 2CEIT602 [1].")

    provider = RemoteOpenModelProvider(
        base_url="https://openrouter.ai/api/v1",
        model="Qwen/Qwen2.5-72B-Instruct",
        api_key=SECRET_KEY,
        provider_name="openrouter",
        transport=fake_server(handler),
    )

    result = provider.generate(GenerationRequest("What is AI?", CONTEXT))
    assert seen["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert seen["auth"] == f"Bearer {SECRET_KEY}"
    assert seen["referer"] == "https://github.com/campusmate"
    assert result.text == "Artificial Intelligence is 2CEIT602 [1]."
    assert result.provider == "openrouter"
    assert result.model == "Qwen/Qwen2.5-72B-Instruct"


@pytest.mark.parametrize("status_code,message_part", [
    (401, "Authentication failed"),
    (403, "Authentication failed"),
    (429, "Rate limit exceeded"),
    (503, "returned HTTP 503"),
])
def test_remote_open_model_provider_http_errors(status_code, message_part):
    handler = lambda r: httpx.Response(status_code, text="error details")
    provider = RemoteOpenModelProvider(
        base_url="https://router.huggingface.co/hf-inference/v1",
        model="Qwen/Qwen2.5-72B-Instruct",
        api_key=SECRET_KEY,
        provider_name="huggingface",
        transport=fake_server(handler),
    )
    with pytest.raises(GenerationError, match=message_part) as error:
        provider.generate(GenerationRequest("Q", CONTEXT))
    assert SECRET_KEY not in str(error.value)


def test_remote_open_model_provider_check_resilience():
    # Hosted endpoints might return 404 or 403 on GET /models, check should not raise
    handler = lambda r: httpx.Response(404, text="Not found")
    provider = RemoteOpenModelProvider(
        base_url="https://router.huggingface.co/hf-inference/v1",
        model="Qwen/Qwen2.5-72B-Instruct",
        api_key=SECRET_KEY,
        provider_name="huggingface",
        transport=fake_server(handler),
    )
    assert "huggingface: Qwen/Qwen2.5-72B-Instruct" in provider.check()

