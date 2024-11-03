from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from credentials import ChatGPT_TOKEN, TG_TOKEN
from gpt import ChatGptService
from util import (
    load_message,
    send_text,
    send_image,
    show_main_menu,
    Dialog,
    load_prompt,
)

dialogues = {
    'gpt': 'handle_gpt_question',
    'random': 'random_dialog',
    'talk': 'handle_talk_message',
    'professor': 'handle_professor_question',
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dialog.mode = 'main'
    text = load_message('main')
    await send_image(update, context, 'main')
    await send_text(update, context, text)
    await show_main_menu(
        update,
        context,
        {
            'start': 'Главное меню',
            'random': 'Узнать случайный интересный факт 🧠',
            'gpt': 'Задать вопрос чату GPT 🤖',
            'talk': 'Поговорить с известной личностью 👤',
            'quiz': 'Поучаствовать в квизе ❓',
            'professor': 'Спросить совета у преподавателя 💻'
        }
    )


async def set_random_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dialog.mode = 'random'
    await random_dialog(update, context)


async def set_gpt_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dialog.mode = 'gpt'
    await send_image(update, context, "gpt")
    await send_text(update, context, "Пожалуйста, введите ваш вопрос для ChatGPT.")


async def set_talk_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dialog.mode = 'talk'
    keyboard = [
        [InlineKeyboardButton("Курт Кобейн", callback_data="talk_cobain")],
        [InlineKeyboardButton("Стивен Хокинг", callback_data="talk_hawking")],
        [InlineKeyboardButton("Фридрих Ницше", callback_data="talk_nietzsche")],
        [InlineKeyboardButton("Королева Виктория", callback_data="talk_queen")],
        [InlineKeyboardButton("Дж. Р. Р. Толкин", callback_data="talk_tolkien")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Выберите известную личность для общения:",
        reply_markup=reply_markup
    )


async def handle_talk_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    personality = query.data

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
    """Обрабатывает сообщения в режиме общения с выбранной личностью"""
    if dialog.mode and dialog.mode.startswith("talk_"):
        user_message = update.message.text

        response = await chat_gpt.add_message(user_message)
        await send_text(update, context, response)
    else:
        await send_text(update, context, "Для начала выберите личность через команду /talk.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главный диспетчер текстовых сообщений, который перенаправляет их в зависимости от dialog.mode"""
    if dialog.mode == "professor":
        await handle_professor_question(update, context)
    elif dialog.mode and dialog.mode.startswith("talk_"):
        await handle_talk_message(update, context)
    elif dialog.mode and dialog.mode.startswith("quiz_"):
        await handle_quiz_answer(update, context)
    elif dialog.mode in dialogues:
        handler_name = dialogues[dialog.mode]
        handler = globals().get(handler_name)
        if handler:
            await handler(update, context)
        else:
            await send_text(update, context, f"Обработчик для режима {dialog.mode} не найден.")
    else:
        await send_text(update, context, "Команда не распознана. Пожалуйста, выберите команду из меню.")


async def random_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, "random")
    prompt = load_prompt("random")
    chat_gpt.set_prompt(prompt)
    response = await chat_gpt.send_message_list()
    await send_text(update, context, response)


async def handle_gpt_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    response = await chat_gpt.add_message(user_message)
    await send_text(update, context, response)


async def set_quiz_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запускает квиз и предлагает выбрать тему"""
    dialog.mode = 'quiz'
    await send_image(update, context, "quiz")
    context.user_data["correct_answers"] = 0

    keyboard = [
        [InlineKeyboardButton("Тема 1: История", callback_data="quiz_history")],
        [InlineKeyboardButton("Тема 2: Наука", callback_data="quiz_science")],
        [InlineKeyboardButton("Тема 3: Искусство", callback_data="quiz_art")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите тему для квиза:", reply_markup=reply_markup)


async def handle_quiz_topic_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор темы квиза и отправляет первый вопрос"""
    query = update.callback_query
    await query.answer()
    topic = query.data

    topic_name = topic.replace("quiz_", "").capitalize()
    topic_prompt = f"Сгенерируй вопрос для квиза по теме '{topic_name}'. Не показывай правильный ответ."

    dialog.mode = topic
    chat_gpt.set_prompt(topic_prompt)

    question = await chat_gpt.send_message_list()
    await send_text(update, context, f"Вопрос по теме '{topic_name}':\n{question}")
    context.user_data['current_question'] = question


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ответ пользователя и автоматически продолжает квиз, пока не скажут 'стоп'"""
    if not dialog.mode or not dialog.mode.startswith("quiz_"):
        await send_text(update, context, "Сначала выберите тему квиза с помощью команды /quiz.")
        return

    user_answer = update.message.text

    if user_answer.lower() == "стоп":
        await send_text(update, context, "Квиз завершён. Спасибо за участие!")
        dialog.mode = 'main'
        return

    question = context.user_data.get('current_question', '')

    check_prompt = (f"Вопрос: '{question}'. Ответ пользователя: '{user_answer}'. Скажи, верно ли это. Если неверно, "
                    f"укажи правильный ответ.")
    chat_gpt.set_prompt(check_prompt)
    response = await chat_gpt.send_message_list()

    if "верно" in response.lower() and "неверно" not in response.lower():
        context.user_data["correct_answers"] += 1
        result_text = f"Правильно! 🎉\n\nВаши правильные ответы: {context.user_data['correct_answers']}"
    else:
        result_text = f"Неправильно 😞\n{response}\n\nВаши правильные ответы: {context.user_data['correct_answers']}"

    await send_text(update, context, result_text)

    await handle_next_question(update, context)


async def handle_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает следующий вопрос для текущей темы квиза"""
    if not dialog.mode or not dialog.mode.startswith("quiz_"):
        await send_text(update, context, "Сначала выберите тему квиза с помощью команды /quiz.")
        return

    topic = dialog.mode.replace("quiz_", "")
    topic_name = topic.capitalize()
    topic_prompt = f"Сгенерируй новый вопрос для квиза по теме '{topic_name}'. Не показывай правильный ответ."
    chat_gpt.set_prompt(topic_prompt)

    question = await chat_gpt.send_message_list()
    context.user_data['current_question'] = question
    await send_text(update, context, f"Вопрос по теме '{topic_name}':\n{question}")


professor_prompt = (
    "Представь, что ты опытный преподаватель по программированию. "
    "Отвечай на вопросы студентов понятно и с деталями, помогай разбирать примеры и, "
    "если возможно, приводить код для наглядности. Постарайся быть терпеливым и дружелюбным. Можешь не здороваться "
    "каждый раз"
)


async def set_professor_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Устанавливает режим 'Препод по программированию'"""
    dialog.mode = 'professor'
    await send_text(update, context,
                    "Добро пожаловать в режим 'Препод по программированию'! Задайте ваш вопрос или попросите пример "
                    "кода.")


async def handle_professor_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает запросы в режиме 'Препод по программированию'"""
    user_message = update.message.text
    prompt = f"{professor_prompt} Вопрос студента: {user_message}"

    response = await chat_gpt.add_message(prompt)

    await send_text(update, context, response)

dialog = Dialog()
dialog.mode = None
chat_gpt = ChatGptService(ChatGPT_TOKEN)
app = ApplicationBuilder().token(TG_TOKEN).build()

app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler("random", set_random_mode))
app.add_handler(CommandHandler("gpt", set_gpt_mode))
app.add_handler(CommandHandler("talk", set_talk_mode))
app.add_handler(CommandHandler("quiz", set_quiz_mode))
app.add_handler(CommandHandler("professor", set_professor_mode))

app.add_handler(CallbackQueryHandler(handle_talk_choice, pattern="^(talk_cobain|talk_hawking|talk_nietzsche"
                                                                 "|talk_queen|talk_tolkien)$"))
app.add_handler(CallbackQueryHandler(handle_quiz_topic_choice, pattern="^(quiz_history|quiz_science|quiz_art)$"))
app.add_handler(CallbackQueryHandler(handle_next_question, pattern="^next_question$"))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app.run_polling()

