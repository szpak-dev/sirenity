from functools import partial
from types import MappingProxyType

from ..contexts.compiler.compatibility import SirenCompatibilityFinding, SirenCompatibilityReport
from ..contexts.graph import SirenDelegatedInput, SirenInput, SirenParameterInput
from ..contexts.runtime.adapter import (
    SirenAdapter,
    SirenAdapterMatch,
    SirenAdapterPolicy,
    SirenAdapterProfile,
    SirenAdapterRequest,
    SirenAdapterResponse,
    SirenAllowAllPolicy,
    SirenCapabilityPolicy,
    SirenDjangoMiddleware,
    SirenStructuredFormProfile,
)
from ..contexts.runtime.document import (
    SirenAction,
    SirenDocument,
    SirenEmbeddedLink,
    SirenEmbeddedRepresentation,
    SirenField,
    SirenFieldValue,
    SirenLink,
)
from ..contexts.runtime.mcp import (
    SirenMcpExecution,
    SirenMcpExecutor,
    SirenMcpInvocation,
    SirenMcpOperation,
    SirenMcpResult,
    SirenMcpTool,
    SirenMcpToolCatalogue,
)
from ..contexts.runtime.request import SirenContext, SirenRelationship, SirenResponseContext
from ..contexts.shared import SirenContractError, SirenityError, SirenScope
from . import adapter, configuration, django, follow_up, siren
from .audit import audit
from .configuration import SirenConfiguration
from .django import SirenContinuation, SirenMiddleware
from .follow_up import SirenFollowUp
from .mcp import siren_mcp
from .source_input import SirenSourceInput

siren_adapter = partial(adapter.siren_adapter, source_path="/", public_path="/", profiles=())
siren_configuration = partial(configuration.siren_configuration, source_path="/", public_path="/", profiles=())
siren_pagination = partial(django.siren_pagination, source_inputs=MappingProxyType({}), status=200)
siren_follow_ups = partial(follow_up.siren_follow_ups, status=200)
siren = partial(siren.siren, source_path="/", public_path="/")

siren_adapter.__doc__ = adapter.siren_adapter.__doc__
siren_adapter.__module__ = adapter.siren_adapter.__module__
siren_configuration.__doc__ = configuration.siren_configuration.__doc__
siren_configuration.__module__ = configuration.siren_configuration.__module__
siren_pagination.__doc__ = django.siren_pagination.__doc__
siren_pagination.__module__ = django.siren_pagination.__module__
siren_follow_ups.__doc__ = follow_up.siren_follow_ups.__doc__
siren_follow_ups.__module__ = django.__name__
siren.__doc__ = siren.func.__doc__
siren.__module__ = siren.func.__module__

__all__ = [
    "SirenAction",
    "SirenAdapter",
    "SirenAdapterMatch",
    "SirenAdapterPolicy",
    "SirenAdapterProfile",
    "SirenAdapterRequest",
    "SirenAdapterResponse",
    "SirenAllowAllPolicy",
    "SirenCapabilityPolicy",
    "SirenCompatibilityFinding",
    "SirenCompatibilityReport",
    "SirenConfiguration",
    "SirenContext",
    "SirenContinuation",
    "SirenContractError",
    "SirenDelegatedInput",
    "SirenDjangoMiddleware",
    "SirenDocument",
    "SirenEmbeddedLink",
    "SirenEmbeddedRepresentation",
    "SirenField",
    "SirenFieldValue",
    "SirenFollowUp",
    "SirenInput",
    "SirenLink",
    "SirenMcpExecution",
    "SirenMcpExecutor",
    "SirenMcpInvocation",
    "SirenMcpOperation",
    "SirenMcpResult",
    "SirenMcpTool",
    "SirenMcpToolCatalogue",
    "SirenMiddleware",
    "SirenParameterInput",
    "SirenRelationship",
    "SirenResponseContext",
    "SirenScope",
    "SirenSourceInput",
    "SirenStructuredFormProfile",
    "SirenityError",
    "audit",
    "siren",
    "siren_adapter",
    "siren_configuration",
    "siren_follow_ups",
    "siren_mcp",
    "siren_pagination",
]
