from ..contracts import ExampleContracts


class ExampleCollectionCommandOpenApi:
    def get_openapi_schema(self) -> dict[str, object]:
        return ExampleContracts().collection_command()


EXAMPLE_BOUNDED_OPENAPI = ExampleContracts().bounded()
EXAMPLE_PAGINATION_OPENAPI = ExampleContracts().explicit_pagination()
EXAMPLE_ITEM_FOLLOW_UPS_OPENAPI = ExampleContracts().item_follow_ups()
EXAMPLE_ENTITY_OPENAPI = ExampleContracts().entity()
EXAMPLE_OPERATION_OPENAPI = ExampleContracts().operation()
EXAMPLE_CREATION_VERIFICATION_OPENAPI = ExampleContracts().creation_verification()
EXAMPLE_COLLECTION_COMMAND_OPENAPI = ExampleCollectionCommandOpenApi()
EXAMPLE_UNSUPPORTED_VERIFICATION_OPENAPI = ExampleContracts().unsupported_verification()
EXAMPLE_VERIFICATION_OPENAPI = ExampleContracts().verification()
EXAMPLE_FOLLOW_UPS_OPENAPI = ExampleContracts().follow_ups()
EXAMPLE_PROJECT_FOLLOW_UPS_OPENAPI = ExampleContracts().project_follow_ups()
EXAMPLE_SINGLE_FOLLOW_UP_OPENAPI = ExampleContracts().single_follow_up()
EXAMPLE_UNSUPPORTED_FOLLOW_UP_OPENAPI = ExampleContracts().unsupported_follow_up()
EXAMPLE_REQUIRED_QUERY_FOLLOW_UP_OPENAPI = ExampleContracts().required_query_follow_up()
EXAMPLE_CROSS_OPERATION_BOUNDED_OPENAPI = ExampleContracts().cross_operation_bounded()
EXAMPLE_INVALID_OPENAPI = ExampleContracts().bounded()
EXAMPLE_INVALID_OPENAPI["components"]["schemas"]["ExampleJobState"]["required"].remove("has_more")
