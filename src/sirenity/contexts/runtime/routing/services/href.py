from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal
from urllib.parse import quote

from pydantic import JsonValue
from wireup import injectable

from ....graph import SirenResource
from ....shared import SirenityError, SirenUri
from ... import SirenContext
from ..contracts.href import SirenHrefService


@injectable(as_type=SirenHrefService)
@dataclass(frozen=True)
class SirenDefaultHrefService(SirenHrefService):
    def href(
        self,
        path: str,
        context: SirenContext,
        resource: SirenResource | Literal[""],
        value: Mapping[str, JsonValue],
        include_query: bool,
    ) -> SirenUri:
        properties = dict(context.value)
        properties.update(value or {})
        resolved_path = path
        for parameter in (
            segment[1:-1] for segment in path.split("/") if segment.startswith("{") and segment.endswith("}")
        ):
            path_value = context.path_values.get(parameter)
            if path_value is None:
                candidates = (parameter,) if not resource else resource.path_bindings[parameter]
                available = tuple(
                    properties[name] for name in candidates if name in properties and properties[name] is not None
                )
                path_value = available[0] if available else None
            if path_value is None:
                raise SirenityError(f"Siren link requires path value: {parameter}")
            resolved_path = resolved_path.replace(f"{{{parameter}}}", quote(str(path_value), safe=""))
        href = f"{context.base_url.rstrip('/')}{resolved_path}"
        if not include_query or not context.query:
            return SirenUri.validate(href)
        query_items = []
        for name, query_value in context.query:
            query_text = str(query_value)
            if query_value is None:
                query_text = ""
            elif query_value is True or query_value is False:
                query_text = str(query_value).lower()
            query_items.append(f"{quote(name, safe='')}={quote(query_text, safe='')}")
        return SirenUri.validate(f"{href}?{'&'.join(query_items)}")
