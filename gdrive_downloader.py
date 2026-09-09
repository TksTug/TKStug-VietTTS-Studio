import os
import re
import requests
import gdown
import urllib.parse
from gdrive_oauth import GDriveOAuthEngine

class GDriveDownloader:
    def __init__(self):
        self.oauth_engine = GDriveOAuthEngine()

    @staticmethod
    def extract_folder_id(url_or_id: str) -> str:
        """Extract Google Drive Folder ID from URL or return raw ID"""
        url_or_id = url_or_id.strip()
        match = re.search(r'/folders/([a-zA-Z0-9-_]+)', url_or_id)
        if match:
            return match.group(1)
        if len(url_or_id) > 20 and '/' not in url_or_id:
            return url_or_id
        return ""

    def list_folder_files(self, folder_url_or_id: str, cookie_str: str = "", use_oauth: bool = False) -> list[dict]:
        """
        List files in Google Drive folder using direct scraper or OAuth API for private folders.
        """
        folder_id = self.extract_folder_id(folder_url_or_id)
        if not folder_id:
            raise ValueError("Đường dẫn Google Drive Folder không hợp lệ!")

        # Try OAuth API if requested or authenticated
        if use_oauth or self.oauth_engine.get_credentials():
            try:
                return self.oauth_engine.list_private_folder_files(folder_id)
            except Exception as oauth_err:
                if use_oauth:
                    raise oauth_err

        # Try direct public/session scraping
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if cookie_str and cookie_str.strip():
            headers["Cookie"] = cookie_str.strip()

        resp = requests.get(folder_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            raise Exception(
                f"Thư mục Google Drive bị khóa riêng tư (Mã lỗi {resp.status_code})!\n\n"
                "💡 ĐỂ TẢI ĐƯỢC FILE TỪ THƯ MỤC RIÊNG TƯ, BẠN CHỌN 1 TRONG 2 CÁCH SAU:\n"
                "• Cách 1 (Rất dễ - 3 giây): Trên Google Drive, nhấp chuột phải thư mục -> Chọn Chia sẻ (Share) -> Chuyển thành 'Bất kỳ ai có link đều xem được'.\n"
                "• Cách 2: Nhấp nút '🔐 ĐĂNG NHẬP GOOGLE ACCOUNT' trên ứng dụng để xác thực tài khoản của bạn."
            )

        html = resp.text
        files = []
        seen_ids = set()

        matches = re.findall(r'\["([a-zA-Z0-9-_]{25,50})",\s*"([^"\\]*(?:\\.[^"\\]*)*)"', html)
        for f_id, f_name in matches:
            if f_id not in seen_ids and not f_name.startswith("http"):
                clean_name = f_name.encode('utf-8').decode('unicode-escape', errors='ignore') if '\\u' in f_name else f_name
                seen_ids.add(f_id)
                files.append({
                    "id": f_id,
                    "name": clean_name.strip()
                })

        # If html parsing yielded no files, try OAuth if available
        if not files:
            try:
                files = self.oauth_engine.list_private_folder_files(folder_id)
            except Exception:
                pass

        return files

    def download_file_by_id(self, file_id: str, output_path: str, cookie_str: str = "", use_oauth: bool = False) -> str:
        """
        Download file by ID using OAuth or direct stream
        """
        if use_oauth or self.oauth_engine.get_credentials():
            try:
                self.oauth_engine.download_private_file(file_id, output_path)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return output_path
            except Exception:
                pass

        url = f"https://drive.google.com/uc?export=download&confirm=t&id={file_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        if cookie_str and cookie_str.strip():
            headers["Cookie"] = cookie_str.strip()

        resp = requests.get(url, headers=headers, stream=True, timeout=30)
        
        confirm_token = None
        for key, val in resp.cookies.items():
            if key.startswith('download_warning'):
                confirm_token = val
                break
        
        if confirm_token:
            url = f"https://drive.google.com/uc?export=download&confirm={confirm_token}&id={file_id}"
            resp = requests.get(url, headers=headers, stream=True, timeout=30)

        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=32768):
                    if chunk:
                        f.write(chunk)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path

        # Fallback to gdown
        url_gdown = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url=url_gdown, output=output_path, quiet=True, fuzzy=True)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
        else:
            raise Exception("File bị khóa riêng tư hoặc không đủ quyền tải.")

    def search_and_download(self, target_name: str, drive_files: list[dict], dest_folder: str, exact_match: bool = False, cookie_str: str = "", use_oauth: bool = False) -> dict:
        target_name_clean = target_name.strip().lower()
        target_base = os.path.splitext(target_name_clean)[0]

        matched_file = None
        for df in drive_files:
            fname = df["name"].strip()
            fname_clean = fname.lower()
            fbase = os.path.splitext(fname_clean)[0]

            if exact_match:
                if fname_clean == target_name_clean or fbase == target_base:
                    matched_file = df
                    break
            else:
                if target_name_clean in fname_clean or target_base in fbase or fbase in target_base:
                    matched_file = df
                    break

        if not matched_file:
            return {
                "status": "not_found",
                "message": f"Không tìm thấy file '{target_name}' trong Google Drive",
                "file_name": target_name,
                "saved_path": ""
            }

        output_name = matched_file["name"]
        save_path = os.path.join(dest_folder, output_name)

        try:
            self.download_file_by_id(matched_file["id"], save_path, cookie_str, use_oauth)
            file_size = os.path.getsize(save_path)
            return {
                "status": "success",
                "message": "Đã tải xong",
                "file_name": output_name,
                "saved_path": save_path,
                "size_bytes": file_size
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Lỗi tải file: {str(e)}",
                "file_name": output_name,
                "saved_path": ""
            }
