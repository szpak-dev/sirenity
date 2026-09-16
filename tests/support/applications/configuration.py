from ..contracts import ExampleContracts

EXAMPLE_BOUNDED_OPENAPI = ExampleContracts().bounded()
EXAMPLE_PAGINATION_OPENAPI = ExampleContracts().pagination()
EXAMPLE_ENTITY_OPENAPI = ExampleContracts().entity()
EXAMPLE_OPERATION_OPENAPI = ExampleContracts().operation()
EXAMPLE_CROSS_OPERATION_BOUNDED_OPENAPI = ExampleContracts().cross_operation_bounded()
EXAMPLE_INVALID_OPENAPI = ExampleContracts().bounded()
EXAMPLE_INVALID_OPENAPI["components"]["schemas"]["ExampleJobState"]["required"].remove("has_more")
