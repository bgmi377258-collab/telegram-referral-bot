import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ContextTypes,
)

# ---------------- CONFIG ---------------- #
BOT_TOKEN = "8062189638:AAEcn8Es8bscOklkRMtV3E9DwFmdLiEfL0Y"
REFERRAL_REWARD = 5
MIN_WITHDRAW = 50
DAILY_BONUS = 2

# ---------------- LOGGING ---------------- #
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# ---------------- TEMP DATABASE ---------------- #
users = {}

# Structure:
# users[user_id] = {
#     "balance": 0,
#     "referrals": 0,
#     "referred_by": None,
#     "daily_claimed": False
# }

# ---------------- HELPER FUNCTIONS ---------------- #
def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "balance": 0,
            "referrals": 0,
            "referred_by": None,
            "daily_claimed": False,
        }
    return users[user_id]


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("👥 Referral Link", callback_data="referral"),
        ],
        [
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="bonus"),
            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
        ],
        [
            InlineKeyboardButton("📖 How To Earn", callback_data="earn"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# ---------------- START COMMAND ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)

    # Referral System
    if context.args:
        try:
            referrer_id = int(context.args[0])

            if (
                referrer_id != user.id
                and user_data["referred_by"] is None
                and referrer_id in users
            ):
                user_data["referred_by"] = referrer_id

                users[referrer_id]["balance"] += REFERRAL_REWARD
                users[referrer_id]["referrals"] += 1

                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=(
                            f"🎉 New referral joined!\n"
                            f"You earned ₹{REFERRAL_REWARD}"
                        ),
                    )
                except Exception as e:
                    logger.error(e)

        except Exception as e:
            logger.error(e)

    text = (
        f"👋 Welcome {user.first_name}!\n\n"
        f"💸 Earn money by inviting friends.\n"
        f"✅ You get ₹{REFERRAL_REWARD} per successful referral.\n\n"
        f"Use the buttons below."
    )

    await update.message.reply_text(
        text,
        reply_markup=main_menu(),
    )


# ---------------- BUTTON HANDLER ---------------- #
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = get_user(user_id)

    # BALANCE
    if query.data == "balance":
        text = (
            f"💰 Your Balance: ₹{user_data['balance']}\n"
            f"👥 Referrals: {user_data['referrals']}"
        )
        await query.message.reply_text(text)

    # REFERRAL LINK
    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username

        referral_link = (
            f"https://t.me/{bot_username}?start={user_id}"
        )

        text = (
            f"👥 Your Referral Link:\n\n"
            f"{referral_link}\n\n"
            f"💸 Earn ₹{REFERRAL_REWARD} for every user who joins."
        )

        await query.message.reply_text(text)

    # DAILY BONUS
    elif query.data == "bonus":
        if not user_data["daily_claimed"]:
            user_data["balance"] += DAILY_BONUS
            user_data["daily_claimed"] = True

            await query.message.reply_text(
                f"🎁 Daily bonus claimed!\n"
                f"You received ₹{DAILY_BONUS}"
            )
        else:
            await query.message.reply_text(
                "❌ You already claimed today's bonus."
            )

    # WITHDRAW
    elif query.data == "withdraw":
        if user_data["balance"] >= MIN_WITHDRAW:
            amount = user_data["balance"]
            user_data["balance"] = 0

            await query.message.reply_text(
                f"✅ Withdrawal request submitted.\n"
                f"💸 Amount: ₹{amount}"
            )
        else:
            needed = MIN_WITHDRAW - user_data["balance"]

            await query.message.reply_text(
                f"❌ Minimum withdrawal is ₹{MIN_WITHDRAW}\n"
                f"You need ₹{needed} more."
            )

    # HOW TO EARN
    elif query.data == "earn":
        text = (
            "📖 HOW TO EARN\n\n"
            "1️⃣ Click Referral Link\n"
            "2️⃣ Share it with friends\n"
            "3️⃣ When they join, you earn money\n"
            "4️⃣ Claim daily bonus daily\n\n"
            f"💰 Referral Reward: ₹{REFERRAL_REWARD}\n"
            f"🎁 Daily Bonus: ₹{DAILY_BONUS}\n"
            f"💸 Minimum Withdraw: ₹{MIN_WITHDRAW}"
        )

        await query.message.reply_text(text)


# ---------------- NEW MEMBER TRACKING ---------------- #
async def track_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        result = update.chat_member

        if result.new_chat_member.status == "member":
            user = result.new_chat_member.user

            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    f"👋 Welcome {user.first_name}!\n\n"
                    "Click /start to begin earning."
                ),
            )

    except Exception as e:
        logger.error(e)


# ---------------- ERROR HANDLER ---------------- #
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling update:", exc_info=context.error)


# ---------------- MAIN ---------------- #
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))

    # Buttons
    app.add_handler(CallbackQueryHandler(button_handler))

    # Member Tracking
    app.add_handler(
        ChatMemberHandler(
            track_members,
            ChatMemberHandler.CHAT_MEMBER,
        )
    )

    # Errors
    app.add_error_handler(error_handler)

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()