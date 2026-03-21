# Workflow: Generate French Language Exercise

## Objective
Given a CEFR level and topic chosen by the user, find a real French article from the web,
generate comprehension questions and vocabulary, then produce a clean PDF exercise sheet.

## Required Inputs
Collect these before starting (ask if not provided):

| Input | Valid values |
|-------|-------------|
| `level` | A1, A2, B1, B2, C1 |
| `topic` | One of the 5 keys below |

**Available topics:**

| Key | Display name |
|-----|-------------|
| `vie_quotidienne` | Vie Quotidienne (Daily Life & Routines) |
| `voyages_tourisme` | Voyages & Tourisme (Travel & Tourism) |
| `environnement_ecologie` | Environnement & Écologie (Environment & Ecology) |
| `technologie_numerique` | Technologie & Numérique (Technology & Digital Life) |
| `culture_histoire` | Culture & Histoire (French Culture & History) |

---

## Steps

### Step 1 — Search for a French article
```
python tools/search_french_text.py --level {level} --topic {topic}
```
- Captures stdout as JSON → `search_result`
- `search_result` contains: `text`, `url`, `site_name`, `word_count`
- On error: see Edge Cases

### Step 2 — Generate exercises
```
python tools/generate_exercises.py \
  --level {level} \
  --topic {topic} \
  --text "{search_result.text}"
```
- Captures stdout as JSON → `exercises`
- `exercises` contains: `questions` (5 items) and `vocabulary` (8-10 items)
- On error: see Edge Cases

### Step 3 — Build the PDF
```
python tools/build_pdf.py \
  --level {level} \
  --topic {topic} \
  --text "{search_result.text}" \
  --url "{search_result.url}" \
  --site_name "{search_result.site_name}" \
  --exercises '{exercises as JSON string}'
```
- Default output: `.tmp/exercise_{level}_{topic}_{timestamp}.pdf`
- Captures stdout → `output_path` (absolute path to the PDF)
- On error: see Edge Cases

### Step 4 — Report to user
Tell the user:
- The PDF is ready at: `{output_path}`
- Summary: level, topic, word count (`{search_result.word_count}` words), number of questions

---

## Edge Cases

| Situation | How to handle |
|-----------|--------------|
| `search_french_text.py` exits with `error: no_results` | Tell the user no results were found. Suggest trying a different topic or level. Do not retry automatically. |
| `search_french_text.py` exits with `error: no_suitable_text` | The scraped texts were too short or not in French. Ask the user if they want to try a different topic or level. |
| `generate_exercises.py` exits with `error: missing_api_key` | Tell the user to add `ANTHROPIC_API_KEY` to the `.env` file in the project root. |
| `generate_exercises.py` exits with `error: invalid_response` | Claude returned malformed JSON twice. Retry Step 2 once more. If it fails again, report the issue to the user. |
| `generate_exercises.py` exits with `error: api_error` | Report the Claude API error message to the user verbatim. |
| `build_pdf.py` exits with `error: pdf_generation_failed` | Report the error. Check that `fpdf2` is installed (`pip install -r requirements.txt`). |
| Any tool returns non-zero exit code | Print the JSON error from stdout, explain what went wrong, and suggest a remedy based on the error type above. |

---

## Notes
- All tools read API keys from `.env` — never pass keys as command-line arguments.
- The `.tmp/` directory is created automatically if it doesn't exist.
- The PDF is saved locally. Share it as needed (email, cloud upload, etc.).
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

3. Test each tool individually before running the full pipeline:
   ```
   python tools/search_french_text.py --level B1 --topic voyages_tourisme
   python tools/generate_exercises.py --level B1 --topic voyages_tourisme --text "Votre texte ici..."
   python tools/build_pdf.py --level B1 --topic voyages_tourisme --text "..." --url "https://example.com" --site_name "example.com" --exercises '{"questions":[],"vocabulary":[]}'
   ```
