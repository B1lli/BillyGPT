# coding=utf-8
"""Small compatibility helper for BillyGPT's legacy API key handling."""

import os

from paths import LEGACY_KEY_FILE, REPO_LEGACY_KEY_FILE


def read_api_key():
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key.strip()

    lines = []
    for key_path in (LEGACY_KEY_FILE, REPO_LEGACY_KEY_FILE):
        try:
            with open(key_path, "r", encoding="utf-8") as key_file:
                lines = key_file.readlines()
                break
        except FileNotFoundError:
            continue

    for line in reversed(lines):
        key = line.strip()
        if key:
            return key
    return None


def write_api_key(api_key=None):
    if not api_key:
        return
    key = api_key.strip()
    if not key:
        return
    os.environ["OPENAI_API_KEY"] = key


# Backward-compatible names for old scripts that imported these helpers.
read_APIKEY = read_api_key
write_APIKEY = write_api_key
