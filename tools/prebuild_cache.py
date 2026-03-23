#!/usr/bin/env python3
"""
Pre-build exercises for all 35 level × topic combinations and store in Supabase.

Runs search_french_text.py + generate_exercises.py for every combination
and upserts each result into the Supabase `exercises` table.

Already-built combinations are skipped (resumable). Use --force to rebuild all.

Usage:
    python tools/prebuild_cache.py            # build all missing
    python tools/prebuild_cache.py --force    # rebuild everything
"""

import argparse
import json
import os
import subprocess
import sys
import time

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

TOTAL = len(LEVELS) * len(TOPICS)   # 35

TOPIC_DISPLAY = {
    "vie_quotidienne":        "Vie quotidienne & Société",
    "sante_bien_etre":        "Santé & Bien-être",
    "education_apprentissage": "Éducation & Apprentissage",
    "voyages_tourisme":       "Voyages & Mobilité",
    "environnement_ecologie": "Environnement & Écologie",
    "technologie_numerique":  "Technologies & Numérique",
    "culture_histoire":       "Culture, Arts & Histoire",
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


def exercise_exists(sb, level: str, topic: str) -> bool:
    rows = (
        sb.table("exercises")
        .select("id")
        .eq("level", level)
        .eq("topic", topic)
        .limit(1)
        .execute()
        .data
    )
    return bool(rows)


def upsert_exercise(sb, result: dict) -> None:
    row = {
        "level":         result["level"],
        "topic":         result["topic"],
        "text":          result["text"],
        "word_count":    result.get("word_count", 0),
        "questions":     result.get("questions", []),
        "vocabulary":    result.get("vocabulary", []),
        "open_question": result.get("open_question", ""),
    }
    level, topic = result["level"], result["topic"]
    existing = (
        sb.table("exercises")
        .select("id")
        .eq("level", level)
        .eq("topic", topic)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        sb.table("exercises").update(row).eq("id", existing[0]["id"]).execute()
    else:
        sb.table("exercises").insert(row).execute()


# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------

def run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def build_one(level: str, topic: str, python: str) -> dict | str:
    """
    Run generate_lesson for one combination.
    Returns the merged dict on success, or an error string on failure.
    """
    code, out = run([python, "tools/generate_lesson.py", "--level", level, "--topic", topic])
    if code != 0:
        try:
            err = json.loads(out).get("message", out)
        except Exception:
            err = out or "unknown error"
        return f"generate_lesson failed: {err}"

    try:
        result = json.loads(out)
    except json.JSONDecodeError:
        return f"generate_lesson returned invalid JSON: {out[:120]}"

    return {**result, "level": level, "topic": topic}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Pre-build exercises for all 35 combinations.")
    parser.add_argument("--force", action="store_true", help="Rebuild even if already exists in Supabase")
    parser.add_argument("--level", choices=["A1", "A2", "B1", "B2", "C1"], help="Run for a single level only")
    parser.add_argument("--topic", choices=TOPICS, help="Run for a single topic only")
    args = parser.parse_args()

    levels = [args.level] if args.level else LEVELS
    topics = [args.topic] if args.topic else TOPICS

    sb = get_supabase()
    python = sys.executable

    succeeded, skipped, failed = 0, 0, []
    n = 0
    total = len(levels) * len(topics)

    print(f"\n{'='*60}")
    print(f"  FLE-agent — Pre-building exercises ({total} combinations)")
    print(f"{'='*60}\n")

    for level in levels:
        for topic in topics:
            n += 1
            label = f"[{n:02d}/{total}] {level} / {TOPIC_DISPLAY[topic]}"

            if not args.force and exercise_exists(sb, level, topic):
                print(f"  ⏭  {label}  →  already in Supabase, skipping")
                skipped += 1
                continue

            print(f"  ⏳  {label}  …", end="", flush=True)
            result = build_one(level, topic, python)

            if isinstance(result, str):
                print(f"\n      ❌  {result}")
                failed.append((level, topic, result))
            else:
                try:
                    upsert_exercise(sb, result)
                    word_count = result.get("word_count", "?")
                    n_q = len(result.get("questions", []))
                    n_v = len(result.get("vocabulary", []))
                    print(f"  ✅  {word_count} words · {n_q} questions · {n_v} vocab items")
                    succeeded += 1
                except Exception as e:
                    print(f"\n      ❌  Supabase upsert failed: {e}")
                    failed.append((level, topic, str(e)))

            # Brief pause between combinations to avoid hammering APIs
            time.sleep(1.5)

    print(f"\n{'='*60}")
    print(f"  Done.  ✅ {succeeded} built  ⏭ {skipped} skipped  ❌ {len(failed)} failed")
    if failed:
        print("\n  Failed combinations:")
        for level, topic, reason in failed:
            print(f"    • {level} / {TOPIC_DISPLAY[topic]}: {reason}")
    print(f"{'='*60}\n")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
