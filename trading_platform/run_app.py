import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "trading_platform" / "app.py"


def main() -> None:
    subprocess.run(
        [
            "streamlit",
            "run",
            str(APP_PATH),
            "--server.address",
            "0.0.0.0",
            "--server.port",
            "8503",
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
