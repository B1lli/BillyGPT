# coding=utf-8
from __future__ import annotations

"""Chat log persistence helpers."""

import hashlib
import json
import os
from datetime import datetime

from paths import CHATLOG_DIR


def create_chat_json(save_path=CHATLOG_DIR):
    save_path = str(save_path)
    os.makedirs(save_path, exist_ok=True)

    now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
    chat_json_path = os.path.join(save_path, f"chat_{now}.json")
    with open(chat_json_path, 'w') as f:
        json.dump([], f, default=str)
    return chat_json_path


def save_now_chat(chat_json_path: str, role: str, content: str) -> str:
    now = datetime.now().timestamp()
    str_to_hash = str(now) + role + content
    hash_obj = hashlib.blake2b(str_to_hash.encode('utf-8'), digest_size=8)
    hash_val = hash_obj.hexdigest()

    try:
        with open(chat_json_path, 'r') as f:
            chats = json.load(f)
    except FileNotFoundError:
        chats = []

    message = {
        'role': role,
        'content': content,
        'keyword': [],
        'summary': ''
    }
    chats.append({
        'chat_seq': len(chats) + 1,
        'hash': hash_val,
        'created_time': now,
        'altered_time': None,
        'message': message
    })

    with open(chat_json_path, 'w') as f:
        json.dump(chats, f, default=str, indent=4)

    return hash_val


def renew_now_chat(chat_json_path: str, hash_val: str,
                   role: str = None, content: str = None, summary=None) -> None:
    with open(chat_json_path, 'r') as f:
        data = json.load(f)

    for chat_item in data:
        if hash_val == chat_item['hash']:
            if role is not None:
                chat_item['message']['role'] = role
            if content is not None:
                chat_item['message']['content'] = content
            if summary is not None:
                chat_item['message']['summary'] = summary
            chat_item["altered_time"] = datetime.now().timestamp()
            break

    with open(chat_json_path, 'w') as f:
        json.dump(data, f, default=str, indent=4)


def get_one_role_and_content(
        chat_json_path: str, hash_value: str) -> tuple[str, str] | None:
    with open(chat_json_path) as f:
        data = json.load(f)

    for chat_item in data:
        if hash_value == chat_item.get('hash'):
            message = chat_item.get('message', {})
            return message.get("role"), message.get("content")

    return None


def get_combined_data(chat_json_path: str) -> list[dict[str, str]]:
    with open(chat_json_path) as f:
        data = json.load(f)

    result = []
    for chat_item in data:
        message = chat_item['message']
        result.append({
            "role": message["role"],
            "content": message["summary"] or message["content"]
        })
    return result
