"""
src/services/persistence/jsonl_store.py

Provides safe JSONL append/read operations. Handles missing files, empty files,
corrupted lines, and directory creation.
"""
import os
import json
from typing import List, Dict, Any, Optional
from src.utils.logger import get_logger

logger = get_logger("jsonl_store")

class JSONLStore:
    """Safe wrapper for reading and appending to JSONL files."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._ensure_directory_exists()
        
    def _ensure_directory_exists(self):
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")

    def append(self, record: Dict[str, Any]) -> bool:
        """Appends a single JSON record to the file safely."""
        self._ensure_directory_exists()
        try:
            with open(self.filepath, 'a', encoding='utf-8') as f:
                json_line = json.dumps(record)
                f.write(json_line + '\n')
            return True
        except Exception as e:
            logger.error(f"Failed to append to {self.filepath}: {e}")
            return False

    def read_all(self) -> List[Dict[str, Any]]:
        """Reads all valid JSON records from the file. Skips malformed lines."""
        if not os.path.exists(self.filepath):
            return []
            
        records = []
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        records.append(record)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Malformed JSON on line {line_num} in {self.filepath}: {e}. Skipping line.")
        except Exception as e:
            logger.error(f"Failed to read {self.filepath}: {e}")
            
        return records
        
    def overwrite_all(self, records: List[Dict[str, Any]]) -> bool:
        """Overwrites the entire file with a list of records. Use with caution!"""
        self._ensure_directory_exists()
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                for record in records:
                    json_line = json.dumps(record)
                    f.write(json_line + '\n')
            return True
        except Exception as e:
            logger.error(f"Failed to overwrite {self.filepath}: {e}")
            return False

    def compute_checksum(self) -> str:
        """Returns SHA-256 hex digest of the file, or '' if the file does not exist."""
        import hashlib
        if not os.path.exists(self.filepath):
            return ""
        h = hashlib.sha256()
        try:
            with open(self.filepath, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception as e:
            logger.error("Checksum computation failed for %s: %s", self.filepath, e)
            return ""

    def verify_integrity(self, expected_checksum: str) -> bool:
        """Returns True if the file's current checksum matches expected_checksum."""
        return self.compute_checksum() == expected_checksum

    def health_status(self) -> dict:
        """Returns a simple health status dict for this store."""
        exists   = os.path.exists(self.filepath)
        writable = os.access(self.filepath, os.W_OK) if exists else False
        records  = self.read_all() if exists else []
        return {
            "filepath":      self.filepath,
            "exists":        exists,
            "writable":      writable,
            "record_count":  len(records),
            "status":        "HEALTHY" if exists and writable else ("WARNING" if exists else "MISSING"),
        }
