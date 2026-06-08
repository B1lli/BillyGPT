#!/usr/bin/env python3
# coding=utf-8
"""Minimal startup check for BillyGPT."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import main
import prompt_engineering
from api_key_store import read_api_key


def main_check():
    assert read_api_key() == "test-key"
    assert callable(main.ft_interface)
    assert callable(main.create_chat_json)
    assert callable(prompt_engineering.prompt_composition_analysis)

    with tempfile.TemporaryDirectory() as tmp_dir:
        chat_path = main.create_chat_json(tmp_dir)
        chat_hash = main.save_now_chat(chat_path, "user", "hello")
        role, content = main.get_one_role_and_content(chat_path, chat_hash)
        assert role == "user"
        assert content == "hello"
        main.renew_now_chat(chat_path, chat_hash, content="")
        combined = main.get_combined_data(chat_path)
        assert combined == [{"role": "user", "content": ""}]
        main.renew_now_chat(chat_path, chat_hash, content="hello again")
        combined = main.get_combined_data(chat_path)
        assert combined == [{"role": "user", "content": "hello again"}]

        first_path = Path(main.create_chat_json(tmp_dir))
        second_path = Path(main.create_chat_json(tmp_dir))
        assert first_path != second_path
        assert first_path.exists()
        assert second_path.exists()

    print("BillyGPT smoke check passed")


if __name__ == "__main__":
    main_check()
