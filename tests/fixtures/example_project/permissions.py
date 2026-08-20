from pydantic import JsonValue

from sirenity import SirenAdapterPolicy


def siren_policy(
    operation_id: str,
    status: int,
    request: object,
    result: JsonValue,
) -> SirenAdapterPolicy:
    return SirenAdapterPolicy(capabilities=frozenset({operation_id}))
