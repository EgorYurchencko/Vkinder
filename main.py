"""
Основной файл для запуска бота
"""

import logging

from vk_api.longpoll import VkLongPoll, VkEventType

from vkinder import VkBot
from config import TOKEN_GROUP, CONNSTR, LOGGING_FILE

from messages import ERROR_MESSAGE_TYPE


def run_vkinder_bot():
    """
    Запуск бота
    """
    vkinder = VkBot(token=TOKEN_GROUP, connection_string=CONNSTR)
    longpoll = VkLongPoll(vkinder.session)
    logging.info("VKinder бот запущен!")

    for event in longpoll.listen():
        try:
            if (
                event.type == VkEventType.MESSAGE_NEW
                and event.to_me
                and event.from_user
            ):
                if event.text:
                    vkinder.process_message(event)
                else:
                    vkinder.send_message(event.user_id, ERROR_MESSAGE_TYPE)
        except FileNotFoundError as error:
            logging.error("Ошибка при обработке сообщения: %s", error)


if __name__ == "__main__":
    # Добавим логгирование
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(LOGGING_FILE), logging.StreamHandler()],
    )
    # Запустим бота
    run_vkinder_bot()
