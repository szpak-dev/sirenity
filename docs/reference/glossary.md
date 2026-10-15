# Glossary

## Siren

A [hypermedia type](https://github.com/kevinswiber/siren) that represents an entity together with its properties,
sub-entities, actions, and links. Sirenity emits the `application/vnd.siren+json` media type.

## Capability

An application-owned permission to expose one compiled operation for one projected result. Capabilities use OpenAPI
operation identifiers.

## Continuation

A typed invocation of the same safe collection operation with the next bounded page arguments. Continuations exist
only while the response states that more results are available.

## Delegated input

An operation input that official Siren fields cannot express completely, such as a structured body, header, cookie,
or structured query value. Sirenity preserves its OpenAPI contract for an adapter or client transport.

## Follow-up

An authorized typed invocation of an independent safe read advertised by an OpenAPI response link.

## Operation graph

The immutable result of compiling OpenAPI routes, operations, inputs, responses, and links. Sirenity integrations
reuse this graph instead of reparsing OpenAPI.

## Public path

The URL mount exposed by Sirenity in projected Siren links and actions.

## Siren action

An operation currently available for a projected resource, expressed as an official Siren action with its method,
target, and supported fields.

## Source path

The application route mount described by the OpenAPI document and used for caller-owned operation dispatch.

## Verification

A typed safe read of the canonical entity after a successful state-changing operation.
