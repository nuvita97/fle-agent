#!/usr/bin/env python3
"""
Insert a lesson JSON file into the Supabase exercises table.

Default behaviour: always INSERT a new row (multiple rows per level/topic are allowed).
Use --update to UPDATE the most recent existing row instead.

Usage:
    python tools/upsert_lesson.py --file .tmp/lesson_b2_voyages_tourisme.json \
                                   --level B2 --topic voyages_tourisme
    python tools/upsert_lesson.py --file ... --level B2 --topic ... --update
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()


def get_supabase():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)
    return create_client(url, key)


def main():
    parser = argparse.ArgumentParser(description="Upsert a lesson JSON into Supabase exercises.")
    parser.add_argument("--file", required=True, help="Path to the lesson JSON file")
    parser.add_argument("--level", required=True, choices=["A1", "A2", "B1", "B2", "C1"])
    parser.add_argument("--topic", required=True)
    parser.add_argument("--update", action="store_true", help="Update the most recent existing row instead of inserting a new one")
    args = parser.parse_args()

    with open(args.file, encoding="utf-8") as f:
        data = json.load(f)

    sb = get_supabase()

    row = {
        "level":         args.level,
        "topic":         args.topic,
        "text":          data["text"],
        "word_count":    data.get("word_count", 0),
        "questions":     data.get("questions", []),
        "vocabulary":    data.get("vocabulary", []),
        "open_question": data.get("open_question", ""),
        "created_at":    datetime.now(timezone(timedelta(hours=2))).replace(tzinfo=None).isoformat(),
    }

    try:
        if args.update:
            existing = (
                sb.table("exercises")
                .select("id")
                .eq("level", args.level)
                .eq("topic", args.topic)
                .order("id", desc=True)
                .limit(1)
                .execute()
                .data
            )
            if existing:
                sb.table("exercises").update(row).eq("id", existing[0]["id"]).execute()
                action = "Updated"
            else:
                sb.table("exercises").insert(row).execute()
                action = "Inserted"
        else:
            sb.table("exercises").insert(row).execute()
            action = "Inserted"

        n_q = len(row["questions"])
        n_v = len(row["vocabulary"])
        print(f"✅  {action} {args.level}/{args.topic} — {row['word_count']} words · {n_q} questions · {n_v} vocab items")
    except Exception as e:
        print(f"❌  Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
