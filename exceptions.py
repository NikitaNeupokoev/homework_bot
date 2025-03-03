class APIConnectionError(Exception):
    """Ошибка соединения с API."""


class APIResponseError(Exception):
    """Ошибка ответа API."""


class HomeworksNotListError(TypeError):
    """Исключение, выбрасываемое, когда 'homeworks' не список."""


class JSONDecodeError(Exception):
    """Ошибка декодирования JSON."""


class MessageSendError(Exception):
    """Исключение для ошибок отправки сообщения в Telegram."""


class MissingHomeworkKeyError(KeyError):
    """Исключение, выбрасываемое при отсутствии ключа 'homeworks'."""


class UnknownHomeworkStatusError(ValueError):
    """Исключение, когда статус домашки неизвестен."""
