from pydantic import BaseModel, ConfigDict


class BaseValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    def supplies(self, field: str) -> bool:
        return field in self.model_fields_set
