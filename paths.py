# coding=utf-8
"""Repository-local paths used by the legacy desktop app."""

import os
import platform
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = ROOT_DIR / "assets"
FONT_PATH = ASSETS_DIR / "font.ttf"


def user_data_dir():
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "BillyGPT"
    if system == "Windows":
        root = os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming"
        return Path(root) / "BillyGPT"
    return Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "BillyGPT"


APP_DATA_DIR = user_data_dir()
CHATLOG_DIR = APP_DATA_DIR / "chatlog"
CACHE_DIR = APP_DATA_DIR / "cache"
SETTINGS_FILE = APP_DATA_DIR / "settings.txt"
LEGACY_KEY_FILE = APP_DATA_DIR / "APIKEY.txt"
REPO_LEGACY_KEY_FILE = ROOT_DIR / "APIKEY.txt"
CUSTOM_FONT_PATH = APP_DATA_DIR / "font.ttf"


def active_font_path():
    return CUSTOM_FONT_PATH if CUSTOM_FONT_PATH.exists() else FONT_PATH
