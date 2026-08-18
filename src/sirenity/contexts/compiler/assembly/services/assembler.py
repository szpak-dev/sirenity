from dataclasses import dataclass

from wireup import injectable

from sirenity.contexts.graph import SirenApi, SirenOperation, SirenResource, SirenRoot
from sirenity.contexts.shared import SirenityError

from ..contracts import SirenApiAssembler


@injectable(as_type=SirenApiAssembler)
@dataclass(frozen=True)
class SirenDefaultApiAssembler(SirenApiAssembler):
    def assemble(self, apis: tuple[SirenApi, ...]) -> SirenApi:
        root = SirenRoot()
        resources: dict[str, SirenResource] = {}
        operations: dict[str, SirenOperation] = {}
        for api in apis:
            root = self.merge_root(root, api.root)
            for resource in api.resources:
                resources[resource.reference] = self.merge_resource(
                    resources.get(resource.reference), resource)
            for operation in api.operations:
                operations[operation.name] = self.merge_operation(
                    operations.get(operation.name), operation)
        return SirenApi(root=root, resources=tuple(resources.values()), operations=tuple(operations.values()))

    def merge_root(self, existing: SirenRoot, incoming: SirenRoot) -> SirenRoot:
        if incoming == SirenRoot():
            return existing
        if existing != SirenRoot() and (
            existing.route != incoming.route or existing.title != incoming.title or existing.version != incoming.version
        ):
            raise SirenityError("Siren sources define conflicting roots")
        return incoming.model_copy(
            update={"operations": tuple(dict.fromkeys(
                (*existing.operations, *incoming.operations)))}
        )

    def merge_resource(self, existing: SirenResource | None, incoming: SirenResource) -> SirenResource:
        if existing is None:
            return incoming
        if (
            existing.name != incoming.name
            or existing.reference != incoming.reference
            or existing.resource_class != incoming.resource_class
            or existing.identifier != incoming.identifier
            or existing.collection != incoming.collection
            or existing.entity != incoming.entity
        ):
            raise SirenityError(
                f"Siren sources define conflicting resource: {existing.reference}")
        return existing.model_copy(
            update={
                "collection_operations": tuple(
                    dict.fromkeys((*existing.collection_operations,
                                  *incoming.collection_operations))
                ),
                "entity_operations": tuple(dict.fromkeys((*existing.entity_operations, *incoming.entity_operations))),
            }
        )

    def merge_operation(self, existing: SirenOperation | None, incoming: SirenOperation) -> SirenOperation:
        if existing is None or existing == incoming:
            return incoming
        raise SirenityError(
            f"Siren sources define conflicting operation: {incoming.name}")
