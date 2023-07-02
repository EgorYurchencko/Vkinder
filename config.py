"""
Получение переменных для бота
"""

import sys
import configparser


config = configparser.ConfigParser()

# Проверяем файл
if len(config.read("settings.ini")) == 0:
    print("Создайте файл setings.ini")
    sys.exit(1)

# Получение значений из файла конфигурации
try:
    TOKEN_USER = config.get("tokens", "user_token")
    TOKEN_GROUP = config.get("tokens", "group_token")
    LOGGING_FILE = config.get("logging", "logging_file")
    CONNSTR = config.get("database", "connstr")
except configparser.NoOptionError as error:
    print(f"Добавьте поле: {error}")
    sys.exit(1)
