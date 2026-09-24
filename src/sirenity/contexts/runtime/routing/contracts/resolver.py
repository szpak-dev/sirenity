from abc import ABC, abstractmethod

from ....graph import SirenApi, SirenResource
from ....shared import SirenityError
from ... import SirenContext


class SirenResourceResolver(ABC):
    @abstractmethod
    def resolve(self, api: SirenApi, context: SirenContext) -> SirenResource:
        raise SirenityError
