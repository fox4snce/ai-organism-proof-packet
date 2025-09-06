import subprocess
import sys
from pathlib import Path


def run(cmd):
    print("$", " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)


def main():
    py = str((Path.cwd() / ".venv" / "Scripts" / "python.exe")) if sys.platform.startswith('win') else "python"
    run([py, "bin/pp", "run", "demos/*.json", "--out", "runs/"])
    r = subprocess.run([py, "bin/pp", "verify", "runs/", "golden/"])
    if r.returncode != 0:
        print("Verify failed; not updating goldens.")
        sys.exit(1)
    if "--update" in sys.argv:
        for p in Path("runs").glob("*.trace.json"):
            gp = Path("golden") / p.name
            gp.write_bytes(p.read_bytes())
        print("Goldens updated.")


if __name__ == "__main__":
    main()


