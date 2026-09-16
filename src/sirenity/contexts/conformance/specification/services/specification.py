from dataclasses import dataclass

from wireup import injectable

from ....shared.siren_schema import SirenSchemaReader
from ..contracts.specification import SirenSpecification
from ..values.requirement import SirenRequirement


@injectable(as_type=SirenSpecification)
@dataclass(frozen=True)
class SirenSchemaSpecification(SirenSpecification):
    schemas: SirenSchemaReader

    def requirements(self) -> tuple[SirenRequirement, ...]:
        document = self.schemas.document()
        definitions = (("Entity", document.value), *document.definitions().items())
        requirements: tuple[SirenRequirement, ...] = ()
        for name, definition in definitions:
            effective = document.effective(definition)
            for member, member_schema in effective.get("properties", {}).items():
                requirement = SirenRequirement(
                    definition=name,
                    member=member,
                    schema=member_schema,
                    required=member in effective.get("required", ()),
                    document=document.value,
                )
                requirements += (requirement,)
                for value in member_schema.get("enum", []):
                    requirements += (
                        SirenRequirement(
                            definition=name,
                            member=member,
                            schema=member_schema,
                            required=requirement.required,
                            document=document.value,
                            enum_value=value,
                        ),
                    )
        return requirements
