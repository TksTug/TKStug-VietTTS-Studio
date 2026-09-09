import sys
import os
import csv
import subprocess
import webbrowser
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QCheckBox, QTableWidget,
    QTableWidgetItem, QFileDialog, QMessageBox, QFrame,
    QProgressBar, QHeaderView, QAbstractItemView, QDialog, QTextEdit
)
from PyQt6.QtGui import QColor, QFont

from gsheet_reader import GSheetReader
from gdrive_downloader import GDriveDownloader
from gdrive_oauth import GDriveOAuthEngine
from browser_drive_downloader import BrowserDriveDownloader
from ui_styles import MAIN_STYLE


class DirectTextDialog(QDialog):
    """Dialog allowing user to paste or type a list of file names directly"""
    def __init__(self, current_text="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nhập / Dán danh sách tên file trực tiếp")
        self.resize(550, 450)
        self.setStyleSheet(MAIN_STYLE)

        layout = QVBoxLayout(self)
        lbl = QLabel("Dán hoặc nhập danh sách tên file (mỗi file một dòng):")
        lbl.setStyleSheet("font-weight: bold; color: #38BDF8;")
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(current_text)
        self.text_edit.setPlaceholderText("Ví dụ:\n20260414_104001_000730\n20260414_110907_000440\n20260414_135419_001350")
        
        btn_box = QHBoxLayout()
        btn_paste = QPushButton("📋 Dán từ Clipboard")
        btn_paste.clicked.connect(self.paste_clipboard)
        
        btn_ok = QPushButton("✅ Đồng ý (Sử dụng danh sách này)")
        btn_ok.setObjectName("btnPlay")
        btn_ok.clicked.connect(self.accept)

        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_paste)
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_ok)

        layout.addWidget(lbl)
        layout.addWidget(self.text_edit)
        layout.addLayout(btn_box)

    def paste_clipboard(self):
        clipboard = QApplication.clipboard()
        self.text_edit.setPlainText(clipboard.text())

    def get_filenames(self) -> list[str]:
        text = self.text_edit.toPlainText().strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines


class DownloadWorker(QThread):
    row_updated = pyqtSignal(int, str, str, str, str)
    progress_changed = pyqtSignal(int, int)
    status_msg = pyqtSignal(str)
    finished_signal = pyqtSignal(int, int, int)

    def __init__(self, selected_items: list[tuple[int, str]], drive_link: str, dest_folder: str, exact_match: bool, cookie_str: str = "", use_oauth: bool = False):
        super().__init__()
        self.selected_items = selected_items
        self.drive_link = drive_link
        self.dest_folder = dest_folder
        self.exact_match = exact_match
        self.cookie_str = cookie_str
        self.use_oauth = use_oauth
        self.is_stopped = False

    def stop(self):
        self.is_stopped = True

    def run(self):
        try:
            total = len(self.selected_items)
            if total == 0:
                raise Exception("Chưa chọn file nào để tải!")

            self.status_msg.emit("Đang quét danh sách file trong Google Drive...")
            downloader = GDriveDownloader()
            drive_file_list = downloader.list_folder_files(self.drive_link, self.cookie_str, self.use_oauth)

            if not drive_file_list:
                raise Exception(
                    "Thư mục Google Drive bị khóa riêng tư!\n\nVui lòng nhấp nút '⚡ TẢI TỰ ĐỘNG QUA CHROME' để ứng dụng tự động mở Chrome và tải file!"
                )

            success_cnt = 0
            failed_cnt = 0

            self.status_msg.emit(f"Bắt đầu tải {total} file đã chọn từ Google Drive...")
            os.makedirs(self.dest_folder, exist_ok=True)

            for i, (row_idx, target_name) in enumerate(self.selected_items):
                if self.is_stopped:
                    self.status_msg.emit("Đã dừng tải theo yêu cầu.")
                    break

                self.row_updated.emit(row_idx, "⏳ Đang tìm & tải...", "loading", "", "")
                self.progress_changed.emit(i, total)

                res = downloader.search_and_download(
                    target_name=target_name,
                    drive_files=drive_file_list,
                    dest_folder=self.dest_folder,
                    exact_match=self.exact_match,
                    cookie_str=self.cookie_str,
                    use_oauth=self.use_oauth
                )

                if res["status"] == "success":
                    success_cnt += 1
                    size_mb = f"{res.get('size_bytes', 0) / (1024*1024):.2f} MB"
                    self.row_updated.emit(row_idx, "🟢 Thành công", "success", size_mb, res["saved_path"])
                elif res["status"] == "not_found":
                    failed_cnt += 1
                    self.row_updated.emit(row_idx, "❌ Không tìm thấy file", "not_found", "", "")
                else:
                    failed_cnt += 1
                    self.row_updated.emit(row_idx, f"⚠️ {res['message']}", "error", "", "")

                self.progress_changed.emit(i + 1, total)

            self.finished_signal.emit(total, success_cnt, failed_cnt)

        except Exception as e:
            self.status_msg.emit(f"Lỗi: {str(e)}")
            self.finished_signal.emit(len(self.selected_items), 0, len(self.selected_items))


class GSheetGDriveDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GSheet & GDrive Downloader - Tự Động Tải File Theo Tên")
        self.resize(1140, 830)
        self.setMinimumSize(940, 650)

        default_dl = os.path.join(os.path.expanduser("~"), "Downloads", "GDrive_Downloads")
        self.default_dest = default_dl
        self.active_browser = None

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setStyleSheet(MAIN_STYLE)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # 1. HEADER CARD
        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_layout = QHBoxLayout(header_card)
        
        header_info = QVBoxLayout()
        title_label = QLabel("📥 GSheet & GDrive Downloader")
        title_label.setObjectName("headerTitle")
        sub_label = QLabel("Đọc tên file từ Google Sheet (hoặc dán trực tiếp) và chọn lọc tải từ Google Drive về máy tính")
        sub_label.setObjectName("headerSubtitle")
        header_info.addWidget(title_label)
        header_info.addWidget(sub_label)

        self.badge_status = QLabel("🟢 Sẵn sàng")
        self.badge_status.setObjectName("badgeTag")
        self.badge_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addLayout(header_info)
        header_layout.addStretch()
        header_layout.addWidget(self.badge_status)

        main_layout.addWidget(header_card)

        # 2. CONFIGURATION CARD
        config_card = QFrame()
        config_card.setObjectName("settingsCard")
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(14, 14, 14, 14)

        sec_title = QLabel("⚙️ Cài đặt đường dẫn nguồn & Đích lưu file")
        sec_title.setObjectName("sectionTitle")
        config_layout.addWidget(sec_title)

        # Row 1: GSheet Link & Column Name + Read / Paste Button
        r1_layout = QHBoxLayout()
        lbl_gsheet = QLabel("Google Sheet Link / ID:")
        lbl_gsheet.setFixedWidth(160)
        self.txt_gsheet = QLineEdit()
        self.txt_gsheet.setObjectName("apiKeyInput")
        self.txt_gsheet.setPlaceholderText("Dán link Google Sheet HOẶC dán danh sách tên file tại đây...")

        lbl_col = QLabel("Cột:")
        self.txt_col = QLineEdit("A")
        self.txt_col.setObjectName("apiKeyInput")
        self.txt_col.setFixedWidth(40)
        self.txt_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_load_sheet = QPushButton("📋 LẤY TỪ SHEET")
        self.btn_load_sheet.setStyleSheet("background-color: #312E81; color: #818CF8; font-weight: bold; padding: 6px 10px;")

        self.btn_paste_direct = QPushButton("📝 DÁN TRỰC TIẾP")
        self.btn_paste_direct.setStyleSheet("background-color: #065F46; color: #34D399; font-weight: bold; padding: 6px 10px;")

        r1_layout.addWidget(lbl_gsheet)
        r1_layout.addWidget(self.txt_gsheet, stretch=1)
        r1_layout.addWidget(lbl_col)
        r1_layout.addWidget(self.txt_col)
        r1_layout.addWidget(self.btn_load_sheet)
        r1_layout.addWidget(self.btn_paste_direct)
        config_layout.addLayout(r1_layout)

        # Row 2: GDrive Folder Link + Open Chrome Button
        r2_layout = QHBoxLayout()
        lbl_gdrive = QLabel("Google Drive Folder Link:")
        lbl_gdrive.setFixedWidth(160)
        self.txt_gdrive = QLineEdit()
        self.txt_gdrive.setObjectName("apiKeyInput")
        self.txt_gdrive.setPlaceholderText("Dán đường link Thư mục Google Drive chứa các file tại đây...")

        btn_open_chrome = QPushButton("🌐 MỞ CHROME DRIVE")
        btn_open_chrome.setStyleSheet("background-color: #0284C7; color: #FFFFFF; font-size: 11px; font-weight: bold;")
        btn_open_chrome.clicked.connect(self.open_chrome_drive)

        r2_layout.addWidget(lbl_gdrive)
        r2_layout.addWidget(self.txt_gdrive, stretch=1)
        r2_layout.addWidget(btn_open_chrome)
        config_layout.addLayout(r2_layout)

        # Row 3: Destination Folder Path
        r3_layout = QHBoxLayout()
        lbl_dest = QLabel("Thư mục lưu trên máy tính:")
        lbl_dest.setFixedWidth(160)
        self.txt_dest = QLineEdit(self.default_dest)
        self.txt_dest.setObjectName("apiKeyInput")
        
        btn_browse = QPushButton("📁 Chọn thư mục...")
        btn_browse.clicked.connect(self.browse_dest_folder)

        r3_layout.addWidget(lbl_dest)
        r3_layout.addWidget(self.txt_dest, stretch=1)
        r3_layout.addWidget(btn_browse)
        config_layout.addLayout(r3_layout)

        # Row 4: Checkbox Options & Filter Box
        r4_layout = QHBoxLayout()
        self.chk_exact = QCheckBox("Khớp từ khóa / tên file linh hoạt")
        self.chk_exact.setChecked(False)

        self.chk_use_oauth = QCheckBox("🔐 Dùng xác thực Google OAuth")
        self.chk_use_oauth.setChecked(False)

        lbl_filter = QLabel("🔍 Lọc danh sách:")
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Gõ từ khóa để lọc file...")
        self.txt_filter.setFixedWidth(180)

        r4_layout.addWidget(self.chk_exact)
        r4_layout.addWidget(self.chk_use_oauth)
        r4_layout.addStretch()
        r4_layout.addWidget(lbl_filter)
        r4_layout.addWidget(self.txt_filter)

        config_layout.addLayout(r4_layout)
        main_layout.addWidget(config_card)

        # 3. SELECTION TOOLBAR & CONTROL BUTTONS
        control_card = QFrame()
        control_card.setObjectName("controlCard")
        control_layout = QVBoxLayout(control_card)
        control_layout.setContentsMargins(14, 10, 14, 10)

        # Selection Action Bar
        select_bar = QHBoxLayout()
        self.btn_select_all = QPushButton("☑ Chọn Tất Cả")
        self.btn_deselect_all = QPushButton("☐ Bỏ Chọn Tất Cả")
        self.lbl_selected_count = QLabel("Đã chọn: 0 / 0 file")
        self.lbl_selected_count.setStyleSheet("color: #38BDF8; font-weight: bold;")

        select_bar.addWidget(self.btn_select_all)
        select_bar.addWidget(self.btn_deselect_all)
        select_bar.addStretch()
        select_bar.addWidget(self.lbl_selected_count)

        control_layout.addLayout(select_bar)

        # Progress Bar
        progress_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.lbl_progress_stat = QLabel("Tiến độ: 0 / 0 file")
        self.lbl_progress_stat.setObjectName("metaInfo")

        progress_row.addWidget(self.progress_bar, stretch=1)
        progress_row.addWidget(self.lbl_progress_stat)
        control_layout.addLayout(progress_row)

        # Action Buttons
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("► TẢI TRỰC TIẾP")
        self.btn_start.setObjectName("btnPlay")

        self.btn_start_chrome = QPushButton("⚡ TẢI TỰ ĐỘNG QUA CHROME (DRIVE KHÓA)")
        self.btn_start_chrome.setStyleSheet("background-color: #7C3AED; color: #FFFFFF; font-size: 13px; font-weight: bold; padding: 10px 14px;")
        self.btn_start_chrome.clicked.connect(self.start_chrome_interactive_flow)

        self.btn_process_zip = QPushButton("📦 LỌC TỪ FILE ZIP")
        self.btn_process_zip.setStyleSheet("background-color: #D97706; color: #FFFFFF; font-size: 13px; font-weight: bold; padding: 10px 14px;")
        self.btn_process_zip.clicked.connect(self.process_zip_file)

        self.btn_stop = QPushButton("⏹ Dừng")
        self.btn_stop.setObjectName("btnStop")

        self.btn_open_folder = QPushButton("📁 Mở thư mục lưu")
        self.btn_export_csv = QPushButton("📊 Xuất báo cáo (.csv)")

        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_start_chrome)
        btn_row.addWidget(self.btn_process_zip)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_open_folder)
        btn_row.addWidget(self.btn_export_csv)

        control_layout.addLayout(btn_row)
        main_layout.addWidget(control_card)

        # 4. LIVE STATUS TABLE WITH CHECKBOXES
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Tải", "STT", "Tên File Cần Tìm", "Trạng Thái Tải", "Dung Lượng", "Đường Dẫn Lưu Trên Máy"])
        
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        
        self.table.setColumnWidth(2, 280)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #030712;
                color: #F9FAFB;
                border: 1px solid #374151;
                gridline-color: #1F2937;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #1F2937;
                color: #38BDF8;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #374151;
            }
        """)

        main_layout.addWidget(self.table, stretch=1)

        # Status Bar
        self.statusBar().showMessage("Sẵn sàng. Nhấp '📝 DÁN TRỰC TIẾP' hoặc dán link Sheet để nạp danh sách tên file!")

    def connect_signals(self):
        self.btn_load_sheet.clicked.connect(self.load_sheet_list)
        self.btn_paste_direct.clicked.connect(self.open_direct_paste_dialog)

        self.btn_select_all.clicked.connect(lambda: self.set_all_checks(True))
        self.btn_deselect_all.clicked.connect(lambda: self.set_all_checks(False))
        self.txt_filter.textChanged.connect(self.filter_table_rows)

        self.btn_start.clicked.connect(self.start_download)
        self.btn_stop.clicked.connect(self.stop_download)
        self.btn_open_folder.clicked.connect(self.open_dest_folder)
        self.btn_export_csv.clicked.connect(self.export_csv_report)

        self.table.itemChanged.connect(self.update_selected_counter)

    def open_chrome_drive(self):
        drive_link = self.txt_gdrive.text().strip()
        if not drive_link:
            QMessageBox.warning(self, "Thiếu link", "Vui lòng nhập đường link Google Drive trước!")
            return
        webbrowser.open(drive_link)

    def start_chrome_interactive_flow(self):
        """Open Chrome visibly, allow user to confirm login, then automate search & download"""
        drive_link = self.txt_gdrive.text().strip()
        dest_folder = self.txt_dest.text().strip()

        if not drive_link:
            QMessageBox.warning(self, "Thiếu link", "Vui lòng dán link Thư mục Google Drive!")
            return

        selected_items = self.get_selected_items()
        if not selected_items:
            QMessageBox.warning(self, "Chưa chọn file", "Vui lòng chọn các file cần tải!")
            return

        try:
            self.statusBar().showMessage("Đang mở cửa sổ Chrome tự động...")
            self.active_browser = BrowserDriveDownloader()
            self.active_browser.start_browser_session(dest_folder)

            # Prompt user to log in if needed in the opened Chrome window
            confirm = QMessageBox.question(
                self,
                "Đã mở cửa sổ Chrome!",
                "Cửa sổ Chrome mới đã được mở trên màn hình!\n\n"
                "👉 NẾU CHROME CHƯA ĐĂNG NHẬP GOOGLE ACCOUNT:\n"
                "Vui lòng thực hiện Đăng nhập tài khoản Google của bạn trên cửa sổ Chrome đó.\n\n"
                "👉 Khi bạn đã đăng nhập xong (hoặc Chrome đã hiển thị Google Drive):\n"
                "Bấm 'Yes' (Đồng ý) dưới đây để Tool BẮT ĐẦU TỰ ĐỘNG TẢI 5 FILE!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if confirm == QMessageBox.StandardButton.Yes:
                self.badge_status.setText("⚡ Đang tự động tải trên Chrome...")
                target_names = [name for row_idx, name in selected_items]
                results = self.active_browser.auto_download_selected_files(
                    folder_url=drive_link,
                    target_names=target_names,
                    download_dir=dest_folder,
                    status_callback=lambda msg: self.statusBar().showMessage(msg)
                )

                res_dict = {res["target_name"]: res for res in results}
                success_cnt = 0
                for row_idx, target_name in selected_items:
                    res = res_dict.get(target_name, {"status": "not_found", "message": "Không thấy"})
                    if res["status"] == "success":
                        success_cnt += 1
                        item_status = QTableWidgetItem("🟢 Đã kích hoạt tải")
                        item_status.setForeground(QColor(52, 211, 153))
                        self.table.setItem(row_idx, 3, item_status)
                        self.table.setItem(row_idx, 5, QTableWidgetItem(res.get("saved_path", "")))
                    else:
                        item_status = QTableWidgetItem("❌ Không thấy trong Chrome")
                        item_status.setForeground(QColor(248, 113, 113))
                        self.table.setItem(row_idx, 3, item_status)

                self.badge_status.setText("🟢 Hoàn tất")
                self.statusBar().showMessage(f"Hoàn tất tải tự động qua Chrome! Đã tải {success_cnt}/{len(selected_items)} file.")
                QMessageBox.information(
                    self,
                    "Hoàn tất tải qua Chrome",
                    f"Đã hoàn thành tự động tải CHỈ CÁC FILE ĐƯỢC CHỌN qua Chrome!\n\n"
                    f"• Số file đã chọn: {len(selected_items)}\n"
                    f"• Đã kích hoạt tải: {success_cnt}\n\n"
                    f"Các file đã được tự động lưu về thư mục:\n{dest_folder}"
                )

        except Exception as e:
            QMessageBox.critical(self, "Lỗi Chrome Automation", f"Không thể tự động tải qua Chrome: {str(e)}")

    def process_zip_file(self):
        """Extract ONLY the matching files from a downloaded Google Drive Zip file"""
        selected_items = self.get_selected_items()
        if not selected_items:
            QMessageBox.warning(self, "Chưa chọn file", "Vui lòng dán danh sách tên file và chọn ít nhất 1 file!")
            return

        zip_path, _ = QFileDialog.getOpenFileName(self, "Chọn file Zip đã tải từ Google Drive", os.path.join(os.path.expanduser("~"), "Downloads"), "Zip Archives (*.zip)")
        if not zip_path:
            return

        try:
            self.statusBar().showMessage("Đang tự động giải nén và lọc các file đã chọn từ Zip...")
            dest_folder = self.txt_dest.text().strip()
            target_names = [name for row_idx, name in selected_items]

            browser_engine = BrowserDriveDownloader()
            results = browser_engine.process_zip_archive(zip_path, target_names, dest_folder, self.chk_exact.isChecked())

            success_cnt = 0
            failed_cnt = 0

            res_dict = {res["target_name"]: res for res in results}
            for row_idx, target_name in selected_items:
                res = res_dict.get(target_name, {"status": "not_found", "message": "Không thấy"})
                if res["status"] == "success":
                    success_cnt += 1
                    size_mb = f"{res.get('size_bytes', 0) / (1024*1024):.2f} MB"
                    item_status = QTableWidgetItem("🟢 Đã giải nén")
                    item_status.setForeground(QColor(52, 211, 153))
                    self.table.setItem(row_idx, 3, item_status)
                    self.table.setItem(row_idx, 4, QTableWidgetItem(size_mb))
                    self.table.setItem(row_idx, 5, QTableWidgetItem(res["saved_path"]))
                else:
                    failed_cnt += 1
                    item_status = QTableWidgetItem("❌ Không thấy trong Zip")
                    item_status.setForeground(QColor(248, 113, 113))
                    self.table.setItem(row_idx, 3, item_status)

            self.statusBar().showMessage(f"Hoàn tất giải nén & lọc file từ Zip! Thành công: {success_cnt}/{len(selected_items)} file.")
            QMessageBox.information(
                self,
                "Hoàn tất lọc file Zip",
                f"Đã giải nén và lọc thành công các file khớp từ file Zip!\n\n"
                f"• Số file đã chọn: {len(selected_items)}\n"
                f"• Giải nén thành công: {success_cnt}\n"
                f"• Không có trong Zip: {failed_cnt}\n\n"
                f"Thư mục lưu:\n{dest_folder}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Lỗi giải nén Zip", f"Không thể xử lý file Zip: {str(e)}")

    def browse_dest_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu file tải về", self.txt_dest.text())
        if folder:
            self.txt_dest.setText(folder)

    def open_dest_folder(self):
        dest = self.txt_dest.text().strip()
        os.makedirs(dest, exist_ok=True)
        subprocess.run(["explorer", os.path.normpath(dest)])

    def populate_filenames_to_table(self, filenames: list[str]):
        if not filenames:
            return

        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.setRowCount(len(filenames))

        for idx, fn in enumerate(filenames):
            chk_item = QTableWidgetItem("✓")
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            chk_item.setCheckState(Qt.CheckState.Checked)
            chk_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item_stt = QTableWidgetItem(str(idx + 1))
            item_stt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_name = QTableWidgetItem(fn)
            item_status = QTableWidgetItem("⚪ Chưa tải")
            item_size = QTableWidgetItem("")
            item_path = QTableWidgetItem("")

            self.table.setItem(idx, 0, chk_item)
            self.table.setItem(idx, 1, item_stt)
            self.table.setItem(idx, 2, item_name)
            self.table.setItem(idx, 3, item_status)
            self.table.setItem(idx, 4, item_size)
            self.table.setItem(idx, 5, item_path)

        self.table.blockSignals(False)
        self.update_selected_counter()
        self.statusBar().showMessage(f"Đã nạp xong {len(filenames)} file vào bảng. Đánh dấu các file bạn muốn tải!")

    def open_direct_paste_dialog(self):
        current_names = [self.table.item(r, 2).text() for r in range(self.table.rowCount()) if self.table.item(r, 2)]
        current_text = "\n".join(current_names)

        dialog = DirectTextDialog(current_text=current_text, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            filenames = dialog.get_filenames()
            if filenames:
                self.populate_filenames_to_table(filenames)

    def load_sheet_list(self):
        sheet_link = self.txt_gsheet.text().strip()
        col_name = self.txt_col.text().strip()

        if not sheet_link:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập đường link Google Sheet HOẶC dùng nút '📝 DÁN TRỰC TIẾP'!")
            return

        try:
            self.statusBar().showMessage("Đang đọc danh sách file từ Google Sheet...")
            reader = GSheetReader()
            filenames = reader.fetch_sheet_rows(sheet_link, col_name)

            if not filenames:
                QMessageBox.warning(self, "Danh sách trống", "Không tìm thấy tên file nào trong cột đã chọn!")
                return

            self.populate_filenames_to_table(filenames)

        except Exception as e:
            QMessageBox.critical(self, "Không thể đọc Google Sheet", str(e))

    def set_all_checks(self, checked: bool):
        self.table.blockSignals(True)
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        text_val = "✓" if checked else ""
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item:
                item.setCheckState(state)
                item.setText(text_val)
        self.table.blockSignals(False)
        self.update_selected_counter()

    def update_selected_counter(self, item=None):
        total = self.table.rowCount()
        selected = 0
        for r in range(total):
            chk_item = self.table.item(r, 0)
            if chk_item:
                is_checked = (chk_item.checkState() == Qt.CheckState.Checked) or (chk_item.text().strip() in ["✓", "v", "V"])
                if is_checked:
                    selected += 1
        self.lbl_selected_count.setText(f"Đã chọn: {selected} / {total} file")

    def filter_table_rows(self, text: str):
        kw = text.strip().lower()
        for r in range(self.table.rowCount()):
            fn_item = self.table.item(r, 2)
            if fn_item:
                fn_text = fn_item.text().lower()
                self.table.setRowHidden(r, bool(kw and kw not in fn_text))

    def get_selected_items(self) -> list[tuple[int, str]]:
        selected = []
        for r in range(self.table.rowCount()):
            if self.table.isRowHidden(r):
                continue
            chk_item = self.table.item(r, 0)
            fn_item = self.table.item(r, 2)
            if fn_item and fn_item.text().strip():
                is_checked = True
                if chk_item:
                    if chk_item.checkState() == Qt.CheckState.Unchecked and chk_item.text().strip() not in ["✓", "v", "V"]:
                        is_checked = False
                if is_checked:
                    selected.append((r, fn_item.text().strip()))
        return selected

    def start_download(self):
        drive_link = self.txt_gdrive.text().strip()
        dest_folder = self.txt_dest.text().strip()
        use_oauth = self.chk_use_oauth.isChecked()

        if not drive_link:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập đường link Thư mục Google Drive!")
            return

        selected_items = self.get_selected_items()
        if not selected_items:
            QMessageBox.warning(self, "Chưa chọn file", "Vui lòng dán danh sách file và tích chọn ít nhất 1 file để tải!")
            return

        total_selected = len(selected_items)
        self.progress_bar.setMaximum(total_selected)
        self.progress_bar.setValue(0)
        self.lbl_progress_stat.setText(f"Tiến độ: 0 / {total_selected} file")

        self.btn_start.setEnabled(False)
        self.badge_status.setText("⚡ Đang tải...")

        # Start worker thread
        self.worker = DownloadWorker(
            selected_items=selected_items,
            drive_link=drive_link,
            dest_folder=dest_folder,
            exact_match=self.chk_exact.isChecked(),
            use_oauth=use_oauth
        )
        self.worker.row_updated.connect(self.on_row_updated)
        self.worker.progress_changed.connect(self.on_progress_changed)
        self.worker.status_msg.connect(self.on_status_msg)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def stop_download(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.statusBar().showMessage("Đang dừng quá trình tải...")

    def on_row_updated(self, row_idx: int, status_text: str, status_code: str, size_str: str, path_str: str):
        if row_idx < self.table.rowCount():
            item_status = QTableWidgetItem(status_text)
            
            if status_code == "success":
                item_status.setForeground(QColor(52, 211, 153))
            elif status_code == "not_found":
                item_status.setForeground(QColor(248, 113, 113))
            elif status_code == "loading":
                item_status.setForeground(QColor(56, 189, 248))

            self.table.setItem(row_idx, 3, item_status)
            if size_str:
                self.table.setItem(row_idx, 4, QTableWidgetItem(size_str))
            if path_str:
                self.table.setItem(row_idx, 5, QTableWidgetItem(path_str))

    def on_progress_changed(self, completed: int, total: int):
        self.progress_bar.setValue(completed)
        self.lbl_progress_stat.setText(f"Tiến độ: {completed} / {total} file")

    def on_status_msg(self, msg: str):
        self.statusBar().showMessage(msg)

    def on_finished(self, total: int, success: int, failed: int):
        self.btn_start.setEnabled(True)
        self.badge_status.setText("🟢 Hoàn tất")
        self.statusBar().showMessage(f"Hoàn tất tải file đã chọn! Thành công: {success}/{total} file, Không tìm thấy: {failed} file.")
        
        if success > 0:
            QMessageBox.information(
                self,
                "Hoàn tất tải file",
                f"Đã hoàn thành tải các file được chọn!\n\n"
                f"• Số file đã chọn: {total}\n"
                f"• Tải thành công: {success}\n"
                f"• Không tìm thấy: {failed}\n\n"
                f"Thư mục lưu:\n{self.txt_dest.text()}"
            )
        else:
            QMessageBox.warning(
                self,
                "Thư mục Drive bị khóa",
                f"Thư mục Google Drive này bị khóa riêng tư!\n\n"
                f"👉 BẠN CHỈ CẦN BẤM NÚT MÀU TÍM:\n"
                f"'⚡ TẢI TỰ ĐỘNG QUA CHROME'\n\n"
                f"Tool sẽ tự động mở Chrome của bạn và tự động tải CHÍNH XÁC CHỈ 5 FILE CỦA BẠN mà không cần tải bừa các file khác hay tải Zip!"
            )

    def export_csv_report(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Chưa có dữ liệu", "Chưa có danh sách dữ liệu để xuất báo cáo!")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Lưu file báo cáo CSV", "baocao_tai_file.csv", "CSV Files (*.csv)")
        if file_path:
            try:
                with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Được Chọn", "STT", "Tên File Cần Tìm", "Trạng Thái", "Dung Lượng", "Đường Dẫn Lưu"])
                    
                    for r in range(self.table.rowCount()):
                        chk = "Co" if self.table.item(r, 0) and self.table.item(r, 0).checkState() == Qt.CheckState.Checked else "Khong"
                        stt = self.table.item(r, 1).text() if self.table.item(r, 1) else ""
                        name = self.table.item(r, 2).text() if self.table.item(r, 2) else ""
                        status = self.table.item(r, 3).text() if self.table.item(r, 3) else ""
                        size = self.table.item(r, 4).text() if self.table.item(r, 4) else ""
                        path = self.table.item(r, 5).text() if self.table.item(r, 5) else ""
                        writer.writerow([chk, stt, name, status, size, path])

                QMessageBox.information(self, "Thành công", f"Đã xuất báo cáo kết quả tại:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi xuất báo cáo", f"Không thể tạo file báo cáo: {str(e)}")


def main():
    app = QApplication(sys.argv)
    window = GSheetGDriveDownloaderApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
