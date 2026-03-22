#!/usr/bin/env python3
"""
One-time helper to obtain a Gmail OAuth2 refresh token.

Run this locally (NOT on Render). It opens a browser for Google consent,
then prints the refresh token. Copy it into your .env and Render env vars.

Prerequisites:
  1. Create a Google Cloud project at console.cloud.google.com
  2. Enable the Gmail API
  3. Create OAuth 2.0 credentials (type: Desktop app)
  4. Add GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET to your .env

Usage:
    python tools/get_gmail_token.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

# Load .env from the project root (one level up from this script)
load_dotenv(Path(__file__).parent.parent / ".env")

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

client_id = os.getenv("GMAIL_CLIENT_ID")
client_secret = os.getenv("GMAIL_CLIENT_SECRET")

if not client_id or not client_secret:
    print("ERROR: GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET must be set in .env")
    raise SystemExit(1)

client_config = {
    "installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
    }
}

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
creds = flow.run_local_server(port=0)

print("\n" + "=" * 60)
print("SUCCESS — add these to your .env and Render env vars:")
print("=" * 60)
print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
print("=" * 60 + "\n")
