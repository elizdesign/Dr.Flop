from flask import Flask, render_template, request
from app.database import get_all_medicines, get_categories, get_medicines_by_category

app = Flask(__name__)

@app.route('/')
@app.route('/<family_id>')
def index(family_id=None):
    # Если семья не указана в пути, пробуем взять из параметров (для обратной совместимости)
    if not family_id:
        family_id = request.args.get('family', '')

    # Получаем параметры поиска и фильтрации
    search_query = request.args.get('search', '').strip()
    selected_category = request.args.get('category', '')

    medicines = []
    categories = []

    if family_id:
        categories = get_categories()
        
        # Логика фильтрации
        if search_query:
            # Если есть поиск, фильтруем по названию
            all_meds = get_all_medicines(family_id)
            medicines = [m for m in all_meds if search_query.lower() in m['name'].lower()]
        elif selected_category:
            # Если выбрана категория
            medicines = get_medicines_by_category(family_id, selected_category)
        else:
            # Иначе показываем все
            medicines = get_all_medicines(family_id)

    return render_template(
        'index.html', 
        medicines=medicines, 
        categories=categories,
        family_id=family_id,
        selected_category=selected_category,
        search_query=search_query
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)