import os
import subprocess
import sys

def build():
    print("Building VietTTS Desktop App into a SINGLE standalone .exe file...")
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "VietTTS_Tool_TiengViet",
        "--clean",
        "main.py"
    ]
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    if result.returncode == 0:
        print("\nSUCCESS! Single file executable created at 'dist/VietTTS_Tool_TiengViet.exe'")
    else:
        print("\nBUILD FAILED with exit code:", result.returncode)

if __name__ == "__main__":
    build()
