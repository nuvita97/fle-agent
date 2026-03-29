---
name: generate-fle-lessons
description: Generate FLE lesson JSON files manually (no API) for given levels and topics. Use this when the user asks to generate, create, or write FLE lessons.
argument-hint: "[levels e.g. A1 or A1-C1] [topics or 'all']"
---

Generate FLE (Français Langue Étrangère) lesson JSON files manually — NO API calls, NO Supabase upsert unless explicitly asked.

## Arguments
$ARGUMENTS — interpret flexibly:
- A single level: `A1`, `B2`, etc.
- A range: `A1-C1` means all 5 levels
- A list of topics or `all` for all 7
- A subfolder name like `2903` → save to `.tmp/2903/`
- If no subfolder specified, save to `.tmp/`

## Filename format
`lesson_{LEVEL}_{TOPIC}_{TIMESTAMP}.json`
Get the timestamp at the start with: `date +%Y%m%d_%H%M%S`

---

## JSON schema (strictly required)
```json
{
  "text": "Titre\n\nParagraphe 1...\n\nParagraphe 2...\n\nParagraphe 3...",
  "word_count": <integer>,
  "questions": [
    {
      "question": "...",
      "choices": {"A": "...", "B": "...", "C": "...", "D": "..."},
      "answer": "B",
      "explanation": "..."
    }
  ],
  "vocabulary": [
    {"word": "...", "pos": "nom/verbe/adjectif/adverbe/expression", "definition_fr": "...", "translation_en": "..."}
  ],
  "open_question": "..."
}
```

---

## Level specs

### A1
- **text**: 100–300 words. Phrases très courtes (8–12 mots), vocabulaire du quotidien, présent de l'indicatif dominant, pas de subordonnées complexes, pas de subjonctif. 2–3 paragraphes.
- **questions**: compréhension globale simple, fait explicite, réponses directement dans le texte, vocabulaire de base.
- **vocabulary**: mots très courants mais potentiellement nouveaux pour un débutant absolu.
- **open_question**: très simple, max 10 mots, invite l'élève à parler de lui-même.

### A2
- **text**: 120–350 words. Phrases courtes à moyennes, vocabulaire courant, connecteurs simples (mais, et, parce que, alors). 2–3 paragraphes.
- **questions**: compréhension globale et repérage d'information. Réponses directement dans le texte.
- **vocabulary**: mots courants du texte utiles pour un apprenant élémentaire.
- **open_question**: simple et concrète, opinion ou comparaison avec sa propre expérience.

### B1
- **text**: 200–450 words. Article de presse accessible, phrases de longueur moyenne, vocabulaire usuel avec quelques mots moins fréquents, connecteurs variés (cependant, en effet, ainsi). 3 paragraphes.
- **questions**: compréhension globale, repérage d'info, déduction simple. Quelques reformulations nécessaires.
- **vocabulary**: mots de niveau intermédiaire, expressions idiomatiques simples.
- **open_question**: avis, préférence ou lien avec sa réalité.

### B2
- **text**: 300–600 words. Article de presse ou éditorial, syntaxe variée incluant subordonnées et participiales, vocabulaire précis, argumentaire structuré. 3–4 paragraphes.
- **questions**: compréhension fine, inférence, ton de l'auteur, idées implicites.
- **vocabulary**: mots avancés, expressions idiomatiques, nuances de sens.
- **open_question**: analyser, nuancer ou prendre position sur une idée du texte.

### C1
- **text**: 350–650 words. Éditorial ou essai court, syntaxe complexe, lexique soutenu, argumentation implicite, registre formel à légèrement littéraire. 4 paragraphes.
- **questions**: inférence avancée, ton et posture de l'auteur, nuances argumentatives, idées sous-jacentes.
- **vocabulary**: mots sophistiqués, registre soutenu, expressions figées complexes.
- **open_question**: réflexion critique, argumenter ou remettre en question une idée implicite.

---

## Topic labels
| Key | Label used in text |
|---|---|
| vie_quotidienne | la vie quotidienne et la société contemporaine |
| sante_bien_etre | la santé, le bien-être et la médecine |
| education_apprentissage | l'éducation, l'apprentissage et la formation |
| voyages_tourisme | les voyages, le tourisme et la mobilité |
| environnement_ecologie | l'environnement, l'écologie et le développement durable |
| technologie_numerique | les technologies numériques et l'intelligence artificielle |
| culture_histoire | la culture, les arts et l'histoire |

---

## Quality rules (apply every time, no exceptions)

### Text
1. Title on the first line, then `\n\n`, then paragraphs separated by `\n\n`
2. **Word count must be within the level range — count before finalising**
3. All content in French; factual, anchored in francophone reality
4. No invented unverifiable statistics

### Questions (from generate_exercises.py)
5. Exactly 5 MCQ questions (A, B, C, D)
6. Vary the correct answer letter across the 5 questions — never the same letter for all 5
7. Cover these 5 question types, one per question (vary the order):
   - **compréhension globale** : identifier l'idée principale ou la thèse du texte
   - **ton de l'auteur** : identifier le registre, l'attitude, la posture (informatif, critique, enthousiaste, nuancé…)
   - **compréhension fine et inférence** : comprendre une idée qui n'est pas formulée explicitement
   - **déduire des idées** : tirer une conclusion logique à partir d'éléments du texte
   - **repérer l'information** : localiser un fait, une donnée, une position précise dans le texte
8. Distractors — apply all four criteria without exception:
   - **Homogènes** : same grammatical structure for all choices in a question (all noun phrases, all causal clauses, all infinitive clauses, etc.)
   - **Plausibles** : close to ideas in the text, but incorrect in this precise context
   - **Non ambigus** : only one answer is clearly correct; the others are clearly wrong on careful reading
   - **Équilibrés en longueur** : avoid one choice being noticeably longer or shorter than the others
9. `explanation`: 1–2 sentences citing the text to justify the correct answer
10. All questions, choices, explanations in French

### Vocabulary (from generate_exercises.py)
11. 8–10 items taken from the text
12. `definition_fr`: short, clear, in French — do not paraphrase the word itself
13. `translation_en`: English equivalent word or expression (not a definition)

### Open question
14. Single question in French, no answer or choices
15. Cannot be answered directly from the text

### JSON
16. Valid JSON — handle apostrophes and accented characters correctly
17. `word_count` must reflect the actual word count of the body text only — **do not count the title line**
18. Each lesson must be unique — different title, different angle

---

## Deduplication against Supabase

Before generating any lesson, check what already exists for the same level + topic in Supabase:

```bash
.venv/bin/python -c "
from supabase import create_client
import os; from dotenv import load_dotenv; load_dotenv()
sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
rows = sb.table('lessons').select('title').eq('level','LEVEL').eq('topic','TOPIC').execute().data
for r in rows: print(r['title'])
"
```

Use the existing titles to ensure the new lesson:
- Has a **different title** (not a minor rewording)
- Takes a **different angle** on the topic (e.g. if an A2 vie_quotidienne lesson already covers shopping, the next one should cover housing, transport, or daily routines — not shopping again)
- Introduces **different vocabulary** (avoid re-teaching the same 8–10 words)

If you cannot query Supabase (no credentials, offline, etc.), note this explicitly and ensure uniqueness based on the lessons generated in the current session.

---

## Self-check before writing each file
- [ ] Word count is within the level range (body text only, title excluded)
- [ ] Exactly 5 questions, each covering a different question type
- [ ] Correct answer letters are varied across the 5 questions
- [ ] Distractors are homogeneous, plausible, unambiguous, and length-balanced
- [ ] 8–10 vocabulary items
- [ ] Valid JSON syntax
- [ ] Title and angle are different from existing lessons at the same level + topic in Supabase

---

## After generating
- Report a summary table: level | topic | word count | questions | vocab items
- Verify word counts with: `for f in .tmp/PATH/lesson_LEVEL_*.json; do .venv/bin/python -c "import json; d=json.load(open('$f')); lines=d['text'].split('\n\n'); body=' '.join(lines[1:]); print(f'{f}: {len(body.split())} words (body only)')"; done`
- Do NOT upsert to Supabase unless the user explicitly asks
