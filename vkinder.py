"""
Функции для работы бота
"""
# pylint: disable = import-error, invalid-name
import logging
import time

import vk_api

from vk_api.exceptions import ApiError

import messages

from config import TOKEN_USER
from database import Saver

# Токен пользователя для поиска
VK_USER_TOKEN = TOKEN_USER


class VKinder:
    """
    Класс для поиска пользователей
    """

    def __init__(self, token):
        self.logger = logging.getLogger(__name__)
        self.session = self.get_vk_session(token)
        self.token = token

    @staticmethod
    def get_vk_session(token: str) -> vk_api.VkApi | None:
        """
        Получение сессии VK.

        Args:
            token (str): Токен пользователя

        Returns:
            Union[vk_api.VkApi, None]: Объект сессии или None при ошибке
        """
        try:
            session = vk_api.VkApi(token=token)
        except vk_api.exceptions.ApiError as error:
            logging.error("Ошибка создании сессии ВК пользователя: %s", error)
            return None
        except vk_api.exceptions.LoginRequired as error:
            logging.error("Ошибка создании сессии ВК пользователя: %s", error)
            return None
        return session

    # pylint: disable = too-many-arguments
    def search_users(
        self,
        age: int,
        gender: int,
        city: int,
        status: int,
        count: int = 15,
        offset: int = 0,
    ) -> list | None:
        """
        Поиск пользователей по заданным критериям.

        Args:
            age (int):    Возраст
            gender (int): Пол
            city (int):   Город
            status (int): Семейное положение
            count (int):  Количество пользователей (по умолчанию 50)
            offset (int): Смещение

        Returns:
            list: Список пользователей / None
        """
        api = self.session.get_api()

        try:
            users = api.users.search(
                count=count,
                age_from=age,
                age_to=age,
                sex=gender,
                city=city,
                offset=offset,
                status=status,
                fields="photo_id",
            )
        except vk_api.exceptions.ApiError as error:
            logging.error("Ошибка при поиске пользователей:  %s", error)
            return None

        return users["items"]

    def get_photo_popularity(self, photo_id: int) -> int:
        """
        Получение популярности фото.

        Args:
            photo_id (int): Идентификатор фото

        Returns:
            int: Количество лайков и комментариев
        """
        api = self.session.get_api()
        try:
            photo_data = api.photos.getById(photos=photo_id)[0]
        except vk_api.exceptions.ApiError as error:
            logging.error("Ошибка при получении информации о фото:  %s", error)
            return 0

        return photo_data["likes"]["count"] + photo_data["comments"]["count"]

    def get_top_photos(self, user_id: int, top_count: int = 3) -> list | None:
        """
        Получение топ N фото пользователя.

        Args:
            user_id (int): Идентификатор пользователя
            top_count (int): Количество фото (по умолчанию 3)

        Returns:
            list: Топ N фото
        """
        api = self.session.get_api()
        try:
            # Получаем фото пользователя
            photos = api.photos.getAll(owner_id=user_id, extended=1)
            if photos.get("count", 0) == 0:
                return None
            # Возвращаем топ n фото
            return sorted(
                photos["items"], key=lambda x: x["likes"]["count"], reverse=True
            )[:top_count]
        except vk_api.exceptions.ApiError as error:
            logging.error("Ошибка при получении фото пользователя:  %s", error)
            return None


class UserDataCache:
    """
    Класс для кэширования данных пользователей
    """

    def __init__(self):
        self.cache = {}

    def initialize_user_data(self, user_id: int, connector) -> None:
        """
        Инициализация данных пользователя при первом взаимодействии.

        Args:
            user_id (int): Идентификатор пользователя.
            connector:     Объект для работы с базой данных.
        """
        self.cache[user_id] = {
            "step": None,
            "in_db": connector.get_user_data_from_db(user_id),
            "offset": 0,
        }

    def get_user_data(self, user_id: int) -> dict:
        """
        Получение данных пользователя из кэша.

        Args:
            user_id (int): Идентификатор пользователя.

        Returns:
            dict or None: Данные пользователя или None, если пользователь не найден.
        """
        return self.cache.get(user_id)

    def save_user_data(self, user_id: int, param: str, data):
        """
        Сохранение данных пользователя в кэше.

        Args:
            user_id (int): Идентификатор пользователя.
            param (str):   Ключ данных.
            data:          Данные пользователя.
        """
        self.cache[user_id][param] = data

    def add_user_to_db(self, user_id: int, profile_id: int) -> None:
        """
        Добавление ID пользователя в базу данных.

        Args:
            user_id (int):    Идентификатор пользователя.
            profile_id (int): ID профиля.
        """
        if user_id in self.cache:
            self.cache[user_id]["in_db"].append(profile_id)


class VkBot:
    """
    Бот для группы
    """

    def __init__(self, token: str, connection_string: str):
        # Локальное сохранение данных
        self.worker_cache = UserDataCache()
        # Сохранение в базе
        self.worker_db = Saver(connection_string)

        # Объекты работы с api vk
        self.token = token
        self.session = self.get_vk_session(token)
        self.api = self.session.get_api()
        self.vkinder = VKinder(VK_USER_TOKEN)
        # Количество сохраняемых пользователей за один поиск
        self.users_in_find = 5

        # Состояния при работе с пользователем
        self.step_handlers = {
            None: self.process_age,
            "age": self.process_gender,
            "gender": self.process_city,
            "city": self.process_status,
            "status": self.process_search_users,
            "final": self.process_search_users,
            "again": self.process_age,
        }

    def send_message(
        self, user_id: int, message: str, attachments: str | None = None
    ) -> None:
        """
        Отправка сообщения пользователю.

        Args:
            user_id (int): Идентификатор пользователя.
            message (str): Сообщение.
            attachments (str, optional): Прикрепленные объекты VK. Defaults to None.
        """
        try:
            self.api.messages.send(
                user_id=user_id, message=message, attachment=attachments, random_id=0
            )
        except ApiError as error:
            logging.error("Ошибка отправки сообщения: %s", error)

    def send_profiles(self, user_id: int, profiles: list) -> None:
        """
        Отправка профилей
        Args:
            user_id (int):  ID пользователя
            profiles:       Список профилей пользователей

        """
        # Отправляем анкеты
        for profile in profiles:
            top_photos = self.vkinder.get_top_photos(profile["id"])
            attachments = ",".join(
                [f"photo{photo['owner_id']}_{photo['id']}" for photo in top_photos]
            )
            self.send_message(user_id, f"https://vk.com/id{profile['id']}", attachments)

            # Добавим задержку для ограничения контроля флуда
            time.sleep(1)

    def process_age(self, user_id: int, *_) -> str:
        """
        Обработка ввода года рождения.

        Args:
            user_id (int): Идентификатор пользователя.

        Returns:
            str: Статус пользователя в боте.
        """
        self.send_message(user_id, messages.PROCESS_AGE)
        return "age"

    def process_gender(self, user_id: int, *_) -> str:
        """
        Обработка ввода пола.

        Args:
            user_id (int): Идентификатор пользователя.

        Returns:
            str: Статус пользователя в боте.
        """
        self.send_message(user_id, messages.PROCESS_GENDER)
        return "gender"

    def process_city(self, user_id: int, *_) -> str:
        """
        Обработка ввода города.

        Args:
            user_id (int): Идентификатор пользователя.

        Returns:
            str: Статус пользователя в боте.
        """
        self.send_message(user_id, messages.PROCESS_CITY)
        return "city"

    def process_status(self, user_id: int, *_) -> str:
        """
        Обработка ввода семейного положения.

        Args:
            user_id (int): Идентификатор пользователя.

        Returns:
            str: Статус пользователя в боте.
        """
        self.send_message(user_id, messages.PROCESS_STATUS)
        return "status"

    def process_search_users(self, user_id: int, text: str, current_step: str) -> str:
        """
        Обработка поиска пользователей

        Args:
            user_id (int): Идентификатор пользователя
            text (str): Текст сообщения
            current_step (str): Текущий шаг

        Returns:
            str: Следующий шаг
        """
        data = self.worker_cache.get_user_data(user_id)

        # Если мы заполняем данные
        if current_step == "status":
            data["status"] = text

        # Иначе ищем пользователей
        age, gender, city, status = (
            data["age"],
            data["gender"],
            data["city"],
            data["status"],
        )

        users = self.vkinder.search_users(
            age, gender, city, status, offset=data["offset"]
        )

        # Найдены ли пользователи
        if users is None:
            self.send_message(user_id, messages.ERROR_TOKEN)
            return current_step
        elif not users:
            self.send_message(user_id, messages.ERROR_FIND)
            return current_step

        data["offset"] += self.users_in_find
        data["profiles"] = [
            user
            for user in users
            if not user.get("is_closed", True)
            and user["id"] not in self.worker_cache.get_user_data(user_id).get("in_db")
        ][: self.users_in_find]

        # Добавим интуитивное взаимодействие
        self.send_message(
            user_id,
            messages.PROCESS_FINAL
            if current_step == "status"
            else messages.PROCESS_NEXT_PROFILES,
        )

        self.send_profiles(user_id, data["profiles"])

        profiles_id = [profile["id"] for profile in data["profiles"]]
        # Сохраняем новые результаты в бд
        self.worker_db.save_session_to_db(user_id, profiles_id)
        # Добавим в список найденных пользователей, чтобы не обращаться заново к базе
        data["in_db"].extend(profiles_id)
        return "final"

    def process_message(self, event) -> None:
        """
        Обработка входящего сообщения.

        Args:
            event: Событие.
        """
        current_data = self.worker_cache.get_user_data(event.user_id)
        if current_data is None:
            self.worker_cache.initialize_user_data(event.user_id, self.worker_db)

            # Отправим приветствие
            greet_message = (
                messages.GREET_AGAIN
                if self.worker_cache.get_user_data(event.user_id).get("in_db")
                else messages.GREET_FIRST
            )
            self.send_message(event.user_id, greet_message)
            current_step = None
        else:
            current_step = current_data["step"]

        self.handle_current_step(event.user_id, event.text, current_step)

    def handle_current_step(self, user_id: int, text: str, current_step: str) -> None:
        """
        Обработка текущего шага бота

        Args:
            user_id (int):      Идентификатор пользователя
            text (str):         Текст сообщения
            current_step (str): Текущий шаг
        """
        if text.lower() == messages.AGAIN_SEARCH.lower():
            self.send_message(
                user_id, "\n".join([messages.GREET_AGAIN, messages.PROCESS_AGE])
            )
            self.worker_cache.get_user_data(user_id)["step"] = "age"
            return

        if current_step in self.step_handlers:
            handler = self.step_handlers[current_step]
            if self.is_valid_input(text, current_step):
                next_step = handler(user_id, text, current_step)
                self.worker_cache.get_user_data(user_id)[current_step] = text
            else:
                self.send_message(user_id, messages.ERROR_MESSAGE_DATA)
                next_step = current_step
        else:
            self.send_message(user_id, messages.ERROR_MESSAGE_DATA)
            next_step = current_step

        self.worker_cache.get_user_data(user_id)["step"] = next_step

    @staticmethod
    def get_vk_session(token: str) -> vk_api.VkApi | None:
        """
        Получение сессии VK.

        Args:
            token (str): Токен пользователя.

        Returns:
            vk_api.VkApi or None: Объект сессии VK или None при ошибке.
        """
        try:
            session = vk_api.VkApi(token=token)
        except vk_api.exceptions.ApiError as error:
            logging.error(error)
            return None
        return session

    @staticmethod
    def is_valid_input(text: str, step: str) -> bool:
        """
        Проверка корректности ввода состояния.

        Args:
            text (str): Текст сообщения.
            step (str): Шаг.

        Returns:
            bool: True, если ввод корректен, иначе False.
        """
        valid_inputs = {
            None: lambda text: True,
            "age": lambda text: text.isdigit() and (12 < int(text) < 90),
            "gender": lambda text: text in ("1", "2"),
            "city": lambda text: text.isdigit(),
            "status": lambda text: text in ("0", "1", "2", "3", "4", "5"),
            "final": lambda text: text.lower()
            in [messages.NEXT_PEOPLE.lower(), messages.AGAIN_SEARCH.lower()],
            "again": lambda text: text.lower() == messages.AGAIN_SEARCH.lower(),
        }
        return valid_inputs.get(step, lambda text: False)(text)
