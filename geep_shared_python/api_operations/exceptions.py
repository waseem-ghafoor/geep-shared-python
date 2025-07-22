class ApiRequestException(Exception):
    """Exception raised when creating a dialogue fails."""

    def __init__(
        self, message: str = "Failed to persist bot or human turns in dialogue service."
    ):
        self.message = message
        super().__init__(self.message)
