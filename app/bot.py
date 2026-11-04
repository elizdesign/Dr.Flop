import os
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup #класс, представляющий собой сообщение от пользователя
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import httpx  #  НУЖНО ДЛЯ ПРОКСИ
from telegram.request import HTTPXRequest  # НУЖНО ДЛЯ ПРОКСИ


# Находим корень проекта (где лежит .env)
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(ENV_PATH)

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

from app.database import (
    get_connection, add_medicine, get_all_medicines, 
    get_categories, get_medicines_by_category, delete_medicine,
    get_user_family_id, join_family 
)
from app.formatting import (
    ICONS, format_medicine_list, format_single_medicine,
    format_add_confirmation, format_start_message
)


def setup_proxy():
    proxy_enabled = os.getenv('PROXY_ENABLED', 'False').lower() == 'true'
    
    print(f" PROXY_ENABLED: {proxy_enabled}") 
    
    if proxy_enabled:
        proxy_type = os.getenv('PROXY_TYPE', 'http')
        proxy_host = os.getenv('PROXY_HOST', 'host.docker.internal')
        proxy_port = os.getenv('PROXY_PORT', '10809')
        proxy_url = f"{proxy_type}://{proxy_host}:{proxy_port}"
        
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
        os.environ['ALL_PROXY'] = proxy_url
        
        print(f" Прокси настроен: {proxy_url}")
        return True
    
    os.environ.pop('HTTP_PROXY', None)
    os.environ.pop('HTTPS_PROXY', None)
    os.environ.pop('ALL_PROXY', None)
    
    print(" Прокси не используется (прямое соединение)")
    return False
    
def get_family(update):
    """Быстрый способ получить family_id текущего пользователя"""
    user_id = update.effective_user.id
    return get_user_family_id(user_id)


async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    family_id = get_family(update)
    await update.message.reply_text(
        f"👨‍👩‍👧‍👦 Ваш код для приглашения в семейную аптечку:\n\n"
        f"<code>{family_id}</code>\n\n"
        f"Отправьте этот код близким. Пусть они напишут боту:\n"
        f"<code>/join {family_id}</code>",
        parse_mode=ParseMode.HTML
    )

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Получаем аргументы после команды /join
    args = context.args
    if not args:
        await update.message.reply_text(" Пожалуйста, укажите код. Пример: <code>/join FAM-A1B2</code>", parse_mode=ParseMode.HTML)
        return
    
    code = args[0].upper()
    user_id = update.effective_user.id
    
    success = join_family(user_id, code)
    if success:
        await update.message.reply_text(f" Вы успешно присоединились к семейной аптечке <b>{code}</b>!", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f" Код <b>{code}</b> не найден. Проверьте правильность.", parse_mode=ParseMode.HTML)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #вызывается когда пользователь пишет start
    #async - может ждать ответа от телеграм
    #update - содержит все:кто написал, что написал, чат и т.д.
    #context - доп данные(временная информация)

    conn = get_connection()
    status = f"{ICONS['success']} Database connected" if conn else f"{ICONS['error']} Database is not available"
    if conn:
        conn.close()
    
    message = format_start_message(status)
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)

    
    #update.message — это сообщение от пользователя
    #eply_text — отправляет ответ в тот же чат

# Временное хранилище для данных пользователя
# context.user_data будет хранить состояние добавления
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"{ICONS['medicine']} <b>Введите название вашего лекарства:</b>\n"
        f"<i>Например: Парацетамол, Ношпа, Амоксициллин</i>",
        parse_mode=ParseMode.HTML
    )
    #сохраняем состояние что мы ждем название
    context.user_data['add_state'] = 'waiting_for_name'

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):

    name = update.message.text.strip()
    if not name:
        await update.message.reply_text(
            f"{ICONS['error']} <b>Ой!</b> Кажется, вы ничего не отправили.\nПопробуйте снова:",
            parse_mode=ParseMode.HTML
        )
        return
    
    #сохраняем название
    context.user_data['add_name'] = name

    #получаем список категорий
    categories = get_categories()

    if not categories:
        await update.message.reply_text(
           f"{ICONS['error']} Не удалось загрузить категории. Попробуй позже. Мур(",
            parse_mode=ParseMode.HTML
        )
        context.user_data['add_state'] = None
        return
    
    #создаем кнопки с категориями 
    keyboard = [[InlineKeyboardButton(f"{ICONS['category']} {cat}", callback_data=f"add_cat_{cat}")] for cat in categories]
    reply_markup = InlineKeyboardMarkup(keyboard)


    await update.message.reply_text(
        f"{ICONS['category']} <b>Выберите категорию:</b>",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

    #сохраяем состояние, что ждем категорию
    context.user_data['add_state'] = 'waiting_for_category'

async def add_category(update: Update, context:ContextTypes.DEFAULT_TYPE):
    #Получаем категорию, спрашиваем срок годности

    query = update.callback_query
    await query.answer() #отвечаем на нажате кнопки

    #получаем категорию из callback_data
    category = query.data.replace('add_cat_', '')
    context.user_data['add_category'] = category
    await query.edit_message_text(
        f"{ICONS['expiration']} <b>Введите срок годности</b>\n"
        f"в формате <code>ГГГГ-ММ-ДД</code>\n\n"
        f"или отправьте <i>нет</i> / <i>skip</i>, если не знаешь:\n\n"
        f"<i>Пример: 2026-12-03</i>",
        parse_mode=ParseMode.HTML
    )
    context.user_data['add_state'] = 'waiting_for_expiration'

async def add_expiration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #получаем срок годности, спрашиваем количество
    text = update.message.text.strip().lower()

    if text in ['нет', 'skip', '-']:
        expiration_date = None
    else:
        try:
            #делаем проверку: в строке должно быть 2 дефиса и она должна состоять из 10 символов
            if text.count('-') == 2 and len(text) == 10:
                expiration_date = text
            else:
                await update.message.reply_text(
                    f"{ICONS['error']} <b>Неверный формат даты</b>\n"
                    f"Используй <code>ГГГГ-ММ-ДД</code>\n"
                    f"<i>Например: 2026-12-03</i>",
                    parse_mode=ParseMode.HTML
                )
                return
        except:
            await update.message.reply_text(
                f"{ICONS['error']} <b>Неверный формат даты</b>\nПопробуй снова:",
            )
            return
        
    context.user_data['add_expiration'] = expiration_date

    await update.message.reply_text(
       f"{ICONS['quantity']} <b>Введите количество</b>\nцифрой, например: <code>10</code>",
        parse_mode=ParseMode.HTML
    )
    context.user_data['add_state'] = 'waiting_for_quantity'

async def add_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #получаем кол-во лекарст и сохраняем лекарство в БД
    try:
        quantity = int(update.message.text.strip())
        if quantity <= 0:
            await update.message.reply_text(
               f"{ICONS['error']} <b>Количество должно быть больше нуля</b>\nПопробуйте снова:",
                parse_mode=ParseMode.HTML 
            )
            return
    except ValueError:
        await update.message.reply_text(
            f"{ICONS['error']} <b>Введите число</b>\n<i>Например: 10</i>",
            parse_mode=ParseMode.HTML
        )
        return
    
    #сохраняем все данные
    name = context.user_data.get('add_name')
    category = context.user_data.get('add_category')
    expiration = context.user_data.get('add_expiration')
    
    # ПОЛУЧАЕМ ID СЕМЬИ
    family_id = get_family(update)

    #добавляем в БД (теперь передаем family_id!)
    medicine_id = add_medicine(family_id, name, category, expiration, quantity)
    
    if medicine_id:
        message = format_add_confirmation(name, category, expiration, quantity)
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(
            f"{ICONS['error']} <b>Не удалось добавить лекарство</b>\nПопробуй позже.",
            parse_mode=ParseMode.HTML
        )

    #очищаем состояния
    context.user_data['add_state'] = None
    context.user_data['add_name'] = None
    context.user_data['add_category'] = None
    context.user_data['add_expiration'] = None

#ПОКАЗ ВСЕХ ЛЕКАРСТВ

async def list_medicines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    family_id = get_family(update) # <-- Получаем ID семьи
    medicines = get_all_medicines(family_id) # <-- Передаем ID
    message = format_medicine_list(medicines, "📋 Твои лекарства")
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    

async def category_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #показывает кнопки с категориями для выбора

    categories = get_categories()

    if not categories:
        await update.message.reply_text(
            f"{ICONS['error']} Не удалось загрузить категории. Попробуй позже",
            parse_mode=ParseMode.HTML
        )
        return
    

    #добавляем кнопку "Все лекарства"
    keyboard = [[InlineKeyboardButton("📋 Все лекарства", callback_data='cat_Все')]]

    #добавляем категории
    for cat in categories:
        keyboard.append([InlineKeyboardButton(f"{ICONS['category']} {cat}", callback_data=f"cat_{cat}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"{ICONS['category']} <b>Выбери категорию:</b>",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def category_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
        #показываем лекарства по выбранной категории
    query = update.callback_query
    await query.answer()
    
    family_id = get_family(update) # <-- Получаем ID семьи
    category = query.data.replace('cat_', '')
        
    if category == "Все":
        medicines = get_all_medicines(family_id) # <-- Передаем ID
        title = "📋 Все лекарства"
    else:
        medicines = get_medicines_by_category(family_id, category) # <-- Передаем ID
        title = f"{ICONS['category']} Лекарства в категории '{category}'"

    message = format_medicine_list(medicines, title)
    await query.edit_message_text(message, parse_mode=ParseMode.HTML)
   

async def delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    family_id = get_family(update) # <-- Получаем ID семьи
    medicines = get_all_medicines(family_id) # <-- Передаем ID
    
    if not medicines:
        await update.message.reply_text(
            f"{ICONS['category']} В твоей аптечке пока нет лекарств.\nДобавь первое с помощью /add",
            parse_mode=ParseMode.HTML
        )
        return
    
    keyboard = [[InlineKeyboardButton(f"{ICONS['delete']} {med['name']} ({med['category']})", callback_data=f"del_{med['id']}")] for med in medicines]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"{ICONS['delete']} <b>Выбери лекарство для удаления:</b>\n\n<i>Нажми на кнопку с названием, чтобы удалить</i>",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    family_id = get_family(update) # <-- Получаем ID семьи
    medicine_id = int(query.data.replace('del_', ''))
    
    medicines = get_all_medicines(family_id) # <-- Передаем ID
    
    medicine_name = next((med['name'] for med in medicines if med['id'] == medicine_id), None)
    
    if not medicine_name:
        await query.edit_message_text(f"{ICONS['error']} Лекарство не найдено.", parse_mode=ParseMode.HTML)
        return
    
    context.user_data['delete_id'] = medicine_id
    
    keyboard = [
        [
            InlineKeyboardButton(f"{ICONS['success']} Да, удалить", callback_data=f"del_yes_{medicine_id}"),
            InlineKeyboardButton(f"{ICONS['error']} Нет, отменить", callback_data=f"del_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"{ICONS['warning']} <b>Ты уверена?</b>\n\nУдалить лекарство: <b>{medicine_name}</b>?\n\n<i>Это действие нельзя отменить!</i>",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def delete_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    family_id = get_family(update) # <-- Получаем ID семьи
    medicine_id = int(query.data.replace('del_yes_', ''))
    
    # Удаляем, передавая family_id (чтобы чужой не удалил)
    success = delete_medicine(family_id, medicine_id)
    
    if success:
        await query.edit_message_text(f"{ICONS['success']} <b>Лекарство успешно удалено! 🗑️</b>", parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text(f"{ICONS['error']} <b>Не удалось удалить лекарство</b>\nПопробуй позже.", parse_mode=ParseMode.HTML)
    
    context.user_data['delete_id'] = None

async def delete_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"{ICONS['success']} <b>Удаление отменено</b>", parse_mode=ParseMode.HTML)
    context.user_data['delete_id'] = None

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    state = context.user_data.get('add_state')

    if state == 'waiting_for_name':
        await add_name(update, context)
    elif state == 'waiting_for_expiration':
        await add_expiration(update, context)
    elif state == 'waiting_for_quantity':
        await add_quantity(update, context)
    else:
        #если никакого сообщения нет
        await update.message.reply_text(
            f"{ICONS['category']} <b>Я не понимаю эту команду.</b>\n\n"
            f"Используй:\n"
            f"/add - добавить лекарство\n"
            f"/list - посмотреть все\n"
            f"/category - посмотреть по категориям\n"
            f"/delete - удалить лекарство\n"
            f"/invite - показать код для семьи\n"
            f"/join - присоединиться к семье",
            parse_mode=ParseMode.HTML
        )   


# Функция, которая выполнится после инициализации бота (для установки меню команд)
async def post_init(application):
    await application.bot.set_my_commands([
        ("start", "Запустить бота"),
        ("add", "Добавить лекарство"),
        ("list", "Показать все лекарства"),
        ("category", "Показать по категориям"),
        ("delete", "Удалить лекарство"),
        ("invite", "Код для семьи"),
        ("join", "Присоединиться к семье"),
    ])


def main(): # <-- ОБЫЧНАЯ ФУНКЦИЯ
    proxy_enabled = setup_proxy()

    # Добавляем post_init в билдер
    app = ApplicationBuilder().token(TOKEN).connect_timeout(60.0).read_timeout(60.0).post_init(post_init).build()
    
    if proxy_enabled:
        print("Бот настроен с прокси")
    else:
        print("Бот настроен без прокси")

    # Когда пользователь пишет /start — вызывается функция start
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_start))
    app.add_handler(CommandHandler("list", list_medicines))
    app.add_handler(CommandHandler("category", category_start))
    app.add_handler(CommandHandler("delete", delete_start))
    app.add_handler(CommandHandler("invite", invite))
    app.add_handler(CommandHandler("join", join))

    #обработчик для кнопок(категории)
    app.add_handler(CallbackQueryHandler(add_category, pattern="^add_cat_"))
    app.add_handler(CallbackQueryHandler(category_show, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(delete_confirm, pattern="^del_[0-9]+$"))

    app.add_handler(CallbackQueryHandler(delete_yes, pattern="^del_yes_"))
    app.add_handler(CallbackQueryHandler(delete_no, pattern="^del_no$"))


    from telegram.ext import MessageHandler, filters
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))


    #запускаем бота
    print("Bot started! Press Ctrl+C to stop.")
    app.run_polling() 


if __name__ == "__main__":
    main() # <-- ПРОСТО ВЫЗОВ