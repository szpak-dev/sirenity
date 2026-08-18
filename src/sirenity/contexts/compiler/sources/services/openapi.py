from dataclasses import dataclass
from typing import Any

from wireup import injectable

from sirenity.contexts.graph import SirenApi
from sirenity.contexts.shared import SirenityError

from ...compatibility import SirenCompatibilityFinding
from ..contracts import SirenSource
from ..state import (
    ComponentResolver,
    OpenApiCompatibilityInspection,
    OpenApiFieldProjection,
    OpenApiResponseProjection,
    RouteCatalog,
)
from ..state.assembly import SirenAssembly
from ..state.compiler import OpenApiOperationCompiler
from .builder import SirenBuilder


@injectable(as_type=SirenSource)
@dataclass(frozen=True)
class OpenApiSource(SirenSource):
    builder: SirenBuilder

    def audit(self, schema: dict[str, Any]) -> tuple[SirenCompatibilityFinding, ...]:
        paths = schema.get("paths")
        if not isinstance(paths, dict):
            return (
                SirenCompatibilityFinding(
                    location="#/paths",
                    category="route",
                    detail="OpenAPI schema requires an object-valued paths field",
                    remediation="Use an object-valued paths field.",
                ),
            )
        components = ComponentResolver(components=schema.get("components", {}))
        responses = OpenApiResponseProjection(components=components)
        return OpenApiCompatibilityInspection(
            components=components,
            projection=OpenApiFieldProjection(components=components),
            responses=responses,
            routes=RouteCatalog(paths=paths),
        ).inspect()

    def load(self, schema: dict[str, Any], source_path: str, public_path: str) -> SirenApi:
        paths = schema.get("paths")
        if not isinstance(paths, dict):
            raise SirenityError(
                "OpenAPI schema requires an object-valued paths field")
        components = ComponentResolver(components=schema.get("components", {}))
        responses = OpenApiResponseProjection(components=components)
        routes = RouteCatalog(
            paths=paths,
            source_path=source_path,
            public_path=public_path,
            single_object_paths=responses.single_object_paths(paths),
        )
        routes.validate_paths()
        info = schema.get("info", {})
        assembly = SirenAssembly().set_root(
            path=public_path,
            title=str(info.get("title", "")) if isinstance(info, dict) else "",
            version=str(info.get("version", "")) if isinstance(
                info, dict) else "",
        )
        for resource in routes.resources():
            assembly.add_resource(
                resource.reference,
                resource.name,
                resource.resource_class,
                routes.public(resource.collection_path),
                routes.public(
                    resource.entity_path) if resource.entity_path else None,
                resource.identifier,
            )
        OpenApiOperationCompiler(
            assembly=assembly,
            routes=routes,
            components=components,
            projection=OpenApiFieldProjection(components=components),
            responses=responses,
        ).compile()
        return self.builder.build(assembly)
