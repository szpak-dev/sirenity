from dataclasses import dataclass

from wireup import injectable

from sirenity.contexts.shared import SirenityError

from ..contracts import SirenContractSource, SirenImplementation
from ..values import SirenCapability


@injectable(as_type=SirenImplementation)
@dataclass(frozen=True)
class PydanticSirenImplementation(SirenImplementation):
    source: SirenContractSource

    def capabilities(self) -> tuple[SirenCapability, ...]:
        capabilities = self.source.capabilities()
        definitions = {capability.definition for capability in capabilities}
        if len(definitions) != len(capabilities):
            message = "Siren contract sources must provide unique official definitions."
            raise SirenityError(message)
        return capabilities
