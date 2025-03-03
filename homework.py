import http
import logging
import os
import sys
import time

import requests
from dotenv import load_dotenv
import telebot
from telebot import TeleBot

from exceptions import (
    APIConnectionError,
    APIResponseError,
    HomeworksNotListError,
    JSONDecodeError,
    MessageSendError,
    MissingHomeworkKeyError,
    UnknownHomeworkStatusError,
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

logger = logging.getLogger(__name__)


def setup_logger():
    """Настраивает логирование."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
        filename='homework.log'
    )
    logger.addHandler(
        logging.StreamHandler(sys.stdout)
    )


def check_tokens():
    """Проверяет доступность переменных окружения."""
    required_tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }

    missing_tokens = [
        token_name for token_name,
        token_value in required_tokens.items() if not token_value
    ]

    if missing_tokens:
        logger.critical(
            'Отсутствуют переменные окружения: %s',
            ', '.join(missing_tokens)
        )
        return False

    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    logger.debug(
        f'Начинаем отправку сообщения: {message}'
    )
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug(
            f'Сообщение отправлено: {message}'
        )
    except (
        telebot.apihelper.ApiException,
        requests.RequestException
    ) as e:
        raise MessageSendError(
            f'Не удалось отправить сообщение: {e}'
        )


def get_api_answer(timestamp):
    """Делает запрос к API сервиса."""
    request_kwargs = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }

    try:
        response = requests.get(**request_kwargs)
    except requests.ConnectionError as e:
        log_message = (
            f'Ошибка соединения с API: {e}. '
            f'Параметры запроса: {request_kwargs}'
        )
        logger.debug(log_message)
        raise APIConnectionError(log_message) from e
    except requests.RequestException as e:
        log_message = (
            f'Ошибка при запросе к API: {e}. '
            f'Параметры запроса: {request_kwargs}'
        )
        logger.debug(log_message)
        raise APIResponseError(log_message) from e

    if response.status_code != http.HTTPStatus.OK:
        log_message = (
            f'API вернул код ответа {response.status_code}. '
            f'Параметры запроса: {request_kwargs}'
        )
        logger.debug(log_message)
        raise APIResponseError(log_message)

    try:
        return response.json()
    except ValueError as e:
        log_message = (
            f'Ошибка при декодировании JSON: {e}. '
            f'Параметры запроса: {request_kwargs}'
        )
        logger.debug(log_message)
        raise JSONDecodeError(log_message) from e


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(
            'Ответ API не является словарем.'
        )

    if 'homeworks' not in response:
        raise MissingHomeworkKeyError(
            'В ответе API отсутствует ключ "homeworks".'
        )

    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise HomeworksNotListError(
            'Значение ключа "homeworks" не является списком.'
        )


def parse_status(homework):
    """Извлекает статус работы и возвращает подготовленную строку."""
    if 'homework_name' not in homework:
        logger.debug(
            'Отсутствует ключ "homework_name" в homework.'
        )
        raise MissingHomeworkKeyError(
            'Отсутствует ключ "homework_name" в homework.'
        )

    if 'status' not in homework:
        logger.debug(
            'Отсутствует ключ "status" в homework.'
        )
        raise MissingHomeworkKeyError(
            'Отсутствует ключ "status" в homework.'
        )

    homework_name = homework['homework_name']
    status = homework['status']

    if status not in HOMEWORK_VERDICTS:
        logger.debug(
            f'Неизвестный статус работы: {status}'
        )
        raise UnknownHomeworkStatusError(
            f'Неизвестный статус работы: {status}'
        )

    verdict = HOMEWORK_VERDICTS[status]

    return (
        f'Изменился статус проверки работы "{homework_name}".'
        f'{verdict}'
    )


def handle_api_request(timestamp):
    """Обрабатывает запрос к API, получает и проверяет ответ."""
    check_response(get_api_answer(timestamp))
    return get_api_answer(timestamp)


def handle_homework(bot, homework, last_status):
    """Обрабатывает домашнюю работу и возвращает новый статус.
    если он изменился.
    """
    status = parse_status(homework)
    if status != last_status:
        send_message(bot, status)
        return status


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(
            'Необходимые токены отсутствуют. Завершение работы.'
        )
        sys.exit(1)

    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = None

    while True:
        try:
            response = handle_api_request(timestamp)
            homeworks = response.get('homeworks', [])

            if homeworks:
                last_message = handle_homework(
                    bot,
                    homeworks[0],
                    last_message
                )
            else:
                logger.debug('Нет новых статусов.')

            timestamp = response.get('current_date', timestamp)

        except Exception as e:
            logger.exception(
                f'Сбой в работе: {e}'
            )
            try:
                send_message(
                    bot,
                    f'Сбой в работе: {e}'
                )
            except Exception as telegram_error:
                logger.error(
                    f'Не удалось отправить сообщение об ошибке в Telegram:'
                    f'{telegram_error}'
                )
            last_message = str(e)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    setup_logger()
    main()
