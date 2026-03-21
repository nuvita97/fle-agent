#!/usr/bin/env python3
"""
Generate comprehension questions and vocabulary for a French passage using Claude API.

Usage:
    python tools/generate_exercises.py --level B1 --topic voyages_tourisme --text "..."

Output (stdout JSON):
    {
      "questions": [{"question": "...", "answer": "..."}, ...],
      "vocabulary": [{"word": "...", "pos": "...", "definition_fr": "...", "translation_en": "..."}, ...]
    }

On failure, exits with code 1 and prints:
    { "error": "...", "message": "..." }
"""

import argparse
import json
import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# CEFR-level instructions for question style
# ---------------------------------------------------------------------------

LEVEL_QUESTION_STYLE = {
    "A1": (
        "questions très simples de type oui/non ou à réponse courte (1-3 mots). "
        "Utilise un vocabulaire de base. Les réponses doivent être dans le texte."
    ),
    "A2": (
        "questions simples à réponse courte. Vocabulaire courant. "
        "Les réponses sont directement dans le texte."
    ),
    "B1": (
        "questions de compréhension générale et de déduction simple. "
        "Certaines réponses demandent une reformulation."
    ),
    "B2": (
        "questions d'inférence et d'opinion. Certaines demandent d'expliquer "
        "le sens implicite ou de donner son avis en s'appuyant sur le texte."
    ),
    "C1": (
        "questions d'analyse et d'argumentation. Demande d'identifier la thèse, "
        "les arguments, le ton de l'auteur, et de formuler une réponse développée."
    ),
}

LEVEL_VOCAB_STYLE = {
    "A1": "mots très courants mais potentiellement nouveaux pour un débutant absolu",
    "A2": "mots courants du texte utiles pour un apprenant élémentaire",
    "B1": "mots de niveau intermédiaire, expressions idiomatiques simples",
    "B2": "mots avancés, expressions idiomatiques, nuances de sens",
    "C1": "mots sophistiqués, registre soutenu, expressions figées complexes",
}

SYSTEM_PROMPT = """Tu es un professeur de français langue étrangère (FLE) expert.
Tu génères des exercices pédagogiques structurés, calibrés au niveau CEFR indiqué.
Tu réponds UNIQUEMENT en JSON valide, sans aucun texte avant ou après le JSON."""

def build_user_prompt(level: str, topic: str, text: str) -> str:
    q_style = LEVEL_QUESTION_STYLE.get(level, LEVEL_QUESTION_STYLE["B1"])
    v_style = LEVEL_VOCAB_STYLE.get(level, LEVEL_VOCAB_STYLE["B1"])

    return f"""Voici un texte en français sur le thème "{topic}" pour le niveau {level} :

---
{text}
---

Génère exactement ce JSON (et RIEN d'autre) :

{{
  "questions": [
    {{
      "question": "...",
      "choices": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "answer": "A",
      "explanation": "..."
    }},
    {{
      "question": "...",
      "choices": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "answer": "B",
      "explanation": "..."
    }},
    {{
      "question": "...",
      "choices": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "answer": "C",
      "explanation": "..."
    }},
    {{
      "question": "...",
      "choices": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "answer": "D",
      "explanation": "..."
    }},
    {{
      "question": "...",
      "choices": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "answer": "A",
      "explanation": "..."
    }}
  ],
  "vocabulary": [
    {{"word": "...", "pos": "nom/verbe/adjectif/adverbe/expression", "definition_fr": "...", "translation_en": "..."}},
    ...
  ]
}}

Instructions pour les questions (style niveau {level}) :
- Génère exactement 5 questions à choix multiples (A, B, C, D)
- Style : {q_style}
- Une seule réponse correcte par question ; les 3 autres choix sont des distracteurs plausibles
- Le champ "answer" contient uniquement la lettre correcte : "A", "B", "C" ou "D"
- Le champ "explanation" explique en 1-2 phrases pourquoi la réponse correcte est juste, en citant le texte si possible
- Les questions, choix et explications sont en français
- Varie quelle lettre est la bonne réponse (ne mets pas toujours A)

Instructions pour le vocabulaire :
- Sélectionne 8 à 10 mots ou expressions du texte
- Cible : {v_style}
- La définition est en français (courte, claire)
- La traduction est en anglais"""


def parse_json_response(content: str) -> dict | None:
    """Extract JSON from Claude's response, handling potential markdown fences."""
    content = content.strip()
    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def validate_exercises(data: dict) -> bool:
    """Basic schema check."""
    if not isinstance(data.get("questions"), list):
        return False
    if not isinstance(data.get("vocabulary"), list):
        return False
    if len(data["questions"]) < 1:
        return False
    if len(data["vocabulary"]) < 1:
        return False
    return True


def generate(level: str, topic: str, text: str) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "error": "missing_api_key",
            "message": "ANTHROPIC_API_KEY not found in .env",
        }

    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = build_user_prompt(level, topic, text)

    for attempt in range(2):
        try:
            message = client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIError as e:
            return {"error": "api_error", "message": str(e)}

        raw = message.content[0].text
        data = parse_json_response(raw)

        if data and validate_exercises(data):
            return data

        if attempt == 0:
            # Retry with a stricter instruction
            user_prompt += "\n\nRappel : réponds UNIQUEMENT avec du JSON valide, sans texte supplémentaire."

    return {
        "error": "invalid_response",
        "message": "Claude returned malformed JSON after 2 attempts.",
    }


def main():
    parser = argparse.ArgumentParser(description="Generate French exercises via Claude API.")
    parser.add_argument("--level", required=True, choices=["A1", "A2", "B1", "B2", "C1"])
    parser.add_argument("--topic", required=True)
    parser.add_argument("--text", required=True, help="French passage text")
    args = parser.parse_args()

    result = generate(args.level, args.topic, args.text)

    if "error" in result:
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
