#!/usr/bin/env python3
"""
Generate a complete FLE lesson (source text + MCQ questions + vocabulary)
using a single Claude API call.

Replaces the two-step pipeline of search_french_text.py + generate_exercises.py.

Usage:
    python tools/generate_lesson.py --level B2 --topic education_apprentissage

Output (stdout JSON):
    {
      "text": "...",
      "url": "https://evoli-fle.app/generated",
      "site_name": "Évoli FLE (texte généré)",
      "word_count": 412,
      "questions": [{"question": "...", "choices": {"A": "...", ...}, "answer": "B", "explanation": "..."}, ...],
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
# CEFR-level and topic configuration
# ---------------------------------------------------------------------------

WORD_COUNT_TARGETS = {
    "A1": (100, 300),
    "A2": (120, 350),
    "B1": (200, 450),
    "B2": (300, 600),
    "C1": (350, 650),
}

TOPIC_LABELS = {
    "vie_quotidienne":          "la vie quotidienne et la société contemporaine",
    "sante_bien_etre":          "la santé, le bien-être et la médecine",
    "education_apprentissage":  "l'éducation, l'apprentissage et la formation",
    "voyages_tourisme":         "les voyages, le tourisme et la mobilité",
    "environnement_ecologie":   "l'environnement, l'écologie et le développement durable",
    "technologie_numerique":    "les technologies numériques et l'intelligence artificielle",
    "culture_histoire":         "la culture, les arts et l'histoire",
}

LEVEL_TEXT_STYLE = {
    "A1": (
        "texte très simple, phrases courtes (8-12 mots), vocabulaire du quotidien, "
        "présent de l'indicatif dominant, sans subordonnées complexes"
    ),
    "A2": (
        "texte simple, phrases courtes à moyennes, vocabulaire courant, "
        "connecteurs simples (mais, et, parce que, alors)"
    ),
    "B1": (
        "article de presse accessible, phrases de longueur moyenne, vocabulaire usuel "
        "avec quelques mots moins fréquents, connecteurs variés (cependant, en effet, ainsi)"
    ),
    "B2": (
        "article de presse ou éditorial, syntaxe variée incluant subordonnées et participiales, "
        "vocabulaire précis, figures de style occasionnelles, argumentaire structuré"
    ),
    "C1": (
        "éditorial ou essai court, syntaxe complexe et variée, lexique soutenu, "
        "ton nuancé, argumentation implicite, registre formel à légèrement littéraire"
    ),
}

LEVEL_QUESTION_STYLE = {
    "A1": (
        "compréhension globale simple (oui/non, fait explicite). "
        "Vocabulaire de base, phrases courtes."
    ),
    "A2": (
        "compréhension globale et repérage d'information. "
        "Réponses directement dans le texte."
    ),
    "B1": (
        "compréhension globale, repérage d'info, déduction simple. "
        "Quelques reformulations nécessaires."
    ),
    "B2": (
        "compréhension fine, inférence, ton de l'auteur, déduire des idées implicites. "
        "Certaines réponses demandent une interprétation."
    ),
    "C1": (
        "inférence avancée, ton et posture de l'auteur, nuances argumentatives, "
        "idées sous-jacentes. Réponses développées et nuancées."
    ),
}

LEVEL_VOCAB_STYLE = {
    "A1": "mots très courants mais potentiellement nouveaux pour un débutant absolu",
    "A2": "mots courants du texte utiles pour un apprenant élémentaire",
    "B1": "mots de niveau intermédiaire, expressions idiomatiques simples",
    "B2": "mots avancés, expressions idiomatiques, nuances de sens",
    "C1": "mots sophistiqués, registre soutenu, expressions figées complexes",
}

LEVEL_OPEN_QUESTION_STYLE = {
    "A1": "question très simple, courte (max 10 mots), qui invite l'élève à parler de lui-même ou de sa vie quotidienne en lien avec le thème",
    "A2": "question simple et concrète qui invite l'élève à donner son opinion ou à comparer avec sa propre expérience",
    "B1": "question ouverte qui demande à l'élève de donner son avis, d'expliquer une préférence ou de faire un lien avec sa réalité",
    "B2": "question de réflexion qui invite l'élève à analyser, nuancer ou prendre position sur une idée du texte ou un enjeu plus large",
    "C1": "question de réflexion critique qui invite l'élève à argumenter, à mobiliser ses connaissances ou à remettre en question une idée implicite du texte",
}

GENERATED_URL = "https://fle-agent.onrender.com"
GENERATED_SITE = "Évoli FLE"

# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Tu es un professeur de français langue étrangère (FLE) expert et auteur de manuels pédagogiques.
Tu rédiges des textes authentiques calibrés au niveau CEFR indiqué et tu crées des exercices de compréhension de haute qualité.
Tu réponds UNIQUEMENT en JSON valide, sans aucun texte avant ou après le JSON."""


def build_user_prompt(level: str, topic: str) -> str:
    min_words, max_words = WORD_COUNT_TARGETS[level]
    topic_label = TOPIC_LABELS.get(topic, topic.replace("_", " "))
    text_style = LEVEL_TEXT_STYLE[level]
    q_style = LEVEL_QUESTION_STYLE[level]
    v_style = LEVEL_VOCAB_STYLE[level]
    oq_style = LEVEL_OPEN_QUESTION_STYLE[level]

    return f"""Génère une leçon complète de FLE pour le niveau {level} sur le thème : {topic_label}.

=== SECTION 1 — TEXTE SOURCE ===

Rédige un texte en français de {min_words} à {max_words} mots sur ce thème.

Contraintes stylistiques pour le niveau {level} :
- {text_style}
- Apparence d'un court article informatif (pas un dialogue, pas une liste à puces)
- Commence par un titre accrocheur sur la première ligne, puis un saut de ligne, puis le corps du texte en 2-4 paragraphes
- Contenu factuel, ancré dans la réalité francophone, sans invention de données chiffrées invérifiables
- Richesse lexicale adaptée au niveau : évite les répétitions inutiles

=== SECTION 2 — COMPRÉHENSION ÉCRITE — QCM ===

Génère exactement 5 questions à choix multiples (A, B, C, D) basées sur le texte que tu viens de rédiger.

Consignes générales (à destination des apprenants) :
Lisez attentivement le texte. Répondez aux QCM en choisissant une seule bonne réponse. Soignez la précision lexicale et la nuance.

Types de questions à couvrir — varie les types sur les 5 questions :
- compréhension globale : identifier l'idée principale ou la thèse du texte
- ton de l'auteur : identifier le registre, l'attitude, la posture (informatif, critique, enthousiaste, nuancé…)
- compréhension fine et inférence : comprendre une idée qui n'est pas formulée explicitement
- déduire des idées : tirer une conclusion logique à partir d'éléments du texte
- repérer l'information : localiser un fait, une donnée, une position précise dans le texte

Niveau de question adapté au {level} : {q_style}

Qualité des distracteurs (CRITIQUE — applique ces règles sans exception) :
- Homogènes : même structure grammaticale pour tous les choix d'une même question (soit tous groupes nominaux, soit toutes propositions causales, soit toutes propositions infinitives, etc.)
- Plausibles : proches des idées circulant dans le texte, mais incorrects dans ce contexte précis
- Non ambigus : une seule réponse est clairement juste ; les autres sont clairement fausses pour un lecteur attentif
- Équilibrés en longueur : évite qu'un choix soit nettement plus long ou court que les autres
- Varie quelle lettre est la bonne réponse sur les 5 questions (ne mets pas toujours A ou B)

=== SECTION 3 — VOCABULAIRE ===

Sélectionne 8 à 10 mots ou expressions du texte que tu viens de rédiger.
Cible : {v_style}
- La définition est en français (courte, claire, sans paraphrase du mot lui-même)
- La traduction est en anglais (mot ou expression équivalente, pas une définition)

=== SECTION 4 — QUESTION OUVERTE ===

Génère UNE SEULE question ouverte, sans proposition de réponse et sans choix multiples.
Objectif : amener l'apprenant à réfléchir au-delà du texte, à mobiliser son vécu ou à exprimer un point de vue personnel.
Style pour le niveau {level} : {oq_style}
- La question doit être courte et claire
- Elle ne doit pas avoir de réponse évidente dans le texte
- Elle est en français

=== FORMAT DE SORTIE ===

Génère UNIQUEMENT ce JSON (rien d'autre, pas de markdown, pas de texte autour) :

{{
  "text": "Titre du texte\\n\\nPremier paragraphe...\\n\\nDeuxième paragraphe...",
  "word_count": {min_words},
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
      "answer": "B",
      "explanation": "..."
    }}
  ],
  "vocabulary": [
    {{"word": "...", "pos": "nom/verbe/adjectif/adverbe/expression", "definition_fr": "...", "translation_en": "..."}},
    {{"word": "...", "pos": "...", "definition_fr": "...", "translation_en": "..."}}
  ],
  "open_question": "..."
}}

Rappels importants :
- Le champ "word_count" doit refléter le nombre réel de mots dans le champ "text" (sans compter le titre)
- Le champ "explanation" explique en 1-2 phrases pourquoi la réponse est correcte, en citant le texte si possible
- Toutes les questions, choix, explications et la question ouverte sont en français
- Le champ "answer" contient uniquement la lettre correcte : "A", "B", "C" ou "D"
- Le champ "open_question" contient uniquement la question, sans réponse ni choix\""""


# ---------------------------------------------------------------------------
# Parsing and validation
# ---------------------------------------------------------------------------

def parse_json_response(content: str) -> dict | None:
    """Extract JSON from Claude's response, handling potential markdown fences."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def validate_lesson(data: dict) -> bool:
    """Basic schema check for the combined lesson output."""
    if not isinstance(data.get("text"), str) or len(data["text"].split()) < 50:
        return False
    if not isinstance(data.get("questions"), list) or len(data["questions"]) < 5:
        return False
    if not isinstance(data.get("vocabulary"), list) or len(data["vocabulary"]) < 1:
        return False
    if not isinstance(data.get("open_question"), str) or not data["open_question"].strip():
        return False
    for q in data["questions"]:
        if not all(k in q for k in ("question", "choices", "answer", "explanation")):
            return False
        if not isinstance(q["choices"], dict) or len(q["choices"]) < 4:
            return False
    return True


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------

def generate(level: str, topic: str) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "error": "missing_api_key",
            "message": "ANTHROPIC_API_KEY not found in .env",
        }

    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = build_user_prompt(level, topic)

    for attempt in range(2):
        try:
            message = client.messages.create(
                model=model,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIError as e:
            return {"error": "api_error", "message": str(e)}

        raw = message.content[0].text
        data = parse_json_response(raw)

        if data and validate_lesson(data):
            # Recompute word count from the actual text (don't trust Claude's self-report)
            actual_word_count = len(data["text"].split())
            return {
                "text": data["text"],
                "word_count": actual_word_count,
                "questions": data["questions"],
                "vocabulary": data["vocabulary"],
                "open_question": data["open_question"],
            }

        if attempt == 0:
            user_prompt += "\n\nRappel CRITIQUE : réponds UNIQUEMENT avec du JSON valide. Pas de texte avant ou après."

    return {
        "error": "invalid_response",
        "message": "Claude returned malformed JSON after 2 attempts.",
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate a complete FLE lesson (text + questions + vocabulary) via Claude API."
    )
    parser.add_argument("--level", required=True, choices=["A1", "A2", "B1", "B2", "C1"])
    parser.add_argument(
        "--topic",
        required=True,
        choices=list(TOPIC_LABELS.keys()),
    )
    args = parser.parse_args()

    result = generate(args.level, args.topic)

    if "error" in result:
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
