# Workflow: Generate French Language Exercise

## Objective
Given a CEFR level and topic chosen by the user, generate a level-appropriate French article
and comprehension exercises in a single AI call, then produce a clean PDF exercise sheet.

## Required Inputs
Collect these before starting (ask if not provided):

| Input | Valid values |
|-------|-------------|
| `level` | A1, A2, B1, B2, C1 |
| `topic` | One of the 7 keys below |

**Available topics:**

| Key | Display name |
|-----|-------------|
| `vie_quotidienne` | Vie Quotidienne (Daily Life & Society) |
| `sante_bien_etre` | Santé & Bien-être (Health & Wellness) |
| `education_apprentissage` | Éducation & Apprentissage (Education & Learning) |
| `voyages_tourisme` | Voyages & Tourisme (Travel & Tourism) |
| `environnement_ecologie` | Environnement & Écologie (Environment & Ecology) |
| `technologie_numerique` | Technologie & Numérique (Technology & Digital Life) |
| `culture_histoire` | Culture & Histoire (French Culture & History) |

---

## Steps

### Step 1 — Generate lesson (text + questions + vocabulary)
```
python tools/generate_lesson.py --level {level} --topic {topic}
```
- Captures stdout as JSON → `lesson`
- `lesson` contains: `text`, `url`, `site_name`, `word_count`, `questions` (5 items), `vocabulary` (8-10 items)
- The text is AI-generated for pedagogical quality — it is NOT scraped from the web
- `url` will be `"https://evoli-fle.app/generated"` and `site_name` will be `"Évoli FLE (texte généré)"`
- On error: see Edge Cases

### Step 2 — Build the PDF
```
python tools/build_pdf.py \
  --level {level} \
  --topic {topic} \
  --text "{lesson.text}" \
  --url "{lesson.url}" \
  --site_name "{lesson.site_name}" \
  --exercises '{"questions": {lesson.questions}, "vocabulary": {lesson.vocabulary}}'
```
- Default output: `.tmp/exercise_{level}_{topic}_{timestamp}.pdf`
- Captures stdout → `output_path` (absolute path to the PDF)
- On error: see Edge Cases

### Step 3 — Report to user
Tell the user:
- The PDF is ready at: `{output_path}`
- Summary: level, topic, word count (`{lesson.word_count}` words), number of questions

---

## Edge Cases

| Situation | How to handle |
|-----------|--------------|
| `generate_lesson.py` exits with `error: missing_api_key` | Tell the user to add `ANTHROPIC_API_KEY` to the `.env` file in the project root. |
| `generate_lesson.py` exits with `error: invalid_response` | Claude returned malformed JSON twice. Retry Step 1 once more. If it fails again, report the issue to the user. |
| `generate_lesson.py` exits with `error: api_error` | Report the Claude API error message to the user verbatim. |
| `build_pdf.py` exits with `error: pdf_generation_failed` | Report the error. Check that `fpdf2` is installed (`pip install -r requirements.txt`). |
| Any tool returns non-zero exit code | Print the JSON error from stdout, explain what went wrong, and suggest a remedy based on the error type above. |

---

## Notes
- All tools read API keys from `.env` — never pass keys as command-line arguments.
- The `.tmp/` directory is created automatically if it doesn't exist.
- The PDF is saved locally. Share it as needed (email, cloud upload, etc.).
- Word count targets per level: A1 (100-300), A2 (120-350), B1 (200-450), B2 (300-600), C1 (350-650).
- If the text contains special French characters (accents), they render correctly — `fpdf2` handles Unicode.
- This workflow does not modify any workflow or tool files. Improvements should be made explicitly.

---

## Setup (first-time only)

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Add your Anthropic API key to `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

3. Test the lesson generator before running the full pipeline:
   ```
   python tools/generate_lesson.py --level B1 --topic voyages_tourisme
   python tools/build_pdf.py --level B1 --topic voyages_tourisme --text "..." --url "https://evoli-fle.app/generated" --site_name "Évoli FLE (texte généré)" --exercises '{"questions":[],"vocabulary":[]}'
   ```
