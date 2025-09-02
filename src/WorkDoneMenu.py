import asyncio
import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, \
    CommandHandler
from MainMenu import MainMenu
from Utils import User, Commands, States, Checker
from src.PhotoLoader import Load

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

class WorkDoneMenu:
    @staticmethod
    async def welcome_message(update: Update, context: CallbackContext):
        query = update.callback_query
        user_id = query.from_user.id
        if user_id == 429394445:
            code = "22"
        elif user_id == 5283130051:
            code = "21"
        elif user_id == 566893692:
            code = "23"
        else:
            code = None
        await query.answer()
        logger.info(f"Код для проверки {code}")

        allowed_users = os.getenv("USER_ALLOW")
        allowed_users_list = [int(uid.strip()) for uid in allowed_users.split(",") if uid.strip().isdigit()]

        if user_id not in allowed_users_list:
            await query.edit_message_text("Доступ запрещен, возвращаю в меню...")
            await MainMenu.show(update, context)
            return ConversationHandler.END

        dirs_to_done = os.listdir("photos/")
        logger.info(f"Получил папки, которые в работе {dirs_to_done}")
        if dirs_to_done:
            in_work_id_to_name_dirs = []
            in_work_ids = []
            in_work_dirs = []
            text, tags = Checker.check_status(dirs_to_done, [code])
            for dir in tags:
                logger.info(f"Обрабатываю {dir}")
                if not os.path.exists(f"photos/{dir}/status.txt"):
                    logger.info("Нет файла status.txt")
                    continue
                with open(f"photos/{dir}/status.txt", "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    status_line = lines[-1].strip().split('_')
                logger.info(f"ID папки = {status_line[0]}")

                in_work_dirs.append(dir)
                name, matched_id = User.get_user_data_dir(dir)
                logger.info(f"Обрабатываю папку {dir}")
                logger.info(f"Имя пользователя, создавшего папку {name}")
                logger.info(f"ID пользователя, создавшего папку {matched_id}")

                length_symbols = len(matched_id)
                # сохраняем метку кнопки
                in_work_id_to_name_dirs.append(name + dir[length_symbols:])
                # сохраняем ID для callback_data
                in_work_ids.append(matched_id)
        else:
            await query.edit_message_text("Не нашел взятые вами задачи в работу")
            await MainMenu().show(update, context)
            return ConversationHandler.END

        logger.info(f"Директории, которые в работе, с именами {in_work_id_to_name_dirs}")
        if not in_work_id_to_name_dirs:
            await query.edit_message_text("Не нашел взятые вами задачи в работу")
            await MainMenu().show(update, context)
            return ConversationHandler.END
        else:
            buttons = [
                [InlineKeyboardButton(text, callback_data=f"dir-done_{uid}")]
                for text, uid in zip(in_work_id_to_name_dirs, in_work_ids)
            ]
            context.user_data["in_work"] = in_work_dirs
            buttons.append([InlineKeyboardButton("Вернуться в меню", callback_data="start")])
            markup = InlineKeyboardMarkup(buttons)
            sent = await query.edit_message_text("Выберите задачу, которую хотите закрыть", reply_markup=markup)
            context.user_data["last_buttons"] = sent.message_id
        return None

    @staticmethod
    async def work_done_func(update: Update, context: CallbackContext):
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()

        callback_data = query.data.split("_", 1)[1]
        available_dirs = context.user_data.get("in_work", [])

        selected_dir = None
        for dir in available_dirs:
            if dir.startswith(callback_data):
                selected_dir = dir
                break

        if not selected_dir:
            await query.edit_message_text("Папка не найдена или уже недоступна.")
            return ConversationHandler.END

        key = [[InlineKeyboardButton("Вернуться в меню", callback_data="start")]]
        markup = InlineKeyboardMarkup(key)
        sent = await query.edit_message_text("Загрузите фото по инструкции:\n"
                                      "1. Нажмите 📎\n"
                                      "2. Выберете ФАЙЛ (загрузка как ФАЙЛ)\n"
                                      "3. Выберете фото для загрузки\n"
                                      "4. Нажмите ОТПРАВИТЬ\n",
                                      reply_markup=markup)
        context.user_data["last_buttons"] = sent.message_id
        context.user_data["curr_dir"] = selected_dir
        context.user_data["from_image_upload"] = False
        context.user_data["only_one_update"] = False

        return States.IN_WORK

    @staticmethod
    async def in_work_comment(update: Update, context: CallbackContext):
        if not context.user_data.get("from_image_upload"):
            message = update.message
            user_id = update.message.from_user.id
            media_group_id = message.media_group_id
            save_dir = "photos/" + context.user_data.get("curr_dir", "photos/unknown") + "/complete"
            os.makedirs(save_dir, exist_ok=True)

            logger.info("Проверка на документ")
            if not message.document or not message.document.mime_type.startswith("image/"):
                logger.error("Это не документ")
                return States.IN_WORK

            if not media_group_id:
                logger.warning("Одиночный файл")
                await message.reply_text("Загружаю фото, секунду...")
                await Load.photo_save([message], save_dir)
                await message.reply_text("Файл успешно загружен. Введите комментарий.")
                context.user_data["from_image_upload"] = True

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

            curr_dir = f"photos/{context.user_data['curr_dir']}"
            user_id = context.user_data['curr_dir'].split('_')[0]
            logger.info(f"Отправляю уведомлению пользователю: {user_id}")

            await context.bot.send_message(chat_id=int(user_id), text="Схемы готовы, проверьте статус")
            if comment:
                await context.bot.send_message(chat_id=int(user_id), text=f"Комментарий к выполненной работе:\n{comment}")
            await update.message.reply_text("Отправили пользователю информацию о завершении работы")

            with open(f"{curr_dir}/status.txt", "a") as f:
                from datetime import datetime
                upl_user_id = update.message.from_user.id
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if upl_user_id == 5283130051:
                    f.write(f"\n{timestamp}_31")
                elif upl_user_id == 429394445:
                    f.write(f"\n{timestamp}_32")
                elif upl_user_id == 566893692:
                    f.write(f"\n{timestamp}_33")

            await MainMenu.show(update, context)
            return ConversationHandler.END
        else:
            await update.message.reply_text("Пожалуйста, сначала загрузите схемы как файлы.")
            return States.IN_WORK

    def get_handler_in_work_dir(self) -> ConversationHandler:
        return ConversationHandler (
            entry_points= [CallbackQueryHandler(self.work_done_func, pattern="^dir-done_")],
            states={
                States.IN_WORK:
                [
                    MessageHandler(filters.Document.IMAGE & ~filters.COMMAND, self.in_work_comment),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_after_upload)
                ],
            },
            fallbacks=
            [
                CommandHandler("cancel", Commands.cancel),
                CommandHandler("start", Commands.start),
                CallbackQueryHandler(Commands.start, pattern="^start$"),
                CallbackQueryHandler(Commands.cancel, pattern="^cancel$")
            ]
        )

    def get_handler_in_work_menu(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(self.welcome_message, pattern="^work_done$")