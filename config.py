from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHECKLISTCHECKER_ID = [
    int(value.strip())
    for value in os.getenv("CHECKLISTCHECKER_ID", "").split(",")
    if value.strip()
]
CHECKLIST_REPORT_CHAT_ID = int(os.getenv("CHECKLIST_REPORT_CHAT_ID", "0"))
CHECKLIST_REPORT_THREAD_ID = int(os.getenv("CHECKLIST_REPORT_THREAD_ID", "0"))
