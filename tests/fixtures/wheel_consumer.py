import sirenity
from sirenity import SirenContext, siren

schema = {
    "openapi": "3.1.1",
    "info": {"title": "Consumer", "version": "1"},
    "paths": {
        "/example_resources": {
            "get": {
                "operationId": "list_example_resources",
                "summary": "List example resources",
                "description": "List example resources.",
                "responses": {"200": {"description": "OK"}},
            }
        }
    },
}
context = SirenContext(
    base_url="https://api.example.com",
    scope="collection",
    resource="example_resource",
    capabilities=frozenset({"list_example_resources"}),
)
document = siren(schema).project(context).model_dump(by_alias=True, mode="json", exclude_none=True)

assert document["links"] == [{"rel": ["self"], "href": "https://api.example.com/example_resources"}]
print(sirenity.__file__)
