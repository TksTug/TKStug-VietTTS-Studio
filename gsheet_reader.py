import re
import urllib.parse
import csv
import io
import requests

class GSheetReader:
    def __init__(self):
        pass

    @staticmethod
    def extract_spreadsheet_id(url_or_id: str) -> str:
        """Extract Spreadsheet ID from URL or return raw ID"""
        url_or_id = url_or_id.strip()
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url_or_id)
        if match:
            return match.group(1)
        if len(url_or_id) > 20 and '/' not in url_or_id:
            return url_or_id
        return ""

    @staticmethod
    def extract_gid(url: str) -> str:
        """Extract gid parameter from URL if present"""
        match = re.search(r'[#&?]gid=([0-9]+)', url)
        if match:
            return match.group(1)
        return "0"

    def fetch_sheet_rows(self, sheet_url_or_id: str, column_name_or_index: str = "A", cookie_str: str = "") -> list[str]:
        """
        Fetch rows from Google Sheet via public CSV export, direct URL with cookies, or text.
        """
        text_input = sheet_url_or_id.strip()
        
        # If input text is not a URL, treat it as a line-by-line list directly!
        if "\n" in text_input or (not text_input.startswith("http") and not text_input.startswith("docs.google")):
            lines = [line.strip() for line in text_input.splitlines() if line.strip()]
            return lines

        sheet_id = self.extract_spreadsheet_id(sheet_url_or_id)
        if not sheet_id:
            lines = [line.strip() for line in text_input.splitlines() if line.strip()]
            return lines

        gid = self.extract_gid(sheet_url_or_id)
        
        # Try export CSV URL
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if cookie_str and cookie_str.strip():
            headers["Cookie"] = cookie_str.strip()

        response = requests.get(csv_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            # Try html pubexport fallback
            pub_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/pub?output=csv&gid={gid}"
            resp_pub = requests.get(pub_url, headers=headers, timeout=15)
            if resp_pub.status_code == 200:
                response = resp_pub
            else:
                raise Exception(
                    "Google Sheet bị khóa hoặc chưa được chia sẻ công khai!\n\n"
                    "💡 BẠN CÓ THỂ DÙNG 2 CÁCH CỰC DỄ SAU:\n"
                    "• Cách 1 (Nhanh nhất): Mở Google Sheet -> Bôi đen cột tên file -> Nhấn Ctrl+C -> Nhấp nút '📋 DÁN TRỰC TIẾP DẠNG CỘT' trên ứng dụng.\n"
                    "• Cách 2: Trên Google Sheet chọn Tệp (File) -> Chia sẻ -> Xuất ra Web (Publish to web) dưới dạng CSV."
                )

        csv_content = response.content.decode('utf-8-sig', errors='ignore')
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        if not rows:
            return []

        # Determine target column index
        col_idx = 0
        col_str = str(column_name_or_index).strip().upper()

        if col_str.isdigit():
            col_idx = int(col_str)
        elif len(col_str) == 1 and 'A' <= col_str <= 'Z':
            col_idx = ord(col_str) - ord('A')
        else:
            headers_list = [h.strip() for h in rows[0]]
            for i, h in enumerate(headers_list):
                if h.lower() == col_str.lower():
                    col_idx = i
                    break

        filenames = []
        for row in rows:
            if col_idx < len(row):
                val = row[col_idx].strip()
                if val and not val.startswith("="):
                    filenames.append(val)

        if filenames and filenames[0].lower() in ['tên file', 'filename', 'file_name', 'tên', 'name', 'stt']:
            filenames = filenames[1:]

        return filenames
