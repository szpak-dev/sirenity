import importlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from wireup import injectable

from sirenity.contexts.compiler import SirenApiService
from sirenity.contexts.runtime.adapter import SirenAdapter, SirenAdapterProfile, SirenCapabilityPolicy
from sirenity.contexts.runtime.adapter.values import SirenAdapterRoute
from sirenity.contexts.runtime.engine import SirenEngineFactory
from sirenity.contexts.runtime.mcp import SirenMcpToolCatalogueService
from sirenity.contexts.shared import SirenityError

from ..contracts import SirenConfigurationResolver
from ..values import SirenConfiguration, SirenConfigurationDeclaration


@injectable(as_type=SirenConfigurationResolver)
@dataclass(frozen=True)
class SirenDefaultConfigurationResolver(SirenConfigurationResolver):
    api_service: SirenApiService
    engine_factory: SirenEngineFactory
    catalogue_service: SirenMcpToolCatalogueService

    def resolve(self, declaration: SirenConfigurationDeclaration) -> SirenConfiguration:
        if not isinstance(declaration.openapi, str) or not declaration.openapi:
            raise SirenityError("Siren configuration openapi must be a dotted import path")
        if not isinstance(declaration.policy, str) or not declaration.policy:
            raise SirenityError("Siren configuration policy must be a dotted import path")
        if not isinstance(declaration.source_path, str) or not isinstance(declaration.public_path, str):
            raise SirenityError("Siren configuration source and public paths must be strings")
        if not isinstance(declaration.profiles, tuple) or any(
            not isinstance(path, str) or not path for path in declaration.profiles
        ):
            raise SirenityError("Siren configuration profiles must be a tuple of dotted import paths")
        try:
            module_name, attribute_name = declaration.openapi.rsplit(".", 1)
            openapi_source = getattr(importlib.import_module(module_name), attribute_name)
            if isinstance(openapi_source, Mapping):
                schema = openapi_source
            elif hasattr(openapi_source, "get_openapi_schema"):
                schema = openapi_source.get_openapi_schema()
            elif callable(openapi_source):
                schema = openapi_source()
            else:
                raise SirenityError("must resolve to a mapping, callable, or Ninja API")
        except Exception as error:
            raise SirenityError(f"Siren configuration openapi could not be loaded: {error}") from error
        if not isinstance(schema, Mapping):
            raise SirenityError("Siren configuration openapi did not produce an OpenAPI mapping")
        try:
            module_name, attribute_name = declaration.policy.rsplit(".", 1)
            selected_policy = getattr(importlib.import_module(module_name), attribute_name)
            if isinstance(selected_policy, type):
                selected_policy = selected_policy()
        except Exception as error:
            raise SirenityError(f"Siren configuration policy could not be loaded: {error}") from error
        if not isinstance(selected_policy, SirenCapabilityPolicy) and not callable(selected_policy):
            raise SirenityError(
                "Siren configuration policy must resolve to a SirenCapabilityPolicy or callable"
            )
        resolved_profiles: list[SirenAdapterProfile] = []
        for profile_path in declaration.profiles:
            try:
                module_name, attribute_name = profile_path.rsplit(".", 1)
                profile = getattr(importlib.import_module(module_name), attribute_name)
                resolved_profiles.append(profile() if isinstance(profile, type) else profile)
            except Exception as error:
                raise SirenityError(
                    f"Siren configuration profile could not load {profile_path!r}: {error}"
                ) from error
        try:
            document = json.loads(json.dumps(schema))
            api = self.api_service.build(document, declaration.source_path, declaration.public_path)
            engine = self.engine_factory.create(api)
            adapter = SirenAdapter(
                engine=engine,
                routes=tuple(
                    SirenAdapterRoute(
                        source_path=operation.source_path,
                        public_path=operation.route.path,
                        method=operation.method,
                        operation_id=operation.name,
                    )
                    for operation in engine.api.operations
                ),
                profiles=tuple(resolved_profiles),
            )
        except Exception as error:
            raise SirenityError(f"Siren configuration openapi could not be compiled: {error}") from error
        if not adapter.routes:
            raise SirenityError(
                "Siren configuration openapi has no registered operations; initialization may be premature"
            )
        return SirenConfiguration(
            adapter_value=adapter,
            policy=selected_policy,
            catalogue_value=self.catalogue_service.build(adapter),
        )
