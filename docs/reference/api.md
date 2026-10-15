# Public API

The supported surface is generated from `sirenity.api.__all__`. Import these names from
`sirenity`; the defining modules remain implementation details.

```{eval-rst}
.. currentmodule:: sirenity.api

.. autoclass:: SirenAction
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: _serialize, model_config, validate_field_names

.. autoclass:: SirenAdapter
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config, validate_routes

.. autoclass:: SirenAdapterMatch
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenAdapterPolicy
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config, validate_capabilities

.. autoclass:: SirenAdapterProfile
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenAdapterRequest
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config, validate_request

.. autoclass:: SirenAdapterResponse
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenAllowAllPolicy
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenCapabilityPolicy
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenCompatibilityFinding
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenCompatibilityReport
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenConfiguration
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenContext
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config, validate_scope

.. autoclass:: SirenContinuation
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenContractError
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenDelegatedInput
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config, validate_transport_metadata

.. autoclass:: SirenDjangoMiddleware
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenDocument
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config, validate_action_names

.. autoclass:: SirenEmbeddedLink
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: _serialize, model_config

.. autoclass:: SirenEmbeddedRepresentation
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenField
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenFieldValue
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenFollowUp
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenInput
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenItemFollowUp
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenLink
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: _serialize, model_config

.. autoclass:: SirenMcpExecution
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenMcpExecutor
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenMcpInvocation
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenMcpOperation
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenMcpResult
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenMcpTool
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenMcpToolCatalogue
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenMiddleware
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenParameterInput
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenRelationship
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config, validate_scope

.. autoclass:: SirenResponseContext
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config, validate_response

.. autoclass:: SirenScope
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenSourceInput
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenStructuredFormProfile
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autoclass:: SirenityError
   :members:
   :undoc-members:
   :member-order: bysource
   :exclude-members: model_config

.. autofunction:: audit

.. autofunction:: siren

.. autofunction:: siren_adapter

.. autofunction:: siren_configuration

.. autofunction:: siren_follow_ups

.. autofunction:: siren_mcp

.. autofunction:: siren_pagination

```
