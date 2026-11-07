from dotenv import load_dotenv
from pathlib import Path
import os
root = Path(__file__).resolve().parent
os.chdir(root)
load_dotenv(root / ".env")
import runpy
runpy.run_module('bot',run_name='__main__')
