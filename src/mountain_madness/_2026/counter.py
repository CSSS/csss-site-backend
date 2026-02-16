import atexit
import datetime
import fcntl
import json
import threading
import time
from pathlib import Path

from constants import TZ_INFO


class CounterFile:
    def __init__(self, filepath: str, save_interval: int, save_threshold: int):
        """
        Counter that saves to a file.

        Args:
            filepath: The absolute file path to save the counter to.
            save_interval: How often to save to the file, in seconds
            save_threshold: How often to save to the file, in number of changes
        """
        self.__counters: dict[str, int] = {}

        self.filepath = Path(filepath)
        self.save_interval = save_interval
        self.save_threshold = save_threshold
        self.lock = threading.Lock()
        self.create_time = datetime.datetime.now(TZ_INFO)
        self.last_save_time = self.create_time
        self.changes_since_last_save = 0

        self._is_auto_save_enabled = save_interval > 0

        # If the program shuts down, turn save one last time
        atexit.register(self.__save_to_file)

        self.start()

    def start(self):
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        save_data = {
            "counters": self.__counters,
            "last_save_time": self.last_save_time.isoformat(),
        }
        # Create file if it doesn't exist
        if not self.filepath.exists():
            self.filepath.write_text(json.dumps(save_data, indent=2))
            self.__save_to_file()
        else:
            # Otherwise check the file and load from it
            try:
                with Path.open(self.filepath) as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        data = json.load(f)
                        self.__counters = data.get("counters", {})
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except (OSError, json.JSONDecodeError):
                self.__counters = {}
        if self._is_auto_save_enabled:
            self.daemon_thread = threading.Thread(target=self.__save_daemon, daemon=True)
            self.daemon_thread.start()

    def increment(self, key: str, amount: int = 1):
        with self.lock:
            self.__counters[key] = self.__counters.get(key, 0) + amount
            self.changes_since_last_save += 1

        if self.changes_since_last_save >= self.save_threshold:
            self.__save_to_file()

    def get_all_counters(self) -> dict[str, int]:
        with self.lock:
            return self.__counters.copy()

    def __save_daemon(self):
        while self._is_auto_save_enabled:
            time.sleep(self.save_interval)
            if self.changes_since_last_save:
                self.__save_to_file()

    def __save_to_file(self):
        with self.lock:
            if not self.changes_since_last_save:
                return
            last_save_time = datetime.datetime.now(TZ_INFO)
            save_data = {"counters": self.__counters.copy(), "last_save_time": last_save_time.isoformat()}

        # Save to temp file and then move it
        temp_file = self.filepath.with_suffix(".tmp")
        try:
            with Path.open(temp_file, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(save_data, f, indent=2)
                    f.flush()
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

                temp_file.replace(self.filepath)
        except OSError:
            print("Error saving counter file")
            return

        with self.lock:
            self.changes_since_last_save = 0
            self.last_save_time = last_save_time

    def shutdown(self):
        self._is_auto_save_enabled = False
        if hasattr(self, "daemon_thread") and self.daemon_thread.is_alive():
            self.daemon_thread.join(timeout=5)
        self.__save_to_file()
