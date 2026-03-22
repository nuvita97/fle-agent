# Workflow: Weekly Content Pipeline

## Objective

Every Monday, automatically refresh the exercise database with 35 new AI-generated exercises (one per CEFR level × topic combination) and send each subscriber a personalized exercise based on their chosen level and topic.

## Schedule

| Time (Europe/Paris) | Job | Tool |
|---|---|---|
| **Monday 06:00** | Generate 35 exercises → insert into Supabase | `tools/weekly_generate.py` |
| **Monday 12:00** | Send latest exercise to each subscriber | `send_newsletter_to_all()` in `app.py` |

Both jobs run automatically via **APScheduler** when the Flask app is running.

---

## Database Design

The `exercises` table is **append-only** — no unique constraint on `(level, topic)`.

- Each Monday's batch adds 35 new rows (or however many succeed)
- Each row has a `created_at` timestamp set to the batch start time
- The exercise pool grows richer every week

**Key behaviors:**
- **Newsletter** → always picks the row with the latest `created_at` for the subscriber's level/topic (`load_latest_exercise()`)
- **Web app** → picks a random row from all available rows for the user's level/topic (`load_cached_exercise()`)

---

## Inputs

- `ANTHROPIC_API_KEY` — Claude API key (in `.env`)
- `SUPABASE_URL` / `SUPABASE_KEY` — Supabase credentials (in `.env`)
- Gmail OAuth credentials — for sending newsletter emails (in `.env`)

---

## Step 1 — Weekly Exercise Generation (06:00)

APScheduler calls `generate_weekly_exercises()` in `app.py`, which runs:

```bash
.venv/bin/python tools/weekly_generate.py
```

### What it does:
1. Iterates over all 5 CEFR levels × 7 topics = 35 combinations
2. For each: calls `tools/generate_lesson.py --level {level} --topic {topic}` as a subprocess
3. Parses the JSON response
4. INSERTs a new row into Supabase `exercises` table (does NOT upsert/overwrite)
5. All rows in the batch share the same `created_at` timestamp
6. Logs success/failure count; exits with code 1 if any combo failed

### Edge cases:
- **API rate limit**: A 1.5-second pause between combos reduces this risk. If a combo fails, it is logged but the rest continue.
- **Partial failure**: Failed combos are reported at the end. Re-run the tool manually for specific combos if needed.
- **App not running**: APScheduler only runs while the Flask process is alive. On Render.com/cloud, ensure the app does not sleep at 6am.

---

## Step 2 — Newsletter Send (12:00)

APScheduler calls `send_newsletter_to_all()` in `app.py`.

### What it does:
1. Fetches all subscribers from Supabase `subscribers` table
2. For each subscriber:
   - Looks up the **latest** exercise matching their `level` and `topic`
   - Falls back to: same topic + any level → any exercise (if exact combo not found)
   - Builds a PDF in memory via `tools/build_pdf.py`
   - Sends email via `tools/send_email.py` (Gmail OAuth2) with PDF attached
   - Includes personalized manage/unsubscribe links
3. Logs sent / failed / skipped counts

### Edge cases:
- **No exercise for subscriber's combo**: Subscriber is skipped and logged as "skipped"
- **PDF build error**: Subscriber counted as "failed", rest continue
- **Gmail send error**: Subscriber counted as "failed", rest continue

---

## Manual Triggers (for testing)

### Trigger exercise generation:
```bash
curl -X POST http://localhost:5001/admin/trigger-generate \
  -H "X-Admin-Token: <ADMIN_TOKEN>"
```
Runs `tools/weekly_generate.py` in a background thread. Check server logs for progress.

### Trigger newsletter send:
```bash
curl -X POST http://localhost:5001/admin/trigger-newsletter \
  -H "X-Admin-Token: <ADMIN_TOKEN>"
```

### Test generation without API calls (use existing JSON):
```bash
.venv/bin/python tools/weekly_generate.py \
  --test-file .tmp/lesson_b2_education.json \
  --level B2 --topic education_apprentissage
```
Inserts one row from the local file — no Claude API call made.

---

## Testing Checklist

- [ ] **Schema migration run** — `exercises` table has `created_at` column, no unique constraint on `(level, topic)`
- [ ] **Test seed** — `weekly_generate.py --test-file` inserts a row with `created_at` set
- [ ] **Verify in Supabase dashboard** — new row visible in `exercises` table
- [ ] **Newsletter trigger** — subscriber receives email with correct level/topic content
- [ ] **Web app random** — inserting a second test row and refreshing `/exercise` may show different content
- [ ] **Scheduler logs** — on app start, logs show both 6am and 12pm jobs registered

---

## Related Files

| File | Role |
|---|---|
| `tools/weekly_generate.py` | Batch generator — INSERT 35 new rows per week |
| `tools/generate_lesson.py` | Single-lesson generator called by weekly_generate.py |
| `tools/send_email.py` | Gmail OAuth2 email sender |
| `tools/build_pdf.py` | PDF builder for exercise emails |
| `app.py` | Flask app, APScheduler, `load_cached_exercise()`, `load_latest_exercise()`, admin endpoints |
| `tools/prebuild_cache.py` | Legacy one-time seeder (UPSERT) — use `weekly_generate.py` going forward |
