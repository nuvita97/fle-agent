#!/usr/bin/env python3
"""
Build a light, educational-themed French exercise PDF from scraped text and generated exercises.

Usage:
    python tools/build_pdf.py \
        --level B1 \
        --topic voyages_tourisme \
        --text "..." \
        --url "https://..." \
        --site_name "lemonde.fr" \
        --exercises '{"questions":[...],"vocabulary":[...]}' \
        --output .tmp/exercise.pdf

Output: prints the absolute path of the saved PDF to stdout.
"""

import argparse
import json
import os
import sys
from datetime import datetime

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ---------------------------------------------------------------------------
# Color palette (light, educational)
# ---------------------------------------------------------------------------
COLOR_ACCENT = (74, 111, 165)       # Slate blue — headers, accents
COLOR_HEADER_TEXT = (255, 255, 255) # White — text on accent bg
COLOR_BODY = (26, 26, 26)           # Near-black — body text
COLOR_ANSWER = (85, 85, 85)         # Muted grey — answers
COLOR_SOURCE_BG = (255, 251, 234)   # Pale yellow — source bar bg
COLOR_SOURCE_TEXT = (100, 80, 20)   # Warm brown — source text
COLOR_VOCAB_BG = (232, 244, 242)    # Soft teal — vocabulary cells
COLOR_DIVIDER = (222, 222, 222)     # Light grey — dividers
COLOR_FOOTER = (150, 150, 150)      # Grey — footer

TOPIC_DISPLAY = {
    "vie_quotidienne": "Vie Quotidienne",
    "voyages_tourisme": "Voyages & Tourisme",
    "environnement_ecologie": "Environnement & Ecologie",
    "technologie_numerique": "Technologie & Numerique",
    "culture_histoire": "Culture & Histoire",
}

# DejaVu TTF fonts bundled in fonts/ (cross-platform)
_FONTS_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")
FONT_REGULAR = os.path.join(_FONTS_DIR, "DejaVuSans.ttf")
FONT_BOLD    = os.path.join(_FONTS_DIR, "DejaVuSans-Bold.ttf")
FONT_ITALIC  = os.path.join(_FONTS_DIR, "DejaVuSans-Oblique.ttf")


class FrenchExercisePDF(FPDF):
    def __init__(self, level: str, topic: str):
        super().__init__(format="A4")
        self.level = level
        self.topic_display = TOPIC_DISPLAY.get(topic, topic.replace("_", " ").title())
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=18)
        # Register Unicode fonts
        self.add_font("DejaVu", style="", fname=FONT_REGULAR)
        self.add_font("DejaVu", style="B", fname=FONT_BOLD)
        self.add_font("DejaVu", style="I", fname=FONT_ITALIC)

    def header(self):
        pass  # Custom header drawn per section

    def footer(self):
        self.set_y(-13)
        self.set_font("DejaVu", "I", 8)
        self.set_text_color(*COLOR_FOOTER)
        date_str = datetime.now().strftime("%d %B %Y")
        self.cell(0, 8, f"Genere le {date_str}  -  FLE-agent  |  p. {self.page_no()}", align="C")

    def draw_title_bar(self):
        """Big header bar at top of first page."""
        self.set_fill_color(*COLOR_ACCENT)
        self.rect(0, 0, 210, 28, "F")
        self.set_y(6)
        self.set_font("DejaVu", "B", 16)
        self.set_text_color(*COLOR_HEADER_TEXT)
        self.cell(
            0, 8,
            f"Exercice de Francais  -  Niveau {self.level}",
            align="C",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        self.set_font("DejaVu", "", 11)
        self.cell(
            0, 7,
            f"Theme : {self.topic_display}",
            align="C",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        self.set_y(32)
        self.ln(2)

    def draw_section_header(self, title: str):
        """Coloured section label."""
        self.ln(4)
        self.set_fill_color(*COLOR_ACCENT)
        self.set_text_color(*COLOR_HEADER_TEXT)
        self.set_font("DejaVu", "B", 10)
        self.cell(
            0, 8,
            f"  {title}",
            fill=True,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        self.ln(3)
        self.set_text_color(*COLOR_BODY)

    def draw_divider(self):
        self.set_draw_color(*COLOR_DIVIDER)
        y = self.get_y()
        self.line(15, y, 195, y)
        self.ln(3)

    def draw_source_bar(self, site_name: str, url: str):
        """Pale yellow source citation bar."""
        self.ln(3)
        self.set_fill_color(*COLOR_SOURCE_BG)
        self.set_text_color(*COLOR_SOURCE_TEXT)
        self.set_font("DejaVu", "I", 8)
        display_url = url if len(url) <= 80 else url[:77] + "..."
        text = f"  Source : {site_name}  -  {display_url}"
        self.cell(
            0, 7,
            text,
            fill=True,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        self.ln(2)
        self.set_text_color(*COLOR_BODY)

    def write_passage(self, text: str):
        self.set_font("DejaVu", "", 11)
        self.set_text_color(*COLOR_BODY)
        self.multi_cell(0, 6, text, align="J")

    def write_questions(self, questions: list):
        """Write MCQ questions without answers."""
        for i, q in enumerate(questions, 1):
            self.set_font("DejaVu", "B", 11)
            self.set_text_color(*COLOR_BODY)
            self.multi_cell(0, 6, f"{i}.  {q['question']}", align="L")
            self.ln(1)

            choices = q.get("choices", {})
            self.set_font("DejaVu", "", 10)
            for letter in ["A", "B", "C", "D"]:
                choice_text = choices.get(letter, "")
                if choice_text:
                    self.set_x(22)
                    self.multi_cell(0, 6, f"{letter}.  {choice_text}", align="L")
            self.ln(4)

        self.set_text_color(*COLOR_BODY)

    def write_answers(self, questions: list):
        """Write answer key: question number + correct letter + full correct text + explanation."""
        for i, q in enumerate(questions, 1):
            correct_letter = q.get("answer", "?")
            choices = q.get("choices", {})
            correct_text = choices.get(correct_letter, "")
            explanation = q.get("explanation", "")

            self.set_font("DejaVu", "B", 11)
            self.set_text_color(*COLOR_BODY)
            self.multi_cell(0, 6, f"{i}.  {q['question']}", align="L")

            self.set_font("DejaVu", "", 10)
            self.set_text_color(*COLOR_ACCENT)
            self.set_x(22)
            self.multi_cell(0, 6, f"Reponse : {correct_letter}.  {correct_text}", align="L")

            if explanation:
                self.set_font("DejaVu", "I", 9)
                self.set_text_color(*COLOR_ANSWER)
                self.set_x(22)
                self.multi_cell(0, 5, f"Explication : {explanation}", align="L")

            self.ln(4)

        self.set_text_color(*COLOR_BODY)

    def write_vocabulary(self, vocabulary: list):
        """2-column grid with teal cell backgrounds."""
        col_w = (self.w - 30) / 2
        row_h = 5.5
        cell_pad = 2

        self.set_font("DejaVu", "B", 9)
        self.set_fill_color(*COLOR_ACCENT)
        self.set_text_color(*COLOR_HEADER_TEXT)
        self.cell(col_w, 7, "  Mot / Expression", fill=True, border=0)
        self.cell(
            col_w, 7,
            "  Definition & Traduction",
            fill=True, border=0,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        self.set_text_color(*COLOR_BODY)

        for item in vocabulary:
            word_text = f"{item['word']}  ({item.get('pos', '')})"
            def_text = f"{item['definition_fr']}  /  {item['translation_en']}"

            self.set_font("DejaVu", "B", 9)
            left_lines = self._count_lines(word_text, col_w - cell_pad * 2)
            self.set_font("DejaVu", "", 9)
            right_lines = self._count_lines(def_text, col_w - cell_pad * 2)
            needed_h = max(left_lines, right_lines) * row_h + cell_pad * 2

            if self.get_y() + needed_h > self.h - self.b_margin:
                self.add_page()

            x_start = self.get_x()
            y_start = self.get_y()

            self.set_fill_color(*COLOR_VOCAB_BG)
            self.rect(x_start, y_start, col_w, needed_h, "F")
            self.set_xy(x_start + cell_pad, y_start + cell_pad)
            self.set_font("DejaVu", "B", 9)
            self.multi_cell(col_w - cell_pad * 2, row_h, word_text, align="L")

            self.set_fill_color(248, 248, 248)
            self.rect(x_start + col_w, y_start, col_w, needed_h, "F")
            self.set_xy(x_start + col_w + cell_pad, y_start + cell_pad)
            self.set_font("DejaVu", "", 9)
            self.multi_cell(col_w - cell_pad * 2, row_h, def_text, align="L")

            self.set_xy(x_start, y_start + needed_h + 1)

    def _count_lines(self, text: str, width: float) -> int:
        char_w = self.get_string_width("M")
        if char_w == 0:
            return 1
        chars_per_line = max(1, int(width / (char_w * 0.6)))
        words = text.split()
        line_count = 1
        line_len = 0
        for word in words:
            word_len = len(word) + 1
            if line_len + word_len > chars_per_line:
                line_count += 1
                line_len = word_len
            else:
                line_len += word_len
        return line_count


def build_pdf(
    level: str,
    topic: str,
    text: str,
    url: str,
    site_name: str,
    exercises: dict,
    output_path: str,
) -> str:
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    pdf = FrenchExercisePDF(level, topic)
    pdf.add_page()

    # Page 1 — Paragraph
    pdf.draw_title_bar()
    pdf.draw_section_header("TEXTE")
    pdf.write_passage(text)
    pdf.draw_source_bar(site_name, url)

    # Page 2 — Questions (MCQ, no answers)
    pdf.add_page()
    pdf.draw_section_header("QUESTIONS DE COMPREHENSION")
    pdf.write_questions(exercises.get("questions", []))

    # Page 3 — Vocabulary
    pdf.add_page()
    pdf.draw_section_header("VOCABULAIRE")
    pdf.write_vocabulary(exercises.get("vocabulary", []))

    # Page 4 — Answer key
    pdf.add_page()
    pdf.draw_section_header("REPONSES")
    pdf.write_answers(exercises.get("questions", []))

    pdf.output(output_path)
    return os.path.abspath(output_path)


def build_pdf_bytes(
    level: str,
    topic: str,
    text: str,
    url: str,
    site_name: str,
    exercises: dict,
) -> bytes:
    """Build PDF and return raw bytes (no filesystem write). Used for in-memory streaming."""
    pdf = FrenchExercisePDF(level, topic)
    pdf.add_page()

    pdf.draw_title_bar()
    pdf.draw_section_header("TEXTE")
    pdf.write_passage(text)
    pdf.draw_source_bar(site_name, url)

    pdf.add_page()
    pdf.draw_section_header("QUESTIONS DE COMPREHENSION")
    pdf.write_questions(exercises.get("questions", []))

    pdf.add_page()
    pdf.draw_section_header("VOCABULAIRE")
    pdf.write_vocabulary(exercises.get("vocabulary", []))

    pdf.add_page()
    pdf.draw_section_header("REPONSES")
    pdf.write_answers(exercises.get("questions", []))

    return bytes(pdf.output())


def main():
    parser = argparse.ArgumentParser(description="Build French exercise PDF.")
    parser.add_argument("--level", required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--site_name", required=True)
    parser.add_argument("--exercises", required=True, help="JSON string from generate_exercises.py")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    try:
        exercises = json.loads(args.exercises)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": "invalid_exercises_json", "message": str(e)}))
        sys.exit(1)

    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f".tmp/exercise_{args.level}_{args.topic}_{timestamp}.pdf"
    else:
        output_path = args.output

    try:
        saved_path = build_pdf(
            level=args.level,
            topic=args.topic,
            text=args.text,
            url=args.url,
            site_name=args.site_name,
            exercises=exercises,
            output_path=output_path,
        )
        print(saved_path)
    except Exception as e:
        print(json.dumps({"error": "pdf_generation_failed", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
