import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServiceConventionChecker:
    root: Path
    include_composition: bool = True

    def run(self) -> int:
        failures = self.violations()
        if not failures:
            return 0
        print("\n".join(failures))
        return 1

    def violations(self) -> tuple[str, ...]:
        paths = tuple(sorted(path for path in self.root.glob("**/*.py") if path.name != "__init__.py"))
        collaborators = self.collaborators(paths)
        injectables = self.injectables(paths)
        failures: list[str] = []
        for path in paths:
            failures.extend(self.check(path, self.root, collaborators, injectables))
        if self.include_composition:
            failures.extend(self.check_composition())
        return tuple(failures)

    def check(
        self, path: Path, root: Path, collaborators: frozenset[str], injectables: frozenset[str]
    ) -> list[str]:
        source = path.read_text()
        tree = ast.parse(source, filename=str(path))
        classes = tuple(item for item in tree.body if isinstance(item, ast.ClassDef))
        failures: list[str] = []
        if "TYPE_CHECKING" in source:
            failures.append(f"{path}: TYPE_CHECKING is forbidden")
        if path != root / "wiring.py" and "create_sync_container" in source:
            failures.append(f"{path}: containers belong only in wiring.py")
        if "@injectable" in source and "services" not in path.parts:
            failures.append(f"{path}: injectables belong only in services")
        for node in classes:
            if any(
                isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == "__init__"
                for member in node.body
            ):
                failures.append(f"{path}: {node.name} must not declare __init__")
        if "state" in path.parts:
            for node in classes:
                if not any(ast.unparse(base) == "BaseState" for base in node.bases):
                    failures.append(f"{path}: {node.name} must inherit BaseState")
        if "services" not in path.parts:
            return failures
        for node in classes:
            decorators = tuple(ast.unparse(decorator) for decorator in node.decorator_list)
            if not any(decorator.startswith("injectable") for decorator in decorators):
                failures.append(f"{path}: {node.name} must be @injectable")
            if "dataclass(frozen=True)" not in decorators:
                failures.append(f"{path}: {node.name} must be a frozen dataclass")
            failures.extend(self.check_export(path, root, node.name))
            failures.extend(self.check_collaborator_parameters(path, node, collaborators))
            failures.extend(self.check_injectable_construction(path, node, injectables))
        return failures

    def collaborators(self, paths: tuple[Path, ...]) -> frozenset[str]:
        names: set[str] = set()
        for path in paths:
            if "services" not in path.parts:
                continue
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in (item for item in tree.body if isinstance(item, ast.ClassDef)):
                for member in node.body:
                    if isinstance(member, ast.AnnAssign):
                        names.update(self.annotation_names(member.annotation))
        return frozenset(names)

    def injectables(self, paths: tuple[Path, ...]) -> frozenset[str]:
        names: set[str] = set()
        for path in paths:
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in (item for item in tree.body if isinstance(item, ast.ClassDef)):
                if any(ast.unparse(decorator).startswith("injectable") for decorator in node.decorator_list):
                    names.add(node.name)
        return frozenset(names)

    def check_collaborator_parameters(
        self, path: Path, node: ast.ClassDef, collaborators: frozenset[str]
    ) -> list[str]:
        failures: list[str] = []
        for method in (member for member in node.body if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))):
            parameters = (*method.args.posonlyargs, *method.args.args, *method.args.kwonlyargs)
            for parameter in parameters:
                if parameter.arg in {"self", "cls"} or parameter.annotation is None:
                    continue
                names = self.annotation_names(parameter.annotation) & collaborators
                if names:
                    rendered = ", ".join(sorted(names))
                    failures.append(
                        f"{path}: {node.name}.{method.name} receives collaborator {rendered} "
                        "as a method parameter; inject it as a dataclass field"
                    )
        return failures

    def check_injectable_construction(
        self, path: Path, node: ast.ClassDef, injectables: frozenset[str]
    ) -> list[str]:
        failures: list[str] = []
        for call in (item for item in ast.walk(node) if isinstance(item, ast.Call)):
            name = self.call_name(call.func)
            if name in injectables:
                failures.append(
                    f"{path}: {node.name} constructs injectable {name}; inject it as a dataclass field"
                )
        return failures

    def annotation_names(self, annotation: ast.expr) -> set[str]:
        return {item.id for item in ast.walk(annotation) if isinstance(item, ast.Name)}

    def call_name(self, expression: ast.expr) -> str | None:
        if isinstance(expression, ast.Name):
            return expression.id
        if isinstance(expression, ast.Attribute):
            return expression.attr
        return None

    def check_export(self, path: Path, root: Path, name: str) -> list[str]:
        relative = path.relative_to(root)
        service_index = relative.parts.index("services")
        package = root.joinpath(*relative.parts[: service_index + 1], "__init__.py")
        tree = ast.parse(package.read_text(), filename=str(package))
        for statement in tree.body:
            if isinstance(statement, ast.ImportFrom) and any(alias.name == name for alias in statement.names):
                return []
        return [f"{path}: injectable {name} is not exported by {package}"]

    def check_composition(self) -> list[str]:
        try:
            from sirenity.wiring import SirenApplicationContainer

            application = SirenApplicationContainer().application()
            application.api_service()
            application.engine_factory()
            application.conformance_service()
        except Exception as error:
            return [f"Wireup composition is unresolvable: {error}"]
        return []


if __name__ == "__main__":
    raise SystemExit(ServiceConventionChecker(Path(__file__).parents[1] / "src" / "sirenity").run())
