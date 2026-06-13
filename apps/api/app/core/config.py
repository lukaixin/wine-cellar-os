from dataclasses import dataclass
import os
from pathlib import Path


def _default_data_dir() -> str:
    return str(Path(__file__).resolve().parents[4] / "data")


@dataclass(frozen=True)
class Settings:
    app_name: str = "Wine Cellar OS API"
    database_url: str = "sqlite:///./wine_cellar.db"
    data_dir: str = _default_data_dir()
    label_upload_dir: str = str(Path(_default_data_dir()) / "uploads" / "labels")
    label_max_upload_bytes: int = 5 * 1024 * 1024


def get_settings() -> Settings:
    data_dir = os.getenv("WINE_CELLAR_DATA_DIR", Settings.data_dir)
    label_upload_dir = os.getenv("WINE_CELLAR_LABEL_UPLOAD_DIR", str(Path(data_dir) / "uploads" / "labels"))
    return Settings(
        app_name=os.getenv("WINE_CELLAR_APP_NAME", Settings.app_name),
        database_url=os.getenv("WINE_CELLAR_DATABASE_URL", Settings.database_url),
        data_dir=data_dir,
        label_upload_dir=label_upload_dir,
        label_max_upload_bytes=int(
            os.getenv("WINE_CELLAR_LABEL_MAX_UPLOAD_BYTES", str(Settings.label_max_upload_bytes))
        ),
    )
