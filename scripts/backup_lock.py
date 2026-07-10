"""Simple exclusive file lock to prevent overlapping backup runs."""

from __future__ import annotations

import os
import time
from pathlib import Path


class BackupLockError(Exception):
    pass


class BackupLock:
    """Best-effort exclusive lock using create-exclusive lock file.

    Not a cross-machine distributed lock — local process coordination only.
    """

    def __init__(self, lock_path: Path, *, timeout_sec: float = 0, stale_sec: float = 3600):
        self.lock_path = Path(lock_path)
        self.timeout_sec = timeout_sec
        self.stale_sec = stale_sec
        self._fd: int | None = None

    def __enter__(self) -> "BackupLock":
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + self.timeout_sec
        while True:
            try:
                self._fd = os.open(
                    str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644
                )
                os.write(self._fd, f"pid={os.getpid()} time={time.time()}\n".encode())
                return self
            except FileExistsError:
                # Stale lock cleanup
                try:
                    age = time.time() - self.lock_path.stat().st_mtime
                    if age > self.stale_sec:
                        self.lock_path.unlink(missing_ok=True)
                        continue
                except OSError:
                    pass
                if self.timeout_sec <= 0 or time.time() >= deadline:
                    raise BackupLockError(
                        f"Another backup holds the lock: {self.lock_path}"
                    )
                time.sleep(0.2)

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        try:
            self.lock_path.unlink(missing_ok=True)
        except OSError:
            pass
