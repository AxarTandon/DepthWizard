"""
Filesystem storage abstraction - rasters/images live on disk, not in Postgres.
storage/projects/{project_id}/input|intermediate|output|validation|exports
"""
import os

from app.core.config import get_settings

settings = get_settings()


def project_dir(project_id: str, subdir: str = "") -> str:
    # Defend against path traversal in project_id and subdir
    clean_project_id = os.path.basename(project_id.replace("\\", "/")).strip(". ")
    clean_subdir = os.path.basename(subdir.replace("\\", "/")).strip(". ") if subdir else ""
    path = os.path.join(settings.STORAGE_ROOT, "projects", clean_project_id, clean_subdir)
    os.makedirs(path, exist_ok=True)
    return path


def safe_filename(filename: str) -> str:
    """Strips path separators across platforms and any '..' traversal attempts."""
    # Normalize forward/backward slashes before basename
    cleaned = filename.replace("\\", "/").strip()
    name = os.path.basename(cleaned)
    name = name.replace("..", "").replace("\0", "").strip()
    return name or "upload"

