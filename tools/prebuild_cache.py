#!/usr/bin/env python3
"""
Pre-build cache for all 25 level × topic combinations.

Runs search_french_text.py + generate_exercises.py for every combination
and saves each result to .tmp/cache/{level}_{topic}.json.

Already-cached combinations are skipped (resumable).

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

# ---------------------------------------------------------------------------
# Combinations
# ---------------------------------------------------------------------------
LEVELS = ["A1", "A2", "B1", "B2", "C1"]
TOPICS = [
    "vie_quotidienne",
    "voyages_tourisme",
    "environnement_ecologie",
    "technologie_numerique",
    "culture_histoire",
]

CACHE_DIR = ".tmp/cache"
TOTAL = len(LEVELS) * len(TOPICS)   # 25

TOPIC_DISPLAY = {
    "vie_quotidienne":        "Vie Quotidienne",
    "voyages_tourisme":       "Voyages & Tourisme",
    "environnement_ecologie": "Environnement & Écologie",
    "technologie_numerique":  "Technologie & Numérique",
    "culture_histoire":       "Culture & Histoire",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cache_path(level: str, topic: str) -> str:
    return os.path.join(CACHE_DIR, f"{level}_{topic}.json")


def run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def build_one(level: str, topic: str, python: str) -> dict | str:
    """
    Run search then generate for one combination.
    Returns the merged dict on success, or an error string on failure.
    """
    # Step 1 — search
    code, out = run([python, "tools/search_french_text.py", "--level", level, "--topic", topic])
    if code != 0:
        try:
            err = json.loads(out).get("message", out)
        except Exception:
            err = out or "unknown search error"
        return f"search failed: {err}"

    try:
        search = json.loads(out)
    except json.JSONDecodeError:
        return f"search returned invalid JSON: {out[:120]}"

    # Step 2 — generate exercises
    code, out = run([
        python, "tools/generate_exercises.py",
        "--level", level,
        "--topic", topic,
        "--text", search["text"],
    ])
    if code != 0:
        try:
            err = json.loads(out).get("message", out)
        except Exception:
            err = out or "unknown generate error"
        return f"generate failed: {err}"

    try:
        exercises = json.loads(out)
    except json.JSONDecodeError:
        return f"generate returned invalid JSON: {out[:120]}"

    return {**search, **exercises, "level": level, "topic": topic}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Pre-build exercise cache for all 25 combinations.")
    parser.add_argument("--force", action="store_true", help="Rebuild even if cache already exists")
    args = parser.parse_args()

    os.makedirs(CACHE_DIR, exist_ok=True)
    python = sys.executable

    succeeded, skipped, failed = 0, 0, []
    n = 0

    print(f"\n{'='*60}")
    print(f"  FLE-agent — Pre-building cache ({TOTAL} combinations)")
    print(f"{'='*60}\n")

    for level in LEVELS:
        for topic in TOPICS:
            n += 1
            path = cache_path(level, topic)
            label = f"[{n:02d}/{TOTAL}] {level} / {TOPIC_DISPLAY[topic]}"

            if not args.force and os.path.exists(path):
                print(f"  ⏭  {label}  →  already cached, skipping")
                skipped += 1
                continue

            print(f"  ⏳  {label}  …", end="", flush=True)
            result = build_one(level, topic, python)

            if isinstance(result, str):
                print(f"\n      ❌  {result}")
                failed.append((level, topic, result))
            else:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                word_count = result.get("word_count", "?")
                n_q = len(result.get("questions", []))
                n_v = len(result.get("vocabulary", []))
                print(f"  ✅  {word_count} words · {n_q} questions · {n_v} vocab items")
                succeeded += 1

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
