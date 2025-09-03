import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler

logger = logging.getLogger()
logger.setLevel(logging.INFO)
load_dotenv()

class MainMenu:
    @staticmethod
    async def show(update: Update, context: CallbackContext):
        """Асинхронный метод для отображения главного меню"""
        if "last_buttons" in context.user_data:
            try:
                logger.info("Нашел кнопки в сообщении, удаляю...")
                await context.bot.edit_message_reply_markup(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data["last_buttons"],
                    reply_markup=None
                )
                del context.user_data["last_buttons"]
            except:
                pass

        try:
            if update.message:
                message = update.message
                user_id = update.message.from_user.id
            elif update.callback_query:
                await update.callback_query.answer()
                message = update.callback_query.message
                user_id = update.callback_query.from_user.id
            else:
                return ConversationHandler.END

            allowed_users = os.getenv("USER_ALLOW")
            allowed_users_list = [int(uid.strip()) for uid in allowed_users.split(",") if uid.strip().isdigit()]

            engineers = os.getenv("ENGINEERS")
            engineers_list = [int(uid.strip()) for uid in engineers.split(",") if uid.strip().isdigit()]

            if user_id == 429394445:
                keyboard = [
                    [InlineKeyboardButton("Запросить схемы", callback_data='load')],
                    [InlineKeyboardButton("Проверить статус схем", callback_data='status')],
                    [InlineKeyboardButton("Взять в работу", callback_data='work'),
                     InlineKeyboardButton("Отправить работу", callback_data='work_done')],
                    [InlineKeyboardButton("Визирование", callback_data="approval")],
                    [InlineKeyboardButton("<ADM>Отправить уведомление", callback_data='send_message')],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
            elif user_id in allowed_users_list and user_id not in engineers_list:
                keyboard = [
                    [InlineKeyboardButton("Запросить схемы", callback_data='load')],
                    [InlineKeyboardButton("Проверить статус схем", callback_data='status')],
                    [InlineKeyboardButton("Взять в работу", callback_data='work'),
                     InlineKeyboardButton("Отправить работу", callback_data='work_done')],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
            elif user_id in engineers_list:
                keyboard = [
                    [InlineKeyboardButton("Запросить схемы", callback_data='load')],
                    [InlineKeyboardButton("Проверить статус схем", callback_data='status')],
                    [InlineKeyboardButton("Взять в работу", callback_data='work'),
                     InlineKeyboardButton("Отправить работу", callback_data='work_done')],
                    [InlineKeyboardButton("Визирование", callback_data="approval")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
            else:
                keyboard = [
                    [InlineKeyboardButton("Запросить схемы", callback_data='load')],
                    [InlineKeyboardButton("Проверить статус схем", callback_data='status')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

            sent = await message.reply_text(
                "Привет, бот LEDsi к вашим услугам",
                reply_markup=reply_markup
            )
            context.user_data["last_buttons"] = sent.message_id
            return ConversationHandler.END
        except Exception as e:
            raise