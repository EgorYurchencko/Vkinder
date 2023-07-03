"""
Файл с сообщениями, которые отправляет бот
"""

# Приветствие
GREET_FIRST = (
    "Я VKinder, бот для поиска интересных людей.\n"
    "Следуя инструкции, введите информацию."
)
GREET_AGAIN = "Давай попробуем снова найти твою половинку!"

# Команды
NEXT_PEOPLE = "Дальше"
AGAIN_SEARCH = "Заново"

# Ввод данных для пунктов
ALREADY_FILLED = "Вы уже указали информацию о"
ERROR_INCOMPLETE_PROFILE = "Не все поля заполнены"
PROCESS_AGE = "Укажите возраст:"
PROCESS_GENDER = "Укажите пол\n(1 - женщина, 2 - мужчина):"
PROCESS_CITY = (
    "Укажите ID города\n"
    "Пример - (1 - Москва, 2 - Санкт-Петербург,"
    " 158 - Владивосток):"
)
PROCESS_STATUS = (
    "Укажите семейное положение:\n0 - не указано\n1 - не женат/не замужем\n2 - встречается\n"
    "3 - помолвлен/помолвлена\n4 - женат/замужем\n5 - всё сложно:"
)
PROCESS_FINAL = 'Вот эти люди могут тебя заинтересовать!\n' \
                f'Пиши "{NEXT_PEOPLE}" для выдачи анкет или "{AGAIN_SEARCH}" для повторного поиска'
PROCESS_NEXT_PROFILES = 'Окей, вот еще найденные люди:\n'
TRY_AGAIN = "Давай попробуем заново!"
NO_MORE_PROFILES = f'Больше анкет нет. Хочешь еще? Напиши "{AGAIN_SEARCH}"'


# Ошибки
ERROR_SESSION = "К сожалению, не удалось получить сессию ВКонтакте." \
                " Пожалуйста, предоставьте токен доступа."
ERROR_MESSAGE_TYPE = "Принимаются только текстовые сообщения"
ERROR_MESSAGE_DATA = "Введены некорректные данные. Пожалуйста, повторите ввод."
ERROR_TOKEN = "Ошибка при работе с API. Обратитесь к администратору."
ERROR_FIND = "Пользователи не найдены."
ERROR_OTHER = "Произошла ошибка. Пожалуйста, начните сначала."
