import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CallbackContext, ConversationHandler, MessageHandler, filters, \
    CommandHandler
from Utils import States, Commands
from MainMenu import MainMenu

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

class Alerter:
    @staticmethod
    async def alerter_entry(update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        await query.answer()
        key = [[InlineKeyboardButton("🔵 В меню", callback_data="start")]]
        markup = InlineKeyboardMarkup(key)
        sent = await query.edit_message_text("Введите текст, который хотите отправить пользователям", reply_markup=markup)
        context.user_data["last_buttons"] = sent.message_id
        return States.ALERT

    @staticmethod
    async def alert_users(update: Update, context: CallbackContext) -> int:
        await context.bot.edit_message_reply_markup(
            chat_id=update.effective_chat.id,
            message_id=context.user_data["last_buttons"],
            reply_markup=None
        )
        text = update.message.text

        with open("users.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            user = line.strip().split("#")
            logger.info(f"Обрабатываю пользователя: {user}")
            id = user[0]
            if int(id) == int(os.getenv("CODE_X2")):
                if user[1] != "Фамилия?":
                    second_name = user[1]
                else:
                    second_name = "Нет фамилии"

                if user[2] != "Имя?":
                    first_name = user[2]
                else:
                    first_name = "Нет имени"

                if user[3] != "Отчество?":
                    patronymic = user[3]
                else:
                    patronymic = "Нет отчества"

                logger.info(f"Отправляю информацию:\nID: {id}\nФамилия: {second_name}\nИмя: {first_name}\nОтчество: {patronymic}")
                await context.bot.send_message(chat_id=int(id), text=text)

        await MainMenu.show(update, context)
        return ConversationHandler.END

    @staticmethod
    async def menu(update, context):
        logger.info("Вызвано меню через Alerter")
        return await Commands.start(update, context)

    def get_handler_send_alert(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[CallbackQueryHandler(self.alerter_entry, pattern="^send_message$")],
            states={States.ALERT: [MessageHandler(filters.TEXT, self.alert_users),
                                   CallbackQueryHandler(self.menu, pattern="^start$")]},
            fallbacks=
            [
                CommandHandler("cancel", Commands.cancel),
                CommandHandler("start", Commands.start),
            ],
        )
