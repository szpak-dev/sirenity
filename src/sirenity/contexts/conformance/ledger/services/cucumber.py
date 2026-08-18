import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from wireup import injectable

from sirenity.contexts.shared import SirenityError

from ..contracts import SirenBddEvidenceReader
from ..values import SirenBddFeature, SirenBddScenario, SirenExpectedScenario, SirenJunitEvidence
from .inventory import SirenGherkinScenarioInventory


@injectable(as_type=SirenBddEvidenceReader)
@dataclass(frozen=True)
class SirenCucumberEvidenceReader(SirenBddEvidenceReader):
    inventory: SirenGherkinScenarioInventory

    def read(self, cucumber_report: Path, feature_directory: Path) -> tuple[SirenBddFeature, ...]:
        document = json.loads(cucumber_report.read_text())
        if not isinstance(document, list) or not document:
            raise SirenityError("Cucumber report must contain a feature list.")
        junit = self.junit(cucumber_report.with_name("junit.xml"))
        features = tuple(self.feature(value, junit.expected_failures)
                         for value in document)
        self.reconcile(self.inventory.read(feature_directory), features, junit)
        return features

    def feature(self, value: Any, expected_failures: frozenset[str]) -> SirenBddFeature:
        if not isinstance(value, Mapping):
            raise SirenityError("Cucumber report feature must be an object.")
        name = value.get("name")
        scenarios = value.get("elements")
        if not isinstance(name, str) or not name:
            raise SirenityError("Cucumber report feature must have a name.")
        if not isinstance(scenarios, list) or not scenarios:
            raise SirenityError(
                f"Cucumber report feature {name!r} must contain scenarios.")
        return SirenBddFeature(
            name=name,
            scenarios=tuple(self.scenario(value, expected_failures)
                            for value in scenarios),
        )

    def scenario(self, value: Any, expected_failures: frozenset[str]) -> SirenBddScenario:
        if not isinstance(value, Mapping):
            raise SirenityError("Cucumber report scenario must be an object.")
        identifier = value.get("id")
        name = value.get("name")
        steps = value.get("steps")
        if not isinstance(identifier, str) or not identifier:
            raise SirenityError(
                "Cucumber report scenario must have an identifier.")
        if not isinstance(name, str) or not name:
            raise SirenityError("Cucumber report scenario must have a name.")
        if not isinstance(steps, list) or not steps:
            raise SirenityError(
                f"Cucumber report scenario {name!r} must contain steps.")
        statuses = tuple(self.status(value, name) for value in steps)
        if all(status == "passed" for status in statuses):
            if identifier in expected_failures:
                raise SirenityError(
                    f"Cucumber report scenario {name!r} unexpectedly passed.")
            return SirenBddScenario(identifier=identifier, name=name, implemented=True)
        if identifier in expected_failures and statuses[-1] == "skipped" and all(
            status == "passed" for status in statuses[:-1]
        ):
            return SirenBddScenario(identifier=identifier, name=name, implemented=False)
        detail = ", ".join(statuses)
        raise SirenityError(
            f"Cucumber report scenario {name!r} has unexpected results: {detail}.")

    def junit(self, junit_report: Path) -> SirenJunitEvidence:
        document = ElementTree.parse(junit_report)
        identifiers: set[str] = set()
        expected_failures: set[str] = set()
        for testcase in document.findall(".//testcase"):
            name = testcase.get("name")
            if not name:
                raise SirenityError(
                    "JUnit report contains a testcase without a name.")
            if name in identifiers:
                raise SirenityError(
                    f"JUnit report has duplicate testcase names: {name}.")
            identifiers.add(name)
            if testcase.find("failure") is not None or testcase.find("error") is not None:
                raise SirenityError(
                    f"JUnit report contains an unsuccessful testcase: {name}.")
            skipped = testcase.find("skipped")
            if skipped is None:
                continue
            if skipped.get("type") != "pytest.xfail":
                raise SirenityError(
                    "JUnit report contains a skipped test that is not a strict expected failure.")
            expected_failures.add(name)
        if not identifiers:
            raise SirenityError("JUnit report contains no testcases.")
        return SirenJunitEvidence(
            identifiers=frozenset(identifiers),
            expected_failures=frozenset(expected_failures),
        )

    def reconcile(
        self,
        expected: tuple[SirenExpectedScenario, ...],
        features: tuple[SirenBddFeature, ...],
        junit: SirenJunitEvidence,
    ) -> None:
        reported = tuple((feature.name, scenario.name)
                         for feature in features for scenario in feature.scenarios)
        if len(reported) != len(set(reported)):
            raise SirenityError(
                "Cucumber report contains duplicate scenarios.")
        expected_labels = frozenset(
            (scenario.feature, scenario.name) for scenario in expected)
        reported_labels = frozenset(reported)
        missing = expected_labels.difference(reported_labels)
        if missing:
            labels = ", ".join(
                f"{feature}: {scenario}" for feature, scenario in sorted(missing))
            raise SirenityError(
                f"Cucumber report is missing committed scenarios: {labels}.")
        unexpected = reported_labels.difference(expected_labels)
        if unexpected:
            labels = ", ".join(
                f"{feature}: {scenario}" for feature, scenario in sorted(unexpected))
            raise SirenityError(
                f"Cucumber report contains unexpected scenarios: {labels}.")
        identifiers = tuple(
            scenario.identifier for feature in features for scenario in feature.scenarios)
        if len(identifiers) != len(set(identifiers)):
            raise SirenityError(
                "Cucumber report contains duplicate scenario identifiers.")
        cucumber_identifiers = frozenset(identifiers)
        missing_junit = cucumber_identifiers.difference(junit.identifiers)
        if missing_junit:
            names = ", ".join(sorted(missing_junit))
            raise SirenityError(
                f"JUnit report is missing Cucumber scenarios: {names}.")
        unexpected_junit = junit.identifiers.difference(cucumber_identifiers)
        if unexpected_junit:
            names = ", ".join(sorted(unexpected_junit))
            raise SirenityError(
                f"JUnit report contains non-Cucumber testcases: {names}.")

    def status(self, value: Any, scenario: str) -> str:
        if not isinstance(value, Mapping):
            raise SirenityError(
                f"Cucumber report scenario {scenario!r} has an invalid step.")
        result = value.get("result")
        if not isinstance(result, Mapping) or not isinstance(result.get("status"), str):
            raise SirenityError(
                f"Cucumber report scenario {scenario!r} has an invalid step result.")
        return result["status"]
