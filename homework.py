import logging
import os
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('P_TOKEN')
TELEGRAM_TOKEN = os.getenv('T_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('T_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
logger.addHandler(handler)


def send_message(bot, message):
    """
    Отправляет сообщение в Telegram чат.
    Чат определяется переменной окружения TELEGRAM_CHAT_ID.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение отправлено')
    except Exception as error:
        message = f'Ошибка при отправке сообщения: {error}'
        logger.error(message)


def get_api_answer(current_timestamp):
    """
    Делаем запрос к эндпоинту API-сервиса.
    В случае успешного запроса возвращает ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        message = f'Эндпоинт API-сервиса не доступен: {error}'
        logger.error(message)

    if response.status_code != HTTPStatus.OK:
        message = 'Ошибка при запросе к основному API'
        logger.error(message)
        raise exceptions.APIResponseStatusCodeException(message)
    return response.json()


def check_response(response):
    """
    Проверяет ответ API на корректность.
    Если ответ API соответствует ожиданиям,
    то возвращает список домашних работ.
    """
    if not isinstance(response, dict):
        message = 'Response не является словарем'
        logger.error(message)
        raise TypeError(message)
    homeworks = response.get('homeworks')
    if 'homeworks' not in response or 'current_date' not in response:
        message = 'Response имеет неправильный формат'
        logger.error(message)
        raise Exception(message)
    if not isinstance(homeworks, list):
        message = 'homeworks не является списком'
        logger.error(message)
        raise TypeError(message)
    return homeworks


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    В случае успеха, функция возвращает подготовленную для отправки в Telegram
    строку, содержащую один из вердиктов словаря HOMEWORK_STATUSES.
    """
    if 'homework_name' not in homework:
        message = 'homework_name не найден в домашней работе'
        logger.error(message)
        raise KeyError(message)
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Неизвестный статус домашней работы'
        logger.error(message)
        raise exceptions.HomeworkStatusException(message)

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем доступность переменных окружения."""
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """
    Основная логика работы бота. Делает запрос к API. Проверяет ответ.
    Если есть обновления — получает статус работы из обновления и
    отправляет сообщение в Telegram. Ждет 600 сек. и сделает новый запрос.
    """
    if not check_tokens():
        message = 'Обязательные переменные окружения отсутствуют'
        logger.critical(message)
        raise SystemExit(message)

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    previous_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                message = parse_status(homework)
                if message != previous_message:
                    send_message(bot, message)
                    previous_message = message
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != previous_message:
                send_message(bot, message)
                previous_message = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
