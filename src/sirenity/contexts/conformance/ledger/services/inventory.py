from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gherkin.parser import Parser
from wireup import injectable

from sirenity.contexts.shared import SirenityError

from ..values import SirenExpectedScenario


@injectable
@dataclass(frozen=True)
class SirenGherkinScenarioInventory:
    def read(self, feature_directory: Path) -> tuple[SirenExpectedScenario, ...]:
        paths = tuple(sorted(feature_directory.glob("*.feature")))
        if not paths:
            raise SirenityError("Gherkin feature inventory is empty.")
        scenarios = tuple(
            scenario for path in paths for scenario in self.feature(path))
        labels = tuple((scenario.feature, scenario.name)
                       for scenario in scenarios)
        if len(labels) != len(set(labels)):
            raise SirenityError(
                "Gherkin feature inventory contains duplicate scenarios.")
        return scenarios

    def feature(self, path: Path) -> tuple[SirenExpectedScenario, ...]:
        document = Parser().parse(path.read_text())
        feature = document.get("feature")
        if not isinstance(feature, Mapping):
            raise SirenityError(f"Gherkin feature file {path} has no feature.")
        name = feature.get("name")
        if not isinstance(name, str) or not name:
            raise SirenityError(
                f"Gherkin feature file {path} has an invalid feature name.")
        scenarios = self.scenarios(feature.get("children"))
        if not scenarios:
            raise SirenityError(f"Gherkin feature {name!r} has no scenarios.")
        return tuple(SirenExpectedScenario(feature=name, name=scenario) for scenario in scenarios)

    def scenarios(self, children: Any) -> tuple[str, ...]:
        if not isinstance(children, list):
            raise SirenityError("Gherkin feature must contain children.")
        scenarios: tuple[str, ...] = ()
        for child in children:
            if not isinstance(child, Mapping):
                raise SirenityError("Gherkin feature has an invalid child.")
            scenario = child.get("scenario")
            if isinstance(scenario, Mapping):
                name = scenario.get("name")
                if not isinstance(name, str) or not name:
                    raise SirenityError(
                        "Gherkin scenario has an invalid name.")
                scenarios += (name,)
                continue
            rule = child.get("rule")
            if isinstance(rule, Mapping):
                scenarios += self.scenarios(rule.get("children"))
        return scenarios
