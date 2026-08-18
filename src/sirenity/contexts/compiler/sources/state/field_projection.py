from typing import Any, Literal

from sirenity.contexts.shared import BaseState, SirenFieldType, SirenityError

from ..values import Field
from .components import ComponentResolver


class OpenApiFieldProjection(BaseState):
    components: ComponentResolver

    def delegated_kind(
        self, name: str, schema: dict[str, Any]
    ) -> Literal["array", "object", "json"] | None:
        try:
            definition = self.definition(name, schema)
        except SirenityError:
            definition = self.components.schema(schema)
            for keyword in ("anyOf", "oneOf"):
                variants = definition.get(keyword)
                if variants is not None:
                    if not isinstance(variants, list) or not variants:
                        return None
                    kinds = tuple(
                        self.delegated_kind(name, variant) if isinstance(
                            variant, dict) else None
                        for variant in variants
                    )
                    if any(kind is None for kind in kinds):
                        return None
                    return kinds[0] if len(set(kinds)) == 1 else "json"
            return None
        schema_type = definition.get("type")
        if schema_type == "object":
            properties = definition.get("properties")
            additional = definition.get("additionalProperties", True)
            if properties is not None and not isinstance(properties, dict):
                raise SirenityError(
                    f"OpenAPI field schema is unsupported: {name}")
            if not isinstance(additional, (bool, dict)):
                raise SirenityError(
                    f"OpenAPI field schema is unsupported: {name}")
            if not (isinstance(properties, dict) and properties) and (
                additional is True or additional == {}
            ):
                return "json"
            return "object"
        if schema_type == "array":
            return None if self.values(name, definition) else "array"
        return None

    def field(self, name: str, schema: dict[str, Any]) -> Field:
        definition = self.definition(name, schema)
        values = self.values(name, definition)
        field_type = self.type(name, definition, values)
        title = definition.get("title")
        default = definition.get("default")
        if title is not None and not isinstance(title, str):
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        if isinstance(default, bool):
            if definition.get("type") != "boolean":
                raise SirenityError(
                    f"OpenAPI field schema is unsupported: {name}")
            default = None
        elif default is not None and not isinstance(default, (str, int, float)):
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        if values and default is not None and default not in values:
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        return Field(name=name, type=field_type, values=values, title=title, default=default)

    def definition(self, name: str, schema: dict[str, Any]) -> dict[str, Any]:
        definition = self.components.schema(schema)
        definition = self.all_of(name, definition)
        definition = self.scalar_composition(name, definition, "oneOf")
        definition = self.scalar_composition(name, definition, "anyOf")
        schema_type = definition.get("type")
        if isinstance(schema_type, list):
            values = [value for value in schema_type if value != "null"]
            if len(values) != 1 or len(values) + 1 != len(schema_type) or not isinstance(values[0], str):
                raise SirenityError(
                    f"OpenAPI field schema is unsupported: {name}")
            definition = {**definition, "type": values[0], "nullable": True}
        return definition

    def all_of(self, name: str, definition: dict[str, Any]) -> dict[str, Any]:
        variants = definition.get("allOf")
        if variants is None:
            return definition
        if not isinstance(variants, list) or not variants:
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        merged = {key: value for key, value in definition.items()
                  if key != "allOf"}
        for variant in variants:
            if not isinstance(variant, dict):
                raise SirenityError(
                    f"OpenAPI field schema is unsupported: {name}")
            for key, value in self.definition(name, variant).items():
                existing = merged.get(key)
                if key in merged and existing != value:
                    raise SirenityError(
                        f"OpenAPI field schema is unsupported: {name}")
                merged[key] = value
        return merged

    def scalar_composition(self, name: str, definition: dict[str, Any], keyword: str) -> dict[str, Any]:
        variants = definition.get(keyword)
        if variants is None:
            return definition
        if not isinstance(variants, list):
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        scalar = [variant for variant in variants if isinstance(
            variant, dict) and variant.get("type") != "null"]
        nulls = [variant for variant in variants if isinstance(
            variant, dict) and variant.get("type") == "null"]
        if len(scalar) != 1 or len(nulls) + len(scalar) != len(variants):
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        normalized = self.definition(name, scalar[0])
        outer = {key: value for key, value in definition.items()
                 if key != keyword}
        for key, value in outer.items():
            if key in normalized and normalized[key] != value:
                raise SirenityError(
                    f"OpenAPI field schema is unsupported: {name}")
        return {**normalized, **outer, "nullable": bool(nulls) or normalized.get("nullable") is True}

    def values(self, name: str, definition: dict[str, Any]) -> tuple[str | int | float, ...]:
        source = definition.get("enum")
        if source is None and definition.get("type") == "array":
            items = definition.get("items")
            if not isinstance(items, dict):
                raise SirenityError(
                    f"OpenAPI field schema is unsupported: {name}")
            source = self.definition(name, items).get("enum")
        if source is None:
            return ()
        if not isinstance(source, list):
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        values = tuple(value for value in source if value is not None)
        if not values or any(isinstance(value, bool) or not isinstance(value, (str, int, float)) for value in values):
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        return values

    def type(self, name: str, definition: dict[str, Any], values: tuple[str | int | float, ...]) -> SirenFieldType:
        unsupported = {"const", "contains", "if", "not", "prefixItems"}
        if unsupported & definition.keys():
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        schema_type = definition.get("type")
        if schema_type == "array":
            items = definition.get("items")
            if not isinstance(items, dict):
                raise SirenityError(
                    f"OpenAPI field schema is unsupported: {name}")
            item_definition = self.definition(name, items)
            if item_definition.get("type") == "array":
                raise SirenityError(
                    f"OpenAPI field schema is unsupported: {name}")
            self.type(name, item_definition, ())
            if values:
                return SirenFieldType.validate("checkbox")
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        if values:
            return SirenFieldType.validate("radio")
        if schema_type == "string":
            formats = {
                None: SirenFieldType.default(),
                "date": SirenFieldType.validate("date"),
                "date-time": SirenFieldType.validate("datetime-local"),
                "email": SirenFieldType.validate("email"),
                "time": SirenFieldType.validate("time"),
                "uri": SirenFieldType.validate("url"),
                "uuid": SirenFieldType.default(),
            }
            field_type = formats.get(definition.get("format"))
            if field_type is not None:
                return field_type
        if schema_type in {"integer", "number"}:
            return SirenFieldType.validate("number")
        if schema_type == "boolean":
            return SirenFieldType.validate("checkbox")
        raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
