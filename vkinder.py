from random import randrange
from datetime import datetime
import vk_api
import sqlite3
from vk_api.longpoll import VkLongPoll, VkEventType
from Token import TOKEN

# Функция для отправки сообщений
def write_msg(user_id, message):
    vk.method('messages.send', {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7)})

# Функция для подключения к базе данных
def connect_to_database():
    conn = sqlite3.connect('vkinder.db')
    return conn

# Функция для создания таблицы в базе данных, если она не существует
def create_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            age INTEGER,
            sex INTEGER,
            city TEXT,
            relation INTEGER,
            photo TEXT,
            popularity INTEGER
        )
    ''')
    conn.commit()

# Функция для сохранения пользователя в базу данных
def save_user_to_database(conn, user):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (id, first_name, last_name, age, sex, city, relation, photo, popularity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user['id'],
        user['first_name'],
        user['last_name'],
        user['age'],
        user['sex'],
        user['city'],
        user['relation'],
        user['photo'],
        user['popularity']
    ))
    conn.commit()

# Функция для получения информации о пользователе из VK
def get_user_info(user_id):
    user = vk.method('users.get', {'user_ids': user_id, 'fields': 'bdate,sex,city,relation'})
    if user:
        user = user[0]
        age = None
        if 'bdate' in user:
            # Вычисляем возраст пользователя на основе даты рождения
            if 'bdate' in user:
                birthdate = user['bdate'].split('.')
                if len(birthdate) == 3:
                    age = calculate_age(int(birthdate[2]), int(birthdate[1]), int(birthdate[0]))
            else:
                age = None
        return {
            'id': user['id'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'age': age,
            'sex': user['sex'],
            'city': user.get('city', {}).get('title'),
            'relation': user.get('relation')
        }
    return None

# Функция для вычисления возраста
def calculate_age(birth_year, birth_month, birth_day):
    current_year = datetime.now().year
    current_month = datetime.now().month
    current_day = datetime.now().day
    age = current_year - birth_year
    if current_month < birth_month or (current_month == birth_month and current_day < birth_day):
        age -= 1
    return age

# Функция для поиска подходящих пользователей
def find_matching_users(user_info):
    search_params = {
        'count': 10,  # Количество найденных пользователей
        'fields': 'photo_max_orig',  # Запрашиваем только ссылку на основную фотографию профиля
        'sex': 1 if user_info['sex'] == 2 else 2,  # Инвертируем пол для поиска пары
        'city': user_info['city'],
        'status': user_info['relation'],  # Семейное положение
        'age_from': user_info['age'] - 5,  # Минимальный возраст - 5 лет меньше, чем у пользователя
        'age_to': user_info['age'] + 5,  # Максимальный возраст - 5 лет больше, чем у пользователя
    }

    search_result = vk.method('users.search', search_params)

    matching_users = []
    for user in search_result['items']:
        matching_users.append({
            'id': user['id'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'photo': user.get('photo_max_orig', '')
        })

    return matching_users

# Функция для определения популярности пользователей
def calculate_user_popularity(user_id):
    # Получение информации о фотографиях пользователя
    photos = vk.method('photos.get', {'owner_id': user_id, 'album_id': 'profile', 'extended': 1})

    # Сортировка фотографий по убыванию количества лайков
    sorted_photos = sorted(photos['items'], key=lambda x: x['likes']['count'], reverse=True)

    # Получение топ-3 популярных фотографий
    top_photos = sorted_photos[:3]

    # Отправка фотографий пользователю
    for photo in top_photos:
        write_msg(user_id, f"Фотография: {photo['sizes'][-1]['url']}")

    # Вычисление общей популярности пользователя на основе лайков и комментариев
    popularity = sum(photo['likes']['count'] + photo['comments']['count'] for photo in photos['items'])

    return popularity

# Получение токена от пользователя
token = input('Token: ')


# Авторизация VK API
vk = vk_api.VkApi(token=token)
longpoll = VkLongPoll(vk)

# Подключение к базе данных
conn = connect_to_database()

# Создание таблицы, если она не существует
create_table(conn)

# Главный цикл бота
for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW:
        if event.to_me:
            request = event.text
            if request == "привет":
                write_msg(event.user_id, f"Хай, {event.user_id}")
            elif request == "пока":
                write_msg(event.user_id, "Пока((")
            else:
                # Получение информации о пользователе
                user_info = get_user_info(request)
                if user_info:
                    matching_users = find_matching_users(user_info)
                    for user in matching_users:
                        popularity = calculate_user_popularity(user['id'])
                        if popularity > 0:
                            # Сохранение пользователя в базу данных
                            user['popularity'] = popularity
                            save_user_to_database(conn, user)

                            write_msg(event.user_id, f"Топ-3 популярных фотографий профиля пользователя {user['first_name']} {user['last_name']} (ID: {user['id']}):")
                            for photo in top_photos:
                                write_msg(event.user_id, f"Фотография: {photo['sizes'][-1]['url']}")
                            write_msg(event.user_id, f"Ссылка на профиль: https://vk.com/id{user['id']}")
                        else:
                            write_msg(event.user_id, "Нет доступных фотографий или профиль пользователя не популярен.")
                else:
                    write_msg(event.user_id, "Пользователь не найден")

# Закрытие соединения с базой данных
conn.close()
