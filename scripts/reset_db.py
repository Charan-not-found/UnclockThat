"""Reset the CLOCKIT SQLite database cleanly (works even if a server holds clockit.db open)."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect, text  # noqa: E402
from backend.app.core.config import get_settings  # noqa: E402
from backend.app.database.base import Base  # noqa: E402
from backend.app.database.connection import engine, init_db  # noqa: E402


def reset_database(clean_files: bool = False) -> None:
    """Delete SQLite files if unlocked, or drop & recreate all tables via SQLAlchemy."""
    engine.dispose()

    unlinked = True
    for suffix in ("", "-wal", "-shm"):
        db_file = ROOT / f"clockit.db{suffix}"
        if db_file.is_file():
            try:
                db_file.unlink()
                print(f"Removed {db_file.name}")
            except PermissionError:
                unlinked = False

    if not unlinked:
        print("clockit.db is open in another process — dropping and recreating all tables in-place...")
        from backend.app.database import models  # noqa: F401
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys=OFF"))
        Base.metadata.drop_all(bind=engine)
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys=ON"))

    if clean_files:
        settings = get_settings()
        for folder in (
            settings.storage_root / "uploads",
            settings.storage_root / "inspection_results",
            settings.data_root / "datasets",
            settings.data_root / "training",
            settings.data_root / "false_positives",
            ROOT / "outputs" / "reports",
            ROOT / "outputs" / "visualizations",
        ):
            if folder.is_dir():
                for item in folder.iterdir():
                    if item.name == ".gitkeep":
                        continue
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                print(f"Cleaned runtime files in {folder.relative_to(ROOT)}")

    init_db()
    tables = sorted(inspect(engine).get_table_names())
    print(f"Database reset complete. Recreated {len(tables)} tables: {tables}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset CLOCKIT SQLite database")
    parser.add_argument(
        "--clean-files",
        action="store_true",
        help="Also remove uploaded images, datasets, heatmaps, and reports.",
    )
    args = parser.parse_args()
    reset_database(clean_files=args.clean_files)
