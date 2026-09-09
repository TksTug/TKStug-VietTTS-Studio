import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class GDriveOAuthEngine:
    def __init__(self):
        self.creds = None
        self.service = None

    def get_credentials(self) -> Credentials:
        """Get or refresh OAuth2 credentials for private Google Drive access"""
        token_path = os.path.join(os.path.expanduser("~"), ".viet_gdrive_token.json")
        
        if os.path.exists(token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            except Exception:
                self.creds = None

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception:
                    self.creds = None
            
        if self.creds:
            with open(token_path, "w") as token_file:
                token_file.write(self.creds.to_json())
            self.service = build('drive', 'v3', credentials=self.creds)

        return self.creds

    def login_interactively(self, client_config: dict = None) -> bool:
        """Launch browser login window for user to authorize private Drive access"""
        token_path = os.path.join(os.path.expanduser("~"), ".viet_gdrive_token.json")

        if not client_config:
            # Standard desktop client credentials configuration
            client_config = {
                "installed": {
                    "client_id": "717762328687-qb16g83d46mlq103ae922b05g3v6kcp2.apps.googleusercontent.com",
                    "project_id": "gdrive-downloader-app",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": "GOCSPX-dummy_secret_for_desktop",
                    "redirect_uris": ["http://localhost"]
                }
            }

        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        self.creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token_file:
            token_file.write(self.creds.to_json())

        self.service = build('drive', 'v3', credentials=self.creds)
        return True

    def list_private_folder_files(self, folder_id: str) -> list[dict]:
        """List all files in private Google Drive folder using authenticated API"""
        if not self.service:
            self.get_credentials()
            if not self.service:
                raise Exception("Chưa đăng nhập Google Account! Vui lòng nhấp nút '🔐 Đăng Nhập Google Account'!")

        query = f"'{folder_id}' in parents and trashed = false"
        results = self.service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, size)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=1000
        ).execute()

        items = results.get('files', [])
        file_list = []
        for item in items:
            file_list.append({
                "id": item["id"],
                "name": item["name"],
                "size": int(item.get("size", 0))
            })
        return file_list

    def download_private_file(self, file_id: str, output_path: str):
        """Download private file using authenticated API"""
        if not self.service:
            self.get_credentials()

        request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)
        with open(output_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

if __name__ == "__main__":
    engine = GDriveOAuthEngine()
    print("GDriveOAuthEngine module ready.")
