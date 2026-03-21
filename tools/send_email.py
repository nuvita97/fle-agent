#!/usr/bin/env python3
"""
Send a French exercise PDF by email via Gmail SMTP.

Usage:
    python tools/send_email.py \
        --pdf .tmp/exercise_B1_voyages_tourisme_20260321_122016.pdf \
        --level B1 \
        --topic voyages_tourisme \
        --source-url "https://example.com/article" \
        --source-name "example.com"

Required .env keys:
    EMAIL_SENDER        your Gmail address
    EMAIL_APP_PASSWORD  Gmail App Password (16-char, from Google Account > Security)
    EMAIL_RECIPIENT     recipient email address

Optional .env keys:
    EMAIL_SMTP_HOST     default: smtp.gmail.com
    EMAIL_SMTP_PORT     default: 587

Output (stdout JSON):
    {"status": "sent", "recipient": "...", "pdf": "..."}

On failure, exits with code 1 and prints:
    {"error": "...", "message": "..."}
"""

import argparse
import json
import os
import smtplib
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

TOPIC_DISPLAY = {
    "vie_quotidienne": "Vie Quotidienne",
    "voyages_tourisme": "Voyages & Tourisme",
    "environnement_ecologie": "Environnement & Ecologie",
    "technologie_numerique": "Technologie & Numerique",
    "culture_histoire": "Culture & Histoire",
}


def build_html_body(level: str, topic: str, source_url: str, source_name: str) -> str:
    topic_display = TOPIC_DISPLAY.get(topic, topic.replace("_", " ").title())

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Exercice de Francais</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f6f9;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f9;padding:30px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background-color:#ffffff;border-radius:8px;overflow:hidden;
                      box-shadow:0 2px 8px rgba(0,0,0,0.08);">

          <!-- Header bar -->
          <tr>
            <td style="background-color:#4a6fa5;padding:28px 32px;text-align:center;">
              <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:bold;letter-spacing:0.5px;">
                Exercice de Fran&ccedil;ais
              </h1>
              <p style="margin:6px 0 0;color:#d0dff0;font-size:15px;">
                Niveau&nbsp;<strong>{level}</strong>
              </p>
            </td>
          </tr>

          <!-- Topic badge -->
          <tr>
            <td style="background-color:#eef2f8;padding:14px 32px;text-align:center;
                       border-bottom:1px solid #dde4ee;">
              <span style="display:inline-block;background-color:#4a6fa5;color:#ffffff;
                           border-radius:20px;padding:4px 18px;font-size:13px;font-weight:bold;">
                {topic_display}
              </span>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:28px 32px;">
              <p style="margin:0 0 16px;color:#1a1a1a;font-size:15px;line-height:1.7;">
                Bonjour,
              </p>
              <p style="margin:0 0 16px;color:#1a1a1a;font-size:15px;line-height:1.7;">
                Votre exercice de fran&ccedil;ais de niveau <strong>{level}</strong> sur le
                th&egrave;me <strong>{topic_display}</strong> est pr&ecirc;t.
                Vous le trouverez en pi&egrave;ce jointe.
              </p>

              <!-- What's inside box -->
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background-color:#f0f7f6;border-left:4px solid #4a6fa5;
                            border-radius:0 6px 6px 0;margin:20px 0;">
                <tr>
                  <td style="padding:16px 20px;">
                    <p style="margin:0 0 10px;color:#1a1a1a;font-size:14px;font-weight:bold;">
                      Contenu du PDF :
                    </p>
                    <ul style="margin:0;padding-left:20px;color:#333333;font-size:14px;line-height:2;">
                      <li>&#128196;&nbsp; Texte en fran&ccedil;ais (niveau {level})</li>
                      <li>&#10067;&nbsp; 5 questions &agrave; choix multiples (A / B / C / D)</li>
                      <li>&#128218;&nbsp; Vocabulaire cl&eacute; avec d&eacute;finitions et traductions</li>
                      <li>&#9989;&nbsp; Corrig&eacute; complet en derni&egrave;re page</li>
                    </ul>
                  </td>
                </tr>
              </table>

              <!-- Source -->
              <p style="margin:20px 0 6px;color:#555555;font-size:13px;">
                <strong>Source du texte&nbsp;:</strong>
                <a href="{source_url}" style="color:#4a6fa5;text-decoration:none;">
                  {source_name}
                </a>
                &mdash;
                <a href="{source_url}" style="color:#888888;font-size:12px;text-decoration:none;
                                              word-break:break-all;">
                  {source_url}
                </a>
              </p>

              <p style="margin:24px 0 0;color:#1a1a1a;font-size:15px;line-height:1.7;">
                Bonne &eacute;tude&nbsp;! &#127891;
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#f4f6f9;padding:16px 32px;text-align:center;
                       border-top:1px solid #e0e6ef;">
              <p style="margin:0;color:#999999;font-size:12px;">
                G&eacute;n&eacute;r&eacute; par <strong>FLE-agent</strong>
                &mdash; French Language Exercise Automation
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def load_config() -> dict | None:
    required = ["EMAIL_SENDER", "EMAIL_APP_PASSWORD", "EMAIL_RECIPIENT"]
    config = {}
    missing = []
    for key in required:
        val = os.getenv(key)
        if not val:
            missing.append(key)
        else:
            config[key] = val

    if missing:
        print(json.dumps({
            "error": "missing_env_keys",
            "message": f"Missing required .env keys: {', '.join(missing)}. "
                       f"Add them to your .env file.",
        }))
        return None

    config["EMAIL_SMTP_HOST"] = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
    config["EMAIL_SMTP_PORT"] = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    return config


def send(
    pdf_path: str,
    level: str,
    topic: str,
    source_url: str,
    source_name: str,
) -> dict:
    config = load_config()
    if config is None:
        sys.exit(1)

    if not os.path.isfile(pdf_path):
        return {
            "error": "pdf_not_found",
            "message": f"PDF file not found: {pdf_path}",
        }

    topic_display = TOPIC_DISPLAY.get(topic, topic.replace("_", " ").title())
    subject = f"Votre exercice de francais - Niveau {level} | {topic_display}"

    # Build message
    msg = MIMEMultipart("alternative" if True else "mixed")
    msg["From"] = config["EMAIL_SENDER"]
    msg["To"] = config["EMAIL_RECIPIENT"]
    msg["Subject"] = subject

    # Attach HTML body
    html_body = build_html_body(level, topic, source_url, source_name)
    msg_html = MIMEMultipart("mixed")
    msg_html.attach(MIMEText(html_body, "html", "utf-8"))

    # Switch to mixed for attachment
    msg = MIMEMultipart("mixed")
    msg["From"] = config["EMAIL_SENDER"]
    msg["To"] = config["EMAIL_RECIPIENT"]
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Attach PDF
    pdf_filename = os.path.basename(pdf_path)
    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{pdf_filename}"')
    msg.attach(part)

    # Send
    try:
        with smtplib.SMTP(config["EMAIL_SMTP_HOST"], config["EMAIL_SMTP_PORT"]) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config["EMAIL_SENDER"], config["EMAIL_APP_PASSWORD"])
            server.sendmail(config["EMAIL_SENDER"], config["EMAIL_RECIPIENT"], msg.as_string())
    except smtplib.SMTPAuthenticationError:
        return {
            "error": "auth_failed",
            "message": (
                "Gmail authentication failed. Make sure EMAIL_APP_PASSWORD is a Gmail App "
                "Password (not your regular password). Generate one at: "
                "https://myaccount.google.com/apppasswords"
            ),
        }
    except smtplib.SMTPException as e:
        return {"error": "smtp_error", "message": str(e)}
    except OSError as e:
        return {"error": "connection_error", "message": str(e)}

    return {
        "status": "sent",
        "recipient": config["EMAIL_RECIPIENT"],
        "pdf": pdf_filename,
    }


def main():
    parser = argparse.ArgumentParser(description="Send French exercise PDF by email.")
    parser.add_argument("--pdf", required=True, help="Path to the PDF file")
    parser.add_argument("--level", required=True, help="CEFR level (A1–C1)")
    parser.add_argument("--topic", required=True, help="Topic key")
    parser.add_argument("--source-url", required=True, dest="source_url", help="Source article URL")
    parser.add_argument("--source-name", required=True, dest="source_name", help="Source site name")
    args = parser.parse_args()

    result = send(
        pdf_path=args.pdf,
        level=args.level,
        topic=args.topic,
        source_url=args.source_url,
        source_name=args.source_name,
    )

    if "error" in result:
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
