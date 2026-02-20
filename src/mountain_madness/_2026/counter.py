import datetime
import fcntl
import json
import threading
from pathlib import Path

from constants import TZ_INFO


class CounterFile:
    """Thread-safe counter with file persistence."""

    def __init__(
        self,
        filepath: Path,
        save_interval: int = 60,
        save_threshold: int = 10,
    ):
        self.filepath = filepath
        self.save_interval = save_interval
        self.save_threshold = save_threshold
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}
        self._changes_since_save = 0
        self.last_save_time: datetime.datetime | None = None
        with self._lock:
            self._load_from_file_unlocked()

    def start(self) -> None:
        """Start the auto-save background thread."""

        def auto_save():
            while True:
                threading.Event().wait(self.save_interval)
                with self._lock:
                    if self._changes_since_save > 0:
                        self._save_to_file_unlocked()

        thread = threading.Thread(target=auto_save, daemon=True)
        thread.start()

    def increment(self, key: str, amount: int = 1) -> dict[str, int]:
        """Increment a counter by the given amount."""
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + amount
            self._maybe_save_unlocked()
            return self._counters.copy()

    def get(self, key: str) -> int:
        """Get the current value of a counter."""
        with self._lock:
            return self._counters.get(key, 0)

    def get_all(self) -> dict[str, int]:
        """Get a copy of all counters."""
        with self._lock:
            return self._counters.copy()

    def reset(self, key: str) -> None:
        """Reset a specific counter to zero."""
        with self._lock:
            self._counters[key] = 0
            self._maybe_save_unlocked()

    def _maybe_save_unlocked(self) -> None:
        """Check threshold and save if needed. Must hold lock."""
        self._changes_since_save += 1
        if self._changes_since_save >= self.save_threshold:
            self._save_to_file_unlocked()

    def _save_to_file_unlocked(self) -> None:
        """Save counters to file. Must hold lock."""
        last_save_time = datetime.datetime.now(TZ_INFO)
        save_data = {
            "counters": self._counters.copy(),
            "last_save_time": last_save_time.isoformat(),
        }

        temp_file = self.filepath.with_suffix(".tmp")
        try:
            with temp_file.open("w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(save_data, f, indent=2)
                    f.flush()
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            temp_file.replace(self.filepath)
            self.last_save_time = last_save_time
            self._changes_since_save = 0
        except OSError as e:
            print(f"Error saving counter file: {e}")

    def _load_from_file_unlocked(self) -> None:
        """Load counters from file. Must hold lock."""
        try:
            with self.filepath.open("r") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            self._counters = data.get("counters", {})
            if last_save := data.get("last_save_time"):
                self.last_save_time = datetime.datetime.fromisoformat(last_save)
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading counter file: {e}")
