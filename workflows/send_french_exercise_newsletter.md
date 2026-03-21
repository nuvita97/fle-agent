# Workflow: Send French Exercise Newsletter

## Objective
Send a generated French exercise PDF to the configured recipient by email.
The email body includes the level, topic, what's inside the PDF, and the source of the text.

This workflow can be run:
- **Standalone** — to send an existing PDF from `.tmp/`
- **After `generate_french_exercise.md`** — as the final delivery step

---

## Required .env Keys
Before running, confirm these keys exist in `.env`:

| Key | Description |
|-----|-------------|
| `EMAIL_SENDER` | Your Gmail address |
| `EMAIL_APP_PASSWORD` | Gmail App Password (16 chars, **not** your regular password) |
| `EMAIL_RECIPIENT` | The email address to send to |

Optional:
| Key | Default |
|-----|---------|
| `EMAIL_SMTP_HOST` | `smtp.gmail.com` |
| `EMAIL_SMTP_PORT` | `587` |

> **How to create a Gmail App Password:**
> Google Account → Security → 2-Step Verification → App passwords
> URL: https://myaccount.google.com/apppasswords

---

## Inputs
- `pdf_path` — path to the PDF file (e.g. `.tmp/exercise_B1_voyages_tourisme_20260321_122016.pdf`)
- `level` — CEFR level used to generate the exercise (e.g. `B1`)
- `topic` — topic key (e.g. `voyages_tourisme`)
- `source_url` — URL of the article the text came from
- `source_name` — display name of the source site

---

## Steps

### Step 1 — Locate the PDF and source info
- If running after `generate_french_exercise.md`: use the `output_path` from Step 3 and the `url`/`site_name` from `search_result`
- If running standalone: use the most recent PDF in `.tmp/` and read source from `.tmp/search_result.json`

To get source info from cached file:
```
python -c "import json; d=json.load(open('.tmp/search_result.json')); print(d['url'], d['site_name'])"
```

### Step 2 — Send the email
```
python tools/send_email.py \
  --pdf {pdf_path} \
  --level {level} \
  --topic {topic} \
  --source-url "{source_url}" \
  --source-name "{source_name}"
```
Capture stdout as JSON → `send_result`

### Step 3 — Report to user
Tell the user:
- Status: sent ✓
- Recipient: `{send_result.recipient}`
- PDF attached: `{send_result.pdf}`

---

## Edge Cases

| Situation | How to handle |
|-----------|--------------|
| `error: missing_env_keys` | Tell the user exactly which key(s) are missing and direct them to `.env` |
| `error: auth_failed` | Remind user to use a Gmail **App Password**, not their regular password. Link: https://myaccount.google.com/apppasswords |
| `error: pdf_not_found` | Check the `--pdf` path is correct. List `.tmp/` contents to find the right filename. |
| `error: smtp_error` or `connection_error` | Check internet connection. Wait 10 seconds and retry once. If it fails again, report the error. |

---

## Notes
- The recipient is always read from `EMAIL_RECIPIENT` in `.env` — no need to pass it as an argument
- Sending to a different address temporarily: change `EMAIL_RECIPIENT` in `.env` before running
- This workflow does not generate a new PDF or call the Claude API — it only sends an existing file
