from dataclasses import dataclass

from wireup import injectable

from ....runtime.document import (
    SirenAction,
    SirenDocument,
    SirenEmbeddedLink,
    SirenEmbeddedRepresentation,
    SirenField,
    SirenFieldValue,
    SirenLink,
)
from ..contracts.source import SirenContractSource
from ..values.capability import SirenCapability
from .exporter import SirenSerializationSchemaExporter


@injectable(as_type=SirenContractSource)
@dataclass(frozen=True)
class SirenDocumentContractSource(SirenContractSource):
    exporter: SirenSerializationSchemaExporter

    def capabilities(self) -> tuple[SirenCapability, ...]:
        return (
            self.exporter.export("Action", SirenAction),
            self.exporter.export("Entity", SirenDocument),
            self.exporter.export("EmbeddedLinkSubEntity", SirenEmbeddedLink),
            self.exporter.export("EmbeddedRepresentationSubEntity", SirenEmbeddedRepresentation),
            self.exporter.export("Field", SirenField),
            self.exporter.export("FieldValueObject", SirenFieldValue),
            self.exporter.export("Link", SirenLink),
        )
