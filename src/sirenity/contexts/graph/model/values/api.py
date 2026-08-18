from pydantic import Field, model_validator

from sirenity.contexts.shared import BaseValue, SirenityError, SirenScope

from .operation import SirenOperation
from .resource import SirenResource
from .root import SirenRoot


class SirenApi(BaseValue):
    root: SirenRoot = Field(default_factory=SirenRoot)
    resources: tuple[SirenResource, ...] = ()
    operations: tuple[SirenOperation, ...] = ()

    @model_validator(mode="after")
    def validate_graph(self) -> "SirenApi":
        resource_references = tuple(
            resource.reference for resource in self.resources)
        operation_names = tuple(
            operation.name for operation in self.operations)
        if len(resource_references) != len(set(resource_references)):
            raise SirenityError("Siren resource references must be unique")
        if len(operation_names) != len(set(operation_names)):
            raise SirenityError("Siren operation names must be unique")
        unknown = {
            operation
            for resource in self.resources
            for operation in (*resource.collection_operations, *resource.entity_operations)
            if operation not in operation_names
        }
        if unknown:
            raise SirenityError(
                f"Siren resources reference unknown operations: {sorted(unknown)}")
        unknown_root_operations = sorted(
            set(self.root.operations) - set(operation_names))
        if unknown_root_operations:
            raise SirenityError(
                f"Siren root references unknown operations: {unknown_root_operations}")
        resource_references_set = set(resource_references)
        unknown_resources = sorted(
            {
                operation.resource
                for operation in self.operations
                if operation.resource is not None and operation.resource not in resource_references_set
            }
        )
        if unknown_resources:
            raise SirenityError(
                f"Siren operations reference unknown resources: {unknown_resources}")
        resources = {
            resource.reference: resource for resource in self.resources}
        unowned = []
        for operation in self.operations:
            if operation.scope == SirenScope.ROOT:
                if operation.resource is not None or operation.name not in self.root.operations:
                    unowned.append(operation.name)
            elif operation.resource is None or operation.name not in (
                resources[operation.resource].collection_operations
                if operation.scope == SirenScope.COLLECTION
                else resources[operation.resource].entity_operations
            ):
                unowned.append(operation.name)
        if unowned:
            raise SirenityError(
                f"Siren operations are not owned by their declared resource scope: {unowned}")
        return self
