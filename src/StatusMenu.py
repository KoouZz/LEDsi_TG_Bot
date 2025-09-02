import os
from Utils import Checker, Commands
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ConversationHandler, CallbackQueryHandler, CallbackContext
import logging

from MainMenu import MainMenu

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class StatusMenu:

    @staticmethod
    async def view(update: Update, context: CallbackContext) -> int:
        await update.callback_query.answer()
        user_id = str(update.callback_query.from_user.id)
        count = len(user_id)
        logger.info(f"{count} - символы юзернейма")
        dirs = os.listdir("photos/")
        logger.info(f"Директории: {dirs}")
        list_tasks = []
        logger.info("Пытаюсь найти папки схожие с сигнатурой пользователя")
        for dir in dirs:
            logger.info(f"Директория создана текущим пользователем? - {dir[:count] == user_id}")
            logger.info(f"Проверяю наличие файла status.txt - {os.path.exists(f"photos/{dir}/status.txt")}")
            if dir[:count] == user_id and os.path.exists(f"photos/{dir}/status.txt"):
                list_tasks.append(dir)
                logger.info(f"Нашел папку {dir}, добавляю в список для обработки")
        if list_tasks:
            key = []
            text, tags = Checker.check_status(list_tasks, ["31", "32", "33"])
            text, j = Checker.check_status(list_tasks, ["10", "11", "12", "13", "21", "22", "23", "50", "31", "32", "33"])
            if tags is not None and tags:
                logger.info(f"Получил готовые работы для отправки пользователю: {tags}")
                for tag in tags:
                    comment_file = f"photos/{tag}/comment.txt"
                    with open(comment_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        name = lines[0]
                    tag_list = tag.strip().split('_')
                    tag_id = tag_list[0]
                    logger.info(f"ID папки: {tag_id}")
                    tag_time = tag_list[2]
                    logger.info(f"Время создания папки: {tag_time}")
                    tag_date = tag_list[1]
                    logger.info(f"Дата создания папки: {tag_date}")
                    # text_button = f"Получить:\n{tag_date[-2:]}/{tag_date[4:6]}/{tag_date[0:4]}\n{tag_time[0:2]}:{tag_time[2:4]}:{tag_time[-2:]}"
                    text_button = f"Получить:\n{name}"
                    key.append([InlineKeyboardButton(text_button, callback_data=f"status_button_{tag}")])
                context.user_data["in_status"] = tags
            if key:
                key.append([InlineKeyboardButton("Вернуться в меню", callback_data="start")])
            else:
                key = [[InlineKeyboardButton("Вернуться в меню", callback_data="start")]]
            markup = InlineKeyboardMarkup(key)
            sent = await update.callback_query.edit_message_text(text, reply_markup=markup)
            context.user_data["last_buttons"] = sent.message_id
        else:
            await update.callback_query.edit_message_text("Не нашел ваших схема")
            await MainMenu.show(update, context)
            return ConversationHandler.END

        return ConversationHandler.END

    @staticmethod
    async def get_files(update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()

        callback_data = query.data.split("_", 2)[2]
        logger.info(f"Получил следующий колбек: {callback_data}")
        available_dirs = context.user_data.get("in_status", [])

        selected_dir = None
        for dir in available_dirs:

            logger.info(f"Обрабатываю: {dir}")
            if dir.startswith(callback_data):
                logger.info(f"Добавил: {dir}")
                selected_dir = dir
                break

        if not selected_dir:
            await query.edit_message_text("Папка не найдена или уже недоступна.")
            await MainMenu.show(update, context)
            return ConversationHandler.END
        photos_dir = f"photos/{selected_dir}/complete"
        files = [f for f in os.listdir(photos_dir) if f.lower().endswith((".jpg", ".png", ".webp", ".bmp", "jpeg"))]

        if not files:
            await query.edit_message_text("Нет файлов для отправки")
            await MainMenu.show(update, context)
            return ConversationHandler.END

        media_group = []
        for file in files:
            file_path = os.path.join(photos_dir, file)
            # Добавляем каждое фото как InputMediaPhoto
            media_group.append(InputMediaPhoto(open(file_path, "rb")))

        await query.edit_message_text("Отправляю файлы, минутку...")
        await context.bot.send_media_group(chat_id=user_id, media=media_group)
        await MainMenu.show(update, context)
        return ConversationHandler.END

    def get_handler_status_menu(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(self.view, pattern="^status$")

    def get_handler_in_status_dir(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(self.get_files, pattern="^status_button_")

    def get_handler_to_menu(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(Commands.start, pattern="^start$")