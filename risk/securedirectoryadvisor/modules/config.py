"""
config.py - User configuration and app settings.

API keys are stored in the OS keychain via the `keyring` library when available,
falling back to the plain-text JSON config file if keyring is not installed.
"""

import contextlib
import copy
import json
import logging
import os
import threading

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional keyring support
# ---------------------------------------------------------------------------
try:
    import keyring as _keyring
    _KEYRING_AVAILABLE = True
except ImportError:
    _keyring = None
    _KEYRING_AVAILABLE = False

_KEYRING_SERVICE = "SecureFileAdvisor"

# Keys that should be kept in the OS keychain rather than the plain JSON file.
_SECURE_KEYS = {"virustotal_api_key", "google_safe_browsing_key"}


def _keyring_get(key: str) -> str:
    if not _KEYRING_AVAILABLE:
        return ""
    try:
        value = _keyring.get_password(_KEYRING_SERVICE, key)
        return value or ""
    except Exception as exc:
        log.warning("keyring read failed for %s: %s", key, exc)
        return ""


def _keyring_set(key: str, value: str):
    if not _KEYRING_AVAILABLE:
        return
    try:
        _keyring.set_password(_KEYRING_SERVICE, key, value)
    except Exception as exc:
        log.warning("keyring write failed for %s: %s", key, exc)


# ---------------------------------------------------------------------------
# Defaults (plain-text fields only)
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "downloads_folder": os.path.expanduser("~/Downloads"),
    "trusted_contact_name": "",
    "trusted_contact_email": "",
    "scan_history": [],
}
_ALLOWED_CONFIG_KEYS = set(DEFAULT_CONFIG)

CONFIG_PATH = os.path.expanduser("~/.secure_file_advisor_config.json")


class Config:
    def __init__(self):
        self._data = copy.deepcopy(DEFAULT_CONFIG)
        self._batch_mode = False
        self._lock = threading.RLock()
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def load(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if not isinstance(saved, dict):
                    raise json.JSONDecodeError("Config root must be a JSON object.", "", 0)

                # Strip any API keys that may have been stored in an older
                # plaintext config and migrate them to the keychain.
                migrated_secure_keys = False
                for key in _SECURE_KEYS:
                    if key in saved:
                        legacy_value = saved.pop(key)
                        if legacy_value and _KEYRING_AVAILABLE:
                            log.info("Migrating %s from config file to keychain.", key)
                            _keyring_set(key, legacy_value)
                            migrated_secure_keys = True
                        elif legacy_value:
                            # Keyring unavailable: keep legacy plaintext value as fallback.
                            saved[key] = legacy_value

                sanitized = {k: v for k, v in saved.items() if k in _ALLOWED_CONFIG_KEYS}
                with self._lock:
                    self._data.update(sanitized)
                    # Preserve legacy plaintext API-key fallback only when keyring is unavailable.
                    if not _KEYRING_AVAILABLE:
                        for key in _SECURE_KEYS:
                            if key in saved:
                                self._data[key] = saved[key]

                if migrated_secure_keys:
                    # Persist a cleaned config file with migrated keys removed.
                    self.save()
            except (json.JSONDecodeError, OSError) as exc:
                log.warning("Could not load config from %s: %s", CONFIG_PATH, exc)

    def save(self):
        with self._lock:
            if self._batch_mode:
                return
            tmp_path = f"{CONFIG_PATH}.tmp"
            config_dir = os.path.dirname(CONFIG_PATH) or "."
            payload = copy.deepcopy(self._data)
            try:
                os.makedirs(config_dir, exist_ok=True)
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, CONFIG_PATH)
            except OSError as exc:
                log.error("Could not save config to %s: %s", CONFIG_PATH, exc)
                with contextlib.suppress(OSError):
                    os.remove(tmp_path)

    @contextlib.contextmanager
    def batch_update(self):
        """Context manager that suppresses intermediate saves and writes once on exit.

        Use this when setting multiple attributes at once to avoid redundant
        disk writes:

            with config.batch_update():
                config.trusted_contact_name  = "Alice"
                config.trusted_contact_email = "alice@example.com"
        """
        with self._lock:
            self._batch_mode = True
        try:
            yield
        finally:
            with self._lock:
                self._batch_mode = False
            self.save()

    # ------------------------------------------------------------------
    # Attribute access (routes secure keys through keychain)
    # ------------------------------------------------------------------
    def __getattr__(self, key):
        if key.startswith("_"):
            raise AttributeError(key)
        if key in _SECURE_KEYS:
            if _KEYRING_AVAILABLE:
                return _keyring_get(key)
            # Fallback: read from plain data dict (legacy or keyring unavailable)
            with self._lock:
                return self._data.get(key, "")
        with self._lock:
            try:
                value = self._data[key]
            except KeyError:
                raise AttributeError(f"No config key: {key}")
        if isinstance(value, (list, dict)):
            return copy.deepcopy(value)
        return value

    def __setattr__(self, key, value):
        if key.startswith("_"):
            super().__setattr__(key, value)
            return
        if key in _SECURE_KEYS:
            if _KEYRING_AVAILABLE:
                _keyring_set(key, value)
                return
            # Fallback: store in plain data dict
            with self._lock:
                self._data[key] = value
            self.save()
            return
        with self._lock:
            self._data[key] = value
        self.save()

    def add_scan_history(self, entry: dict):
        with self._lock:
            history = self._data.get("scan_history", [])
            history.insert(0, entry)
            self._data["scan_history"] = history[:100]
            self.save()

    def clear_scan_history(self):
        with self._lock:
            self._data["scan_history"] = []
            self.save()
