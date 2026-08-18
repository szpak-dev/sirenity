from sirenity.contexts.shared import BaseValue, SirenHttpMethod


class SirenAdapterRoute(BaseValue):
    source_path: str
    public_path: str
    method: SirenHttpMethod
    operation_id: str
