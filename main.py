"""
MusicBrainzBOT - a Telegram bot that searches music metadata via the
MusicBrainz API (artists, releases/albums, and recordings/tracks).

MusicBrainz is a metadata database, not a streaming service, so this
bot returns rich info (artist bios, release dates, track lists, cover
art, links) rather than audio playback. See README.md for details and
for why full audio streaming isn't included.
"""

import logging
import os

import musicbrainzngs
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

# MusicBrainz asks that every client identify itself with a useful user agent
musicbrainzngs.set_useragent(
    "MusicBrainzBOT",
    "1.0",
    contact=os.environ.get("CONTACT_EMAIL", "example@example.com"),
)

RESULTS_PER_PAGE = 5

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def search_recordings(query: str, limit: int = RESULTS_PER_PAGE):
    result = musicbrainzngs.search_recordings(query=query, limit=limit)
    return result.get("recording-list", [])


def search_artists(query: str, limit: int = RESULTS_PER_PAGE):
    result = musicbrainzngs.search_artists(query=query, limit=limit)
    return result.get("artist-list", [])


def search_releases(query: str, limit: int = RESULTS_PER_PAGE):
    result = musicbrainzngs.search_releases(query=query, limit=limit)
    return result.get("release-list", [])


def format_recording(rec: dict) -> str:
    title = rec.get("title", "Unknown title")
    artists = ", ".join(
        c.get("artist", {}).get("name", "")
        for c in rec.get("artist-credit", [])
        if isinstance(c, dict)
    )
    length = rec.get("length")
    length_str = f"{int(length) // 60000}:{(int(length) // 1000) % 60:02d}" if length else "?"
    return f"🎵 *{title}*\n👤 {artists or 'Unknown artist'}\n⏱ {length_str}"


def format_artist(artist: dict) -> str:
    name = artist.get("name", "Unknown")
    area = artist.get("area", {}).get("name", "") if artist.get("area") else ""
    life_span = artist.get("life-span", {})
    begin = life_span.get("begin", "")
    disambiguation = artist.get("disambiguation", "")
    lines = [f"👤 *{name}*"]
    if disambiguation:
        lines.append(f"_{disambiguation}_")
    if area:
        lines.append(f"📍 {area}")
    if begin:
        lines.append(f"📅 Active since {begin}")
    return "\n".join(lines)


def format_release(rel: dict) -> str:
    title = rel.get("title", "Unknown release")
    date = rel.get("date", "Unknown date")
    artists = ", ".join(
        c.get("artist", {}).get("name", "")
        for c in rel.get("artist-credit", [])
        if isinstance(c, dict)
    )
    return f"💿 *{title}*\n👤 {artists or 'Unknown artist'}\n📅 {date}"


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🎧 *Welcome to MusicBrainzBOT!*\n\n"
        "I look up music metadata from the MusicBrainz database.\n\n"
        "Commands:\n"
        "/search <query> - search tracks\n"
        "/artist <name> - search artists\n"
        "/album <name> - search releases/albums\n",
        parse_mode=ParseMode.MARKDOWN,
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Usage: /search <song or artist name>")
        return

    recordings = search_recordings(query)
    if not recordings:
        await update.message.reply_text("No results found.")
        return

    for rec in recordings:
        buttons = [[InlineKeyboardButton("🔗 View on MusicBrainz", url=f"https://musicbrainz.org/recording/{rec['id']}")]]
        await update.message.reply_text(
            format_recording(rec),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )


async def artist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Usage: /artist <artist name>")
        return

    artists = search_artists(query)
    if not artists:
        await update.message.reply_text("No results found.")
        return

    for a in artists:
        buttons = [[InlineKeyboardButton("🔗 View on MusicBrainz", url=f"https://musicbrainz.org/artist/{a['id']}")]]
        await update.message.reply_text(
            format_artist(a),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )


async def album(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Usage: /album <album/release name>")
        return

    releases = search_releases(query)
    if not releases:
        await update.message.reply_text("No results found.")
        return

    for rel in releases:
        buttons = [[InlineKeyboardButton("🔗 View on MusicBrainz", url=f"https://musicbrainz.org/release/{rel['id']}")]]
        await update.message.reply_text(
            format_release(rel),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("artist", artist))
    application.add_handler(CommandHandler("album", album))

    logger.info("Bot starting (polling mode)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
