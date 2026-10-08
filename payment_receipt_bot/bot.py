"""
Payment Receipt Telegram Bot
Main entry point
"""
import asyncio
import logging
import os
import random
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import List, Dict, Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from payment_receipt_bot.config import BotConfig, TEMPLATES_DIR
from payment_receipt_bot.engines.snapshot_engine import SnapshotEngine
from payment_receipt_bot.engines.data_generator import IndianDataGenerator
from payment_receipt_bot.utils.image_processor import compress_image
from payment_receipt_bot.modifiers import MODIFIERS

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class _HealthHandler(BaseHTTPRequestHandler):
    """Minimal Render health endpoint for Web Service deployments."""

    def do_GET(self):
        if self.path not in ("/", "/health"):
            self.send_response(404)
            self.end_headers()
            return
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def _start_health_server() -> ThreadingHTTPServer:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logger.info("Health server listening on port %s", port)
    return server


_MODIFIER_KEYS = ("phonepe", "gpay", "google", "slice", "supermoney",
                  "super.money", "payzapp", "navi")


def _pick_modifier(html_file: Path):
    stem = html_file.stem.lower()
    for key in _MODIFIER_KEYS:
        if key in stem:
            modifier = MODIFIERS.get(key)
            if modifier:
                return modifier
    return MODIFIERS.get("gpay")


def _snapshot_caption(html_file: Path, data: Dict[str, Any]) -> str:
    """Caption matches app label and amount formatting on the receipt image."""
    amount = int(data["amount"])
    stem = html_file.stem.lower()
    path = str(html_file).lower().replace("\\", "/")
    if "slice" in stem or "/slice/" in path:
        return f"slice · ₹{amount:,}"
    if "gpay" in stem or "google" in stem or "/google_pay/" in path:
        return f"Google Pay · ₹{amount:,}.00"
    return f"{data.get('receiver_bank', 'Payment')} · ₹{amount:,}"


def _esc_html(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _menu_footer() -> list[list[InlineKeyboardButton]]:
    return [[InlineKeyboardButton("◀️ Command center", callback_data="cmd_menu")]]


def _main_menu_text() -> str:
    return (
        "<b>🧾 Payment Receipt Bot</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📱 Realistic UPI receipt snapshots\n"
        "<i>GPay · Slice · batch send</i>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Choose an option below 👇"
    )


def _main_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚀 Start snapshots", callback_data="start_sending")],
            [
                InlineKeyboardButton("⏹ Stop", callback_data="cmd_stop"),
                InlineKeyboardButton("📊 Status", callback_data="cmd_status"),
            ],
            [
                InlineKeyboardButton("⚙️ Configuration", callback_data="cmd_config"),
                InlineKeyboardButton("📖 Commands", callback_data="cmd_help"),
            ],
        ]
    )


def _help_text() -> str:
    return (
        "<b>📖 Commands</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<code>/start</code> — Open command center\n"
        "<code>/config</code> — Settings &amp; amounts\n"
        "<code>/status</code> — Bot status\n"
        "<code>/stop</code> — Stop sending\n"
        "<code>/startsendingsnapshot</code>\n"
        "    Start batch (slash shortcut)\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Tip: use buttons on /start for faster control.</i>"
    )


def _help_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(_menu_footer())


class PaymentReceiptBot:
    """Main bot class."""

    def __init__(self):
        self.config = BotConfig()
        self.snapshot_engine = SnapshotEngine()
        self.data_generator = IndianDataGenerator(
            realism_level=self.config.get("data_realism_level", 3)
        )
        self.is_running = False
        self.send_task: asyncio.Task | None = None

        token = self.config.get("telegram_token")
        if not token:
            raise RuntimeError(
                "telegram_token is empty. Set it in bot_config.json before running the bot."
            )

        self.application = Application.builder().token(token).build()
        self.setup_handlers()

    def setup_handlers(self) -> None:
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("stop", self.stop))
        self.application.add_handler(
            CommandHandler(
                ["start_sending_snapshot", "startsendingsnapshot"],
                self.start_sending_snapshot,
            )
        )
        self.application.add_handler(CommandHandler("status", self.status))
        self.application.add_handler(CommandHandler("config", self.show_config))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_input)
        )

    def _config_summary_text(self) -> str:
        receiver_mode = self.config.get("receiver_mode", "random")
        receiver_upi_mode = self.config.get("receiver_upi_mode", "random")
        receiver_line = receiver_mode
        if receiver_mode == "custom" and self.config.get("custom_receiver_name"):
            receiver_line = f"custom ({self.config.get('custom_receiver_name')})"
        receiver_upi_line = receiver_upi_mode
        if receiver_upi_mode == "custom" and self.config.get("custom_receiver_upi"):
            receiver_upi_line = f"custom ({self.config.get('custom_receiver_upi')})"

        custom_amount = self.config.get("custom_amount")
        if custom_amount:
            amount_line = f"fixed ₹{int(custom_amount):,}"
        else:
            lo = int(self.config.get("amount_min", 1000))
            hi = int(self.config.get("amount_max", 50000))
            rounding = self.config.get("amount_rounding", "thousands")
            amount_line = f"random ₹{lo:,} – ₹{hi:,} ({rounding})"

        return (
            "<b>⚙️ Configuration</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>👤 Receiver</b>\n"
            f"• Name — <code>{_esc_html(receiver_line)}</code>\n"
            f"• UPI — <code>{_esc_html(receiver_upi_line)}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>💰 Amount</b>\n"
            f"• <code>{_esc_html(amount_line)}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>📋 Other</b>\n"
            f"• Payer — <code>{_esc_html(self.config.get('payer_mode', 'random'))}</code>\n"
            f"• UTR — <code>{_esc_html(self.config.get('utr_mode', 'random'))}</code>\n"
            f"• Time — <code>{_esc_html(self.config.get('datetime_mode', 'random'))}</code>\n"
            f"• Realism — <code>{self.config.get('data_realism_level', 3)}</code>\n"
            f"• Delay — <code>{self.config.get('delay_between_receipts', 4)}s</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Edit with the buttons below</i>"
        )

    def _config_markup(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✏️ Receiver name", callback_data="edit_receiver"),
                    InlineKeyboardButton("🎲 Random", callback_data="random_receiver"),
                ],
                [
                    InlineKeyboardButton("✏️ Receiver UPI", callback_data="edit_receiver_upi"),
                    InlineKeyboardButton("🎲 Random", callback_data="random_receiver_upi"),
                ],
                [InlineKeyboardButton("💵 Custom amount range", callback_data="set_amount")],
                [
                    InlineKeyboardButton("🔢 Fixed amount", callback_data="edit_amount_fixed"),
                    InlineKeyboardButton("🎲 Random amount", callback_data="random_amount"),
                ],
                [
                    InlineKeyboardButton("₹1k–10k", callback_data="amount_preset_1000_10000"),
                    InlineKeyboardButton("₹5k–50k", callback_data="amount_preset_5000_50000"),
                ],
                [
                    InlineKeyboardButton("₹10k–1L", callback_data="amount_preset_10000_100000"),
                    InlineKeyboardButton("₹25k–2L", callback_data="amount_preset_25000_200000"),
                ],
                *_menu_footer(),
            ]
        )

    async def _reply_config(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        await context.bot.send_message(
            chat_id=chat_id,
            text=self._config_summary_text(),
            parse_mode="HTML",
            reply_markup=self._config_markup(),
        )

    async def _reply_menu(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        await context.bot.send_message(
            chat_id=chat_id,
            text=_main_menu_text(),
            parse_mode="HTML",
            reply_markup=_main_menu_markup(),
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._reply_menu(update.message.chat_id, context)

    async def start_sending_snapshot(self, update: Update,
                                     context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_sending_snapshot - start sending immediately"""
        await self._begin_sending(update.message.chat_id, context)

    async def handle_callback(self, update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data or ""
        user_data = context.user_data

        if data == "edit_receiver":
            user_data["setting"] = "receiver"
            await query.message.reply_text(
                "Enter receiver details:\n"
                "Line 1: name\n"
                "Line 2: UPI ID (optional)\n\n"
                "Example:\n"
                "Adhyayan Thakur\n"
                "9891320029@mbk"
            )
        elif data == "random_receiver":
            self.config.update_batch(
                receiver_mode="random",
                receiver_upi_mode="random",
            )
            await query.message.reply_text("Receiver name and UPI set to random")
        elif data == "edit_receiver_upi":
            user_data["setting"] = "receiver_upi"
            await query.message.reply_text("Enter receiver UPI ID:")
        elif data == "random_receiver_upi":
            self.config.set("receiver_upi_mode", "random")
            await query.message.reply_text("Receiver UPI set to random")
        elif data == "edit_payer":
            user_data["setting"] = "payer"
            await query.message.reply_text("Enter payer name:")
        elif data == "random_payer":
            self.config.set("payer_mode", "random")
            await query.message.reply_text("Payer set to random")
        elif data == "set_amount":
            user_data["setting"] = "amount"
            await query.message.reply_text(
                "💰 Enter random amount *range* (min max):\n"
                "Example: `1000 50000`",
                parse_mode="Markdown",
            )
        elif data == "edit_amount_fixed":
            user_data["setting"] = "amount_fixed"
            await query.message.reply_text(
                "🔢 Enter a *fixed* amount for every receipt:\n"
                "Example: `25000`",
                parse_mode="Markdown",
            )
        elif data == "random_amount":
            self.config.update_batch(custom_amount=None)
            await query.message.reply_text(
                "🎲 Amount set to random (uses your min–max range)."
            )
        elif data.startswith("amount_preset_"):
            parts = data.removeprefix("amount_preset_").split("_")
            if len(parts) == 2:
                lo, hi = int(parts[0]), int(parts[1])
                self.config.update_batch(
                    amount_min=lo,
                    amount_max=hi,
                    custom_amount=None,
                )
                await query.message.reply_text(
                    f"💰 Random amount range: ₹{lo:,} – ₹{hi:,}"
                )
        elif data == "cmd_menu":
            await self._reply_menu(query.message.chat_id, context)
        elif data == "cmd_help":
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=_help_text(),
                parse_mode="HTML",
                reply_markup=_help_markup(),
            )
        elif data == "cmd_config":
            await self._reply_config(query.message.chat_id, context)
        elif data == "cmd_status":
            await self._reply_status(query.message.chat_id, context)
        elif data == "cmd_stop":
            self.is_running = False
            if self.send_task and not self.send_task.done():
                self.send_task.cancel()
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="⏹ <b>Stopped</b>\n<i>Sending has been halted.</i>",
                parse_mode="HTML",
                reply_markup=_main_menu_markup(),
            )
        elif data == "edit_utr":
            user_data["setting"] = "utr"
            await query.message.reply_text("Enter custom 12-digit UTR:")
        elif data == "set_datetime":
            user_data["setting"] = "datetime"
            await query.message.reply_text(
                "Enter date/time (YYYY-MM-DD HH:MM):\nExample: 2026-01-15 14:30"
            )
        elif data == "quick_random":
            self.config.update_batch(
                receiver_mode="random",
                receiver_upi_mode="random",
                payer_mode="random",
                utr_mode="random",
                datetime_mode="random",
            )
            await query.message.reply_text("All fields set to random. Starting...")
            await self._begin_sending(query.message.chat_id, context)
        elif data == "start_sending":
            await self._begin_sending(query.message.chat_id, context)
        elif data == "cancel_config":
            await query.message.reply_text("Cancelled")

    async def handle_text_input(self, update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        setting = context.user_data.get("setting")

        if setting == "receiver":
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if len(lines) >= 2:
                self.config.update_batch(
                    custom_receiver_name=lines[0],
                    receiver_mode="custom",
                    custom_receiver_upi=lines[1],
                    receiver_upi_mode="custom",
                )
                await update.message.reply_text(
                    f"Receiver set to:\n{lines[0]}\nUPI: {lines[1]}"
                )
            else:
                self.config.update_batch(
                    custom_receiver_name=lines[0] if lines else text,
                    receiver_mode="custom",
                )
                await update.message.reply_text(
                    f"Receiver name set to: {lines[0] if lines else text}"
                )
            context.user_data["setting"] = None
        elif setting == "receiver_upi":
            self.config.update_batch(
                custom_receiver_upi=text,
                receiver_upi_mode="custom",
            )
            await update.message.reply_text(f"Receiver UPI set to: {text}")
            context.user_data["setting"] = None
        elif setting == "payer":
            self.config.update_batch(custom_payer_name=text, payer_mode="custom")
            await update.message.reply_text(f"Payer set to: {text}")
            context.user_data["setting"] = None
        elif setting == "amount":
            try:
                lo, hi = map(int, text.replace(",", "").split())
                if lo <= 0 or hi <= 0 or lo > hi:
                    raise ValueError("invalid range")
                self.config.update_batch(
                    amount_min=lo,
                    amount_max=hi,
                    custom_amount=None,
                )
                await update.message.reply_text(
                    f"💰 Random amount range: ₹{lo:,} – ₹{hi:,}"
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid format. Use: min max (e.g. 1000 50000)"
                )
            context.user_data["setting"] = None
        elif setting == "amount_fixed":
            try:
                amount = int(text.replace(",", "").strip())
                if amount <= 0:
                    raise ValueError()
                self.config.set("custom_amount", amount)
                await update.message.reply_text(f"🔢 Fixed amount: ₹{amount:,}")
            except ValueError:
                await update.message.reply_text(
                    "❌ Enter a valid amount (e.g. 25000)"
                )
            context.user_data["setting"] = None
        elif setting == "utr":
            digits = "".join(ch for ch in text if ch.isdigit())
            if len(digits) != 12:
                await update.message.reply_text("UTR must be exactly 12 digits")
            else:
                self.config.update_batch(custom_utr=digits, utr_mode="custom")
                await update.message.reply_text(f"UTR set to: {digits}")
            context.user_data["setting"] = None
        elif setting == "datetime":
            from datetime import datetime
            try:
                dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
                self.config.update_batch(
                    custom_datetime=dt.isoformat(), datetime_mode="custom"
                )
                await update.message.reply_text(
                    f"Date/time set: {dt.strftime('%d %b %Y, %I:%M %p')}"
                )
            except ValueError:
                await update.message.reply_text(
                    "Invalid format. Use: YYYY-MM-DD HH:MM"
                )
            context.user_data["setting"] = None

    async def _begin_sending(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        if self.is_running:
            await context.bot.send_message(chat_id=chat_id, text="Already running. /stop first.")
            return
        self.is_running = True
        mode = self.config.get("sending_mode", "batch")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Starting in {mode} mode. Delay: {self.config.get('delay_between_receipts', 4)}s",
        )
        if mode == "continuous":
            self.send_task = asyncio.create_task(self._continuous_loop(chat_id, context))
        else:
            await self._send_batch(chat_id, context)

    async def _send_batch(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        html_files = list(TEMPLATES_DIR.rglob("*.html"))
        if not html_files:
            await context.bot.send_message(chat_id=chat_id, text="No HTML templates found")
            self.is_running = False
            return
        random.shuffle(html_files)
        for html_file in html_files:
            if not self.is_running:
                break
            try:
                await self._send_single_receipt(html_file, chat_id, context)
            except Exception as e:
                logger.exception("send_single_receipt failed for %s", html_file)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Could not send {html_file.name}: {e}",
                )
        self.is_running = False
        await context.bot.send_message(chat_id=chat_id, text="Batch sending completed")

    async def _continuous_loop(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        html_files = list(TEMPLATES_DIR.rglob("*.html"))
        if not html_files:
            return
        while self.is_running:
            order = html_files[:]
            random.shuffle(order)
            for html_file in order:
                if not self.is_running:
                    return
                try:
                    await self._send_single_receipt(html_file, chat_id, context)
                except Exception as e:
                    logger.exception("send_single_receipt failed for %s", html_file)
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"Could not send {html_file.name}: {e}",
                    )
            if self.is_running:
                await asyncio.sleep(self.config.get("delay_between_receipts", 4))

    async def _send_single_receipt(self, html_file: Path, chat_id: int,
                                   context: ContextTypes.DEFAULT_TYPE):
        modifier_class = _pick_modifier(html_file)
        if not modifier_class:
            await context.bot.send_message(
                chat_id=chat_id, text=f"No modifier for {html_file.name}"
            )
            return

        modifier = modifier_class(html_file)
        data_style = getattr(modifier_class, "data_style", "gpay")
        data = self.data_generator.generate_complete_transaction(
            self.config.config, app=data_style
        )
        rendered_html = modifier.modify(data)

        temp_html = modifier.html_template.parent / f"_temp_{html_file.stem}.html"
        screenshot = self.snapshot_engine.output_dir / f"{html_file.stem}.png"
        compressed = None
        try:
            temp_html.write_text(rendered_html, encoding="utf-8")
            screenshot = await self.snapshot_engine.capture(temp_html)

            compressed = compress_image(screenshot)
            with open(compressed, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=_snapshot_caption(html_file, data),
                )
        finally:
            temp_html.unlink(missing_ok=True)
            if screenshot and screenshot.exists():
                screenshot.unlink(missing_ok=True)
            if compressed and compressed.exists():
                compressed.unlink(missing_ok=True)
        logger.info("Sent: %s", html_file.name)

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.is_running = False
        if self.send_task and not self.send_task.done():
            self.send_task.cancel()
        await update.message.reply_text(
            "⏹ <b>Stopped</b>\n<i>Sending has been halted.</i>",
            parse_mode="HTML",
            reply_markup=_main_menu_markup(),
        )

    async def _reply_status(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        if self.is_running:
            state_line = "🟢 <b>Active</b> — sending receipts"
        else:
            state_line = "🔴 <b>Idle</b> — ready to start"
        mode = _esc_html(self.config.get("sending_mode", "batch"))
        delay = self.config.get("delay_between_receipts", 4)
        templates = len(list(TEMPLATES_DIR.rglob("*.html")))
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "<b>📊 Bot status</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"{state_line}\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 Mode — <code>{mode}</code>\n"
                f"⏱ Delay — <code>{delay}s</code>\n"
                f"📄 Templates — <code>{templates}</code>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "<i>Start a new batch from the command center.</i>"
            ),
            parse_mode="HTML",
            reply_markup=_main_menu_markup(),
        )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._reply_status(update.message.chat_id, context)

    async def show_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._reply_config(update.message.chat_id, context)

    def run(self) -> None:
        logger.info("Starting bot...")
        _start_health_server()
        try:
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        finally:
            asyncio.run(self.snapshot_engine.close())


def main() -> None:
    PaymentReceiptBot().run()


if __name__ == "__main__":
    main()
