"""Cerno Telegram Bot — Structured guided intake flow."""
import os
import logging
import httpx
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

API_URL = os.getenv("API_URL", "http://backend:8000/api/v1")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

DESCRIPTION, SERVICE, CONFIRM = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Cerno SRE Triage Bot.\n\n"
        "I'll guide you through reporting an incident.\n\n"
        "Step 1/3: Describe the incident.\n"
        "What is happening? (e.g., 'Checkout returns 500 error')",
        reply_markup=ReplyKeyboardRemove(),
    )
    return DESCRIPTION


async def description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await update.message.reply_text(
        "Step 2/3: Which service or area is affected?\n"
        "(e.g., 'checkout', 'payments', 'database')"
    )
    return SERVICE


async def service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["service"] = update.message.text
    desc = context.user_data["description"]
    svc = context.user_data["service"]
    await update.message.reply_text(
        f"Step 3/3: Confirm submission\n\n"
        f"Description: {desc}\n"
        f"Service: {svc}\n\n"
        f"Submit this incident?",
        reply_markup=ReplyKeyboardMarkup([["Yes", "No"]], one_time_keyboard=True),
    )
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() != "yes":
        await update.message.reply_text("Cancelled. Use /start to try again.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    desc = context.user_data["description"]
    svc = context.user_data["service"]

    await update.message.reply_text("Submitting incident...", reply_markup=ReplyKeyboardRemove())

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            reg_resp = await client.post(
                f"{API_URL}/auth/register",
                json={"username": f"tg_{update.effective_user.id}", "password": "telegram_bot_user_password_placeholder"},
            )

            login_resp = await client.post(
                f"{API_URL}/auth/login",
                json={"username": f"tg_{update.effective_user.id}", "password": "telegram_bot_user_password_placeholder"},
            )
            if login_resp.status_code != 200:
                await update.message.reply_text("Authentication failed. Please try again later.")
                return ConversationHandler.END

            token = login_resp.json()["access_token"]

            resp = await client.post(
                f"{API_URL}/incidents/",
                json={"title": desc[:200], "description": desc, "service": svc},
                headers={"Authorization": f"Bearer {token}"},
            )

            if resp.status_code in (201, 202):
                incident = resp.json()
                await update.message.reply_text(
                    f"Incident submitted.\n\n"
                    f"ID: {incident['id']}\n"
                    f"State: {incident['state']}\n\n"
                    f"Triage is running. Check the dashboard for results:\n"
                    f"http://localhost:3000/incidents/{incident['id']}"
                )
            else:
                await update.message.reply_text(f"Failed to submit: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.exception("Failed to submit incident")
        await update.message.reply_text(f"Error: {e}")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Bot will not start.")
        import time
        while True:
            time.sleep(3600)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, service)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    logger.info("Telegram bot starting with long-polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
