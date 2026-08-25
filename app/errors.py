class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ToolFailure(Exception):
    def __init__(self, code: str, retryable: bool = False, response: dict | None = None):
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.response = response

