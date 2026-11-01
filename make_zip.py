"""Package the project for submission: a folder named hw3 and hw3.zip beside it.

Leaves out the real .env, the virtual environment, caches, editor settings, and the course
data pack. Stops if any file to be packaged contains the Portkey key.
"""

from __future__ import annotations

import os
import shutil
import sys
import zipfile
from pathlib import Path

from config import PROJECT_DIR, load_environment

STAGING = PROJECT_DIR / "hw3"
ZIP_PATH = PROJECT_DIR / "hw3.zip"
TOP_LEVEL_FILES = [
    "AI_prompts.md", "README.md", "requirements.txt", ".env.example", ".gitignore",
    "agent.py", "tools.py", "models.py", "build_catalogue.py", "config.py", "catalogue_db.py",
    "build_profiles.py", "evaluate.py", "review_app.py", "view_catalogue.py", "view_audit.py",
    "build_report.py", "make_zip.py", "test_agent.py", "test_catalogue.py",
]
FOLDERS = ["prompts", "profiles", "output", ".claude/skills"]
SKIP_SUFFIXES = {".tmp", ".pyc"}
REQUIRED = [
    "AI_prompts.md", "requirements.txt", ".env.example", "agent.py", "tools.py",
    "build_catalogue.py", "models.py", "prompts/prompt.md", "profiles/profile_student.json",
    "profiles/profile_parent.json", "output/catalogue.json", "output/harness.md",
    "output/identify_product.json", "output/agent_evaluation.md",
    "output/ad_effectiveness.json", "output/audit_trail.json",
]


def files_to_package() -> list[Path]:
    files = [PROJECT_DIR / name for name in TOP_LEVEL_FILES]
    for folder in FOLDERS:
        files += [
            path for path in sorted((PROJECT_DIR / folder).rglob("*"))
            if path.is_file() and path.suffix not in SKIP_SUFFIXES and "__pycache__" not in path.parts
        ]
    return files


def main() -> int:
    files = files_to_package()
    missing = [name for name in REQUIRED if PROJECT_DIR / name not in files or not (PROJECT_DIR / name).is_file()]
    if missing:
        print(f"Missing required files: {missing}", file=sys.stderr)
        return 1

    load_environment()
    secret = (os.getenv("PORTKEY_API_KEY") or "").encode()
    leaked = [f for f in files if secret and secret in f.read_bytes()]
    if leaked or any(f.name == ".env" for f in files):
        print(f"Refusing to package: secret found in {[str(f) for f in leaked]}", file=sys.stderr)
        return 1

    if STAGING.exists():
        shutil.rmtree(STAGING)
    for source in files:
        target = STAGING / source.relative_to(PROJECT_DIR)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    ZIP_PATH.unlink(missing_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(STAGING.rglob("*")):
            if path.is_file():
                archive.write(path, (Path("hw3") / path.relative_to(STAGING)).as_posix())
    size = ZIP_PATH.stat().st_size / 1_000_000
    print(f"Packaged {len(files)} files into hw3/ and hw3.zip ({size:.1f} MB). No secret found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
