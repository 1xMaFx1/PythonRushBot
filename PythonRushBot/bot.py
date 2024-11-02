from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, \
    CallbackQueryHandler, CommandHandler, ContextTypes

from credentials import ChatGPT_TOKEN, TG_TOKEN
from gpt import ChatGptService
from util import load_message, send_text, \
    send_image, show_main_menu, Dialog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from util import load_prompt


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dialog.mode = 'main'
    text = load_message('main')
    await send_image(update, context, 'main')
    await send_text(update, context, text)
    await show_main_menu(update, context, {
        'start': 'Главное меню',
        'random': 'Узнать случайный интересный факт 🧠',
        'gpt': 'Задать вопрос чату GPT 🤖',
        'talk': 'Поговорить с известной личностью 👤',
        'quiz': 'Поучаствовать в квизе ❓'
    })


async def random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, "random")
    prompt = load_prompt("random")
    chat_gpt.set_prompt(prompt)
    response = await chat_gpt.send_message_list()
    await send_text(update, context, response)


async def gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, "gpt")
    await send_text(update, context, "Пожалуйста, введите ваш вопрос для ChatGPT.")
    dialog.mode = 'awaiting_gpt_question'


async def handle_gpt_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if dialog.mode != 'awaiting_gpt_question':
        return
    user_message = update.message.text
    response = await chat_gpt.add_message(user_message)
    await send_text(update, context, response)
    dialog.mode = None


async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Курт Кобейн", callback_data="talk_cobain")],
        [InlineKeyboardButton("Стивен Хокинг", callback_data="talk_hawking")],
        [InlineKeyboardButton("Фридрих Ницше", callback_data="talk_nietzsche")],
        [InlineKeyboardButton("Королева Виктория", callback_data="talk_queen")],
        [InlineKeyboardButton("Дж. Р. Р. Толкин", callback_data="talk_tolkien")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите известную личность для общения:", reply_markup=reply_markup)


async def handle_talk_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    personality = query.data

    # Загружаем промпт и устанавливаем его в ChatGPT
    prompt = load_prompt(personality)
    if not prompt:
        await query.edit_message_text("Извините, промпт для выбранной личности не найден.")
        return

    dialog.mode = personality
    chat_gpt.set_prompt(prompt)

    await send_image(update, context, personality)
    personality_name = personality.replace("talk_", "").capitalize()
    await query.edit_message_text(f"Вы выбрали {personality_name}. Можете начать диалог.")


async def handle_talk_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if dialog.mode and dialog.mode.startswith("talk_"):
        user_message = update.message.text
        response = await chat_gpt.add_message(user_message)
        await send_text(update, context, response)
    else:
        await send_text(update, context, "Для начала выберите личность через команду /talk.")


# Инициализация и запуск приложения
dialog = Dialog()
dialog.mode = None
chat_gpt = ChatGptService(ChatGPT_TOKEN)
app = ApplicationBuilder().token(TG_TOKEN).build()

app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler("random", random))
app.add_handler(CommandHandler("gpt", gpt))
app.add_handler(CommandHandler("talk", talk))
app.add_handler(CallbackQueryHandler(handle_talk_choice,
                                     pattern="^(talk_cobain|talk_hawking|talk_nietzsche|talk_queen|talk_tolkien)$"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gpt_question))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_talk_message))

app.run_polling()
