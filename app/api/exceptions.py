
class APIError(IOError):
    def __init__(self, *args,**kwargs):
        super().__init__(args, kwargs)

        self.code = kwargs["code"]
        self.reason = kwargs["reason"]
        self.result = kwargs["result"]
        self.solution = kwargs["solution"]


    def __str__(self):
        return f"API Error [{self.code}]: {self.reason} {self.result} {self.solution}"