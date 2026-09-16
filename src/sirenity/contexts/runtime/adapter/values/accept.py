import re
from math import isfinite

from ....shared import BaseValue


class SirenAccept(BaseValue):
    value: str

    def preference(self, media_type: str) -> tuple[float, int, int] | None:
        offered_type, offered_subtype = media_type.lower().split("/", 1)
        selected = None
        for order, item in enumerate(self.value.split(",")):
            parts = tuple(part.strip() for part in item.split(";"))
            if not parts[0] or parts[0].count("/") != 1:
                continue
            range_type, range_subtype = parts[0].lower().split("/", 1)
            if not range_type or not range_subtype or (range_type == "*" and range_subtype != "*"):
                continue
            quality = 1.0
            valid = True
            for parameter in parts[1:]:
                name, separator, raw_value = parameter.partition("=")
                if name.strip().lower() != "q":
                    continue
                if not separator or re.fullmatch(r"(?:0(?:\.\d+)?|1(?:\.0+)?)", raw_value.strip()) is None:
                    valid = False
                    break
                quality = float(raw_value.strip())
                if not isfinite(quality) or not 0.0 <= quality <= 1.0:
                    valid = False
                    break
            if not valid:
                continue
            if range_type not in {"*", offered_type}:
                continue
            if range_subtype not in {"*", offered_subtype}:
                continue
            specificity = int(range_type != "*") + int(range_subtype != "*")
            candidate = (quality, specificity, -order)
            if selected is None or candidate[1:] > selected[1:]:
                selected = candidate
        return selected

    def selects_siren(self) -> bool:
        siren = self.preference("application/vnd.siren+json")
        if siren is None or siren[0] == 0.0:
            return False
        json = self.preference("application/json")
        return json is None or siren > json
