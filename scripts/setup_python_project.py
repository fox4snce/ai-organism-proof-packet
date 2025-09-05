import os
import sys
import subprocess
import shutil
import venv
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def ensure_virtual_environment(project_root: Path) -> Path:
    env_dir = project_root / ".venv"
    if env_dir.exists():
        print(f"[venv] Existing virtual environment found at: {env_dir}")
        return env_dir

    print(f"[venv] Creating virtual environment at: {env_dir}")
    builder = venv.EnvBuilder(with_pip=True, clear=False, upgrade=False, symlinks=None, upgrade_deps=False)
    builder.create(str(env_dir))
    print("[venv] Virtual environment created.")

    # Upgrade core tooling inside the venv for reliability
    venv_python = get_venv_python(env_dir)
    try:
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], check=True)
        print("[venv] Upgraded pip, setuptools, and wheel.")
    except subprocess.CalledProcessError as e:
        print(f"[venv] Warning: Failed to upgrade pip tooling: {e}")

    return env_dir


def get_venv_python(env_dir: Path) -> Path:
    if os.name == "nt":
        return env_dir / "Scripts" / "python.exe"
    return env_dir / "bin" / "python"


def ensure_gitignore(project_root: Path) -> None:
    gitignore_path = project_root / ".gitignore"
    default_content = """
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# PEP 582
__pypackages__/

# Celery
celerybeat-schedule
celerybeat.pid

# SageMath
*.sage.py

# Environments
.env
.env.*
.venv/
venv/
ENV/
env/
env.bak/
venv.bak/

# Spyder
.spyderproject
.spyproject

# Rope
.ropeproject

# mkdocs
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# pyre type checker
.pyre/

# pytype
.pytype/

# Cython debug symbols
cython_debug/

# IDEs/editors
.vscode/
.idea/
""".lstrip()

    if gitignore_path.exists():
        existing = gitignore_path.read_text(encoding="utf-8")
        if ".venv/" not in existing:
            print("[gitignore] Appending '.venv/' to existing .gitignore")
            with gitignore_path.open("a", encoding="utf-8") as f:
                f.write("\n.venv/\n")
        else:
            print("[gitignore] .gitignore already contains '.venv/'")
        return

    print("[gitignore] Creating .gitignore with Python defaults and '.venv/' entry")
    gitignore_path.write_text(default_content, encoding="utf-8")


def initialize_git_repo(project_root: Path) -> None:
    git_dir = project_root / ".git"
    if git_dir.exists():
        print("[git] Existing Git repository detected.")
        return

    if shutil.which("git") is None:
        print("[git] Git is not installed or not on PATH. Skipping git initialization.")
        return

    print("[git] Initializing Git repository...")
    try:
        subprocess.run(["git", "init"], cwd=project_root, check=True)
        # Standardize default branch to main when possible
        subprocess.run(["git", "branch", "-M", "main"], cwd=project_root, check=False)
        print("[git] Git repository initialized.")
    except subprocess.CalledProcessError as e:
        print(f"[git] Warning: Failed to initialize git: {e}")


def main() -> None:
    project_root = get_project_root()
    print(f"[info] Project root: {project_root}")

    ensure_virtual_environment(project_root)
    ensure_gitignore(project_root)
    initialize_git_repo(project_root)

    # Print activation hints for Windows PowerShell and POSIX shells
    print("\n[done] Setup complete.")
    if os.name == "nt":
        print("[hint] Activate with: .\\.venv\\Scripts\\Activate.ps1")
    else:
        print("[hint] Activate with: source ./.venv/bin/activate")


if __name__ == "__main__":
    if sys.version_info < (3, 8):
        raise SystemExit("Python 3.8+ is required.")
    main()


