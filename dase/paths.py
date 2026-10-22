"""Repository resource paths, independent of the process working directory."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROFILES_DIR = DATA_DIR / "company_profiles"
PROMPT_PATH = DATA_DIR / "prompts" / "prompt.txt"
ENV_PATH = PROJECT_ROOT / ".env"
SESSION_LOG_DIR = PROJECT_ROOT / "session_logs"
