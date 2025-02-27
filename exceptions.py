class APIResponseError(Exception):
    """Исключение, выбрасываемое при ошибке в ответе API."""

    pass


class MissingHomeworkKeyError(KeyError):
    """Исключение, выбрасываемое при отсутствии ключа 'homeworks'."""

    pass


class HomeworksNotListError(TypeError):
    """Исключение, выбрасываемое, когда 'homeworks' не список."""

    pass


class MissingTokenError(Exception):
    """Исключение, когда отсутствует обязательный токен."""

    pass


class UnknownHomeworkStatusError(ValueError):
    """Исключение, когда статус домашки неизвестен."""

    pass
