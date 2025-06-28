import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, filters,
                          ConversationHandler, ContextTypes)
import asyncio

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# States for ConversationHandler
GENDER, AGE, PREFERENCES = range(3)

# Store users and chat sessions in memory
users = {}
waiting_users = []
active_chats = {}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Global Chat & Date Bot! Use /register to get started.")

# Register command starts the process
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("What's your gender? (Male/Female/Other)")
    return GENDER

async def set_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("How old are you?")
    return AGE

async def set_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['age'] = update.message.text
    await update.message.reply_text("Who do you want to chat with? (Male/Female/Anyone)")
    return PREFERENCES

async def set_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['preferences'] = update.message.text
    user_id = update.message.from_user.id
    users[user_id] = context.user_data.copy()
    await update.message.reply_text("You're registered! Use /findmatch to find someone to chat with.")
    return ConversationHandler.END

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = users.get(user_id)
    if user:
        profile_text = f"Gender: {user['gender']}\nAge: {user['age']}\nPreferences: {user['preferences']}"
    else:
        profile_text = "You are not registered yet. Use /register to begin."
    await update.message.reply_text(profile_text)

async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in active_chats:
        await update.message.reply_text("You are already in a chat. Use /next to switch or /stop to end.")
        return

    user = users.get(user_id)
    if not user:
        await update.message.reply_text("Please register first using /register.")
        return

    for other_id in waiting_users:
        other = users.get(other_id)
        if other and other_id != user_id:
            # Match based on preferences
            if user['preferences'] in ["Anyone", other['gender']] and \
               other['preferences'] in ["Anyone", user['gender']]:
                active_chats[user_id] = other_id
                active_chats[other_id] = user_id
                waiting_users.remove(other_id)
                await context.bot.send_message(other_id, "You have been matched! Say hi!")
                await update.message.reply_text("You have been matched! Say hi!")
                return

    waiting_users.append(user_id)
    await update.message.reply_text("Waiting for someone to match with you... Use /stop to cancel.")

async def forward_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.message.from_user.id
    receiver_id = active_chats.get(sender_id)
    if receiver_id:
        await context.bot.send_message(receiver_id, update.message.text)

async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop_chat(update, context)
    await find_match(update, context)

async def stop_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    partner_id = active_chats.pop(user_id, None)
    if partner_id:
        active_chats.pop(partner_id, None)
        await context.bot.send_message(partner_id, "Your partner has left the chat.")
    await update.message.reply_text("You have left the chat.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Setup the bot
def main():
    app = ApplicationBuilder().token("7562728976:AAEEb8npaWXOKSnGlKfgeZC5l8unA-rX9W0").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('register', register)],
        states={
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_gender)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_age)],
            PREFERENCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_preferences)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('profile', profile))
    app.add_handler(CommandHandler('findmatch', find_match))
    app.add_handler(CommandHandler('next', next_chat))
    app.add_handler(CommandHandler('stop', stop_chat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_messages))

    app.run_polling()

if __name__ == '__main__':
    main()
