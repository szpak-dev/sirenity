from collections.abc import Mapping

from pydantic import JsonValue

from ....shared import BaseValue
from .invocation import SirenMcpInvocation


class SirenMcpResult(BaseValue):
    structured_content: Mapping[str, JsonValue]
    is_error: bool = False
    continuations: tuple[SirenMcpInvocation, ...] = ()
