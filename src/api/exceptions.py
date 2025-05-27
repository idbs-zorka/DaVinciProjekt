class APIError(IOError):
    """
    Wyjątek reprezentujący błąd specyficzny dla API GIOŚ.

    Zawiera szczegółowe informacje o błędzie zwróconym przez API:
    - kod błędu (`code`),
    - przyczyna (`reason`),
    - wynik (`result`),
    - możliwe rozwiązanie (`solution`).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)

        self.code = kwargs["code"]
        self.reason = kwargs["reason"]
        self.result = kwargs["result"]
        self.solution = kwargs["solution"]

    def __str__(self):
        return f"API Error [{self.code}]: {self.reason} {self.result} {self.solution}"
