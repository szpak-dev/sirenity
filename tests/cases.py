from .support.contracts import ExampleContracts


class SirenityCase:
    contracts: ExampleContracts

    def setup_method(self) -> None:
        self.contracts = ExampleContracts()


class OpenApiCase(SirenityCase):
    pass


class CompilationCase(OpenApiCase):
    pass


class ProjectionCase(OpenApiCase):
    pass


class AdapterCase(OpenApiCase):
    pass


class AuditCase(OpenApiCase):
    pass


class ConfiguredCase(OpenApiCase):
    pass


class DjangoCase(ConfiguredCase):
    pass


class McpCase(ConfiguredCase):
    pass


class DistributionCase(SirenityCase):
    pass
