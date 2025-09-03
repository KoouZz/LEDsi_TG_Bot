import asyncio
import logging
import os.path
from typing import Any

from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler, ConversationHandler

from MainMenu import MainMenu

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class Commands:
    @staticmethod
    async def start(update: Update, context: CallbackContext) -> int:
        """Обработчик команды /start"""
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

        if update.message:
            cur_user_id = update.message.from_user.id
            await MainMenu.show(update, context)
        elif update.callback_query:
            await update.callback_query.answer()
            cur_user_id = update.callback_query.from_user.id
            await MainMenu.show(update, context)
        else:
            cur_user_id = None
            await MainMenu.show(update, context)

        with open("users.txt", "a", encoding="utf-8") as f:
            users = User().get_users_list()
            tag = True
            for user in users:
                logger.info(f"Нашел пользователя в users.txt -  {user}")
                logger.info(f"ID пользователя - {user[0]}")
                if user[0] == str(cur_user_id):
                    tag = False
            if tag:
                f.write(f"{cur_user_id}#Фамилия?#Имя?#Отчество?\n")

        return ConversationHandler.END

    @staticmethod
    async def cancel(update: Update, context: CallbackContext) -> int:
        """Обработчик команды /cancel"""
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

        logger.info("Команда /cancel вызвана")
        await update.message.reply_text("Операция прервана, возвращаю в меню...")
        if update.message:
            await MainMenu.show(update, context)
        elif update.callback_query:
            await update.callback_query.answer()
            await MainMenu.show(update, context)
        return ConversationHandler.END

    @staticmethod
    async def to_menu(update: Update, context: CallbackContext):

        if "last_buttons" in context.user_data:
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data["last_buttons"],
                    reply_markup=None
                )
                del context.user_data["last_buttons"]
            except:
                pass

        if update.callback_query:
            await update.callback_query.answer()
            cur_user_id = update.callback_query.from_user.id
        elif update.message:
            cur_user_id = update.message.from_user.id
        else:
            cur_user_id = None

        await MainMenu.show(update, context)

        return ConversationHandler.END

    def get_handler_to_menu(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(self.to_menu, pattern="^start$")

class States:
    NAMING_IMG, LOAD_IMG, NAMING, WIDTH, HEIGHT, PITCH, COM, IN_WORK, ALERT, APPROVAL_MNU, DISCARD_COM = range(11)

class StatusCodes:
    dict={"10": "Схемы ожидают принятия в работу", "21": "Схемы приняты в работу Данилом Гильвановым",
          "22": "Схемы приняты в работу Данилом Доценко", "11": "Схемы возвращены Данилом Гильвановым для уточнения",
          "12": "Схемы возвращены Данилом Доценко для уточнения", "31": "Схемы готовы. Автор - Данил Гильванов",
          "32": "Схемы готовы. Автор - Данил Доценко", "13": "Схемы возвращены Косенко Романом для уточнения",
          "23": "Схемы приняты в работу Романом Косенко", "33": "Схемы готовы. Автор - Роман Косенко",
          "50": "Схемы на визировании инженером", "51": "Схемы проверены Данилом Гильвановым", "52": "Схемы проверены Данилом Доценко",
          "61": "Схемы возвращены на доработку Данилом Гильвановым", "62": "Схемы возвращены на доработку Данилом Доценко"}

class User:
    @staticmethod
    def get_users_list():
        try:
            if not os.path.exists("users.txt"):
                raise FileExistsError

            with open("users.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()

                if not lines:
                    logger.info("Список пользователей user.txt существует, но файл пуст")

                # Конструкция списка users_list = [user_1[ID, Фамилия, Имя, Отчество (если есть, иначе пусто)], user_2[...], ...]
                users_list = []
                for line in lines:
                    users_list.append(line.strip().split('#'))

            return users_list

        except FileExistsError:
            logger.info("Список пользователей не существует. Не найден файл users.txt")
            return None

    @staticmethod
    def get_user_name_from_id(id: int | str, return_list = False) -> str | list[str] | None:
        name = None
        if id is None:
            return name

        users = User.get_users_list()
        if type(id) is int:
            str_id = str(id)
        else:
            str_id = id

        for user in users:
            if user[0] == str_id:
                name = user[1] + " " + user[2] + " " + user[3]

        if return_list is True:
            # Возвращаем список [Фамилия, Имя, Отчество]
            return name.strip().split(" ")

        # Стандартно возвращаем строку "Фамилия Имя Отчество"
        return name

    @staticmethod
    def get_user_data_dir(dir: str):
        name = None
        matched_id = None
        user_list = User.get_users_list()

        for user in user_list:
            length_symbols = len(user[0])
            logger.info(f"ID: {user[0]}")
            logger.info(f"Длина ID: {length_symbols}")

            if dir[:length_symbols] == user[0]:
                matched_id = user[0]
                logger.info(f"В папке {dir} я знаю, кто создал задачу, это {user[1]}, с ID = {user[0]}")
                if user[1] == "Имя?":
                    name = f"Инкогнито-{user[0]}_"
                else:
                    name = user[1]
                break

        if name is None:
            logger.info(f"В папке {dir} я не знаю, кто создал задачу")
            name = "Инкогнито-NoID_"
            matched_id = f"noid_{dir}"
        return [name, matched_id]

class Checker:
    @staticmethod
    def check_status(tasks: list, codes: list) -> list[str | Any] | list[str | None]:
        text = "Нашел ваши схемы:\n"
        tag = []
        for indx, task in enumerate(tasks, start=1):
            try:
                with open(f"photos/{task}/status.txt", 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                if not lines:
                    logger.warning(f"Файл {task}/status.txt пуст")
                    continue

                last_line = lines[-1].strip().split('_')
                code = last_line[2]

                if code not in codes:
                    logger.warning(f"Код в {task} не соответствует запрашиваему списку")
                    continue

                date_line = lines[0].strip().split('_')

                logger.info(f"Создание - {date_line}")
                logger.info(f"Изменение статуса - {last_line}")
                logger.info(f"Прочитал последнюю строку: {last_line}")

                text += f"{indx}. "
                with open(f"photos/{task}/comment.txt", "r", encoding="utf-8") as com:
                    row = com.readlines()
                    if row:
                        if len(row[0]) > 15:
                            text += f"{row[0][:15]} ...\n"
                        else:
                            text += f"{row[0][:len(row[0]) - 1]}\n"
                    else:
                        text += "__Комментарий отсутствует__\n"
                # Дата и время отправления
                text += f"Дата и время отправления:\n{date_line[0][-2:]}/{date_line[0][4:6]}/{date_line[0][0:4]} {date_line[1][0:2]}:{date_line[1][2:4]}:{date_line[1][-2:]}\n\n"

                status = StatusCodes.dict.get(code)
                if code == "10":
                    prefix = "\n"
                elif code in ["21", "22", "23", "31", "32", "33", "11", "12", "13", "50", "51", "52", "61", "62"]:
                    prefix = f"Дата и время отправления:\n{last_line[0][-2:]}/{last_line[0][4:6]}/{last_line[0][0:4]} {last_line[1][0:2]}:{last_line[1][2:4]}:{last_line[1][-2:]}\n"
                else:
                    status = "!!Ошибка!!"
                    prefix = "\n"

                tag.append(task)
                text += f"Статус - {status}\n" + f"{prefix}\n"

            except Exception as e:
                logger.exception(f"Ошибка при обработке схемы {task}: {e}")
                text += f"{indx}. Ошибка при чтении схемы {task}\n\n"

        if text.strip() != "Нашел ваши схемы:":
            return [text, tag]
        else:
            return ["Схемы не найдены", None]