import os #for work with OS. it's let to read env
import psycopg2 #for work with postgresql
from psycopg2 import OperationalError #cach errors
from dotenv import load_dotenv #save data form env


load_dotenv() #load all variables to memory. now we can use them

def get_connection():
    try:
        conn = psycopg2.connect(
            host = os.getenv('DB_HOST'),
            port = os.getenv('DB_PORT'),
            dbname = os.getenv('DB_NAME'),
            user = os.getenv('DB_USER'),
            password = os.getenv('DB_PASSWORD')
        )
        print("Connection to PostgreSQL is successfully")

        return conn
    
    except OperationalError as e:
        print(f"Error of connection: {e}")

        return None
    

def create_tables():
    
    conn = get_connection()

    #check connectiion
    if not conn:
        return #just left
    
    #курсор как ручка, которой мы пишем запросы в БД
    cursor = conn.cursor()

    ##таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id BIGINT PRIMARY KEY,
            family_id VARCHAR(50) NOT NULL
        );
    """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS medicines (
                        id SERIAL PRIMARY KEY,
                        family_id VARCHAR(50) NOT NULL,
                        name VARCHAR(200) NOT NULL,
                        category VARCHAR(100) NOT NULL,
                        expiration_date DATE,
                        quantity INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
                   """)
    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS categories (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL
                   );
                    """)
    
    cursor.execute("""
        INSERT INTO categories (name)
        VALUES
            ('Ухо/Горло/Нос'),
            ('Обезболивающие'),
            ('ЖКТ'),
            ('Антигистаминные'),
            ('Сердечно-сосудистые'),
            ('Раны/Ожоги'),
            ('Мазь'),
            ('Другое')
        ON CONFLICT (name) DO NOTHING;
                   """)
     
    conn.commit() #сохраняем все изменения в БД
    cursor.close() #освобождаем ресурсы
    conn.close() #закрываем подключение к БД
    print("Tables created/updated!")

   
    
def add_medicine(family_id, name, category, expiration_date=None, quantity=1):
    conn = get_connection()
    if not conn:
        return None
    
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO medicines(family_id, name, category, expiration_date, quantity)
            VALUES (%s, %s, %s, %s, %s) 
            RETURNING id;
        """, (family_id, name, category, expiration_date, quantity))

        medicine_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Лекарство '{name}' добавлено с ID {medicine_id} (семья: {family_id})")
        return medicine_id
    
    except Exception as e:
        print(f"Ошибка при добавлении лекарства: {e}")
        conn.rollback() #откатываем изменения
        cursor.close()
        conn.close()
        return None
    
def delete_medicine(family_id, medicine_id):

    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()

    #получаем название для отчета
    try:
        # Проверяем, что лекарство принадлежит этой семье, и получаем его название
        cursor.execute("SELECT name FROM medicines WHERE id = %s AND family_id = %s;", (medicine_id, family_id))
        result = cursor.fetchone() # извлекает ровно одну строку из БД

        if not result:
            cursor.close()
            conn.close()
            return False 
        
        medicine_name = result[0]
        
        cursor.execute("DELETE from medicines WHERE id = %s AND family_id = %s;", (medicine_id, family_id))
        conn.commit()
        cursor.close()
        conn.close()


        print(f"Лекарство '{medicine_name}' (ID: {medicine_id}) удалено")
        return True

    except Exception as e:
        print(f"ОШибка при удалении лекарства: {e}")
        conn.rollback()
        cursor.close()
        conn.close()
        return False
    
def get_all_medicines(family_id):

    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, name, category, expiration_date, quantity, created_at
            FROM medicines
            WHERE family_id = %s
            ORDER BY name;
             """, (family_id,))
        
        #получаем все записи
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        medicines = []
        for row in rows:
            medicines.append({
                'id' : row[0],
                'name' : row[1],
                'category' : row[2],
                'expiration_date': row[3],
                'quantity': row[4],
                'created_at': row[5]
            })
        return medicines
    
    except Exception as e:
        print(f"Ошибка при получении списка лекарств {e}")
        cursor.close()
        conn.close()
        return []
    
def get_medicines_by_category(family_id, category):
    conn = get_connection()
    if not conn:
        return []
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, name, category, expiration_date, quantity, created_at
            FROM medicines
            WHERE family_id = %s AND category = %s
            ORDER BY name;
        """, (family_id, category))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        medicines = []
        for row in rows:
             medicines.append({
                'id': row[0],
                'name': row[1],
                'category': row[2],
                'expiration_date': row[3],
                'quantity': row[4],
                'created_at': row[5]
            })
        return medicines
    except Exception as e:
        print(f"Ошибка при получении лекарств по категории: {e}")
        cursor.close()
        conn.close()
        return []
    
def get_categories():

    conn =get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT name FROM categories ORDER BY name;
        """)

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        #преобразуем в список строк
        categories = [row[0] for row in rows]
        return categories
    
    except Exception as e:
        print(f"Ошибка при получении категории: {e}")
        cursor.close()
        conn.close()
        return []


def get_user_family_id(telegram_id):
    """Возвращает family_id пользователя. Если его нет, создает новый."""
    conn = get_connection()
    if not conn:
        return None
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT family_id FROM users WHERE telegram_id = %s;", (telegram_id,))
        result = cursor.fetchone()
        
        if result:
            # Пользователь уже есть
            return result[0]
        else:
            # Новый пользователь! Генерируем ему код семьи
            import random
            import string
            # Генерируем что-то вроде "FAM-A1B2"
            family_id = "FAM-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            
            cursor.execute(
                "INSERT INTO users (telegram_id, family_id) VALUES (%s, %s);",
                (telegram_id, family_id)
            )
            conn.commit()
            return family_id
    except Exception as e:
        print(f"Ошибка при получении пользователя: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def join_family(telegram_id, family_id):
    """Привязывает пользователя к существующей семье."""
    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    try:
        # Проверяем, существует ли такая семья (есть ли в ней хоть одно лекарство или пользователь)
        # Для простоты проверяем, есть ли такой family_id у кого-то из пользователей
        cursor.execute("SELECT 1 FROM users WHERE family_id = %s LIMIT 1;", (family_id,))
        if not cursor.fetchone():
            return False # Такой семьи нет
            
        # Обновляем пользователя
        cursor.execute(
            "UPDATE users SET family_id = %s WHERE telegram_id = %s;",
            (family_id, telegram_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка при присоединении к семье: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

    

if __name__ == "__main__":
    create_tables()
    print("Database ready for work")