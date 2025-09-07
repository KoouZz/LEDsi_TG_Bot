import os
from datetime import datetime

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
        flag = True
        await query.answer()

        allowed_users = os.getenv("ENGINEERS")
        allowed_users_list = [int(uid.strip()) for uid in allowed_users.split(",") if uid.strip().isdigit()]

        if user_id not in allowed_users_list:
            await query.edit_message_text("Доступ запрещен, возвращаю в меню...")
            await MainMenu.show(update, context)
            return ConversationHandler.END

        dirs = os.listdir("photos/")

        text, tags = Checker.check_status(dirs, ["50"])
        text_none, dev_dir = Checker.check_status(dirs, ["83"])
        logger.info(f"Получил папки dev_dir: {dev_dir}")

        if tags and tags is not None:
            flag = False
            context.user_data["approval_dirs"] = tags

            for tag in tags:
                path = f"photos/{tag}"
                with open(f"{path}/comment.txt", "r", encoding="utf-8") as com:
                    comment_in_lines = com.readlines()
                title = comment_in_lines[0]
                manager = User.get_user_name_from_id(tag.split("_")[0], True)[0]
                but = [InlineKeyboardButton(f"{manager} - {title}", callback_data=f"show_{tag}")]
                buttons_list.append(but)


        if dev_dir and dev_dir is not None:
            context.user_data["dev_dirs"] = dev_dir
            flag = False
            for dir in dev_dir:
                logger.info(f"Обрабатываю папку {dir} со схемами, присланными разработчиком")
                dev_but = []
                path_dev = f"photos/{dir}"
                with open(f"{path_dev}/comment.txt", "r", encoding="utf-8") as com:
                    comment_in_lines = com.readlines()
                title = comment_in_lines[0]
                manager = User.get_user_name_from_id(dir.split("_")[0], True)[0]
                with open(f"{path_dev}/status.txt", "r", encoding="utf-8") as stat:
                    status_last_line = stat.readlines()[-1]
                code_dev = status_last_line.split("_")[2]
                if code_dev == "83":
                    dev_name = User.get_user_name_from_id(os.getenv("CODE_X3"), True)[0]
                    dev_but = [InlineKeyboardButton(f"{manager} - {title} ({dev_name})", callback_data=f"dev_{dir}")]
                else:
                    logger.warning(f"Не могу добавить кнопку со схемами разработчика. Не найден пользователь с кодом - {code_dev}")

                if dev_but:
                    buttons_list.append(dev_but)

                context.user_data["code_dev"] = code_dev

        if flag:
            await query.edit_message_text("Нет схем для визирования. Возвращаю в меню...")
            await MainMenu.show(update, context)
            return ConversationHandler.END



        if not buttons_list:
            logger.error("Кнопки были получены, но почему-то не удалось их добавить в массив с ")
            await query.edit_message_text("Нет схем для визирования. Возвращаю в меню...")
            await MainMenu.show(update, context)
            return ConversationHandler.END

        buttons_list.append([InlineKeyboardButton("🔵 В меню", callback_data="start")])
        markup = InlineKeyboardMarkup(buttons_list)

        sent = await query.edit_message_text("Необходимо проверить следующие схемы", reply_markup=markup)
        context.user_data["last_buttons"] = sent.message_id

        return ConversationHandler.END

    @staticmethod
    async def show_dialog(update: Update, context: CallbackContext):
        query = update.callback_query
        user_id = query.from_user.id
        context.user_data["button_text"] = query.data

        await query.answer()

        list_data = query.data.split("_", 1)
        folder = list_data[1]
        manager_dev = list_data[0]

        if manager_dev == "show":
            work_dirs = context.user_data.get("approval_dirs", [])
        elif manager_dev == "dev":
            work_dirs = context.user_data.get("dev_dirs", [])
        else:
            logger.warning("Ошибка. Не могу получить папки из контекста")
            await context.bot.send_message(chat_id=user_id, text="Произошла ошибка. Возвращаю в меню")
            await MainMenu.show(update, context)
            return ConversationHandler.END

        selected_dir = None

        for dir in work_dirs:
            if dir.startswith(folder) or dir.endswith(folder):
                selected_dir = dir
                break
        folder_path = f"photos/{selected_dir}"
        comment_path = f"{folder_path}/comment.txt"
        jpg_files = []
        media_path = None

        if manager_dev == "dev":
            media_path = f"{folder_path}/complete"


        if not selected_dir:
            await query.edit_message_text("Папка не найдена или уже недоступна.")
            return ConversationHandler.END

        await query.edit_message_text("Секунду, отправляю тебе файлы для проверки...")

        jpg_files_source = sorted(
            [f for f in os.listdir(folder_path) if f.lower().endswith((".jpg", ".png", ".webp", ".bmp", "jpeg"))])

        if media_path and media_path is not None:
            jpg_files = sorted(
                [f for f in os.listdir(media_path) if f.lower().endswith((".jpg", ".png", ".webp", ".bmp", "jpeg"))])


        if jpg_files_source:
            from telegram import InputMediaPhoto
            media_group = [InputMediaPhoto(open(os.path.join(folder_path, img), "rb")) for img in jpg_files_source]
            try:
                await context.bot.send_message(chat_id=query.message.chat_id, text="Исходные данные")
                await context.bot.send_media_group(chat_id=query.message.chat_id, media=media_group)
            except:
                await context.bot.send_message(chat_id=query.message.chat_id,
                                               text="Что-то пошло не так. Возвращаю в меню")
                await MainMenu.show(update, context)
                return ConversationHandler.END

            if jpg_files:
                from telegram import InputMediaPhoto
                media_group = [InputMediaPhoto(open(os.path.join(media_path, img), "rb")) for img in jpg_files]
                try:
                    await context.bot.send_message(chat_id=query.message.chat_id, text="Данные от разработчика схем")
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
        context.user_data["manager_dev"] = manager_dev
        buttons = [[InlineKeyboardButton("Подтвердить", callback_data="approve")],
                   [InlineKeyboardButton("Вернуть на доработку", callback_data="discard")],
                   [InlineKeyboardButton("🔵 В меню", callback_data="start")]]
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

        event = query.data
        selected_dir = context.user_data.get("curr_dir", [])
        manager_id = selected_dir.split("_")[0]
        dev_id = None
        manager_dev = context.user_data.get("manager_dev", [])
        code_dev = None

        with open(f"photos/{selected_dir}/comment.txt", "r", encoding="utf-8") as com:
            comment_in_lines = com.readlines()
        title = comment_in_lines[0]
        manager_name = User.get_user_name_from_id(manager_id, True)[0]

        if "code_dev" in context.user_data and context.user_data["code_dev"] and context.user_data["code_dev"] is not None:
            code_dev = context.user_data.get("code_dev", [])
        status_file = f"photos/{selected_dir}/status.txt"
        code = None

        if manager_dev == "show":
            if user_id == int(os.getenv("CODE_X1")):
                code = "51"
            elif user_id == int(os.getenv("CODE_X2")):
                code = "52"
            else:
                await query.edit_message_text(
                    "Ошибка, Вы - пользователь без права доступа, перенаправляю в главное меню. ")
                await MainMenu().show(update, context)
                return ConversationHandler.END
        else:
            if code_dev is not None and code_dev:
                if code_dev == "83":
                    code = "33"
                    dev_id = os.getenv("CODE_X3")

        with open(status_file, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if event == "approve":
                if code is not None and code:
                    f.write(f"\n{timestamp}_{code}")
                else:
                    await query.edit_message_text(
                        "Ошибка, кода пользователя не существует в базе, возвращаю в меню")
                    await MainMenu().show(update, context)
                    return ConversationHandler.END

                if manager_dev == "show":
                    but = [[InlineKeyboardButton("Да", callback_data="have_spec"),
                           InlineKeyboardButton("Нет", callback_data="havent_spec")]]
                    mark = InlineKeyboardMarkup(but)
                    await query.edit_message_text("Подтверждено. Есть информация по щиту питания?", reply_markup=mark)
                    return ConversationHandler.END
                else:
                    await context.bot.send_message(chat_id=int(manager_id), text="Схемы готовы, проверьте статус")
                    await context.bot.send_message(chat_id=int(dev_id), text=f"Схемы приняты.\nРабота: {manager_name} - {title}")
                    await query.edit_message_text("Отправил пользователям информацию о завершении работы")

                    await MainMenu.show(update, context)
                    return ConversationHandler.END

            elif event == "discard":
                if code is not None and code:
                    if code == "51":
                        code = "61"
                    elif code == "52":
                        code = "62"
                    elif code == "33":
                        code = "23"
                    f.write(f"\n{timestamp}_{code}")
                else:
                    await query.edit_message_text(
                        "Ошибка, кода пользователя не существует в базе, возвращаю в меню")
                    await MainMenu().show(update, context)
                    return ConversationHandler.END

                await query.edit_message_text("Не подтверждено. Укажите причину")
                context.user_data["curr_dir"] = selected_dir
                context.user_data["manager_dev"] = manager_dev
                context.user_data["dev_id"] = dev_id
                return States.DISCARD_COM
            else:
                await query.edit_message_text("Произошел сбой, возвращаю в меню...")
                await MainMenu.show(update, context)
                return ConversationHandler.END


    @staticmethod
    async def have_spec_dialog(update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()

        key = [[InlineKeyboardButton("🔵 В меню", callback_data="start")]]
        markup = InlineKeyboardMarkup(key)
        sent = await query.edit_message_text("Загрузите документ по инструкции:\n"
                                             "1. Нажмите 📎 или перетащите .xlsx или .xls файл\n"
                                             "2. После нажатия 📎 выберете ФАЙЛ (загрузка как ФАЙЛ)\n"
                                             "3. Выберете .xlsx или .xls файл для загрузки\n"
                                             "4. Нажмите ОТПРАВИТЬ\n",
                                             reply_markup=markup)

        context.user_data["last_buttons"] = sent.message_id
        return States.SPEC_SEND

    @staticmethod
    async def send_spec(update: Update, context: CallbackContext):
        message = update.message
        user_id = update.message.from_user.id
        media_group_id = message.media_group_id
        save_dir = "photos/" + context.user_data.get("curr_dir", [])

        logger.info("Проверка на документ")
        if not message.document or not message.document.mime_type.startswith("application/"):
            logger.error("Это не документ .xlsx или .xls")
            await context.bot.send_message(chat_id=user_id, text="Загрузите .xlsx или .xls файл")
            return States.SPEC_SEND

        if not media_group_id:
            logger.info("Загружаю файл")
            await message.reply_text("Загружаю файл, секунду...")
            await Load.photo_save([message], save_dir)
        else:
            logger.error("Это не одиночный файл .xlsx или .xls")
            await context.bot.send_message(chat_id=user_id, text="Загрузите один .xlsx или .xls файл")
            return States.SPEC_SEND

        allowed_users = os.getenv("USER_ALLOW")
        allowed_users_list = [int(uid.strip()) for uid in allowed_users.split(",") if uid.strip().isdigit()]

        for allowed_user in allowed_users_list:
            logger.info(f"Отправляю уведомление {allowed_user}...")
            await context.bot.send_message(chat_id=allowed_user, text="Добавлена новая задача!")

        await message.reply_text("Отправили спецификацию на щит питания. Возвращаю в меню...")

        await MainMenu.show(update, context)
        return ConversationHandler.END


    @staticmethod
    async def havent_spec_dialog(update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()

        allowed_users = os.getenv("USER_ALLOW")
        allowed_users_list = [int(uid.strip()) for uid in allowed_users.split(",") if uid.strip().isdigit()]

        for allowed_user in allowed_users_list:
            logger.info(f"Отправляю уведомление {allowed_user}...")
            await context.bot.send_message(chat_id=allowed_user, text="Добавлена новая задача!")

        await MainMenu.show(update, context)
        return ConversationHandler.END


    @staticmethod
    async def discard_dialog(update: Update, context: CallbackContext):
        message = update.message
        discard_comment = message.text

        selected_dir = context.user_data.get("curr_dir", [])
        comment_path = f"photos/{selected_dir}/comment.txt"
        manager_dev = context.user_data.get("manager_dev", [])
        complete_dir = f"photos/{selected_dir}/complete"
        files = os.listdir(complete_dir)
        for file in files:
            os.remove(f"{complete_dir}/{file}")

        os.rmdir(complete_dir)

        if manager_dev == "show":
            send_id = selected_dir.split("_")[0]
        else:
            send_id = context.user_data.get("dev_id", [])
        title = None

        if os.path.exists(comment_path):
            with open(comment_path, "r", encoding="utf-8") as f:
                title = f.readlines()[0]

        await message.reply_text("Отправляю уведомление пользователю...Возвращаю в меню")

        if title is not None or title:
            await context.bot.send_message(chat_id=send_id, text=f"Схема - {title} не прошла проверку")
            await context.bot.send_message(chat_id=send_id, text=f"Комментарий инженера:\n{discard_comment}")
        else:
            await context.bot.send_message(chat_id=send_id,
                                           text="Ваша схема не прошла проверку")
            await context.bot.send_message(chat_id=send_id, text=f"Комментарий инженера:\n{discard_comment}")


        await MainMenu.show(update, context)
        return ConversationHandler.END

    def get_handler_approval_dialog(self) -> ConversationHandler:
        return ConversationHandler(entry_points=[CallbackQueryHandler(self.show_dialog, pattern="^show_"),
                                                 CallbackQueryHandler(self.show_dialog, pattern="^dev_")],
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

    def get_handler_have_spec(self) -> ConversationHandler:
        return ConversationHandler(entry_points=[CallbackQueryHandler(self.have_spec_dialog, pattern="^have_spec$")],
                                   states={
                                       States.SPEC_SEND: [
                                           MessageHandler(filters.Document.APPLICATION & ~filters.COMMAND, self.send_spec),
                                       ]
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

    def get_handler_havent_spec(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(self.havent_spec_dialog, pattern="^havent_spec$")