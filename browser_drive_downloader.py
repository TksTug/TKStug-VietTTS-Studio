import os
import time
import zipfile
import re
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class BrowserDriveDownloader:
    def __init__(self):
        self.driver = None

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

    def start_browser_session(self, download_dir: str):
        """Start a visible Chrome browser session with dedicated profile"""
        options = Options()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Dedicated profile directory for this app
        tool_profile_dir = os.path.join(os.path.expanduser("~"), ".gdrive_tool_chrome_profile")
        os.makedirs(tool_profile_dir, exist_ok=True)
        options.add_argument(f"--user-data-dir={tool_profile_dir}")

        prefs = {
            "download.default_directory": os.path.abspath(download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        return self.driver

    def auto_download_selected_files(self, folder_url: str, target_names: list[str], download_dir: str, status_callback=None) -> list[dict]:
        """
        Search and download target files STRICTLY INSIDE the specified Google Drive folder only
        """
        os.makedirs(download_dir, exist_ok=True)
        results = []

        folder_id = self.extract_folder_id(folder_url)

        try:
            if not self.driver:
                self.start_browser_session(download_dir)

            if status_callback:
                status_callback(f"Đang mở Thư mục Google Drive (ID: {folder_id})...")

            # Navigate directly to the target folder URL first
            target_folder_url = f"https://drive.google.com/drive/folders/{folder_id}" if folder_id else folder_url
            self.driver.get(target_folder_url)
            time.sleep(4)

            # Check if user needs to log in
            if "accounts.google.com" in self.driver.current_url:
                if status_callback:
                    status_callback("🔑 CHÚ Ý: Vui lòng đăng nhập Google Account của bạn trên cửa sổ Chrome vừa mở...")
                for _ in range(60):
                    if "drive.google.com" in self.driver.current_url:
                        break
                    time.sleep(2)
                # Return to target folder after login
                self.driver.get(target_folder_url)
                time.sleep(3)

            for target in target_names:
                target_clean = target.strip()
                if not target_clean:
                    continue

                if status_callback:
                    status_callback(f"🔍 Đang lọc file '{target_clean}' trong đúng thư mục...")

                try:
                    # Construct search query scoped STRICTLY inside target folder: 'FOLDER_ID' in parents
                    if folder_id:
                        query_str = f"'{folder_id}' in parents and fullText contains '{target_clean}'"
                        scoped_url = f"https://drive.google.com/drive/search?q={urllib.parse.quote(query_str)}"
                        self.driver.get(scoped_url)
                        time.sleep(3.5)
                    else:
                        # Fallback to folder page navigation
                        self.driver.get(target_folder_url)
                        time.sleep(3)

                    # Look for items matching target
                    elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{target_clean}')]")
                    if not elements:
                        base_target = os.path.splitext(target_clean)[0]
                        elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{base_target}')]")

                    if elements:
                        target_elem = None
                        for el in elements:
                            if el.is_displayed():
                                target_elem = el
                                break

                        if not target_elem and len(elements) > 0:
                            target_elem = elements[0]

                        if target_elem:
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", target_elem)
                            time.sleep(0.5)
                            target_elem.click()
                            time.sleep(1)

                            # Trigger Download: Try Toolbar Download button or Shift+D
                            toolbar_buttons = self.driver.find_elements(By.XPATH, "//div[@data-tooltip='Tải xuống' or @aria-label='Tải xuống' or @data-tooltip='Download' or @aria-label='Download']")
                            if toolbar_buttons and toolbar_buttons[0].is_displayed():
                                toolbar_buttons[0].click()
                            else:
                                webdriver.ActionChains(self.driver).key_down(Keys.SHIFT).send_keys("d").key_up(Keys.SHIFT).perform()

                            time.sleep(3)
                            results.append({
                                "target_name": target,
                                "status": "success",
                                "message": "Đã kích hoạt tải file trong thư mục",
                                "saved_path": os.path.join(download_dir, target_clean)
                            })
                        else:
                            results.append({
                                "target_name": target,
                                "status": "not_found",
                                "message": "Không thấy file trong thư mục",
                                "saved_path": ""
                            })
                    else:
                        results.append({
                            "target_name": target,
                            "status": "not_found",
                            "message": "Không thấy file trong thư mục",
                            "saved_path": ""
                        })

                except Exception as e:
                    results.append({
                        "target_name": target,
                        "status": "error",
                        "message": f"Lỗi tìm file: {str(e)}",
                        "saved_path": ""
                    })

            if status_callback:
                status_callback("Hoàn tất kích hoạt tải các file đã chọn!")

            time.sleep(4)
            return results

        except Exception as e:
            if status_callback:
                status_callback(f"Lỗi Chrome: {str(e)}")
            raise e

    def process_zip_archive(self, zip_path: str, target_names: list[str], dest_folder: str, exact_match: bool = False) -> list[dict]:
        """Extract matching files from a downloaded Google Drive ZIP archive"""
        if not os.path.exists(zip_path):
            raise Exception(f"File zip không tồn tại: {zip_path}")

        os.makedirs(dest_folder, exist_ok=True)
        results = []

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            
            for target in target_names:
                target_clean = target.strip().lower()
                target_base = os.path.splitext(target_clean)[0]
                matched_name = None

                for item_name in file_list:
                    base_item = os.path.basename(item_name)
                    item_clean = base_item.lower()
                    item_base = os.path.splitext(item_clean)[0]

                    if exact_match:
                        if item_clean == target_clean or item_base == target_base:
                            matched_name = item_name
                            break
                    else:
                        if target_clean in item_clean or target_base in item_base or item_base in target_base:
                            matched_name = item_name
                            break

                if matched_name:
                    extracted_filename = os.path.basename(matched_name)
                    save_path = os.path.join(dest_folder, extracted_filename)
                    
                    with zip_ref.open(matched_name) as source, open(save_path, "wb") as target_file:
                        target_file.write(source.read())

                    size_bytes = os.path.getsize(save_path)
                    results.append({
                        "target_name": target,
                        "status": "success",
                        "message": "Đã giải nén xong",
                        "saved_path": save_path,
                        "size_bytes": size_bytes
                    })
                else:
                    results.append({
                        "target_name": target,
                        "status": "not_found",
                        "message": "Không tìm thấy trong file Zip",
                        "saved_path": "",
                        "size_bytes": 0
                    })

        return results

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
