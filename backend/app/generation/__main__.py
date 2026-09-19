"""Generation command line.

    python -m app.generation check            is the configured provider usable?
    python -m app.generation check --probe    ... and does it follow the rules, how fast?

The probe uses a fixed, obviously fictitious context (course "PRB-101"), not university data:
it tests instruction following (cite, label demo data, abstain), not knowledge.
"""

import argparse
import sys

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.generation.base import ABSTAIN_MESSAGE, ContextBlock, GenerationError, GenerationRequest
from app.generation.runtime import get_generator

PROBE_CONTEXT = [
    ContextBlock(1, "structured", "official", "probe source A",
                 "PRB-101 Probe Engineering carries 4 credits (theory 3 + practical 1) and 150 total marks."),
    ContextBlock(2, "document", "synthetic", "probe source B",
                 "PRB-101 practicals are held in Lab 0 on the ground floor."),
]
PROBES = [
    ("How many credits does PRB-101 carry, and where are its practicals held?",
     {"states 4 credits": lambda a: "4 credits" in a, "cites [1]": lambda a: "[1]" in a,
      "cites [2]": lambda a: "[2]" in a, "labels the demo data": lambda a: "demo" in a.lower() or "synthetic" in a.lower()}),
    ("Who is the head of the PRB department?",
     {"abstains with the exact sentence": lambda a: a.strip() == ABSTAIN_MESSAGE}),
]


def check(probe: bool) -> int:
    settings = get_settings()
    provider = get_generator()
    try:
        print(provider.check())
    except GenerationError as exc:
        print(f"NOT USABLE: {exc}")
        return 1
    if not probe:
        return 0
    failures = 0
    for run in ("first call (may include loading the model)", "second call"):
        print(f"--- {run}")
        for question, checks in PROBES:
            result = provider.generate(GenerationRequest(question, PROBE_CONTEXT, settings.generation_max_tokens,
                                                         settings.generation_temperature))
            speed = (f", {result.completion_tokens / (result.latency_ms / 1000):.1f} tokens/s"
                     if result.completion_tokens and result.latency_ms else "")
            print(f"Q: {question}")
            print(f"A: {result.text}")
            print(f"   {result.latency_ms} ms, prompt {result.prompt_tokens} / answer {result.completion_tokens} tokens{speed}")
            for name, passed in checks.items():
                ok = passed(result.text)
                failures += not ok
                print(f"   [{'PASS' if ok else 'FAIL'}] {name}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.generation")
    commands = parser.add_subparsers(dest="command", required=True)
    check_parser = commands.add_parser("check", help="verify the configured generation provider")
    check_parser.add_argument("--probe", action="store_true", help="also run two fixed test questions")
    args = parser.parse_args(argv)
    setup_logging("WARNING")
    return check(args.probe)


if __name__ == "__main__":
    sys.exit(main())
