from pydantic import Field

from ....shared import BaseValue, SirenHttpMethod, SirenMediaType, SirenScope
from .field import SirenField
from .input import SirenInput
from .response import SirenResponse
from .route import SirenRoute


class SirenOperation(BaseValue):
    name: str
    resource: str = ""
    scope: SirenScope
    method: SirenHttpMethod
    route: SirenRoute
    source_path: str
    title: str
    description: str
    media_type: SirenMediaType = Field(default_factory=SirenMediaType.default)
    fields: tuple[SirenField, ...] = ()
    input: SirenInput = Field(default_factory=SirenInput)
    responses: tuple[SirenResponse, ...] = ()
