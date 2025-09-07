import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, CallbackQueryHandler
from Utils import User, Checker
from MainMenu import MainMenu

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

class WorkMenu:
    @staticmethod
    async def begin(update: Update, context: CallbackContext):
        query = update.callback_query
        user_id = query.from_user.id
        context.user_data["my_folders"] = []
        await query.answer()

        allowed_users = os.getenv("USER_ALLOW")
        allowed_users_list = [int(uid.strip()) for uid in allowed_users.split(",") if uid.strip().isdigit()]

        if user_id not in allowed_users_list:
            await query.edit_message_text("Доступ запрещен, возвращаю в меню...")
            await MainMenu.show(update, context)
            return ConversationHandler.END

        dirs = os.listdir("photos/")

        to_work_origin_dirs = []
        to_work_id_to_name_dirs = []
        to_work_ids = []  # для callback_data

        text, tags = Checker.check_status(dirs, ["10", "11", "12", "13", "51", "52"])
        if not tags or tags is None:
            await query.edit_message_text("Не нашел схемы к работе. Возвращаю в меню...")
            await MainMenu.show(update, context)
            return ConversationHandler.END

        for tag in tags:
            logger.info(f"ОБРАБАТЫВАЮ {tag} в WorkMenu")
            name, matched_id = User.get_user_data_dir(tag)
            with open(f"photos/{tag}/comment.txt", "r", encoding="utf-8") as f:
                comment = f.readlines()[0]

            to_work_origin_dirs.append(tag)
            # сохраняем метку кнопки
            to_work_id_to_name_dirs.append(name + f" - {comment}")
            # сохраняем ID для callback_data
            to_work_ids.append(matched_id)

        logger.info(f"Директории к работе {to_work_origin_dirs}")
        logger.info(f"Директории к работе с именами {to_work_id_to_name_dirs}")

        buttons = [
            [InlineKeyboardButton(text, callback_data=f"dir_{uid}")]
            for text, uid in zip(to_work_id_to_name_dirs, to_work_ids)
        ]

        context.user_data["work_dir"] = to_work_origin_dirs
        buttons.append([InlineKeyboardButton("🔵 В меню", callback_data="start")])

        markup = InlineKeyboardMarkup(buttons)
        if to_work_origin_dirs:
            sent = await query.edit_message_text("Выберите, что возьмем в работу", reply_markup=markup)
            context.user_data["last_buttons"] = sent.message_id
        else:
            await query.edit_message_text("Не нашел, что взять в работу")
            await MainMenu().show(update, context)
            return ConversationHandler.END
        logger.info(f"Получил следующие директории для работы: {context.user_data["work_dir"]}")
        return None

    @staticmethod
    async def work_step_1(update: Update, context: CallbackContext):
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()

        callback_data = query.data.split("_", 1)[1]

        available_dirs = context.user_data.get("work_dir", [])

        selected_dir = None
        for dir in available_dirs:
            if dir.startswith(callback_data) or dir.endswith(callback_data):
                selected_dir = dir
                break

        if not selected_dir:
            await query.edit_message_text("Папка не найдена или уже недоступна.")
            return ConversationHandler.END

        context.user_data["my_folders"].append(selected_dir)
        await query.edit_message_text("Отправляю тебе задачу, секунду...")

        folder_path = f"photos/{selected_dir}"
        jpg_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith((".jpg", ".png", ".webp", ".bmp", "jpeg"))])
        xlsx_files = sorted(
            [f for f in os.listdir(folder_path) if f.lower().endswith((".xls", ".xlsx"))])
        comment_path = os.path.join(folder_path, "comment.txt")

        if jpg_files:
            from telegram import InputMediaPhoto
            media_group = [InputMediaPhoto(open(os.path.join(folder_path, img), "rb")) for img in jpg_files]
            try:
                await context.bot.send_media_group(chat_id=query.message.chat_id, media=media_group)
            except:
                await context.bot.send_message(chat_id=query.message.chat_id, text="Что-то пошло не так. Возвращаю в меню")
                await MainMenu.show(update, context)
                return None

        if xlsx_files:
            from telegram import InputMediaDocument
            media_group = [InputMediaDocument(open(os.path.join(folder_path, xls), "rb")) for xls in xlsx_files]
            try:
                await context.bot.send_message(chat_id=query.message.chat_id, text = "Спецификация для щита питания:")
                await context.bot.send_media_group(chat_id=query.message.chat_id, media=media_group)
            except:
                await context.bot.send_message(chat_id=query.message.chat_id, text="Что-то пошло не так. Возвращаю в меню")
                await MainMenu.show(update, context)
                return None

        if os.path.exists(comment_path):
            with open(comment_path, "r", encoding="utf-8") as f:
                comment = f.read()
            if comment:
                await context.bot.send_message(chat_id=query.message.chat_id, text=comment)
            else:
                await context.bot.send_message(chat_id=query.message.chat_id, text="Нет комментария")

        status_file = f"photos/{selected_dir}/status.txt"
        with open(status_file, "a", encoding="utf-8") as f:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if user_id == int(os.getenv("CODE_X1")):
                f.write(f"\n{timestamp}_21")
            elif user_id == int(os.getenv("CODE_X2")):
                f.write(f"\n{timestamp}_22")
            elif user_id == int(os.getenv("CODE_X3")):
                f.write(f"\n{timestamp}_23")
            else:
                await query.edit_message_text(
                    "Ошибка, Вы - пользователь без права доступа, перенаправляю в главное меню. ")
                await MainMenu().show(update, context)
                return ConversationHandler.END

        await context.bot.send_message(chat_id=query.message.chat_id, text=f"Задача взята в работу. Чтобы выслать готовую работу, перейдите в Главное меню -> Отправить работу")
        await MainMenu().show(update, context)
        return None

    def get_handler_work_menu(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(self.begin, pattern="^work$")

    def get_handler_to_work_dir(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(self.work_step_1, pattern="^dir_")


