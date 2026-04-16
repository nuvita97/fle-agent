#!/usr/bin/env python3
"""
Weekly batch generator — generates 35 exercises (5 levels × 7 topics) and INSERTs
each as a new row in the Supabase `exercises` table.

Unlike prebuild_cache.py (which upserts/overwrites), this script appends a fresh
batch every week so the exercise pool grows over time.

Usage:
    # Production: generate all 35 via Claude API
    python tools/weekly_generate.py

    # Test mode: load a local JSON file, no API calls
    python tools/weekly_generate.py --test-file .tmp/lesson_b2_education.json \
        --level B2 --topic education_apprentissage
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Combinations
# ---------------------------------------------------------------------------
LEVELS = ["A1", "A2", "B1", "B2", "C1"]
TOPICS = [
    "vie_quotidienne",
    "sante_bien_etre",
    "education_apprentissage",
    "voyages_tourisme",
    "environnement_ecologie",
    "technologie_numerique",
    "culture_histoire",
]

TOTAL = len(LEVELS) * len(TOPICS)  # 35

TOPIC_DISPLAY = {
    "vie_quotidienne":         "Vie quotidienne & Société",
    "sante_bien_etre":         "Santé & Bien-être",
    "education_apprentissage": "Éducation & Apprentissage",
    "voyages_tourisme":        "Voyages & Mobilité",
    "environnement_ecologie":  "Environnement & Écologie",
    "technologie_numerique":   "Technologies & Numérique",
    "culture_histoire":        "Culture, Arts & Histoire",
}


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def get_supabase():
    from supabase import create_client  # noqa: PLC0415
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)
    return create_client(url, key)


def insert_exercise(sb, result: dict, created_at: str) -> None:
    """INSERT a new row — intentionally does not upsert so history accumulates."""
    row = {
        "level":        result["level"],
        "topic":        result["topic"],
        "text":         result["text"],
        "word_count":   result.get("word_count", 0),
        "questions":    result.get("questions", []),
        "vocabulary":   result.get("vocabulary", []),
        "open_question": result.get("open_question", ""),
        "created_at":   created_at,
    }
    sb.table("exercises").insert(row).execute()


# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------

def run(cmd: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def generate_one(level: str, topic: str, python: str) -> dict | str:
    """Call generate_lesson.py for one combination. Returns dict or error string."""
    code, out, err = run([python, "tools/generate_lesson.py", "--level", level, "--topic", topic])
    if code != 0:
        try:
            msg = json.loads(out).get("message", out or err)
        except Exception:
            msg = out or err or "unknown error"
        return f"generate_lesson failed: {msg}"

    try:
        result = json.loads(out)
    except json.JSONDecodeError:
        return f"generate_lesson returned invalid JSON: {out[:120]}"

    return {**result, "level": level, "topic": topic}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Weekly batch: generate & insert 35 exercises.")
    parser.add_argument("--test-file", metavar="PATH",
                        help="Load a local JSON file instead of calling the API (for testing).")
    parser.add_argument("--level", metavar="LEVEL",
                        help="Used with --test-file: the level to assign (e.g. B2).")
    parser.add_argument("--topic", metavar="TOPIC",
                        help="Used with --test-file: the topic to assign (e.g. education_apprentissage).")
    args = parser.parse_args()

    # Validate test-file args
    if args.test_file and not (args.level and args.topic):
        print("ERROR: --test-file requires both --level and --topic.")
        sys.exit(1)
    if args.test_file and args.level and args.level not in LEVELS:
        print(f"ERROR: --level must be one of {LEVELS}")
        sys.exit(1)
    if args.test_file and args.topic and args.topic not in TOPICS:
        print(f"ERROR: --topic must be one of {list(TOPICS)}")
        sys.exit(1)

    sb = get_supabase()
    python = sys.executable
    created_at = datetime.now(timezone(timedelta(hours=2))).isoformat()

    print(f"\n{'='*60}")

    # ------------------------------------------------------------------
    # TEST MODE: single JSON file, no API calls
    # ------------------------------------------------------------------
    if args.test_file:
        print(f"  FLE-agent — Weekly generate (TEST MODE)")
        print(f"  File : {args.test_file}")
        print(f"  Level: {args.level}  Topic: {TOPIC_DISPLAY.get(args.topic, args.topic)}")
        print(f"{'='*60}\n")

        try:
            with open(args.test_file, encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"ERROR reading test file: {e}")
            sys.exit(1)

        result = {**data, "level": args.level, "topic": args.topic}

        try:
            insert_exercise(sb, result, created_at)
            word_count = result.get("word_count", "?")
            n_q = len(result.get("questions", []))
            n_v = len(result.get("vocabulary", []))
            print(f"  ✅  Inserted  {args.level} / {TOPIC_DISPLAY.get(args.topic, args.topic)}")
            print(f"      {word_count} words · {n_q} questions · {n_v} vocab items")
            print(f"      created_at: {created_at}")
        except Exception as e:
            print(f"  ❌  Supabase insert failed: {e}")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"  Done.  1 row inserted.")
        print(f"{'='*60}\n")
        return

    # ------------------------------------------------------------------
    # PRODUCTION MODE: generate all 35 combinations
    # ------------------------------------------------------------------
    print(f"  FLE-agent — Weekly generate ({TOTAL} combinations)")
    print(f"  Batch timestamp: {created_at}")
    print(f"{'='*60}\n")

    succeeded, failed = 0, []
    n = 0

    for level in LEVELS:
        for topic in TOPICS:
            n += 1
            label = f"[{n:02d}/{TOTAL}] {level} / {TOPIC_DISPLAY[topic]}"
            print(f"  ⏳  {label}  …", end="", flush=True)

            result = generate_one(level, topic, python)

            if isinstance(result, str):
                print(f"\n      ❌  {result}")
                failed.append((level, topic, result))
            else:
                try:
                    insert_exercise(sb, result, created_at)
                    word_count = result.get("word_count", "?")
                    n_q = len(result.get("questions", []))
                    n_v = len(result.get("vocabulary", []))
                    print(f"  ✅  {word_count} words · {n_q} Q · {n_v} vocab")
                    succeeded += 1
                except Exception as e:
                    print(f"\n      ❌  Supabase insert failed: {e}")
                    failed.append((level, topic, str(e)))

            # Brief pause between API calls to avoid rate limits
            time.sleep(1.5)

    print(f"\n{'='*60}")
    print(f"  Done.  ✅ {succeeded} inserted  ❌ {len(failed)} failed")
    if failed:
        print("\n  Failed combinations:")
        for lvl, tpc, reason in failed:
            print(f"    • {lvl} / {TOPIC_DISPLAY[tpc]}: {reason}")
    print(f"{'='*60}\n")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
