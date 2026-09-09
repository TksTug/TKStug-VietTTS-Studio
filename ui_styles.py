MAIN_STYLE = """
/* App Main Window */
QMainWindow {
    background-color: #0B0F19;
    color: #F8FAFC;
}

QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    color: #E2E8F0;
}

/* Header Panel */
#headerCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E1B4B, stop:0.5 #0F172A, stop:1 #172554);
    border: 1px solid #312E81;
    border-radius: 12px;
    padding: 16px;
}

#headerTitle {
    font-size: 22px;
    font-weight: bold;
    color: #F8FAFC;
}

#headerSubtitle {
    font-size: 12px;
    color: #94A3B8;
}

#badgeTag {
    background-color: #312E81;
    color: #818CF8;
    font-weight: bold;
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 12px;
    border: 1px solid #4338CA;
}

/* Section Cards */
.QFrame#editorCard, .QFrame#settingsCard, .QFrame#controlCard {
    background-color: #111827;
    border: 1px solid #1F2937;
    border-radius: 12px;
}

/* Section Titles */
.QLabel#sectionTitle {
    font-size: 14px;
    font-weight: bold;
    color: #38BDF8;
    padding-bottom: 4px;
}

/* Text Editor */
QTextEdit#textEditor {
    background-color: #030712;
    color: #F9FAFB;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 12px;
    font-size: 14px;
    line-height: 1.5;
    selection-background-color: #4F46E5;
    selection-color: #FFFFFF;
}

QTextEdit#textEditor:focus {
    border: 1px solid #6366F1;
}

/* Info Labels */
QLabel#metaInfo {
    color: #9CA3AF;
    font-size: 11px;
}

/* Buttons */
QPushButton {
    background-color: #1F2937;
    color: #F3F4F6;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #374151;
    border-color: #4B5563;
}

QPushButton:pressed {
    background-color: #111827;
}

/* Preset Buttons */
QPushButton.presetBtn {
    background-color: #1E293B;
    color: #38BDF8;
    border: 1px solid #0284C7;
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 6px;
}

QPushButton.presetBtn:hover {
    background-color: #0284C7;
    color: #FFFFFF;
}

/* Primary Action Button (Play) */
QPushButton#btnPlay {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED);
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    border: none;
    padding: 10px 24px;
    border-radius: 8px;
}

QPushButton#btnPlay:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #8B5CF6);
}

QPushButton#btnPlay:disabled {
    background-color: #374151;
    color: #6B7280;
}

/* Secondary Buttons */
QPushButton#btnPause, QPushButton#btnStop {
    background-color: #374151;
    color: #F9FAFB;
    border: 1px solid #4B5563;
    font-size: 13px;
}

QPushButton#btnPause:hover, QPushButton#btnStop:hover {
    background-color: #4B5563;
}

/* Export Button */
QPushButton#btnExport {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10B981);
    color: #FFFFFF;
    font-weight: bold;
    border: none;
    padding: 10px 18px;
    border-radius: 8px;
}

QPushButton#btnExport:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #34D399);
}

/* Voice Card Radio Buttons / Group */
QRadioButton {
    spacing: 8px;
    font-weight: bold;
    color: #E5E7EB;
    padding: 6px;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid #6B7280;
    background-color: #1F2937;
}

QRadioButton::indicator:checked {
    border: 2px solid #818CF8;
    background-color: #4F46E5;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #1F2937;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #38BDF8);
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #F9FAFB;
    border: 2px solid #6366F1;
    width: 16px;
    height: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #818CF8;
}

/* API Key LineEdit */
QLineEdit#apiKeyInput {
    background-color: #030712;
    color: #F9FAFB;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit#apiKeyInput:focus {
    border: 1px solid #818CF8;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #0B0F19;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #374151;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #4B5563;
}

/* Progress bar */
QProgressBar {
    border: 1px solid #374151;
    border-radius: 4px;
    text-align: center;
    background-color: #1F2937;
    color: #F3F4F6;
    height: 14px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #06B6D4);
    border-radius: 3px;
}
"""
