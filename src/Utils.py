import asyncio
import logging
import os.path
from typing import Any
from datetime import datetime
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
    NAMING_IMG, LOAD_IMG, NAMING, WIDTH, HEIGHT, PITCH, COM, IN_WORK, ALERT, APPROVAL_MNU, DISCARD_COM, SPEC_SEND = range(12)

class StatusCodes:
    dict={"10": "Ожидание принятия в работу", "21": "В работе у Данила Гильванова",
          "22": "В работе у Данила Доценко", "11": "Возврат Данилом Гильвановым для уточнения",
          "12": "Возврат Данилом Доценко для уточнения", "31": "Готово! Автор - Данил Гильванов",
          "32": "Готово! Автор - Данил Доценко", "13": "Возврат Романом Косенко для уточнения",
          "23": "В работе у Романа Косенко", "33": "Готово! Автор - Роман Косенко",
          "50": "На проверке", "51": "Проверено Данилом Гильвановым", "52": "Проверено Данилом Доценко",
          "61": "Не прошло проверку Данила Гильванова", "62": "Не прошло проверку Данила Доценко",
          "90": "В архиве", "83": "Проверка после разработки Романом Косенко"}

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
        text = "Нашел ваши схемы:\n\n"
        tag = []
        num = 1
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

                with open(f"photos/{task}/comment.txt", "r", encoding="utf-8") as com:
                    row = com.readlines()
                    if row:
                        if len(row[0]) > 15:
                            text += f"━━━\n\n📌 *{row[0][:15]} ...*\n"
                        else:
                            text += f"━━━\n\n📌 *{row[0][:len(row[0]) - 1]}*\n"
                    else:
                        text += "__Комментарий отсутствует__\n"
                # Дата и время отправления
                text += f"📅 Отправлено: {date_line[0][-2:]}/{date_line[0][4:6]}/{date_line[0][0:4]} {date_line[1][0:2]}:{date_line[1][2:4]}:{date_line[1][-2:]}\n"

                status = StatusCodes.dict.get(code)
                prefix = f"🕒 Обновлено: {last_line[0][-2:]}/{last_line[0][4:6]}/{last_line[0][0:4]} {last_line[1][0:2]}:{last_line[1][2:4]}:{last_line[1][-2:]}\n"
                if code == "10":
                    status = "⌛ " + status
                    prefix = "\n"
                elif code in ["11", "12", "13"]:
                    status = "🔙 " + status
                elif code in ["21", "22", "23"]:
                    status = "⚙️ " + status
                elif code in ["31", "32", "33"]:
                    status = "✅ " + status
                elif code == "50":
                    status = "🛃 " + status
                elif code in ["51", "52"]:
                    status = "🆒 " + status
                elif code in ["61", "62"]:
                    status = "❌ " + status
                elif code == "90":
                    status = "📖 " + status
                elif code in ["83"]:
                    status = "🛃 " + status
                else:
                    status = "!!Ошибка!!"
                    prefix = "\n"

                tag.append(task)
                text += f"{status}\n" + f"{prefix}\n"
                num += 1
            except Exception as e:
                logger.exception(f"Ошибка при обработке схемы {task}: {e}")
                text += f"Ошибка при чтении схемы {task}\n\n"
        text += "\n━━━"
        if text.strip() != "Нашел ваши схемы:":
            return [text, tag]
        else:
            return ["Схемы не найдены", None]

    @staticmethod
    def check_time(dir: str) -> bool | None:
        status_path = f"photos/{dir}/status.txt"
        try:
            with open(status_path, "r", encoding="utf-8") as status:
                lines = status.readlines()
        except Exception as e:
            logger.warning(e)
            return None

        if lines:
            last_line = lines[-1]
        else:
            return None

        info_list = last_line.split("_")

        if len(info_list) != 3:
            logger.warning("Строка в статусе состоит не из [дата]_[время]_[статус-код]")
            return None

        code = info_list[2]
        if code not in ["31", "32", "33"]:
            logger.warning("Задача все ещё в работе")
            return None


        task_day = int(info_list[0][-2:])
        task_month = int(info_list[0][4:6])
        task_year = int(info_list[0][:4])
        task_hour = int(info_list[1][:2])
        task_minute = int(info_list[1][2:4])
        task_second = int(info_list[1][-2:])
        logger.info(f"год {task_year}, месяц {task_month}, день {task_day}, час {task_hour}, минута {task_minute}, секунда {task_second}")

        current_time = datetime.now()
        task_time = datetime(task_year, task_month, task_day, task_hour, task_minute, task_second)

        delta = current_time - task_time

        if delta.days >= 3:
            logger.info("Схемы закончены и прошло более 3-х дней, можно помещать в архив")
            return True
        logger.info("Помещать в архив схемы нельзя")
        return False