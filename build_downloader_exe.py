import os
import sys
import subprocess

def build_exe():
    print("Building GSheet & GDrive Auto Downloader into a SINGLE standalone .exe file...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, "main_downloader_gui.py")

    hidden_imports = [
        "--hidden-import=selenium",
        "--hidden-import=selenium.webdriver",
        "--hidden-import=selenium.webdriver.chrome",
        "--hidden-import=selenium.webdriver.chrome.service",
        "--hidden-import=selenium.webdriver.chrome.options",
        "--hidden-import=selenium.webdriver.chrome.webdriver",
        "--hidden-import=selenium.webdriver.common.by",
        "--hidden-import=selenium.webdriver.common.keys",
        "--hidden-import=webdriver_manager",
        "--hidden-import=webdriver_manager.chrome",
        "--hidden-import=google_auth_oauthlib",
        "--hidden-import=google.oauth2.credentials",
        "--hidden-import=googleapiclient.discovery",
        "--hidden-import=googleapiclient.http"
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "GSheet_GDrive_Downloader",
        "--clean"
    ] + hidden_imports + [main_script]

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=script_dir)

    if result.returncode == 0:
        dist_exe = os.path.join(script_dir, "dist", "GSheet_GDrive_Downloader.exe")
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        desktop_exe = os.path.join(desktop, "GSheet_GDrive_Downloader.exe")
        
        print(f"\nSUCCESS! Single file executable created at '{dist_exe}'")
    else:
        print(f"\nBUILD FAILED with exit code: {result.returncode}")

if __name__ == "__main__":
    build_exe()
