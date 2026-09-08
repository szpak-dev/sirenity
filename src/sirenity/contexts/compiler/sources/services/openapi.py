from dataclasses import dataclass
from typing import Any

from wireup import injectable

from sirenity.contexts.shared import SirenityError

from ...compatibility import SirenCompatibilityFinding, SirenCompilation, SirenDiagnostics
from ..contracts import SirenSource
from ..state import (
    ComponentResolver,
    OpenApiFieldProjection,
    OpenApiResponseProjection,
    RouteCatalog,
)
from ..state.compiler import OpenApiOperationCompiler
from ..values import NormalizedOpenApi
from .builder import SirenBuilder


@injectable(as_type=SirenSource)
@dataclass(frozen=True)
class OpenApiSource(SirenSource):
    builder: SirenBuilder

    def compile(
        self, schema: dict[str, Any], source_path: str, public_path: str
    ) -> SirenCompilation | SirenDiagnostics:
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
            findings.append(SirenCompatibilityFinding(
                    location="#/paths",
                    category="route",
                    detail="OpenAPI schema requires an object-valued paths field",
                    remediation="Use an object-valued paths field.",
            ))
            return SirenDiagnostics(findings=tuple(findings))
        components = ComponentResolver(components=schema.get("components", {}))
        responses = OpenApiResponseProjection(components=components)
        routes = RouteCatalog(
            paths=paths,
            source_path=source_path,
            public_path=public_path,
            single_object_paths=responses.single_object_paths(paths),
        )
        compiler = OpenApiOperationCompiler(
            routes=routes,
            components=components,
            projection=OpenApiFieldProjection(components=components),
            responses=responses,
        )
        findings.extend(compiler.compile())
        try:
            routes.validate_paths()
            resources = tuple(
                resource.model_copy(update={
                    "collection_path": routes.public(resource.collection_path),
                    "entity_path": (
                        routes.public(resource.entity_path)
                        if resource.entity_path else None
                    ),
                })
                for resource in routes.resources()
            )
        except (SirenityError, ValueError) as error:
            findings.append(SirenCompatibilityFinding(
                location="#/paths",
                category="route",
                detail=str(error),
                remediation="Use valid, unambiguous routes within the configured source path.",
            ))
            resources = ()
        if findings:
            return SirenDiagnostics(findings=tuple(findings))
        assert isinstance(info, dict)
        title = info["title"]
        version = info["version"]
        assert isinstance(title, str)
        assert isinstance(version, str)
        normalized = NormalizedOpenApi(
            root_path=public_path,
            root_title=title,
            root_version=version,
            resources=resources,
            operations=tuple(compiler.operations),
            root_operations=tuple(compiler.root_operations),
        )
        try:
            return SirenCompilation(api=self.builder.build(normalized))
        except (SirenityError, ValueError) as error:
            return SirenDiagnostics(findings=(SirenCompatibilityFinding(
                location="#",
                category="graph",
                detail=str(error),
                remediation="Correct the conflicting normalized OpenAPI declarations.",
            ),))
