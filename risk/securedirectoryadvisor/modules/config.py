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
    "trusted_contact_phone": "",
    "font_size": "large",
    "high_contrast": False,
    "scan_history": [],
}

CONFIG_PATH = os.path.expanduser("~/.secure_file_advisor_config.json")


class Config:
    def __init__(self):
        self._data = copy.deepcopy(DEFAULT_CONFIG)
        self._batch_mode = False
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def load(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # Strip any API keys that may have been stored in an older
                # plaintext config and migrate them to the keychain.
                for key in _SECURE_KEYS:
                    if key in saved:
                        legacy_value = saved.pop(key)
                        if legacy_value and _KEYRING_AVAILABLE:
                            log.info("Migrating %s from config file to keychain.", key)
                            _keyring_set(key, legacy_value)
                self._data.update(saved)
            except (json.JSONDecodeError, OSError) as exc:
                log.warning("Could not load config from %s: %s", CONFIG_PATH, exc)

    def save(self):
        if self._batch_mode:
            return
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except OSError as exc:
            log.error("Could not save config to %s: %s", CONFIG_PATH, exc)

    @contextlib.contextmanager
    def batch_update(self):
        """Context manager that suppresses intermediate saves and writes once on exit.

        Use this when setting multiple attributes at once to avoid redundant
        disk writes:

            with config.batch_update():
                config.trusted_contact_name  = "Alice"
                config.trusted_contact_email = "alice@example.com"
        """
        self._batch_mode = True
        try:
            yield
        finally:
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
            return self._data.get(key, "")
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(f"No config key: {key}")

    def __setattr__(self, key, value):
        if key.startswith("_"):
            super().__setattr__(key, value)
            return
        if key in _SECURE_KEYS:
            if _KEYRING_AVAILABLE:
                _keyring_set(key, value)
                return
            # Fallback: store in plain data dict
            self._data[key] = value
            self.save()
            return
        self._data[key] = value
        self.save()

    def add_scan_history(self, entry: dict):
        history = self._data.get("scan_history", [])
        history.insert(0, entry)
        self._data["scan_history"] = history[:100]
        self.save()
