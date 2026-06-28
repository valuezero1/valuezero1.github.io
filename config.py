import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()
else:
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _required_int(name: str) -> int:
    value = _required(name)
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer") from exc


BOT_TOKEN = _required("BOT_TOKEN")
ADMIN_ID = _required_int("ADMIN_ID")
CHECKLISTCHECKER_ID = [
    int(value.strip())
    for value in os.getenv("CHECKLISTCHECKER_ID", "").split(",")
    if value.strip()
]
CHECKLIST_REPORT_CHAT_ID = int(os.getenv("CHECKLIST_REPORT_CHAT_ID", "0"))
CHECKLIST_REPORT_THREAD_ID = int(os.getenv("CHECKLIST_REPORT_THREAD_ID", "0"))
LANGAME_DOMAIN = os.getenv("LANGAME_DOMAIN", "rave4-200.langame.ru")
LANGAME_TOKEN = os.getenv("LANGAME_TOKEN", "")
