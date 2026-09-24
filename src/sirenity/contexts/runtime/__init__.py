from importlib import import_module
from typing import Any, ClassVar


class _RuntimeExports:
    modules: ClassVar[dict[str, str]] = {
        "SirenAction": ".document.values.action",
        "SirenCapabilityValidator": ".capabilities.contracts.validator",
        "SirenContext": ".request.values.context",
        "SirenDocument": ".document.values.document",
        "SirenEmbeddedRepresentation": ".document.values.embedded_representation",
        "SirenEngine": ".engine.engine",
        "SirenField": ".document.values.field",
        "SirenFieldValue": ".document.values.field_value",
        "SirenHrefService": ".routing.contracts.href",
        "SirenLink": ".document.values.link",
        "SirenProjectedNavigation": ".projection.values.navigation",
        "SirenProjectionService": ".projection.services.projection",
        "SirenRelationship": ".request.values.relationship",
        "SirenResourceResolver": ".routing.contracts.resolver",
        "SirenResponseContext": ".request.values.response",
        "SirenResponseProjectionService": ".projection.services.response",
    }
    aliases: ClassVar[dict[str, tuple[str, str]]] = {
        "SirenDocumentField": (".document.values.field", "SirenField")
    }

    def __call__(self, name: str) -> Any:
        module_name, attribute = self.aliases.get(name, (self.modules.get(name), name))
        module = import_module(module_name, __name__)
        value = getattr(module, attribute)
        globals()[name] = value
        return value


__getattr__ = _RuntimeExports()

__all__ = sorted(_RuntimeExports.modules | _RuntimeExports.aliases)
