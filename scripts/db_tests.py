import os
import sys
import subprocess
from pathlib import Path

def main():
    # Determine directories
    root_dir = Path(__file__).resolve().parent.parent
    src_dir = root_dir / "src"
    
    # Add src to python path for the runner process
    env = os.environ.copy()
    python_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([str(src_dir), python_path]) if python_path else str(src_dir)
    
    # Ensure POSTGRES_ENGINE is configured for DB tests if not already set
    if "POSTGRES_ENGINE" not in env:
        env["POSTGRES_ENGINE"] = "postgres:postgres@localhost:5432/nps_db"

    tests = [
        ("test_adapter", [sys.executable, str(src_dir / "nps_crawling" / "db" / "test_adapter.py")]),
        ("test_db_scenarios", [sys.executable, str(src_dir / "nps_crawling" / "db" / "test_db_scenarios.py")]),
    ]

    success = True
    for name, cmd in tests:
        print("=" * 60)
        print(f"Running database test: {name}")
        print("=" * 60)
        try:
            subprocess.run(cmd, env=env, check=True)
            print(f"-> {name} completed successfully.\n")
        except subprocess.CalledProcessError as e:
            print(f"-> ERROR in {name}: {e}\n")
            success = False

    if success:
        print("All database tests completed successfully!")
        sys.exit(0)
    else:
        print("Some database tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
