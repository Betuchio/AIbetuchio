"""Streamlit ვებ ინტერფეისის გაშვება."""
import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.db_manager import init_database


def main():
    init_database()

    app_path = os.path.join(os.path.dirname(__file__), "src", "web", "app.py")

    subprocess.run([
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.port=8501",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ])


if __name__ == "__main__":
    main()
