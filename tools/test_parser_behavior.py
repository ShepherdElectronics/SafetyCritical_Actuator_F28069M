"""Behavioral tests compiled against the real C2000 parser implementation."""
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    compiler = shutil.which("cc") or shutil.which("gcc")
    if compiler is None:
        raise SystemExit("No C compiler found; install one to run parser behavior checks.")
    with tempfile.TemporaryDirectory() as directory:
        binary = Path(directory) / "parser_behavior_harness"
        subprocess.run([compiler, "-std=c99", "-Wall", "-Wextra", "-Werror", str(ROOT / "src" / "command_parser.c"), str(ROOT / "tools" / "parser_behavior_harness.c"), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)

if __name__ == "__main__":
    main()
