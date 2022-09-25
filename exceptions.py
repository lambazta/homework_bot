class MissingRequiredTokenException(Exception):
    def __init__(self, text):
        self.txt = text


class APIResponseStatusCodeException(Exception):
    def __init__(self, text):
        self.txt = text


class HomeworkStatusException(Exception):
    def __init__(self, text):
        self.txt = text


class HomeworkNameException(Exception):
    def __init__(self, text):
        self.txt = text
