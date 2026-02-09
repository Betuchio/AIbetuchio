"""AIbetuchio - Streamlit Cloud entry point."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.db_manager import init_database

# ბაზის ინიციალიზაცია გაშვებისას
init_database()

# მთავარი აპლიკაციის გაშვება
exec(open(os.path.join(os.path.dirname(__file__), "src", "web", "app.py"), encoding="utf-8").read())
