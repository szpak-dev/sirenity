# Current architecture

This is the as-is architecture baseline for Sirenity before structural cleanup. The canonical boundary configuration
lives in Enclosure; this document records what Modwire resolves from that configuration and the current source tree.
It does not duplicate the configuration or define the target design.

## Provenance

- Enclosure configuration revision: `f084f59ae0e673fcb2a29ddb9a5b962ca4f5070a23d8e1a30da731f62f7e7918`.
- Modwire inspected 275 Python source files and left zero files unknown. These are coverage counts, not configured limits.
- The shape report is empty under the project-wide zero-functions and strict-optionality policy.
- The flow report retains 95 findings: 52 backward-flow edges and 43 module-boundary edges.
- The cycle and re-entry analyzers report no findings.

## Resolved ownership

```text
compiler
├── assembly
├── compatibility
└── sources

conformance
├── implementation
├── ledger
└── specification

graph
└── model

runtime
├── adapter
├── capabilities
├── configuration
├── document
├── engine
├── mcp
├── projection
├── request
└── routing

shared
├── foundation
├── siren_schema
└── vocabulary
```

The remaining top-level ownership boundaries are `public-api`, `package-entrypoint`, `autowiring`,
`contexts-entrypoint`, `generated`, `tests`, and `tooling`.

## Boundary findings

The 43 module-boundary findings fall into six concrete seams:

| Edges | Dependency | Finding |
| ---: | --- | --- |
| 34 | `tests/**` → `src/sirenity/__init__.py` | Tests consume the supported root package, while the test rule names only the internal `public-api` package. This is a configuration-versus-public-entrypoint ambiguity. |
| 3 | `src/sirenity/api/{audit,configuration,siren}.py` → `src/sirenity/wiring.py` | Public functions reach into composition to obtain services. Target design must decide whether composition supplies the public API or remains an allowed dependency. |
| 2 | `src/sirenity/api/{audit,siren}.py` → `src/sirenity/contexts/compiler/document.py` | Public API bypasses the compiler context facade for document normalization. |
| 2 | `scripts/{check_service_conventions,siren_spec}.py` → `src/sirenity/wiring.py` | Repository tooling intentionally inspects or uses composition, but the tooling rule currently exposes only the public API. |
| 1 | `src/sirenity/contexts/compiler/document.py` → `src/sirenity/contexts/shared/__init__.py` | Context-root compiler code consumes the shared facade without a matching source rule. |
| 1 | `src/sirenity/contexts/runtime/configuration/services/resolver.py` → `src/sirenity/contexts/compiler/document.py` | Runtime configuration imports compiler-internal document normalization across a context boundary. |

The last two compiler-document edges make `src/sirenity/contexts/compiler/document.py` the clearest ownership ambiguity:
it sits at context root, is not a module facade, and is consumed from both the root public API and runtime.

## Dependency-direction findings

The modules realm currently orders layers as `module-facade → state → services → contracts → values`. The 52
backward-flow findings group by resolved layer pair as follows. These values count dependency edges, not files.

| Edges | Direction |
| ---: | --- |
| 30 | `services` → `module-facade` |
| 12 | `contracts` → `module-facade` |
| 8 | `state` → `module-facade` |
| 1 | `services` → `state` |
| 1 | `values` → `module-facade` |

Fifty-one findings therefore cross into another module facade. That may indicate inverted dependencies, or it may
mean module facades are contracts between sibling modules and should not participate in one global layer ordering.
The target architecture must decide that explicitly before any rule or code is changed.

The most concentrated source locations are:

- `src/sirenity/contexts/runtime/projection/services/projection.py`
- `src/sirenity/contexts/runtime/projection/services/relationship.py`
- `src/sirenity/contexts/runtime/adapter/state/adapter.py`
- `src/sirenity/contexts/runtime/engine/state/engine.py`
- `src/sirenity/contexts/runtime/projection/services/action.py`
- `src/sirenity/contexts/runtime/projection/services/entity.py`
- `src/sirenity/contexts/runtime/projection/services/response.py`

## Baseline decision

The current configuration covers the source tree and resolves every intended context, module, and outer boundary.
No violation is suppressed here. Configuration tensions and code-ownership violations remain separate findings for
the as-is diagrams and target-design work that follow.
