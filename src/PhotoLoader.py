import logging
import os
import asyncio
from datetime import datetime
from telegram import Update, Message
from telegram.ext import CallbackContext
from Utils import States

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

class Load:

    @staticmethod
    async def photo_save(messages: list[Message], save_dir: str):
        import os

        os.makedirs(save_dir, exist_ok=True)

        for i, msg in enumerate(messages, start=1):
            document = msg.document
            file = await document.get_file()
            filename = document.file_name or f"image_{i}.jpg"
            file_path = os.path.join(save_dir, filename)
            await file.download_to_drive(file_path)
            logging.info(f"Сохранил файл: {file_path}")