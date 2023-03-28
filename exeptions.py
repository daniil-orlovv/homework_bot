class MyRequestsException(Exception):
    """Класс для своих исключений."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class MyBotHTTPError(Exception):
    """Исключение, которое возникает при ошибках HTTP."""

    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

    def __str__(self):
        return f"{self.status_code}: {self.message}"
