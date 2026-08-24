import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from wireup import injectable

from sirenity.contexts.graph import SirenResource
from sirenity.contexts.shared import SirenityError, SirenUri

from ...request import SirenContext
from ..contracts import SirenHrefService

_PARAMETER = re.compile(r"\{([^}]+)\}")


@injectable(as_type=SirenHrefService)
@dataclass(frozen=True)
class SirenDefaultHrefService(SirenHrefService):
    def href(
        self,
        path: str,
        context: SirenContext,
        resource: SirenResource | None,
        value: Mapping[str, Any] | None = None,
        include_query: bool = True,
    ) -> SirenUri:
        properties = dict(context.value)
        properties.update(value or {})
        resolved_path = path
        for parameter in _PARAMETER.findall(path):
            path_value = context.path_values.get(parameter)
            if path_value is None:
                candidates = (parameter,) if resource is None else resource.path_bindings[parameter]
                available = tuple(
                    properties[name]
                    for name in candidates
                    if name in properties and properties[name] is not None
                )
                path_value = available[0] if available else None
            if path_value is None:
                raise SirenityError(
                    f"Siren link requires path value: {parameter}")
            resolved_path = resolved_path.replace(
                f"{{{parameter}}}", quote(str(path_value), safe=""))
        href = f"{context.base_url.rstrip('/')}{resolved_path}"
        if not include_query or not context.query:
            return SirenUri.validate(href)
        query_items = []
        for name, query_value in context.query:
            query_text = str(query_value)
            if query_value is None:
                query_text = ""
            elif isinstance(query_value, bool):
                query_text = query_text.lower()
            query_items.append(
                f"{quote(name, safe='')}={quote(query_text, safe='')}")
        return SirenUri.validate(f"{href}?{'&'.join(query_items)}")
