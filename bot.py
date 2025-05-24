#!/usr/bin/env python3
import time
import threading
import logging
from telegram import Bot, Update
from telegram.error import TelegramError

# ─── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN = "7970422115:AAHP6yr36stM_B3Nc-Y4pPOL2Qw6k8mZJk0"
POLL_INTERVAL = 1  # seconds between get_updates calls

# follow-up delays: 1m, 15m, 2h, 8h, 24h
FOLLOW_UP_INTERVALS = [
    1 * 60,
    15 * 60,
    2 * 3600,
    8 * 3600,
    24 * 3600
]
FOLLOW_UP_MESSAGES = [
    "Just checking in—if you're ready to begin or have any questions, feel free to type here anytime.",
    "Still here if you need help. Whether it's your first deposit, platform walkthrough, or trading tips, we've got you!",
    "Let's not miss the opportunity to grow today. We can help you place your first trade in just a few minutes.",
    "Hello again! Our team is ready whenever you are. We don't want you to miss the ongoing signals and guidance.",
    "This will be our final message for today. We're always here when you're ready to continue—just say hi anytime!"
]
# ────────────────────────────────────────────────────────────────────────────────

bot = Bot(token=BOT_TOKEN)
offset = 0
user_timers = {}  # chat_id → list of threading.Timer

def send_followup(chat_id, message):
    bot.send_message(chat_id=chat_id, text=message)

def cancel_timers(chat_id):
    for t in user_timers.get(chat_id, []):
        t.cancel()
    user_timers.pop(chat_id, None)

def schedule_followups(chat_id):
    cancel_timers(chat_id)
    timers = []
    for delay, msg in zip(FOLLOW_UP_INTERVALS, FOLLOW_UP_MESSAGES):
        t = threading.Timer(delay, send_followup, args=(chat_id, msg))
        t.daemon = True
        t.start()
        timers.append(t)
    user_timers[chat_id] = timers

def handle_update(update: Update):
    global offset
    offset = update.update_id + 1

    # ─── 1) GROUP: New members welcome ─────────────────────────────────────────
    if update.message and update.message.new_chat_members:
        for user in update.message.new_chat_members:
            if user.is_bot:
                continue
            name = user.first_name or user.username or "there"
            grp_id = update.message.chat.id

            # Greet in the group
            bot.send_message(
                chat_id=grp_id,
                text=f"Welcome, {name}! 🎉"
            )
            # DM greeting + follow-ups
            bot.send_message(user.id,
                f"Hey, {name}! Welcome to {update.message.chat.title}!")
            bot.send_message(user.id,
                "I’m Mr. Bull—tell me where you’re from and your trading experience.")
            schedule_followups(user.id)
        return

    # ─── 2) CHANNEL: Approved join-request ─────────────────────────────────────
    if update.chat_member:
        cm = update.chat_member
        if (
            cm.chat.type == 'channel'
            and cm.old_chat_member.status in ['left', 'kicked']
            and cm.new_chat_member.status == 'member'
        ):
            user = cm.new_chat_member.user
            uid = user.id
            bot.send_message(uid,
                f"Hey, {user.first_name}! Welcome to {cm.chat.title}!")
            bot.send_message(uid,
                "I’m Mr. Bull—tell me where you’re from and your trading experience.")
            schedule_followups(uid)
        return

    # ─── 3) DIRECT MESSAGES: /start & replies ───────────────────────────────────
    msg = update.message
    if not msg or not msg.text:
        return

    chat_id = msg.chat.id
    text = msg.text.strip()
    user = msg.from_user
    name = user.first_name or user.username or "Trader"

    if text == "/start":
        # Initial greeting on /start
        bot.send_message(chat_id,
            f"Hey, {name}! Let's get to know each other first!")
        bot.send_message(chat_id,
            "I’m Mr. Bull—please tell me where you’re from and your trading experience.")
        schedule_followups(chat_id)

    else:
        # On any user reply: cancel old timers, log, and let you reply manually
        cancel_timers(chat_id)
        print(f"\n--- New message from {name} ({chat_id}) ---")
        print(text)

        reply = input("Type your reply (and press Enter): ").strip()
        if reply:
            bot.send_message(chat_id, reply)
            schedule_followups(chat_id)

def main():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    global offset
    print("Bot is running. Waiting for messages...")

    while True:
        try:
            updates = bot.get_updates(
                offset=offset,
                timeout=30,
                allowed_updates=['message', 'chat_member']
            )
            for upd in updates:
                handle_update(upd)

        except TelegramError as e:
            logging.error(f"TelegramError: {e}")
            time.sleep(5)

        except Exception:
            logging.exception("Unexpected error")
            time.sleep(5)

        finally:
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
