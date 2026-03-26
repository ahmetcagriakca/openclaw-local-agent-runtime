"""Telegram Bot — re-export from current location."""
# Actual code in agent/telegram_bot.py
# This shim enables `from app.services.telegram import bot`
try:
    import telegram_bot as bot
except ImportError:
    bot = None
