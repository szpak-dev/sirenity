# Django integration

## `SirenMiddleware`

Install Siren through Django's standard middleware loader.

The loader consumes an exact immutable ``SirenConfiguration`` or turns the current ``SIRENITY``
mapping into one, then installs middleware from that same configuration. Resolved settings
declarations remain fresh for each Django startup, autoreload process, and ``override_settings``
lifecycle; a supplied configuration retains its caller-owned adapter lifecycle. ``OPENAPI`` and
``POLICY`` are dotted import paths; ``PROFILES`` is an optional sequence of profile paths. A
missing policy retains the standard allow-all behavior.

Django Ninja consumers can declare Siren relationships on the source operation with the native
``openapi_extra`` argument. Add the standard OpenAPI Link Object beneath the generated response,
bind target path parameters from the response body, and declare the Siren relation and scope:

```python
@api.get(
    "/api/example_groups/{example_group_id}",
    description="Read an example group.",
    operation_id="get_example_group",
    response=ExampleGroup,
    summary="Read example group",
    openapi_extra={
        "responses": {
            200: {
                "links": {
                    "example_resources": {
                        "operationId": "list_example_group_resources",
                        "parameters": {
                            "path.example_group_id": "$response.body#/example_group_id",
                        },
                        "x-sirenity": {"rel": "collection", "scope": "collection"},
                    }
                }
            }
        }
    },
)
def get_example_group(request, example_group_id: str):
    return {"example_group_id": example_group_id}
```

Django Ninja merges this declaration into its generated response without an OpenAPI wrapper or
post-processing provider. Middleware construction validates the operation target, path bindings,
runtime expression, relation, and scope while compiling that generated document. The declared
relationship therefore needs no application Siren policy solely to appear in the representation.
