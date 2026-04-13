#!/usr/bin/env python3
"""
Extract poll text from a Telegram Desktop export (result.json) and write
one line per text fragment to data/training_data.txt (newline-delimited).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Iterable


def flatten_text(value: Any) -> str:
    """Turn Telegram export `text` (str or list of str / entities) into a plain string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
        return "".join(parts)
    return str(value)


def iter_poll_texts(message: dict[str, Any]) -> Iterable[str]:
    """Yield non-empty strings from a message's poll, if present."""
    poll = message.get("poll")
    if not isinstance(poll, dict):
        return

    q = flatten_text(poll.get("question"))
    if q.strip():
        yield q.strip()

    answers = poll.get("answers")
    if not isinstance(answers, list):
        return

    for ans in answers:
        if not isinstance(ans, dict):
            continue
        opt = ans.get("text")
        if opt is None:
            opt = ans.get("option")
        label = flatten_text(opt) if opt is not None else ""
        if label.strip():
            yield label.strip()


def extract_from_export(data: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    messages = data.get("messages")
    if not isinstance(messages, list):
        return lines

    for msg in messages:
        if not isinstance(msg, dict):
            continue
        if msg.get("type") != "message":
            continue
        for piece in iter_poll_texts(msg):
            lines.append(piece)
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Build training_data.txt from Telegram export JSON.")
    parser.add_argument(
        "export_path",
        nargs="?",
        default="result.json",
        help="Path to result.json from a Telegram export (default: result.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=os.path.join("data", "training_data.txt"),
        help="Output file path (default: data/training_data.txt)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.export_path):
        print(f"Error: file not found: {args.export_path}", file=sys.stderr)
        return 1

    try:
        with open(args.export_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"Error reading JSON: {e}", file=sys.stderr)
        return 1

    if not isinstance(data, dict):
        print("Error: export root must be a JSON object.", file=sys.stderr)
        return 1

    lines = extract_from_export(data)
    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line.replace("\r", " ").replace("\n", " ").strip() + "\n")

    print(f"Wrote {len(lines)} lines to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
