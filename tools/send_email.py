#!/usr/bin/env python3
"""
Send a French exercise PDF by email via Gmail SMTP.

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
    EMAIL_SENDER        your Gmail address
    EMAIL_APP_PASSWORD  Gmail App Password (16-char, from Google Account > Security)

Optional .env keys:
    EMAIL_RECIPIENT     fallback recipient (overridden by --recipient flag)
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


def build_html_body(
    level: str,
    topic: str,
    source_url: str,
    source_name: str,
    manage_url: str = "",
    unsubscribe_url: str = "",
    recipient_name: str = "",
) -> str:
    topic_display = TOPIC_DISPLAY.get(topic, topic.replace("_", " ").title())
    greeting = f"Bonjour {recipient_name}," if recipient_name else "Bonjour,"

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
  <title>Exercice de Fran&ccedil;ais — Lumi&egrave;re FLE Agent</title>
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
                Lumi&egrave;re &mdash; FLE Agent
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
{manage_section}
          <!-- Branding footer -->
          <tr>
            <td style="background-color:#f4f6f9;padding:16px 32px;text-align:center;
                       border-top:1px solid #e0e6ef;">
              <p style="margin:0;color:#999999;font-size:12px;">
                G&eacute;n&eacute;r&eacute; par <strong>Lumi&egrave;re - FLE Agent</strong>
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
  <title>Bienvenue sur Lumi&egrave;re - FLE Agent</title>
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
                Lumi&egrave;re &mdash; FLE Agent
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
                <strong>Lumi&egrave;re &mdash; FLE Agent</strong>.
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
                G&eacute;n&eacute;r&eacute; par <strong>Lumi&egrave;re - FLE Agent</strong>
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
    required = ["EMAIL_SENDER", "EMAIL_APP_PASSWORD"]
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

    config["EMAIL_RECIPIENT"] = os.getenv("EMAIL_RECIPIENT", "")
    config["EMAIL_SMTP_HOST"] = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
    config["EMAIL_SMTP_PORT"] = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    return config


def _smtp_send(config: dict, recipient: str, msg) -> dict | None:
    """Send a pre-built MIME message. Returns error dict or None on success."""
    try:
        with smtplib.SMTP(config["EMAIL_SMTP_HOST"], config["EMAIL_SMTP_PORT"], timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config["EMAIL_SENDER"], config["EMAIL_APP_PASSWORD"])
            server.sendmail(config["EMAIL_SENDER"], recipient, msg.as_string())
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

    msg = MIMEMultipart("mixed")
    msg["From"] = config["EMAIL_SENDER"]
    msg["To"] = to
    msg["Subject"] = subject

    html_body = build_html_body(
        level, topic, source_url, source_name,
        manage_url=manage_url,
        unsubscribe_url=unsubscribe_url,
        recipient_name=recipient_name,
    )
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    pdf_filename = os.path.basename(pdf_path)
    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{pdf_filename}"')
    msg.attach(part)

    err = _smtp_send(config, to, msg)
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
        return {"error": "missing_env_keys", "message": "EMAIL_SENDER or EMAIL_APP_PASSWORD not set."}

    msg = MIMEMultipart("mixed")
    msg["From"] = config["EMAIL_SENDER"]
    msg["To"] = recipient
    msg["Subject"] = "Bienvenue sur Lumière - FLE Agent 🎉"

    html_body = build_welcome_html(name, level, topic, manage_url, unsubscribe_url)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    err = _smtp_send(config, recipient, msg)
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
        manage_url=args.manage_url,
        unsubscribe_url=args.unsubscribe_url,
    )

    if "error" in result:
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
