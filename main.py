#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram bot: trimite zilnic la ora 07:00 un sticker aleator dintr-un sticker pack ales.

Comenzi:
- /start – pornește botul, setează implicit 07:00 (Europe/Chisinau)
- /pack <short_name> – setează sticker pack-ul (partea de după addstickers/ din link)
- /showpack – afișează pack-ul curent și câte stickere sunt în cache
- /test – trimite imediat un sticker aleator din pack
- /when HH:MM – schimbă ora zilnică (format 24h)
- /tz <IANA TZ> – schimbă fusul orar (ex: Europe/Chisinau, Europe/Bucharest)

Note:
- Necesită python-telegram-bot v21 cu extra-ul [job-queue].
- Pentru Railway, setează variabile: BOT_TOKEN, TZ, SEND_HOUR, SEND_MINUTE, PERSIST_PATH (/data/bot_state.pkl)
"""

import logging
import os
import random
from datetime import time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    PicklePersistence,
)

# -------- CONFIG --------
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")
DEFAULT_TZ = os.getenv("TZ", "Europe/Chisinau")
DEFAULT_HOUR = int(os.getenv("SEND_HOUR", "7"))
DEFAULT_MINUTE = int(os.getenv("SEND_MINUTE", "0"))

# Persistență: pe Railway atașează un Volume la /data și folosește PERSIST_PATH=/data/bot_state.pkl
PERSIST_PATH = os.getenv("PERSIST_PATH", "/data/bot_state.pkl")
if not os.path.isdir(os.path.dirname(PERSIST_PATH)):
    PERSIST_PATH = "bot_state.pkl"
# ------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def job_name(chat_id: int) -> str:
    return f"daily_{chat_id}"


async def send_random_from_pack(context: ContextTypes.DEFAULT_TYPE, chat_id: int | None = None) -> None:
    """
    Trimite un sticker random din pack-ul setat.
    - Dacă e apelată din JobQueue, ia chat_id din context.job.chat_id
    - Dacă e apelată din /test, primește chat_id explicit.
    """
    if chat_id is None:
        chat_id = context.job.chat_id if getattr(context, "job", None) else None
    if chat_id is None:
        return

    cd = context.chat_data
    pack_name = cd.get("pack_name")
    cached = cd.get("pack_cache")

    if not pack_name:
        await context.bot.send_message(chat_id, "Nu ai setat încă un sticker pack. Folosește /pack <short_name>.")
        return

    if not cached:
        try:
            sticker_set = await context.bot.get_sticker_set(pack_name)
            file_ids = [st.file_id for st in sticker_set.stickers]
            if not file_ids:
                await context.bot.send_message(chat_id, f"Pack-ul {pack_name} nu are stickere. Încearcă altul.")
                return
            cd["pack_cache"] = file_ids
            cached = file_ids
        except Exception as e:
            logger.exception("Eroare la get_sticker_set pentru %s: %s", pack_name, e)
            await context.bot.send_message(chat_id, f"N-am putut încărca sticker pack-ul {pack_name}. E corect short_name-ul?")
            return

    try:
        file_id = random.choice(cached)
        await context.bot.send_sticker(chat_id, file_id)
    except Exception as e:
        logger.exception("Eroare la trimiterea sticker-ului: %s", e)
        await context.bot.send_message(chat_id, f"Eroare la trimitere: {e}")


def schedule_daily_job(application, chat_id: int, tz: str, hh: int, mm: int):
    """(Re)creează jobul zilnic pentru chat."""
    if application.job_queue is None:
        raise RuntimeError(
            'JobQueue nu este disponibil. Instalează extra-ul: pip install "python-telegram-bot[job-queue]==21.4"'
        )
    # ștergem joburile vechi cu același nume
    for j in application.job_queue.get_jobs_by_name(job_name(chat_id)):
        j.schedule_removal()

    application.job_queue.run_daily(
        send_random_from_pack,
        time=time(hour=hh, minute=mm, tzinfo=ZoneInfo(tz)),
        name=job_name(chat_id),
        chat_id=chat_id,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cd = context.chat_data
    cd.setdefault("tz", DEFAULT_TZ)
    cd.setdefault("time", {"hour": DEFAULT_HOUR, "minute": DEFAULT_MINUTE})
    schedule_daily_job(context.application, update.effective_chat.id, cd["tz"], cd["time"]["hour"], cd["time"]["minute"])

    msg = (
        "Salut! Voi trimite zilnic la {hh:02d}:{mm:02d} ({tz}) un sticker aleator din sticker pack-ul tău.\n\n"
        "Comenzi:\n"
        "• /pack <short_name>\n"
        "• /showpack\n"
        "• /test\n"
        "• /when HH:MM\n"
        "• /tz Europe/Chisinau\n"
    ).format(hh=cd['time']['hour'], mm=cd['time']['minute'], tz=cd['tz'])
    await update.message.reply_text(msg)


async def set_pack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Folosește: /pack <short_name> (ex: partea după addstickers/ din link)")
        return
    pack_name = context.args[0]
    try:
        sticker_set = await context.bot.get_sticker_set(pack_name)
        file_ids = [st.file_id for st in sticker_set.stickers]
        if not file_ids:
            await update.message.reply_text(f"Pack-ul {pack_name} pare gol. Încearcă altul.")
            return
        context.chat_data["pack_name"] = pack_name
        context.chat_data["pack_cache"] = file_ids
        await update.message.reply_text(f"Gata! Am setat pack-ul {pack_name} cu {len(file_ids)} stickere.")
    except Exception as e:
        logger.exception("set_pack failed pentru %s: %s", pack_name, e)
        await update.message.reply_text("N-am putut citi pack-ul. Verifică short_name-ul sau încearcă altul.")


async def show_pack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pack = context.chat_data.get("pack_name")
    cache = context.chat_data.get("pack_cache") or []
    if not pack:
        await update.message.reply_text("Nu ai setat încă un sticker pack. Folosește /pack <short_name>.")
        return
    await update.message.reply_text(f"Pack curent: {pack}\nStickere în cache: {len(cache)}")


async def test_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_random_from_pack(context, chat_id=update.effective_chat.id)


async def when(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or len(context.args) != 1 or ":" not in context.args[0]:
        await update.message.reply_text("Folosește: /when HH:MM (format 24h). Exemplu: /when 07:00")
        return
    try:
        hh_str, mm_str = context.args[0].split(":", 1)
        hh = int(hh_str)
        mm = int(mm_str)
        assert 0 <= hh <= 23 and 0 <= mm <= 59
    except Exception:
        await update.message.reply_text("Ora invalidă. Încearcă de ex: /when 07:00 sau /when 8:30")
        return
    cd = context.chat_data
    tz = cd.get("tz", DEFAULT_TZ)
    cd["time"] = {"hour": hh, "minute": mm}
    schedule_daily_job(context.application, update.effective_chat.id, tz, hh, mm)
    await update.message.reply_text(f"Perfect. Trimit zilnic la {hh:02d}:{mm:02d} ({tz}).")


async def settz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Folosește: /tz <IANA TZ>, ex: /tz Europe/Chisinau")
        return
    tz = context.args[0]
    try:
        ZoneInfo(tz)
    except Exception:
        await update.message.reply_text("Timezone invalid. Exemplu valid: Europe/Chisinau")
        return
    cd = context.chat_data
    cd["tz"] = tz
    hh = cd.get("time", {}).get("hour", DEFAULT_HOUR)
    mm = cd.get("time", {}).get("minute", DEFAULT_MINUTE)
    schedule_daily_job(context.application, update.effective_chat.id, tz, hh, mm)
    await update.message.reply_text(f"Fus orar setat pe {tz}.")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception: %s", context.error)


def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "PUT_YOUR_TOKEN_HERE":
        raise SystemExit("Setează BOT_TOKEN în variabilele de mediu sau înlocuiește în cod.")

    persistence = PicklePersistence(filepath=PERSIST_PATH)
    app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()

    if app.job_queue is None:
        raise SystemExit(
            'JobQueue nu este disponibil. Instalează extra-ul: pip install "python-telegram-bot[job-queue]==21.4"'
        )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pack", set_pack))
    app.add_handler(CommandHandler("showpack", show_pack))
    app.add_handler(CommandHandler("test", test_now))
    app.add_handler(CommandHandler("when", when))
    app.add_handler(CommandHandler("tz", settz))
    app.add_error_handler(on_error)

    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
