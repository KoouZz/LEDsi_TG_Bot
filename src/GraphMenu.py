import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, CallbackQueryHandler
from Utils import Commands
from Utils import States
from MainMenu import MainMenu
from PhotoLoader import Load
import logging
import asyncio

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

class GraphMenu:
    @staticmethod
    async def func(update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()

        from datetime import datetime
        user_id = query.from_user.id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = f"photos/{user_id}_{timestamp}"

        context.user_data["current_photo_dir"] = save_dir  # сохранить путь
        context.user_data["from_image_upload"] = False
        context.chat_data["document_groups"] = {}  # сбросить группы, если нужно

        keyboard = [
            [InlineKeyboardButton("Загрузить фото", callback_data="image")],
            [InlineKeyboardButton("Выслать текстом исходные данные", callback_data="write")],
            [InlineKeyboardButton("Вернуться в меню", callback_data="start")],
        ]
        markup = InlineKeyboardMarkup(keyboard)
        sent = await query.edit_message_text("Как хотите дать задачу?", reply_markup=markup)
        context.user_data["last_buttons"] = sent.message_id

    @staticmethod
    async def image_way_naming(update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        await query.answer()
        key = [[InlineKeyboardButton("Вернуться в меню", callback_data="start")]]
        markup = InlineKeyboardMarkup(key)
        sent = await query.edit_message_text("Введите наименование схемы для удобства. Например:\n"
                                             "1. ЗПУП-******\n"
                                             "2. ООО Ромашка",
                                             reply_markup=markup)
        context.user_data["last_buttons"] = sent.message_id
        context.user_data["from_image_upload"] = False
        return States.NAMING_IMG

    @staticmethod
    async def image_way(update: Update, context: CallbackContext) -> int:
        await context.bot.edit_message_reply_markup(
            chat_id=update.effective_chat.id,
            message_id=context.user_data["last_buttons"],
            reply_markup=None
        )
        context.user_data["screen_name"] = update.message.text
        key = [[InlineKeyboardButton("Вернуться в меню", callback_data="start")]]
        markup = InlineKeyboardMarkup(key)
        sent = await update.message.reply_text("Загрузите фото по инструкции:\n"
                                             "1. Нажмите 📎\n"
                                             "2. Выберете ФАЙЛ (загрузка как ФАЙЛ)\n"
                                             "3. Выберете фото для загрузки\n"
                                             "4. Нажмите ОТПРАВИТЬ\n",
                                             reply_markup=markup)
        context.user_data["last_buttons"] = sent.message_id
        context.user_data["from_image_upload"] = False
        return States.LOAD_IMG

    @staticmethod
    async def load_image(update: Update, context: CallbackContext):
        if not context.user_data["from_image_upload"]:
            message = update.message
            media_group_id = message.media_group_id
            save_dir = context.user_data.get("current_photo_dir", "photos/unknown")
            os.makedirs(save_dir, exist_ok=True)

            logger.info("Проверка на документ")
            if not message.document or not message.document.mime_type.startswith("image/"):
                logger.error("Это не документ")
                return States.LOAD_IMG

            # Один файл вне альбома
            if not media_group_id:
                logger.warning("Одиночный файл")
                await message.reply_text("Загружаю фото, секунду...")
                await Load.photo_save([message], save_dir)
                await message.reply_text("Файл успешно загружен. Введите комментарий")
                context.user_data["from_image_upload"] = True

            # Групповая загрузка
            logger.info(f"Группа документов: {media_group_id}")
            group_store = context.chat_data.setdefault("document_groups", {})
            group_list = group_store.setdefault(media_group_id, [])
            group_list.append(message)
            logger.info(f"Всего документов в группе: {len(group_list)}")

            # Ставим задачу на сохранение (один раз)
            if f"timer_{media_group_id}" not in context.chat_data and media_group_id != None:
                logger.info("Устанавливаю таймер сохранения группы...")
                await message.reply_text("Загружаю фото, секунду...")

                async def delayed_save():
                    await asyncio.sleep(2.5)
                    messages = group_store.pop(media_group_id, [])
                    context.chat_data.pop(f"timer_{media_group_id}", None)
                    if messages:
                        await Load.photo_save(messages, save_dir)
                        logger.info("Файлы успешно сохранены")
                        # переход состояния можно сделать через context
                        await messages[0].reply_text("Файлы успешно загружены. Введите комментарий")
                        context.user_data["from_image_upload"] = True
                    else:
                        logger.warning("Не удалось найти сообщения в группе после таймера")
                context.chat_data[f"timer_{media_group_id}"] = context.application.create_task(delayed_save())

        return None

    @staticmethod
    async def handle_after_upload(update: Update, context: CallbackContext) -> int:
        if context.user_data.get("from_image_upload"):
            # продолжаем, как только пользователь ввёл комментарий
            context.user_data.pop("from_image_upload", None)
            comment = update.message.text
            name = context.user_data["screen_name"]
            logger.info(f"Комментарий к файлам: {comment}")
            with open(f"{context.user_data["current_photo_dir"]}/comment.txt", 'w', encoding="utf-8") as f:
                f.write(f"{name}\n\n{comment}\n")
            await update.message.reply_text("Мы сохранили ваш комментарий")

            with open(f"{context.user_data["current_photo_dir"]}/status.txt", "w", encoding="utf-8") as f:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                f.write(f"{timestamp}_10")

            allowed_users = os.getenv("USER_ALLOW")
            allowed_users_list = [int(uid.strip()) for uid in allowed_users.split(",") if uid.strip().isdigit()]
            for allowed_user in allowed_users_list:
                await context.bot.send_message(chat_id=allowed_user, text="Добавлена новая задача!")

            await MainMenu.show(update, context)
            return ConversationHandler.END
        else:
            await update.message.reply_text("Пожалуйста, сначала загрузите схемы как файлы.")
            return States.LOAD_IMG

    @staticmethod
    async def write_way(update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        await query.answer()
        key = [[InlineKeyboardButton("Вернуться в меню", callback_data="start")]]
        markup = InlineKeyboardMarkup(key)
        sent = await query.edit_message_text("Введите наименование схемы для удобства. Например:\n1. ЗПУП-******\n2. ООО Ромашка", reply_markup=markup)
        context.user_data["last_buttons"] = sent.message_id
        return States.NAMING

    @staticmethod
    async def write_way_naming(update: Update, context: CallbackContext) -> int:
        await context.bot.edit_message_reply_markup(
            chat_id=update.effective_chat.id,
            message_id=context.user_data["last_buttons"],
            reply_markup=None
        )
        context.chat_data["screen_name"] = update.message.text
        key = [[InlineKeyboardButton("Вернуться в меню", callback_data="start")]]
        markup = InlineKeyboardMarkup(key)
        sent = await update.message.reply_text("Введите ширину экрана в мм", reply_markup=markup)
        context.user_data["last_buttons"] = sent.message_id
        return States.WIDTH

    @staticmethod
    async def write_way_step_1(update: Update, context: CallbackContext) -> int:
        await context.bot.edit_message_reply_markup(
            chat_id=update.effective_chat.id,
            message_id=context.user_data["last_buttons"],
            reply_markup=None
        )
        context.chat_data["screen_width"] = update.message.text
        key = [[InlineKeyboardButton("Вернуться в меню", callback_data="start")]]
        markup = InlineKeyboardMarkup(key)
        sent = await update.message.reply_text("Введите высоту экрана в мм", reply_markup=markup)
        context.user_data["last_buttons"] = sent.message_id
        return States.HEIGHT

    @staticmethod
    async def write_way_step_2(update: Update, context: CallbackContext) -> int:
        await context.bot.edit_message_reply_markup(
            chat_id=update.effective_chat.id,
            message_id=context.user_data["last_buttons"],
            reply_markup=None
        )
        context.chat_data["screen_height"] = update.message.text
        key = [[InlineKeyboardButton("Вернуться в меню", callback_data="start")]]
        markup = InlineKeyboardMarkup(key)
        sent = await update.message.reply_text("Введите шаг пикселя экрана в мм", reply_markup=markup)
        context.user_data["last_buttons"] = sent.message_id
        return States.PITCH

    @staticmethod
    async def write_way_step_3(update: Update, context: CallbackContext) -> int:
        await context.bot.edit_message_reply_markup(
            chat_id=update.effective_chat.id,
            message_id=context.user_data["last_buttons"],
            reply_markup=None
        )
        context.chat_data["screen_pitch"] = update.message.text
        key = [[InlineKeyboardButton("Вернуться в меню", callback_data="start")]]
        markup = InlineKeyboardMarkup(key)
        sent = await update.message.reply_text("Введите дополнительные комментарии(замечания) к задаче", reply_markup=markup)
        context.user_data["last_buttons"] = sent.message_id
        return States.COM

    @staticmethod
    async def write_way_step_4(update: Update, context: CallbackContext) -> int:
        await context.bot.edit_message_reply_markup(
            chat_id=update.effective_chat.id,
            message_id=context.user_data["last_buttons"],
            reply_markup=None
        )
        comment = update.message.text
        name = context.chat_data.pop("screen_name", None)
        pith = context.chat_data.pop("screen_pitch", None)
        width = context.chat_data.pop("screen_width", None)
        height = context.chat_data.pop("screen_height", None)
        logger.info(f"Комментарий к файлам: {comment}")
        os.makedirs(context.user_data["current_photo_dir"], exist_ok=True)
        with open(f"{context.user_data["current_photo_dir"]}/comment.txt", 'w', encoding="utf-8") as f:
            f.write(
                f"{name}\n"
                f"Параметры экрана:\nP{pith} {width}x{height}\n\n"
                f"Дополнительные комментарии:\n{comment}")

        with open(f"{context.user_data["current_photo_dir"]}/status.txt", "w", encoding="utf-8") as f:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            f.write(f"{timestamp}_10")
        await update.message.reply_text("Я сохранил вашу задачу и передал в работу")

        allowed_users = os.getenv("USER_ALLOW")
        allowed_users_list = [int(uid.strip()) for uid in allowed_users.split(",") if uid.strip().isdigit()]
        for allowed_user in allowed_users_list:
            await context.bot.send_message(chat_id=allowed_user, text="Добавлена новая задача!")

        await MainMenu.show(update, context)
        return ConversationHandler.END

    @staticmethod
    async def menu(update, context):
        logger.info("Вызвано меню через GraphMenu")
        return await Commands.start(update, context)


    def get_handler_graph_menu_image(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[CallbackQueryHandler(self.image_way_naming, pattern="^image$")],
            states={
                States.NAMING_IMG: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.image_way),
                               CallbackQueryHandler(self.menu, pattern="^start$")],
                States.LOAD_IMG: [
                    MessageHandler(filters.Document.IMAGE & ~filters.COMMAND, self.load_image),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_after_upload),
                    CallbackQueryHandler(self.menu, pattern="^start$")
                ],
            },
            fallbacks=[
                CommandHandler("cancel", Commands.cancel),
                CommandHandler("start", Commands.start),
            ]
        )
    def get_handler_graph_menu_entry(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(self.func, pattern="^load$")
    def get_handler_graph_menu_write(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[CallbackQueryHandler(self.write_way, pattern="^write")],
            states={
                States.NAMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.write_way_naming),
                               CallbackQueryHandler(self.menu, pattern="^start$")],
                States.WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.write_way_step_1),
                               CallbackQueryHandler(self.menu, pattern="^start$")],
                States.HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.write_way_step_2),
                                CallbackQueryHandler(self.menu, pattern="^start$")],
                States.PITCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.write_way_step_3),
                               CallbackQueryHandler(self.menu, pattern="^start$")],
                States.COM: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.write_way_step_4),
                             CallbackQueryHandler(self.menu, pattern="^start$")],
            },
            fallbacks=[
                CommandHandler("cancel", Commands.cancel),
                CommandHandler("start", Commands.start),
            ]
        )
