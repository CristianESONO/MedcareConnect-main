from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent

for directory in (BACKEND_DIR, REPO_DIR):
    directory_str = str(directory)
    if directory_str not in sys.path:
        sys.path.insert(0, directory_str)
