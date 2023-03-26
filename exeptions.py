

class MyException(Exception):
    """Класс для своих исключений."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
