import os

BASE = os.path.dirname(os.path.abspath(__file__))
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def main():
    creds_path = os.path.join(BASE, "credentials.json")
    token_path = os.path.join(BASE, "token.json")

    if not os.path.exists(creds_path):
        print("ERROR: credentials.json not found.")
        print("Steps:")
        print("  1. Go to console.cloud.google.com")
        print("  2. Create a project → Enable Google Calendar API")
        print("  3. APIs & Services → Credentials → Create OAuth 2.0 Client ID (Desktop)")
        print("  4. Download JSON → save as credentials.json next to this script")
        return

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(token_path, "w") as f:
        f.write(creds.to_json())

    print(f"Saved {token_path}")
    print("Run main.py to start the display.")

if __name__ == "__main__":
    main()
