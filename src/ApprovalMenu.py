import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, CallbackQueryHandler
from Utils import Commands
from Utils import States, User
from MainMenu import MainMenu
from PhotoLoader import Load
import logging
import asyncio

class ApprovalMenu:
    @staticmethod
    async def welcome_message(update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()



