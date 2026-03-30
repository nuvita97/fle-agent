#!/usr/bin/env python3
"""
Send a French exercise PDF by email via the Gmail API (OAuth2).

Uses a stored refresh token — no browser interaction at runtime.
Run tools/get_gmail_token.py once locally to obtain the refresh token.

Usage:
    python tools/send_email.py \
        --pdf .tmp/exercise_B1_voyages_tourisme_20260321_122016.pdf \
        --level B1 \
        --topic voyages_tourisme \
        --source-url "https://example.com/article" \
        --source-name "example.com" \
        --recipient "user@example.com" \
        --manage-url "https://yourapp.com/manage?token=xxx" \
        --unsubscribe-url "https://yourapp.com/unsubscribe?token=xxx"

Required .env keys:
    GMAIL_CLIENT_ID       OAuth2 client ID (from Google Cloud Console)
    GMAIL_CLIENT_SECRET   OAuth2 client secret
    GMAIL_REFRESH_TOKEN   Refresh token (run tools/get_gmail_token.py to obtain)
    EMAIL_SENDER          Your Gmail address (must match the Google account used for OAuth)

Optional .env keys:
    EMAIL_RECIPIENT       fallback recipient (overridden by --recipient flag)

Output (stdout JSON):
    {"status": "sent", "recipient": "...", "pdf": "..."}

On failure, exits with code 1 and prints:
    {"error": "...", "message": "..."}
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

TOPIC_DISPLAY = {
    "vie_quotidienne":        "Vie quotidienne & Société",
    "sante_bien_etre":        "Santé & Bien-être",
    "education_apprentissage": "Éducation & Apprentissage",
    "voyages_tourisme":       "Voyages & Mobilité",
    "environnement_ecologie": "Environnement & Écologie",
    "technologie_numerique":  "Technologies & Numérique",
    "culture_histoire":       "Culture, Arts & Histoire",
}


def build_html_body(
    level: str,
    topic: str,
    source_url: str = "",
    source_name: str = "",
    manage_url: str = "",
    unsubscribe_url: str = "",
    recipient_name: str = "",
) -> str:
    topic_display = TOPIC_DISPLAY.get(topic, topic.replace("_", " ").title())
    greeting = f"Bonjour {recipient_name}\u00a0!" if recipient_name else "Bonjour\u00a0!"
    MONTHS_FR = ["janvier","février","mars","avril","mai","juin",
                 "juillet","août","septembre","octobre","novembre","décembre"]
    now = datetime.now()
    date_str = f"{now.day} {MONTHS_FR[now.month - 1]} {now.year}"

    manage_section = ""
    if manage_url or unsubscribe_url:
        links = []
        if manage_url:
            links.append(
                f'<a href="{manage_url}" style="color:#4a6fa5;text-decoration:none;font-weight:bold;">'
                "Modifier mes pr&eacute;f&eacute;rences</a>"
            )
        if unsubscribe_url:
            links.append(
                f'<a href="{unsubscribe_url}" style="color:#999999;text-decoration:none;">'
                "Se d&eacute;sabonner</a>"
            )
        manage_section = f"""
          <!-- Manage preferences -->
          <tr>
            <td style="background-color:#f4f6f9;padding:14px 32px;text-align:center;
                       border-top:1px solid #e0e6ef;">
              <p style="margin:0;font-size:12px;color:#888888;">
                {' &nbsp;&middot;&nbsp; '.join(links)}
              </p>
            </td>
          </tr>"""

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Exercice de Fran&ccedil;ais — &Eacute;voli FLE Agent</title>
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
              <p style="margin:0 0 4px;color:rgba(255,255,255,0.75);font-size:12px;letter-spacing:1px;text-transform:uppercase;">
                &Eacute;voli - FLE Agent
              </p>
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
              <p style="margin:0 0 4px;color:#888888;font-size:12px;">
                {date_str}
              </p>
              <p style="margin:0 0 16px;color:#1a1a1a;font-size:15px;line-height:1.7;">
                {greeting}
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

              <p style="margin:24px 0 0;color:#1a1a1a;font-size:15px;line-height:1.7;">
                Bonne &eacute;tude&nbsp;! &#127891;
              </p>
            </td>
          </tr>
{manage_section}
          <!-- Branding footer -->
          <tr>
            <td style="background-color:#f4f6f9;padding:16px 32px;text-align:center;
                       border-top:1px solid #e0e6ef;">
              <p style="margin:0;color:#999999;font-size:12px;">
                G&eacute;n&eacute;r&eacute; par <strong>&Eacute;voli - FLE Agent</strong>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def build_welcome_html(
    name: str,
    level: str,
    topic: str,
    manage_url: str,
    unsubscribe_url: str,
) -> str:
    topic_display = TOPIC_DISPLAY.get(topic, topic.replace("_", " ").title())
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bienvenue sur &Eacute;voli - FLE Agent</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f6f9;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f9;padding:30px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background-color:#ffffff;border-radius:8px;overflow:hidden;
                      box-shadow:0 2px 8px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background-color:#4a6fa5;padding:28px 32px;text-align:center;">
              <p style="margin:0 0 4px;color:rgba(255,255,255,0.75);font-size:12px;letter-spacing:1px;text-transform:uppercase;">
                &Eacute;voli - FLE Agent
              </p>
              <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:bold;">
                Bienvenue, {name}&nbsp;! &#127881;
              </h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:28px 32px;">
              <p style="margin:0 0 16px;color:#1a1a1a;font-size:15px;line-height:1.7;">
                Vous &ecirc;tes maintenant inscrit(e) &agrave; la newsletter hebdomadaire
                <strong>&Eacute;voli - FLE Agent</strong>.
              </p>

              <!-- Preferences summary -->
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background-color:#eef2f8;border-radius:6px;margin:16px 0;">
                <tr>
                  <td style="padding:16px 20px;">
                    <p style="margin:0 0 8px;color:#1a1a1a;font-size:14px;font-weight:bold;">
                      Vos pr&eacute;f&eacute;rences :
                    </p>
                    <p style="margin:0;color:#333333;font-size:14px;line-height:2;">
                      &#127891;&nbsp; Niveau : <strong>{level}</strong><br>
                      &#127775;&nbsp; Th&egrave;me : <strong>{topic_display}</strong>
                    </p>
                  </td>
                </tr>
              </table>

              <p style="margin:16px 0;color:#1a1a1a;font-size:15px;line-height:1.7;">
                Chaque lundi &agrave; midi, vous recevrez un exercice PDF personnalis&eacute;
                selon votre niveau et votre th&egrave;me.
              </p>

              <p style="margin:0;color:#555555;font-size:14px;line-height:1.7;">
                Vous pouvez &agrave; tout moment modifier vos pr&eacute;f&eacute;rences ou
                vous d&eacute;sabonner via les liens ci-dessous.
              </p>
            </td>
          </tr>

          <!-- Action links -->
          <tr>
            <td style="background-color:#f4f6f9;padding:16px 32px;text-align:center;
                       border-top:1px solid #e0e6ef;">
              <p style="margin:0;font-size:13px;">
                <a href="{manage_url}" style="color:#4a6fa5;text-decoration:none;font-weight:bold;">
                  Modifier mes pr&eacute;f&eacute;rences
                </a>
                &nbsp;&middot;&nbsp;
                <a href="{unsubscribe_url}" style="color:#999999;text-decoration:none;">
                  Se d&eacute;sabonner
                </a>
              </p>
            </td>
          </tr>

          <!-- Branding footer -->
          <tr>
            <td style="background-color:#f4f6f9;padding:12px 32px;text-align:center;">
              <p style="margin:0;color:#999999;font-size:12px;">
                G&eacute;n&eacute;r&eacute; par <strong>&Eacute;voli - FLE Agent</strong>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def load_config() -> "dict | None":
    required = ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN", "EMAIL_SENDER"]
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
                       f"Add them to your .env file. Run tools/get_gmail_token.py to obtain GMAIL_REFRESH_TOKEN.",
        }))
        return None

    config["EMAIL_RECIPIENT"] = os.getenv("EMAIL_RECIPIENT", "")
    return config


def _gmail_send(
    config: dict,
    to: str,
    subject: str,
    html: str,
    pdf_bytes: "bytes | None" = None,
    pdf_filename: "str | None" = None,
) -> "dict | None":
    """Send via Gmail API. Returns error dict or None on success."""
    try:
        creds = Credentials(
            token=None,
            refresh_token=config["GMAIL_REFRESH_TOKEN"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config["GMAIL_CLIENT_ID"],
            client_secret=config["GMAIL_CLIENT_SECRET"],
            scopes=["https://www.googleapis.com/auth/gmail.send"],
        )
        creds.refresh(Request())

        msg = MIMEMultipart("mixed")
        msg["From"] = config["EMAIL_SENDER"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html, "html", "utf-8"))

        if pdf_bytes and pdf_filename:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(pdf_bytes)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{pdf_filename}"')
            msg.attach(part)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service = build("gmail", "v1", credentials=creds)
        service.users().messages().send(userId="me", body={"raw": raw}).execute()

    except HttpError as e:
        return {"error": "gmail_api_error", "message": str(e)}
    except Exception as e:
        return {"error": "gmail_error", "message": str(e)}
    return None


def send(
    pdf_path: str,
    level: str,
    topic: str,
    source_url: str,
    source_name: str,
    recipient: str = "",
    manage_url: str = "",
    unsubscribe_url: str = "",
    recipient_name: str = "",
    pdf_filename: str = "",
) -> dict:
    config = load_config()
    if config is None:
        sys.exit(1)

    to = recipient or config["EMAIL_RECIPIENT"]
    if not to:
        return {"error": "missing_recipient", "message": "No recipient specified. Pass --recipient or set EMAIL_RECIPIENT in .env."}

    if not os.path.isfile(pdf_path):
        return {"error": "pdf_not_found", "message": f"PDF file not found: {pdf_path}"}

    topic_display = TOPIC_DISPLAY.get(topic, topic.replace("_", " ").title())
    subject = f"Votre exercice de français - Niveau {level} | {topic_display}"

    html_body = build_html_body(
        level, topic, source_url, source_name,
        manage_url=manage_url,
        unsubscribe_url=unsubscribe_url,
        recipient_name=recipient_name,
    )

    pdf_filename = pdf_filename or os.path.basename(pdf_path)
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    err = _gmail_send(config, to, subject, html_body, pdf_bytes=pdf_bytes, pdf_filename=pdf_filename)
    if err:
        return err

    return {"status": "sent", "recipient": to, "pdf": pdf_filename}


def send_welcome(
    recipient: str,
    name: str,
    level: str,
    topic: str,
    manage_url: str,
    unsubscribe_url: str,
) -> dict:
    """Send a welcome email (no PDF) after a new subscription."""
    config = load_config()
    if config is None:
        return {"error": "missing_env_keys", "message": "GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, or GMAIL_REFRESH_TOKEN not set."}

    html_body = build_welcome_html(name, level, topic, manage_url, unsubscribe_url)

    err = _gmail_send(config, recipient, "Bienvenue sur Évoli - FLE Agent 🎉", html_body)
    if err:
        return err

    return {"status": "sent", "recipient": recipient}


def main():
    parser = argparse.ArgumentParser(description="Send French exercise PDF by email.")
    parser.add_argument("--pdf", required=True, help="Path to the PDF file")
    parser.add_argument("--level", required=True, help="CEFR level (A1–C1)")
    parser.add_argument("--topic", required=True, help="Topic key")
    parser.add_argument("--source-url", required=True, dest="source_url", help="Source article URL")
    parser.add_argument("--source-name", required=True, dest="source_name", help="Source site name")
    parser.add_argument("--recipient", default="", help="Override recipient email")
    parser.add_argument("--recipient-name", default="", dest="recipient_name", help="Recipient first name")
    parser.add_argument("--manage-url", default="", dest="manage_url", help="Manage preferences URL")
    parser.add_argument("--unsubscribe-url", default="", dest="unsubscribe_url", help="Unsubscribe URL")
    args = parser.parse_args()

    result = send(
        pdf_path=args.pdf,
        level=args.level,
        topic=args.topic,
        source_url=args.source_url,
        source_name=args.source_name,
        recipient=args.recipient,
        recipient_name=args.recipient_name,
        manage_url=args.manage_url,
        unsubscribe_url=args.unsubscribe_url,
    )

    if "error" in result:
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
