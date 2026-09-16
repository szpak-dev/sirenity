from dataclasses import dataclass
from pathlib import Path

from gherkin.parser import Parser
from pydantic import JsonValue, TypeAdapter
from wireup import injectable

from ....shared import SirenityError
from ..values.expected_scenario import SirenExpectedScenario


@injectable
@dataclass(frozen=True)
class SirenGherkinScenarioInventory:
    def read(self, feature_directory: Path) -> tuple[SirenExpectedScenario, ...]:
        paths = tuple(sorted(feature_directory.glob("*.feature")))
        if not paths:
            raise SirenityError("Gherkin feature inventory is empty.")
        scenarios = tuple(scenario for path in paths for scenario in self.feature(path))
        labels = tuple((scenario.feature, scenario.name) for scenario in scenarios)
        if len(labels) != len(set(labels)):
            raise SirenityError("Gherkin feature inventory contains duplicate scenarios.")
        return scenarios

    def feature(self, path: Path) -> tuple[SirenExpectedScenario, ...]:
        document = TypeAdapter(dict[str, JsonValue]).validate_python(Parser().parse(path.read_text()))
        feature = document["feature"]
        name = feature["name"]
        if not name:
            raise SirenityError(f"Gherkin feature file {path} has an invalid feature name.")
        scenarios = self.scenarios(feature["children"])
        if not scenarios:
            raise SirenityError(f"Gherkin feature {name!r} has no scenarios.")
        return tuple(SirenExpectedScenario(feature=name, name=scenario) for scenario in scenarios)

    def scenarios(self, children: list[dict[str, JsonValue]]) -> tuple[str, ...]:
        scenarios: tuple[str, ...] = ()
        for child in children:
            scenario = child.get("scenario")
            if scenario is not None:
                name = scenario["name"]
                if not name:
                    raise SirenityError("Gherkin scenario has an invalid name.")
                scenarios += (name,)
                continue
            rule = child.get("rule")
            if rule is not None:
                scenarios += self.scenarios(rule["children"])
        return scenarios
