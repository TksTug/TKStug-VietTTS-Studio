import sys
import os
import shutil
import random
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QRadioButton, QButtonGroup,
    QSlider, QFileDialog, QMessageBox, QFrame, QSplitter
)
from PyQt6.QtGui import QColor, QPainter, QBrush

from tts_engine import TTSEngine, VOICES
from audio_player import AudioPlayer
from ui_styles import MAIN_STYLE


class SoundWaveVisualizer(QWidget):
    """Visualizer widget with animated sound bars"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(45)
        self.bars = [5, 10, 15, 8, 20, 12, 18, 6, 25, 14, 10, 22, 16, 8, 12]
        self.is_active = False
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(80)

    def set_active(self, active: bool):
        self.is_active = active
        if not active:
            self.bars = [5 for _ in self.bars]
            self.update()

    def _animate(self):
        if self.is_active:
            self.bars = [random.randint(4, 32) for _ in self.bars]
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        bar_count = len(self.bars)
        spacing = 6
        total_spacing = spacing * (bar_count + 1)
        bar_width = max(4, int((w - total_spacing) / bar_count))

        start_x = int((w - (bar_width * bar_count + spacing * (bar_count - 1))) / 2)

        for i, val in enumerate(self.bars):
            x = start_x + i * (bar_width + spacing)
            bar_height = val if self.is_active else 4
            y = int((h - bar_height) / 2)

            if self.is_active:
                color = QColor(99, 102, 241) if i % 2 == 0 else QColor(56, 189, 248)
            else:
                color = QColor(55, 65, 81)

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x, y, bar_width, bar_height, 2, 2)


class TTSWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, tts_engine: TTSEngine, text: str, voice_key: str, rate: int, pitch: int, volume: int, output_path: str = None):
        super().__init__()
        self.tts_engine = tts_engine
        self.text = text
        self.voice_key = voice_key
        self.rate = rate
        self.pitch = pitch
        self.volume = volume
        self.output_path = output_path

    def run(self):
        try:
            path = self.tts_engine.synthesize(
                text=self.text,
                voice_key=self.voice_key,
                rate=self.rate,
                pitch=self.pitch,
                volume=self.volume,
                output_path=self.output_path
            )
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))


class VietTTSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VietTTS - Công Cụ Đọc Văn Bản Tiếng Việt (Giọng Nữ, Nam Minh & Giọng Adam)")
        self.resize(950, 720)
        self.setMinimumSize(850, 650)

        self.tts_engine = TTSEngine()
        self.audio_player = AudioPlayer()
        self.current_audio_file = None

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
        title_label = QLabel("🎙️ VietTTS - Chuyển Văn Bản Thành Giọng Nói")
        title_label.setObjectName("headerTitle")
        sub_label = QLabel("Đọc văn bản Tiếng Việt tự động bằng trí tuệ nhân tạo (Giọng Nữ Hoài My, Giọng Nam Nam Minh & Giọng Adam)")
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

        # SPLITTER FOR EDITOR AND SETTINGS
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # 2. LEFT: TEXT EDITOR CARD
        editor_card = QFrame()
        editor_card.setObjectName("editorCard")
        editor_layout = QVBoxLayout(editor_card)
        editor_layout.setContentsMargins(14, 14, 14, 14)

        # Presets & Tools Bar
        presets_bar = QHBoxLayout()
        sec_title = QLabel("📝 Nội dung văn bản")
        sec_title.setObjectName("sectionTitle")
        
        presets_bar.addWidget(sec_title)
        presets_bar.addStretch()

        btn_sample1 = QPushButton("Thử giọng Adam")
        btn_sample1.setProperty("class", "presetBtn")
        btn_sample1.clicked.connect(lambda: self.load_sample(1))

        btn_sample2 = QPushButton("Truyện ngắn")
        btn_sample2.setProperty("class", "presetBtn")
        btn_sample2.clicked.connect(lambda: self.load_sample(2))

        btn_sample3 = QPushButton("Thông báo")
        btn_sample3.setProperty("class", "presetBtn")
        btn_sample3.clicked.connect(lambda: self.load_sample(3))

        presets_bar.addWidget(btn_sample1)
        presets_bar.addWidget(btn_sample2)
        presets_bar.addWidget(btn_sample3)

        editor_layout.addLayout(presets_bar)

        # Text Editor
        self.text_editor = QTextEdit()
        self.text_editor.setObjectName("textEditor")
        self.text_editor.setPlaceholderText("Nhập hoặc dán văn bản tiếng Việt cần đọc tại đây...\n\nVí dụ: Xin chào! Chúc bạn một ngày làm việc tràn đầy năng lượng và hiệu quả.")
        editor_layout.addWidget(self.text_editor)

        # Editor Footer Buttons & Counters
        editor_footer = QHBoxLayout()
        
        btn_paste = QPushButton("📋 Dán (Paste)")
        btn_paste.clicked.connect(self.paste_text)

        btn_clear = QPushButton("🗑️ Xóa sạch")
        btn_clear.clicked.connect(self.clear_text)

        btn_open_file = QPushButton("📁 Mở file .txt")
        btn_open_file.clicked.connect(self.open_text_file)

        self.lbl_counters = QLabel("0 ký tự | 0 từ")
        self.lbl_counters.setObjectName("metaInfo")

        editor_footer.addWidget(btn_paste)
        editor_footer.addWidget(btn_clear)
        editor_footer.addWidget(btn_open_file)
        editor_footer.addStretch()
        editor_footer.addWidget(self.lbl_counters)

        editor_layout.addLayout(editor_footer)
        splitter.addWidget(editor_card)

        # 3. RIGHT: VOICE SETTINGS CARD
        settings_card = QFrame()
        settings_card.setObjectName("settingsCard")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(14, 14, 14, 14)

        set_title = QLabel("⚙️ Tùy chọn giọng đọc & Âm thanh")
        set_title.setObjectName("sectionTitle")
        settings_layout.addWidget(set_title)

        # Voice Selector Group
        lbl_voice_group = QLabel("Chọn giọng phát âm:")
        lbl_voice_group.setStyleSheet("font-weight: bold; color: #E2E8F0;")
        settings_layout.addWidget(lbl_voice_group)

        self.btn_group_voice = QButtonGroup(self)
        
        self.rb_female = QRadioButton("👩 Giọng Nữ - Hoài My (Tiếng Việt)")
        self.rb_male_nam = QRadioButton("👨 Giọng Nam - Nam Minh (Tiếng Việt)")
        self.rb_eleven_adam = QRadioButton("🎙️ Giọng Nam - Adam (Trầm ấm ElevenLabs)")

        self.btn_group_voice.addButton(self.rb_female, 1)
        self.btn_group_voice.addButton(self.rb_male_nam, 2)
        self.btn_group_voice.addButton(self.rb_eleven_adam, 3)

        self.rb_female.setChecked(True)

        settings_layout.addWidget(self.rb_female)
        settings_layout.addWidget(self.rb_male_nam)
        settings_layout.addWidget(self.rb_eleven_adam)

        # Divider line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #1F2937;")
        settings_layout.addWidget(line)

        # Speed Slider (-50 to +100 %)
        speed_header = QHBoxLayout()
        lbl_speed = QLabel("🚀 Tốc độ đọc (Speed):")
        self.lbl_speed_val = QLabel("1.0x (Chuẩn)")
        self.lbl_speed_val.setStyleSheet("color: #38BDF8; font-weight: bold;")
        speed_header.addWidget(lbl_speed)
        speed_header.addStretch()
        speed_header.addWidget(self.lbl_speed_val)
        settings_layout.addLayout(speed_header)

        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setRange(-50, 100)
        self.slider_speed.setValue(0)
        settings_layout.addWidget(self.slider_speed)

        # Pitch Slider (-20 to +20 Hz)
        pitch_header = QHBoxLayout()
        lbl_pitch = QLabel("🎵 Cao độ giọng (Pitch):")
        self.lbl_pitch_val = QLabel("0 Hz (Chuẩn)")
        self.lbl_pitch_val.setStyleSheet("color: #818CF8; font-weight: bold;")
        pitch_header.addWidget(lbl_pitch)
        pitch_header.addStretch()
        pitch_header.addWidget(self.lbl_pitch_val)
        settings_layout.addLayout(pitch_header)

        self.slider_pitch = QSlider(Qt.Orientation.Horizontal)
        self.slider_pitch.setRange(-20, 20)
        self.slider_pitch.setValue(0)
        settings_layout.addWidget(self.slider_pitch)

        # Volume Slider (0 to 100 %)
        vol_header = QHBoxLayout()
        lbl_vol = QLabel("🔊 Âm lượng (Volume):")
        self.lbl_vol_val = QLabel("100%")
        self.lbl_vol_val.setStyleSheet("color: #34D399; font-weight: bold;")
        vol_header.addWidget(lbl_vol)
        vol_header.addStretch()
        vol_header.addWidget(self.lbl_vol_val)
        settings_layout.addLayout(vol_header)

        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(100)
        settings_layout.addWidget(self.slider_vol)

        settings_layout.addStretch()
        splitter.addWidget(settings_card)

        # Splitter proportion (60% left, 40% right)
        splitter.setSizes([550, 350])
        main_layout.addWidget(splitter, stretch=1)

        # 4. BOTTOM CONTROL CARD
        control_card = QFrame()
        control_card.setObjectName("controlCard")
        control_layout = QVBoxLayout(control_card)
        control_layout.setContentsMargins(14, 12, 14, 12)

        # Sound Visualizer & Progress Slider
        vis_row = QHBoxLayout()
        self.visualizer = SoundWaveVisualizer()
        vis_row.addWidget(self.visualizer, stretch=1)
        control_layout.addLayout(vis_row)

        audio_time_row = QHBoxLayout()
        self.lbl_current_time = QLabel("00:00")
        self.lbl_current_time.setObjectName("metaInfo")
        
        self.slider_progress = QSlider(Qt.Orientation.Horizontal)
        self.slider_progress.setRange(0, 1000)
        self.slider_progress.setValue(0)

        self.lbl_total_time = QLabel("00:00")
        self.lbl_total_time.setObjectName("metaInfo")

        audio_time_row.addWidget(self.lbl_current_time)
        audio_time_row.addWidget(self.slider_progress, stretch=1)
        audio_time_row.addWidget(self.lbl_total_time)
        control_layout.addLayout(audio_time_row)

        # Action Buttons Row
        actions_row = QHBoxLayout()
        
        self.btn_play = QPushButton("► ĐỌC VĂN BẢN")
        self.btn_play.setObjectName("btnPlay")

        self.btn_pause = QPushButton("⏸ Tạm dừng")
        self.btn_pause.setObjectName("btnPause")

        self.btn_stop = QPushButton("⏹ Dừng đọc")
        self.btn_stop.setObjectName("btnStop")

        self.btn_export = QPushButton("💾 Xuất File MP3")
        self.btn_export.setObjectName("btnExport")

        actions_row.addWidget(self.btn_play, stretch=2)
        actions_row.addWidget(self.btn_pause)
        actions_row.addWidget(self.btn_stop)
        actions_row.addWidget(self.btn_export)

        control_layout.addLayout(actions_row)
        main_layout.addWidget(control_card)

        # Status Bar
        self.statusBar().showMessage("Sẵn sàng. Chọn giọng đọc, nhập văn bản và nhấn '► ĐỌC VĂN BẢN'")

    def connect_signals(self):
        # Text Editor counters
        self.text_editor.textChanged.connect(self.update_counters)

        # Sliders value change display
        self.slider_speed.valueChanged.connect(self.update_speed_label)
        self.slider_pitch.valueChanged.connect(self.update_pitch_label)
        self.slider_vol.valueChanged.connect(self.update_vol_label)

        # Audio control buttons
        self.btn_play.clicked.connect(self.start_synthesis)
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_stop.clicked.connect(self.stop_audio)
        self.btn_export.clicked.connect(self.export_mp3)

        # Audio Player Signals
        self.audio_player.state_changed.connect(self.on_player_state_changed)
        self.audio_player.position_changed.connect(self.on_player_position_changed)
        self.audio_player.error_occurred.connect(self.on_player_error)

        # Seek slider
        self.slider_progress.sliderMoved.connect(self.on_seek)

    def update_counters(self):
        text = self.text_editor.toPlainText()
        char_count = len(text)
        words = text.split()
        word_count = len(words)
        self.lbl_counters.setText(f"{char_count:,} ký tự | {word_count:,} từ")

    def update_speed_label(self, val: int):
        multiplier = 1.0 + (val / 100.0)
        self.lbl_speed_val.setText(f"{multiplier:.1f}x")

    def update_pitch_label(self, val: int):
        self.lbl_pitch_val.setText(f"{'+' if val >= 0 else ''}{val} Hz")

    def update_vol_label(self, val: int):
        self.lbl_vol_val.setText(f"{val}%")
        self.audio_player.set_volume(val)

    def load_sample(self, index: int):
        samples = {
            1: "Xin chào quý vị! Đây là bài đọc thử bằng giọng nam Adam tự động cực kỳ trầm ấm và truyền cảm.",
            2: "Một buổi sáng mùa thu trong lành, ánh nắng vàng nhạt len lỏi qua từng kẽ lá. Gió heo may thổi nhẹ làm xào xạc những tán cây góc phố. Cả thành phố như khoác lên mình một vẻ đẹp yên bình và thơ mộng.",
            3: "Trân trọng thông báo: Hệ thống sẽ tiến hành bảo trì nâng cấp dịch vụ vào lúc 24 giờ đêm nay. Quý khách vui lòng hoàn tất các giao dịch trước thời gian trên. Xin chân thành cảm ơn!"
        }
        self.text_editor.setPlainText(samples.get(index, ""))

    def paste_text(self):
        clipboard = QApplication.clipboard()
        self.text_editor.insertPlainText(clipboard.text())

    def clear_text(self):
        self.text_editor.clear()

    def open_text_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file văn bản", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.text_editor.setPlainText(f.read())
            except Exception as e:
                QMessageBox.critical(self, "Lỗi đọc file", f"Không thể đọc file: {str(e)}")

    def get_selected_voice_key(self) -> str:
        if self.rb_female.isChecked():
            return "female_hoaimy"
        elif self.rb_male_nam.isChecked():
            return "male_namminh"
        elif self.rb_eleven_adam.isChecked():
            return "elevenlabs_adam"
        return "female_hoaimy"

    def start_synthesis(self):
        text = self.text_editor.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập văn bản tiếng Việt cần đọc!")
            return

        voice_key = self.get_selected_voice_key()
        voice_info = VOICES.get(voice_key, {})
        voice_name = voice_info.get("name", "Giọng đọc")

        rate = self.slider_speed.value()
        pitch = self.slider_pitch.value()
        volume = self.slider_vol.value()

        # UI state updating
        self.btn_play.setEnabled(False)
        self.badge_status.setText("⚡ Đang tạo giọng...")
        self.statusBar().showMessage(f"Đang tổng hợp: {voice_name}...")

        # Stop previous playback
        self.audio_player.stop()

        # Worker thread execution
        self.worker = TTSWorker(
            tts_engine=self.tts_engine,
            text=text,
            voice_key=voice_key,
            rate=rate,
            pitch=pitch,
            volume=volume
        )
        self.worker.finished.connect(self.on_synthesis_finished)
        self.worker.error.connect(self.on_synthesis_error)
        self.worker.start()

    def on_synthesis_finished(self, audio_path: str):
        self.btn_play.setEnabled(True)
        self.current_audio_file = audio_path
        
        voice_key = self.get_selected_voice_key()
        voice_info = VOICES.get(voice_key, {})
        voice_name = voice_info.get("name", "Audio")

        self.badge_status.setText("🔊 Đang phát audio")
        self.statusBar().showMessage(f"Đang phát: {voice_name}")
        
        # Load and play audio file
        self.audio_player.load_and_play(audio_path)

    def on_synthesis_error(self, error_msg: str):
        self.btn_play.setEnabled(True)
        self.badge_status.setText("❌ Có lỗi xảy ra")
        self.statusBar().showMessage(f"Lỗi: {error_msg}")
        QMessageBox.critical(self, "Lỗi tạo giọng nói", f"{error_msg}")

    def toggle_pause(self):
        if self.audio_player.is_playing():
            self.audio_player.pause()
            self.btn_pause.setText("▶ Tiếp tục")
            self.badge_status.setText("⏸ Đang tạm dừng")
        else:
            self.audio_player.play()
            self.btn_pause.setText("⏸ Tạm dừng")
            self.badge_status.setText("🔊 Đang phát audio")

    def stop_audio(self):
        self.audio_player.stop()
        self.visualizer.set_active(False)
        self.btn_pause.setText("⏸ Tạm dừng")
        self.badge_status.setText("🟢 Sẵn sàng")
        self.statusBar().showMessage("Đã dừng phát âm thanh.")

    def on_player_state_changed(self, state: str):
        if state == 'playing':
            self.visualizer.set_active(True)
            self.btn_pause.setText("⏸ Tạm dừng")
            self.badge_status.setText("🔊 Đang phát audio")
        else:
            self.visualizer.set_active(False)
            if state == 'stopped':
                self.btn_pause.setText("⏸ Tạm dừng")
                self.badge_status.setText("🟢 Sẵn sàng")
                self.statusBar().showMessage("Hoàn tất đọc văn bản.")

    def on_player_position_changed(self, position_ms: int, total_ms: int):
        if total_ms > 0:
            self.slider_progress.setMaximum(total_ms)
            self.slider_progress.setValue(position_ms)
            
            cur_sec = position_ms // 1000
            tot_sec = total_ms // 1000
            
            self.lbl_current_time.setText(f"{cur_sec//60:02d}:{cur_sec%60:02d}")
            self.lbl_total_time.setText(f"{tot_sec//60:02d}:{tot_sec%60:02d}")

    def on_seek(self, position_ms: int):
        self.audio_player.set_position(position_ms)

    def on_player_error(self, error_str: str):
        self.statusBar().showMessage(f"Lỗi phát âm thanh: {error_str}")

    def export_mp3(self):
        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            QMessageBox.warning(self, "Chưa có file âm thanh", "Vui lòng nhấn '► ĐỌC VĂN BẢN' trước khi xuất file MP3!")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Lưu file MP3", "viet_tts_audio.mp3", "Audio Files (*.mp3)")
        if file_path:
            try:
                shutil.copyfile(self.current_audio_file, file_path)
                QMessageBox.information(self, "Thành công", f"Đã xuất file âm thanh thành công tại:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi xuất file", f"Không thể lưu file: {str(e)}")


def main():
    app = QApplication(sys.argv)
    window = VietTTSApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
