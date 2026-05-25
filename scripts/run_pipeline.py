from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_PATH = PROJECT_ROOT / "venv" / "bin" / "python"

SCRIPTS = [
    "load_ticker_metadata.py",
    "load_stock_prices.py",
    "load_economic_indicators.py",
]


def run_script(script_name: str) -> None:
    script_path = PROJECT_ROOT / "scripts" / script_name

    print("=" * 70)
    print(f"Running: {script_name}")
    print(f"Path: {script_path}")
    print("=" * 70)

    result = subprocess.run(
        [str(PYTHON_PATH), str(script_path)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print("STDERR:")
        print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"{script_name} failed with exit code {result.returncode}"
        )

    print(f"Finished: {script_name}")


def main() -> None:
    print("=" * 70)
    print("Starting Finance/Economics Pipeline")
    print(f"Project root: {PROJECT_ROOT}")
    print("=" * 70)

    for script in SCRIPTS:
        run_script(script)

    print("=" * 70)
    print("Pipeline completed successfully.")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Pipeline failed: {error}")
        sys.exit(1)
