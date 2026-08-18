from sirenity.contexts.shared import BaseValue, SirenHttpMethod, SirenMediaType, SirenScope

from .field import SirenField
from .input import SirenInput
from .response import SirenResponse
from .route import SirenRoute


class SirenOperation(BaseValue):
    name: str
    resource: str | None = None
    scope: SirenScope
    method: SirenHttpMethod
    route: SirenRoute
    source_path: str
    title: str
    description: str
    media_type: SirenMediaType | None = None
    fields: tuple[SirenField, ...] = ()
    input: SirenInput | None = None
    responses: tuple[SirenResponse, ...] = ()
