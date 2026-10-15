# Typed navigation after execution

A link is useful to a human-facing client because the client knows how to follow a URL. An agent needs more than
that. It needs the operation identity and the arguments already bound by the result it just received.

Sirenity exposes three kinds of typed navigation through `SirenMcpResult`:

- `follow_ups` are independent safe reads declared by response links.
- `continuations` advance a bounded collection while more results exist.
- `verifications` read the canonical entity after a successful state-changing operation.

Each value is a `SirenMcpInvocation`, not a URL that the caller must parse. The invocation contains the target
operation identifier and the path or query arguments that OpenAPI and the runtime result were able to bind.

The distinction between the three collections is intentional. Pagination is not a verification, and a verification
is not a general recommendation about what the caller should do next. Keeping those meanings separate lets an agent
choose the next operation without guessing from relation names or transport details.

Sirenity still does not execute application policy. It omits navigation that cannot be authorized or bound safely,
then hands the remaining invocation to the caller-owned executor. The same ownership boundary holds before and after
the operation.
