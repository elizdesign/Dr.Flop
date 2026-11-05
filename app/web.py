from flask import Flask, render_template, request
from app.database import get_all_medicines

app = Flask(__name__)

@app.route('/')
def index():
    # Получаем код семьи из адресной строки
    # Если код не указан, показываем пустую страницу с просьбой ввести код
    family_id = request.args.get('family', '')
    
    medicines = []
    if family_id:
        medicines = get_all_medicines(family_id)
        
    return render_template('index.html', medicines=medicines, family_id=family_id)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)