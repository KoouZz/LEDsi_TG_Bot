import os
from GraphMenu import GraphMenu
from StatusMenu import StatusMenu
from WorkMenu import WorkMenu
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler
from Utils import Commands
from WorkDoneMenu import WorkDoneMenu
from Alerter import Alerter

# Запуск библиотеки для неявного указания токена ТГ бота
load_dotenv()

class Main:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(BASE_DIR)
    os.chdir(PROJECT_ROOT)

    def __init__(self, token = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("Telegram bot token not provided")
        # Создаем объект Application
        self.application = Application.builder().token(self.token).build()
        self._register_handlers()

    def _register_handlers(self):
        """Регистрация обработчиков команд"""
        self.application.add_handler(CommandHandler("start", Commands.start))
        self.application.add_handler(CommandHandler("cancel", Commands.cancel))
        self.application.add_handler(GraphMenu().get_handler_graph_menu_image())
        self.application.add_handler(GraphMenu().get_handler_graph_menu_entry())
        self.application.add_handler(GraphMenu().get_handler_graph_menu_write())
        self.application.add_handler(StatusMenu().get_handler_status_menu())
        self.application.add_handler(StatusMenu().get_handler_in_status_dir())
        self.application.add_handler(WorkMenu().get_handler_work_menu())
        self.application.add_handler(WorkMenu().get_handler_to_work_dir())
        self.application.add_handler(WorkDoneMenu().get_handler_in_work_menu())
        self.application.add_handler(WorkDoneMenu().get_handler_in_work_dir())
        self.application.add_handler(Alerter().get_handler_send_alert())
        self.application.add_handler(StatusMenu().get_handler_to_menu())


    def run(self):
        """Запуск бота"""
        self.application.run_polling()


if __name__ == "__main__":
    main = Main()
    main.run()