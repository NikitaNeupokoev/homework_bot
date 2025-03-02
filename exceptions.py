class APIResponseError(Exception):
    """Исключение, выбрасываемое при ошибке в ответе API."""


class MessageSendError(Exception):
    """Исключение для ошибок отправки сообщения в Telegram."""


class MissingHomeworkKeyError(KeyError):
    """Исключение, выбрасываемое при отсутствии ключа 'homeworks'."""


class HomeworksNotListError(TypeError):
    """Исключение, выбрасываемое, когда 'homeworks' не список."""


class UnknownHomeworkStatusError(ValueError):
    """Исключение, когда статус домашки неизвестен."""
