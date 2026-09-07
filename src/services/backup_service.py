"""
src/services/backup_service.py

Lightweight local backup and recovery service.

PROTOTYPE NOTICE:
Backs up the `data/` directory to a timestamped ZIP file in `backups/`.
Restore requires ADMIN role authorization. A pre-restore safety backup
is always created before any restore operation.
"""
import os
import shutil
import zipfile
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.utils.logger import get_logger

logger = get_logger("backup_service")

BACKUP_DIR   = "backups"
DATA_DIR     = "data"
LOGS_DIR     = "logs"


def _ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _zip_directory(source_dir: str, zip_path: str) -> bool:
    """Creates a ZIP of source_dir at zip_path."""
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, start=os.path.dirname(source_dir))
                    zf.write(full_path, arcname)
        return True
    except Exception as e:
        logger.error("Failed to create ZIP %s: %s", zip_path, e)
        return False


def _sha256_of_file(filepath: str) -> str:
    """Computes SHA-256 checksum of a file."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logger.error("Failed to compute checksum for %s: %s", filepath, e)
        return ""


class BackupService:

    @staticmethod
    def create_backup(label: str = "") -> Dict[str, Any]:
        """
        Creates a timestamped backup of data/ and logs/ directories.
        Returns metadata dict with path and checksum.
        """
        _ensure_backup_dir()
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        safe_label = label.replace(" ", "_")[:30] if label else "manual"
        zip_name   = f"backup_{ts}_{safe_label}.zip"
        zip_path   = os.path.join(BACKUP_DIR, zip_name)

        # Create a combined temporary directory to zip both data/ and logs/
        tmp_dir = os.path.join(BACKUP_DIR, f"_tmp_{ts}")
        os.makedirs(tmp_dir, exist_ok=True)
        try:
            if os.path.exists(DATA_DIR):
                shutil.copytree(DATA_DIR, os.path.join(tmp_dir, "data"))
            if os.path.exists(LOGS_DIR):
                shutil.copytree(LOGS_DIR, os.path.join(tmp_dir, "logs"))

            ok = _zip_directory(tmp_dir, zip_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        if not ok:
            return {"status": "FAILED", "reason": "ZIP creation failed."}

        checksum = _sha256_of_file(zip_path)
        size_kb  = os.path.getsize(zip_path) // 1024

        meta = {
            "status":    "OK",
            "filename":  zip_name,
            "path":      zip_path,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "label":     label,
            "size_kb":   size_kb,
            "sha256":    checksum,
        }
        logger.info("Backup created: %s (%.1f KB, sha256=%s)", zip_name, size_kb, checksum[:12])
        return meta

    @staticmethod
    def list_backups() -> List[Dict[str, Any]]:
        """Lists all available backup files with metadata."""
        _ensure_backup_dir()
        backups = []
        for fname in sorted(os.listdir(BACKUP_DIR)):
            if fname.endswith(".zip"):
                fpath = os.path.join(BACKUP_DIR, fname)
                stat  = os.stat(fpath)
                backups.append({
                    "filename":    fname,
                    "path":        fpath,
                    "size_kb":     stat.st_size // 1024,
                    "modified_at": datetime.utcfromtimestamp(stat.st_mtime).isoformat() + "Z",
                })
        return backups

    @staticmethod
    def validate_backup(zip_path: str) -> Dict[str, Any]:
        """Validates that a backup file is a readable ZIP."""
        if not os.path.exists(zip_path):
            return {"valid": False, "reason": "Backup file not found."}
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                bad = zf.testzip()
                if bad:
                    return {"valid": False, "reason": f"Corrupt file in ZIP: {bad}"}
            checksum = _sha256_of_file(zip_path)
            size_kb  = os.path.getsize(zip_path) // 1024
            return {"valid": True, "sha256": checksum, "size_kb": size_kb}
        except zipfile.BadZipFile as e:
            return {"valid": False, "reason": f"Bad ZIP: {e}"}
        except Exception as e:
            return {"valid": False, "reason": f"Unexpected error: {e}"}

    @staticmethod
    def restore_backup(zip_path: str, actor_role: str = "ADMIN") -> Dict[str, Any]:
        """
        Restores data/ and logs/ from a backup ZIP.
        Requires ADMIN authorization (enforced by the caller via AccessControl).
        Creates a pre-restore safety backup before overwriting.
        """
        # 1. Validate backup before touching anything
        validation = BackupService.validate_backup(zip_path)
        if not validation.get("valid"):
            return {"status": "FAILED", "reason": validation.get("reason")}

        # 2. Pre-restore safety backup
        logger.info("Creating pre-restore safety backup before restore.")
        safety = BackupService.create_backup(label="pre_restore_safety")
        if safety.get("status") != "OK":
            return {"status": "FAILED", "reason": "Pre-restore safety backup failed. Aborting."}

        # 3. Extract backup to temporary staging area
        tmp_extract = os.path.join(BACKUP_DIR, "_restore_tmp")
        if os.path.exists(tmp_extract):
            shutil.rmtree(tmp_extract, ignore_errors=True)
        os.makedirs(tmp_extract, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(tmp_extract)

            # 4. Replace data/ and logs/ if they exist in backup
            restored = []
            for subdir in ["data", "logs"]:
                src = os.path.join(tmp_extract, subdir)
                dst = subdir
                if os.path.exists(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    restored.append(subdir)

            logger.info("Restore completed by %s. Restored: %s", actor_role, restored)
            return {
                "status": "OK",
                "restored": restored,
                "safety_backup": safety.get("filename"),
                "actor_role": actor_role,
            }
        except Exception as e:
            logger.error("Restore failed: %s", e)
            return {"status": "FAILED", "reason": f"Restore error (system logged). Safety backup: {safety.get('filename')}"}
        finally:
            shutil.rmtree(tmp_extract, ignore_errors=True)
