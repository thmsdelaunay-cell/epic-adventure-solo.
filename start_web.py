"""Local game interface: run from the existing bot folder with py start_web.py."""
from pathlib import Path
import os

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
# Resolve the same save next to the bot, even when Windows starts elsewhere.
save = Path(os.getenv("DATABASE_PATH", "adventure.db")).expanduser()
if not save.is_absolute():
    save = ROOT / save
os.environ["DATABASE_PATH"] = str(save.resolve())

if __name__ == "__main__":
    from web_game import main
    main()
