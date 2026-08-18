from .error import SirenityError


class SirenContractError(SirenityError):
    def __new__(cls, location: str, category: str, detail: str):
        return super().__new__(cls, location, category, detail)

    @property
    def location(self) -> str:
        return self.args[0]

    @property
    def category(self) -> str:
        return self.args[1]

    @property
    def detail(self) -> str:
        return self.args[2]

    def __str__(self) -> str:
        return self.detail
