ICONS = {
    'medicine': '💊',
    'category': '📂',
    'expiration': '📅',
    'quantity': '🔢',
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'delete': '🗑️',
    'bullet': '•',
    'separator': '═',
    'divider': '─',
}

def format_medicine_list(medicines, title="Твои лекарства"):
    if not medicines:
        return (
            f"<b>{title}</b>\n\n"
            f"<em>В твоей аптечке пока нет лекарств.</em>\n\n"
            f"Добавь первое с помощью /add"
        )
    
    message = f"<b>{title}</b>\n\n"
    message += f"<code>{ICONS['separator'] * 30}</code>\n\n"


    for med in medicines:
        #форматируеме одно лекарство
        message += format_single_medicine(med)
        message += f"<code>{ICONS['divider'] * 30}</code>\n\n"

    return message


def format_single_medicine(med):
    
    #форматируем одно лекарство для выовда в списке
     
    exp = med.get('expiration_date') or 'не указан'

    #срок годности с отметкой о просрочке
    exp_display = format_expiration_date(med.get('expiration_date'))

    return (
        f"<b>{ICONS['medicine']} {med['name']}</b>\n"
        f"  {ICONS['category']} <i>{med['category']}</i>\n"
        f"  {ICONS['expiration']} {exp_display}\n"
        f"  {ICONS['quantity']} {med['quantity']} шт."
    )


#ФОРМАТИРУЕМ СРОК ГОДНОСТИ С ОТМЕТКОЙ О ПРОСРОЧКЕ
def format_expiration_date(date_str):

    from datetime import datetime

    if not date_str:
        return '<i>не указан</i>'

    try:
        exp_date = datetime.strptime(date_str, '%Y-%m-%d')
        today = datetime.now().date()

        if exp_date.date() < today:
            #просрочено - красным
            return f'<b><u><s>{date_str}</s></u></b> ⚠️ ПРОСРОЧЕНО!'
        elif (exp_date.date() - today).days <30:
            #скоро просрочиться  желтый
            return f'<b>{date_str}</b> ⏳ скоро'
        else: 
            return date_str
    except:
        return date_str
    

#ФОРМАТИРУЕМ ПОДТВЕРЖДЕНИЕ ДОБАВЛЕНИЯ ЛЕКАРТСВА
def format_add_confirmation(name, category, expiration, quantity):
    exp_text = expiration or 'не указан'

    return (
        f"{ICONS['success']} <b>Лекарство добавлено! 🎉</b>\n\n"
        f"<b>📌 Название:</b> {name}\n"
        f"<b>{ICONS['category']} Категория:</b> {category}\n"
        f"<b>{ICONS['expiration']} Срок годности:</b> {exp_text}\n"
        f"<b>{ICONS['quantity']} Количество:</b> {quantity} шт."
    )

def format_start_message(status):
     return (
        f"<b>🐱 Мур! Это Доктор Флоп</b>\n"
        f"<i>Главный специалист по твоей домашней аптечке</i>\n\n"
        f"Чем я могу тебя помочь?\n\n"
        f"Статус: {status}\n\n"
        f"<b>📋 Доступные команды:</b>\n"
        f"/start - Показать это сообщение\n"
        f"/add - Добавить лекарство\n"
        f"/list - Показать все лекарства\n"
        f"/category - Показать лекарства по категории\n"
        f"/delete - Удалить лекарство\n"
        f"/invite - Показать код для семьи\n"
        f"/join - Присоединиться к семье"
    )