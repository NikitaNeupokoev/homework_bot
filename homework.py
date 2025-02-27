import logging
import os
import time

from dotenv import load_dotenv
import requests
from telebot import TeleBot

from exceptions import (
    MissingTokenError,  # Токен отсутствует - критическая ошибка

    APIResponseError,  # Ошибка при запросе к API

    HomeworksNotListError,  # Неправильный формат ответа API
    MissingHomeworkKeyError,  # Отсутствует ключ в данных API
    UnknownHomeworkStatusError,  # Неизвестный статус домашки
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
    filename='homework.log'
)
logger = logging.getLogger(__name__)
stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    required_tokens = {
        "PRACTICUM_TOKEN": PRACTICUM_TOKEN,
        "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    }

    for token_name, token_value in required_tokens.items():
        if not token_value:
            logger.critical(
                f"Отсутствует переменная окружения {token_name}."
            )
            raise MissingTokenError(
                f"Отсутствует переменная окружения {token_name}."
            )

    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(
            f'Сообщение отправлено: {message}'
        )
    except Exception as e:
        logger.error(
            f'Не удалось отправить сообщение: {e}'
        )


def get_api_answer(timestamp):
    """Делает запрос к API сервиса."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code != 200:
            raise APIResponseError(
                f"API вернул код ответа {response.status_code}"
            )

        return response.json()
    except requests.RequestException as e:
        logger.error(
            f'Ошибка при запросе к API: {e}'
        )
        raise APIResponseError(
            f"Ошибка при запросе к API: {e}"
        ) from e


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise HomeworksNotListError(
            'Ответ API не является словарем'
        )

    homeworks = response.get('homeworks')
    if homeworks is None:
        raise MissingHomeworkKeyError(
            'В ответе API отсутствует ключ "homeworks"'
        )

    if not isinstance(homeworks, list):
        raise HomeworksNotListError(
            'Значение ключа "homeworks" не является списком'
        )

    return response


def parse_status(homework):
    """Извлекает статус работы и возвращает подготовленную строку."""
    if homework.get(
        'homework_name'
    ) is None or homework.get('status') is None:
        missing_key = 'homework_name' if homework.get(
            'homework_name'
        ) is None else 'status'
        logger.error(
            f"Отсутствует ключ в homework: {missing_key}"
        )
        raise MissingHomeworkKeyError(
            f"Отсутствует ключ в homework: {missing_key}"
        )

    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))

    if verdict is None:
        logger.error(
            f'Неизвестный статус работы: {homework.get("status")}'
        )
        raise UnknownHomeworkStatusError(
            f"Неизвестный статус работы: {homework.get('status')}"
        )

    return (
        f'Изменился статус проверки работы "{homework.get("homework_name")}". '
        f'{verdict}'
    )


def main():
    """Основная логика работы бота."""
    try:
        check_tokens()
    except MissingTokenError as e:
        logger.critical(f"Необходимый токен отсутствует: {e}")
        exit()

    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            api_answer = get_api_answer(timestamp)
            response = check_response(api_answer)
            homeworks = response['homeworks']

            if homeworks:
                for homework in homeworks:
                    try:
                        status = parse_status(homework)
                        send_message(bot, status)
                    except Exception as e:
                        logger.error(f"Ошибка при обработке статуса: {e}")

            else:
                logger.debug('Нет новых статусов.')

            timestamp = api_answer.get('current_date', timestamp)

        except Exception as e:
            logger.exception(f'Сбой в работе: {e}')

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
