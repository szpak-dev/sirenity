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
        findings: list[SirenCompatibilityFinding] = []
        info = schema.get("info")
        if not isinstance(info, dict):
            findings.append(SirenCompatibilityFinding(
                location="#/info",
                category="metadata",
                detail="OpenAPI schema requires an object-valued info field",
                remediation="Provide an info object with non-empty title and version.",
            ))
        else:
            for member in ("title", "version"):
                value = info.get(member)
                if not isinstance(value, str) or not value:
                    findings.append(SirenCompatibilityFinding(
                        location=f"#/info/{member}",
                        category="metadata",
                        detail=f"OpenAPI info requires a non-empty {member}",
                        remediation=f"Provide a non-empty info.{member} value.",
                    ))
        paths = schema.get("paths")
        if not isinstance(paths, dict):
            return (*findings,
                SirenCompatibilityFinding(
                    location="#/paths",
                    category="route",
                    detail="OpenAPI schema requires an object-valued paths field",
                    remediation="Use an object-valued paths field.",
                ))
        components = ComponentResolver(components=schema.get("components", {}))
        responses = OpenApiResponseProjection(components=components)
        return (*findings, *OpenApiCompatibilityInspection(
            components=components,
            projection=OpenApiFieldProjection(components=components),
            responses=responses,
            routes=RouteCatalog(paths=paths),
        ).inspect())

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
        info = schema.get("info")
        if not isinstance(info, dict):
            raise SirenityError("OpenAPI schema requires an object-valued info field")
        title = info.get("title")
        version = info.get("version")
        if not isinstance(title, str) or not title:
            raise SirenityError("OpenAPI info requires a non-empty title")
        if not isinstance(version, str) or not version:
            raise SirenityError("OpenAPI info requires a non-empty version")
        assembly = SirenAssembly().set_root(
            path=public_path,
            title=title,
            version=version,
        )
        for resource in routes.resources():
            assembly.add_resource(
                reference=resource.reference,
                name=resource.name,
                resource_class=resource.resource_class,
                collection_path=routes.public(resource.collection_path),
                path_bindings=resource.path_bindings,
                entity_path=(
                    routes.public(resource.entity_path)
                    if resource.entity_path else None
                ),
                identifier=resource.identifier,
            )
        OpenApiOperationCompiler(
            assembly=assembly,
            routes=routes,
            components=components,
            projection=OpenApiFieldProjection(components=components),
            responses=responses,
        ).compile()
        return self.builder.build(assembly)
