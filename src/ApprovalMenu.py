import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, CallbackQueryHandler
from Utils import Commands
from Utils import States, User
from MainMenu import MainMenu
from PhotoLoader import Load
import logging
import asyncio

from Utils import Checker

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

class ApprovalMenu:
    @staticmethod
    async def welcome_message(update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        user_id = query.from_user.id
        buttons_list = []
        await query.answer()

        allowed_users = os.getenv("USER_ALLOW")
        allowed_users_list = [int(uid.strip()) for uid in allowed_users.split(",") if uid.strip().isdigit()]

        if user_id not in allowed_users_list:
            await query.edit_message_text("Доступ запрещен, возвращаю в меню...")
            await MainMenu.show(update, context)
            return ConversationHandler.END

        dirs = os.listdir("photos/")

        text, tags = Checker.check_status(dirs, ["50"])

        if not tags or tags is None:
            logger.error("Схем для визирования нет в папках")
            await query.edit_message_text("Нет схем для визирования. Возвращаю в меню...")
            await MainMenu.show(update, context)
            return ConversationHandler.END

        context.user_data["approval_dirs"] = tags

        for tag in tags:
            path = f"photos/{tag}"
            with open(f"{path}/comment.txt", "r", encoding="utf-8") as com:
                comment_in_lines = com.readlines()
            title = comment_in_lines[0]
            manager = User.get_user_name_from_id(tag.split("_")[0], True)[0]
            but = [InlineKeyboardButton(f"{manager} - {title}", callback_data=f"show_{tag}")]
            buttons_list.append(but)

        if not buttons_list:
            logger.error("Кнопки были получены, но почему-то не удалось их добавить в массив с ")
            await query.edit_message_text("Нет схем для визирования. Возвращаю в меню...")
            await MainMenu.show(update, context)
            return ConversationHandler.END

        buttons_list.append([InlineKeyboardButton("Вернуться в меню", callback_data="start")])
        markup = InlineKeyboardMarkup(buttons_list)

        sent = await query.edit_message_text("Необходимо проверить следующие схемы", reply_markup=markup)
        context.user_data["last_buttons"] = sent.message_id

        return ConversationHandler.END

    @staticmethod
    async def show_dialog(update: Update, context: CallbackContext):
        query = update.callback_query
        user_id = query.from_user.id

        await query.answer()

        folder = query.data.split("_", 1)[1]
        approval_dirs = context.user_data.get("approval_dirs", [])
        selected_dir = None

        for dir in approval_dirs:
            if dir.startswith(folder) or dir.endswith(folder):
                selected_dir = dir
                break

        if not selected_dir:
            await query.edit_message_text("Папка не найдена или уже недоступна.")
            return ConversationHandler.END

        await query.edit_message_text("Секунду, отправляю тебе файлы для проверки...")

        folder_path = f"photos/{selected_dir}"
        jpg_files = sorted(
            [f for f in os.listdir(folder_path) if f.lower().endswith((".jpg", ".png", ".webp", ".bmp", "jpeg"))])
        comment_path = os.path.join(folder_path, "comment.txt")

        if jpg_files:
            from telegram import InputMediaPhoto
            media_group = [InputMediaPhoto(open(os.path.join(folder_path, img), "rb")) for img in jpg_files]
            try:
                await context.bot.send_media_group(chat_id=query.message.chat_id, media=media_group)
            except:
                await context.bot.send_message(chat_id=query.message.chat_id,
                                               text="Что-то пошло не так. Возвращаю в меню")
                await MainMenu.show(update, context)
                return ConversationHandler.END

        if os.path.exists(comment_path):
            with open(comment_path, "r", encoding="utf-8") as f:
                comment = f.read()
            if comment:
                await context.bot.send_message(chat_id=query.message.chat_id, text=comment)
            else:
                await context.bot.send_message(chat_id=query.message.chat_id, text="Нет комментария")

        context.user_data["curr_dir"] = selected_dir
        buttons = [[InlineKeyboardButton("Подтвердить", callback_data="approve")],
                   [InlineKeyboardButton("Вернуть на доработку", callback_data="discard")],
                   [InlineKeyboardButton("Вернуться в меню", callback_data="start")]]
        markup = InlineKeyboardMarkup(buttons)

        sent = await context.bot.send_message(chat_id=query.message.chat_id,
                                       text=f"Что делаем?", reply_markup=markup)

        context.user_data["last_buttons"] = sent.message_id
        return States.APPROVAL_MNU

    @staticmethod
    async def event_dialog(update: Update, context: CallbackContext):
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()

        allowed_users = os.getenv("USER_ALLOW")
        allowed_users_list = [int(uid.strip()) for uid in allowed_users.split(",") if uid.strip().isdigit()]

        event = query.data
        selected_dir = context.user_data.get("curr_dir", [])
        status_file = f"photos/{selected_dir}/status.txt"
        with open(status_file, "a", encoding="utf-8") as f:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if event == "approve":
                if user_id == 5283130051:
                    f.write(f"\n{timestamp}_51")
                elif user_id == 429394445:
                    f.write(f"\n{timestamp}_52")
                else:
                    await query.edit_message_text(
                        "Ошибка, Вы - пользователь без права доступа, перенаправляю в главное меню. ")
                    await MainMenu().show(update, context)
                    return ConversationHandler.END

                await query.edit_message_text("Подтверждено. Отправляю в работу")

                for allowed_user in allowed_users_list:
                    logger.info(f"Отправляю уведомление {allowed_user}...")
                    await context.bot.send_message(chat_id=allowed_user, text="Добавлена новая задача!")

            elif event == "discard":
                if user_id == 5283130051:
                    f.write(f"\n{timestamp}_61")
                elif user_id == 429394445:
                    f.write(f"\n{timestamp}_62")
                else:
                    await query.edit_message_text(
                        "Ошибка, Вы - пользователь без права доступа, перенаправляю в главное меню. ")
                    await MainMenu().show(update, context)
                    return ConversationHandler.END
                await query.edit_message_text("Не подтверждено. Укажите причину")
                context.user_data["curr_dir"] = selected_dir
                return States.DISCARD_COM
            else:
                await query.edit_message_text("Произошел сбой, возвращаю в меню...")
                await MainMenu.show(update, context)
                return ConversationHandler.END

        await MainMenu.show(update, context)
        return ConversationHandler.END

    @staticmethod
    async def discard_dialog(update: Update, context: CallbackContext):
        message = update.message
        discard_comment = message.text

        selected_dir = context.user_data.get("curr_dir", [])
        comment_path = f"photos/{selected_dir}/comment.txt"
        manager_id = selected_dir.split("_")[0]
        title = None

        if os.path.exists(comment_path):
            with open(comment_path, "r", encoding="utf-8") as f:
                title = f.readlines()[0]

        await message.reply_text("Отправляю уведомление пользователю...Возвращаю в меню")

        if title is not None or title:
            await context.bot.send_message(chat_id=manager_id, text=f"Схема - {title} не прошла проверку")
            await context.bot.send_message(chat_id=manager_id, text=f"Комментарий инженера:\n{discard_comment}")
        else:
            await context.bot.send_message(chat_id=manager_id,
                                           text="Ваша схема не прошла проверку, проверьте статус схем")
            await context.bot.send_message(chat_id=manager_id, text=f"Комментарий инженера:\n{discard_comment}")

        await MainMenu.show(update, context)
        return ConversationHandler.END

    def get_handler_approval_dialog(self) -> ConversationHandler:
        return ConversationHandler(entry_points=[CallbackQueryHandler(self.show_dialog, pattern="^show_")],
                                   states={
                                       States.APPROVAL_MNU: [CallbackQueryHandler(self.event_dialog)],
                                       States.DISCARD_COM: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.discard_dialog)]
                                   },
                                   fallbacks=
                                   [
                                       CommandHandler("cancel", Commands.cancel),
                                       CommandHandler("start", Commands.start),
                                       CallbackQueryHandler(Commands.start, pattern="^start$"),
                                       CallbackQueryHandler(Commands.cancel, pattern="^cancel$")
                                   ]
                                   )

    def get_handler_in_approval_menu(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(self.welcome_message, pattern="^approval$")