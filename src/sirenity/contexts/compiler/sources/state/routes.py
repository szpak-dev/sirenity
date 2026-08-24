from typing import Any

from pydantic import Field

from sirenity.contexts.shared import BaseState, SirenityError, SirenScope

from ..values import Resource


class RouteCatalog(BaseState):
    paths: dict[str, Any]
    source_path: str = "/"
    public_path: str = "/"
    segment_cache: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    parameter_cache: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    ownership_cache: dict[str, tuple[Resource, SirenScope]
                          | None] = Field(default_factory=dict)
    resource_cache: tuple[Resource, ...] | None = None
    single_object_paths: frozenset[str] = frozenset()

    def validate_paths(self) -> None:
        for path in self.paths:
            self.public(path)

    def public(self, path: str) -> str:
        if path.rstrip("/") == self.source_path.rstrip("/"):
            return self.public_path
        if self.source_path != "/" and not path.startswith(f"{self.source_path}/"):
            raise SirenityError(
                f"OpenAPI route {path!r} is outside configured source path {self.source_path!r}"
            )
        suffix = path if self.source_path == "/" else path[len(
            self.source_path):]
        return suffix if self.public_path == "/" else f"{self.public_path}{suffix}"

    def resources(self) -> tuple[Resource, ...]:
        if self.resource_cache is None:
            self.resource_cache = self.compile_resources()
        return self.resource_cache

    def compile_resources(self) -> tuple[Resource, ...]:
        candidates: dict[str, Resource] = {}
        names: dict[tuple[str, tuple[str, ...]], str] = {}
        for path in self.paths:
            segments = self.segments(path)
            collection_path: str | None = None
            entity_path: str | None = None
            if self.is_collection(segments) and not self.is_nested_object_operation(path):
                collection_path = path
            elif self.is_entity(segments):
                collection_path = "/" + "/".join(segments[:-1])
                entity_path = path
            if collection_path is None:
                continue
            name = self.singular(
                segments[-1] if entity_path is None else segments[-2])
            selection = name, self.parameters(collection_path)
            existing_path = names.get(selection)
            if existing_path is not None and existing_path != collection_path:
                raise SirenityError(
                    f"OpenAPI routes derive duplicate resource {name!r}: {existing_path!r} and {collection_path!r}"
                )
            names[selection] = collection_path
            existing = candidates.get(collection_path)
            if existing is None:
                candidates[collection_path] = Resource(
                    reference=collection_path,
                    name=name,
                    resource_class=name.replace("_", "-"),
                    collection_path=collection_path,
                    entity_path=entity_path,
                    identifier="id",
                    path_bindings=self.path_bindings(
                        collection_path, entity_path, "id"),
                )
            elif entity_path is not None:
                candidates[collection_path] = Resource(
                    reference=existing.reference,
                    name=existing.name,
                    resource_class=existing.resource_class,
                    collection_path=existing.collection_path,
                    entity_path=entity_path,
                    identifier=existing.identifier,
                    path_bindings=self.path_bindings(
                        existing.collection_path, entity_path, existing.identifier),
                )
        return tuple(candidates.values())

    def path_bindings(
        self, collection_path: str, entity_path: str | None, identifier: str
    ) -> dict[str, tuple[str, ...]]:
        collection_parameters = self.parameters(collection_path)
        bindings = {name: (name,) for name in collection_parameters}
        if entity_path is None:
            return bindings
        entity_parameters = self.parameters(entity_path)
        owned_parameters = tuple(
            name for name in entity_parameters if name not in collection_parameters)
        if len(owned_parameters) != 1:
            raise SirenityError(
                f"OpenAPI entity route must add exactly one resource identifier: {entity_path!r}"
            )
        owned = owned_parameters[0]
        bindings[owned] = tuple(dict.fromkeys((identifier, owned)))
        return bindings

    def is_nested_object_operation(self, path: str) -> bool:
        if path not in self.single_object_paths:
            return False
        parent_segments = self.segments(path)[:-1]
        return self.is_entity(parent_segments) and any(
            self.segments(candidate) == parent_segments for candidate in self.paths
        )

    def ownership(self, path: str) -> tuple[Resource, SirenScope] | None:
        if path in self.ownership_cache:
            return self.ownership_cache[path]
        candidates: list[tuple[int, Resource, SirenScope]] = []
        for resource in self.resources():
            if resource.entity_path and self.belongs(path, resource.entity_path):
                candidates.append(
                    (len(self.segments(resource.entity_path)), resource, SirenScope.ENTITY))
            if self.belongs(path, resource.collection_path):
                candidates.append(
                    (len(self.segments(resource.collection_path)), resource, SirenScope.COLLECTION))
        if not candidates:
            self.ownership_cache[path] = None
            return None
        longest = max(candidate[0] for candidate in candidates)
        owners = [(resource, scope) for length, resource,
                  scope in candidates if length == longest]
        if len(owners) != 1:
            raise SirenityError(
                f"OpenAPI route ownership is ambiguous: {path!r}")
        self.ownership_cache[path] = owners[0]
        return owners[0]

    def belongs(self, path: str, base: str) -> bool:
        path_segments = self.segments(path)
        base_segments = self.segments(base)
        return path_segments[: len(base_segments)] == base_segments and self.parameters(path) == self.parameters(base)

    def segments(self, path: str) -> tuple[str, ...]:
        cached = self.segment_cache.get(path)
        if cached is not None:
            return cached
        if path == "/":
            self.segment_cache[path] = ()
            return ()
        if not isinstance(path, str) or not path.startswith("/"):
            raise SirenityError(f"OpenAPI route is unsupported: {path!r}")
        normalized = path[:-1] if path.endswith("/") else path
        segments = tuple(normalized[1:].split("/"))
        if any(
            not segment or (("{" in segment or "}" in segment)
                            and not self.is_parameter(segment))
            for segment in segments
        ):
            raise SirenityError(f"OpenAPI route is unsupported: {path!r}")
        self.segment_cache[path] = segments
        return segments

    def is_collection(self, segments: tuple[str, ...]) -> bool:
        return bool(segments) and not self.is_parameter(segments[-1]) and self.is_plural(segments[-1])

    def is_entity(self, segments: tuple[str, ...]) -> bool:
        return len(segments) > 1 and self.is_parameter(segments[-1]) and self.is_plural(segments[-2])

    def is_parameter(self, segment: str) -> bool:
        return len(segment) > 2 and segment.startswith("{") and segment.endswith("}")

    def parameters(self, path: str) -> tuple[str, ...]:
        cached = self.parameter_cache.get(path)
        if cached is not None:
            return cached
        parameters = tuple(
            segment[1:-1] for segment in self.segments(path) if self.is_parameter(segment))
        self.parameter_cache[path] = parameters
        return parameters

    def is_plural(self, value: str) -> bool:
        return value.endswith("s") and len(value) > 1

    def singular(self, value: str) -> str:
        normalized = value.replace("-", "_")
        if normalized.endswith("ies"):
            return f"{normalized[:-3]}y"
        if self.is_plural(normalized):
            return normalized[:-1]
        raise SirenityError(
            f"OpenAPI collection path must be plural: {value!r}")
