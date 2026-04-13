#!/usr/bin/env python3
"""Telegram bot: Markov-generated surreal polls from exported poll history."""

from __future__ import annotations

import asyncio
import logging
import os
import random
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

import markovify
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

import config


def _setup_logging() -> None:
    """Console + small rotating file under DATA_DIR (persists with Docker volume)."""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    log_path = os.path.join(config.DATA_DIR, "bot.log")
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    fh = RotatingFileHandler(
        log_path,
        maxBytes=512_000,
        backupCount=2,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(sh)
    root.addHandler(fh)


_setup_logging()
log = logging.getLogger("pollbot")

router = Router(name="pollbot")

# Absurd fallbacks when Markov generation fails or collides (no paid APIs).
FALLBACK_QUESTIONS: tuple[str, ...] = (
    "Which moon tastes most like Tuesday?",
    "Who is the official ambassador of forgotten socks?",
    "Pick the weapon of choice for a polite pigeon revolution.",
    "What is the sound of one database clapping?",
    "Which void should we promote to middle management?",
)

FALLBACK_OPTIONS: tuple[str, ...] = (
    "A jar of sideways gravity",
    "The color of silent music",
    "A committee of nervous spoons",
    "Seventeen imaginary meters per thought",
    "The echo of a spreadsheet dreaming",
    "A cloud wearing business casual",
    "Recursive soup (base case: crouton)",
    "A polite but firm topological donut",
    "The warranty on yesterday",
    "An elevator that only visits emotions",
    "A spreadsheet filled with fog",
    "The middle third of a rainbow invoice",
)

markov_model: Optional[markovify.NewlineText] = None
training_error: Optional[str] = None


def _safe_make_sentence(model: markovify.NewlineText, tries: int = 80) -> Optional[str]:
    try:
        out = model.make_sentence(tries=tries)
    except (KeyError, TypeError, ValueError):
        return None
    return out if isinstance(out, str) else None


def _truncate(s: str, max_len: int) -> str:
    s = s.strip()
    if not s:
        return ""
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def _load_training_model() -> tuple[Optional[markovify.NewlineText], Optional[str]]:
    path = config.TRAINING_PATH
    if not os.path.isfile(path):
        return None, (
            f"No training file at `{path}`. Run `parser.py` on your Telegram export "
            "or add poll lines to that file, then restart the bot."
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError as e:
        return None, f"Could not read training file `{path}`: {e}"

    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return None, (
            f"Training file `{path}` is empty. Export poll history with `parser.py` "
            "or add one poll text per line, then restart the bot."
        )

    # NewlineText: one training "sentence" per line (lightweight for small VPS).
    try:
        model = markovify.NewlineText("\n".join(lines), state_size=2)
    except (ValueError, TypeError, KeyError) as e:
        return None, f"Could not build Markov model from `{path}`: {e}"

    return model, None


def _generate_unique_line(
    used: set[str],
    max_len: int,
    tries: int = 120,
) -> str:
    assert markov_model is not None
    for _ in range(tries):
        sent = _safe_make_sentence(markov_model, tries=50)
        if not sent:
            continue
        cand = _truncate(sent, max_len)
        if cand and cand not in used:
            used.add(cand)
            return cand
    fb = random.choice(FALLBACK_OPTIONS)
    fb = _truncate(fb, max_len)
    if fb not in used:
        used.add(fb)
        return fb
    # Extremely unlikely: rotate with suffix
    for i in range(50):
        alt = _truncate(f"{fb} ({i + 1})", max_len)
        if alt not in used:
            used.add(alt)
            return alt
    return _truncate(f"{fb} ?", max_len)


async def on_startup() -> None:
    global markov_model, training_error
    markov_model, training_error = _load_training_model()
    if training_error:
        log.warning("%s", training_error)
    else:
        log.info("Markov model loaded from %s", config.TRAINING_PATH)


@router.message(Command("generate_poll"))
async def cmd_generate_poll(message: Message) -> None:
    if training_error or markov_model is None:
        await message.answer(training_error or "Training data is not available.")
        return

    used: set[str] = set()

    question = _truncate(_safe_make_sentence(markov_model, tries=80) or "", config.MAX_QUESTION_LEN)
    if not question or question in used:
        question = _truncate(random.choice(FALLBACK_QUESTIONS), config.MAX_QUESTION_LEN)
    used.add(question)

    options: list[str] = []
    while len(options) < 10:
        opt = _generate_unique_line(used, config.MAX_OPTION_LEN)
        options.append(opt)

    await message.bot.send_poll(
        chat_id=message.chat.id,
        question=question,
        options=options,
        is_anonymous=True,
        type="regular",
    )


async def main() -> None:
    if not config.TELEGRAM_TOKEN:
        log.error("TELEGRAM_TOKEN is not set. Add it to your environment or .env file.")
        sys.exit(1)

    bot = Bot(token=config.TELEGRAM_TOKEN)
    dp = Dispatcher()
    dp.startup.register(on_startup)
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
