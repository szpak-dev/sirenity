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

    def check(self, path: Path, root: Path, collaborators: frozenset[str], injectables: frozenset[str]) -> list[str]:
        source = path.read_text()
        tree = ast.parse(source, filename=str(path))
        classes = self.classes(tree)
        failures: list[str] = []
        if "TYPE_CHECKING" in source:
            failures.append(f"{path}: TYPE_CHECKING is forbidden")
        if path != root / "wiring.py" and "create_sync_container" in source:
            failures.append(f"{path}: containers belong only in wiring.py")
        if "@injectable" in source and "services" not in path.parts:
            failures.append(f"{path}: injectables belong only in services")
        for node in classes:
            if "__init__" in {method.name for method in self.methods(node)}:
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
            for node in self.classes(tree):
                for member in node.body:
                    match member:
                        case ast.AnnAssign(annotation=annotation):
                            names.update(self.annotation_names(annotation))
        return frozenset(names)

    def injectables(self, paths: tuple[Path, ...]) -> frozenset[str]:
        names: set[str] = set()
        for path in paths:
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in self.classes(tree):
                if any(ast.unparse(decorator).startswith("injectable") for decorator in node.decorator_list):
                    names.add(node.name)
        return frozenset(names)

    def check_collaborator_parameters(self, path: Path, node: ast.ClassDef, collaborators: frozenset[str]) -> list[str]:
        failures: list[str] = []
        for method in self.methods(node):
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

    def check_injectable_construction(self, path: Path, node: ast.ClassDef, injectables: frozenset[str]) -> list[str]:
        failures: list[str] = []
        for item in ast.walk(node):
            match item:
                case ast.Call() as call:
                    pass
                case _:
                    continue
            name = self.call_name(call.func)
            if name in injectables:
                failures.append(f"{path}: {node.name} constructs injectable {name}; inject it as a dataclass field")
        return failures

    def annotation_names(self, annotation: ast.expr) -> set[str]:
        names = set()
        for item in ast.walk(annotation):
            match item:
                case ast.Name(id=name) if name[:1].isupper():
                    names.add(name)
        return names

    def call_name(self, expression: ast.expr) -> str | None:
        match expression:
            case ast.Name(id=name):
                return name
            case ast.Attribute(attr=name):
                return name
            case _:
                return None

    def classes(self, tree: ast.Module) -> tuple[ast.ClassDef, ...]:
        classes = []
        for item in tree.body:
            match item:
                case ast.ClassDef() as node:
                    classes.append(node)
        return tuple(classes)

    def methods(self, node: ast.ClassDef) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
        methods = []
        for member in node.body:
            match member:
                case ast.FunctionDef() | ast.AsyncFunctionDef():
                    methods.append(member)
        return tuple(methods)

    def check_export(self, path: Path, root: Path, name: str) -> list[str]:
        relative = path.relative_to(root)
        service_index = relative.parts.index("services")
        package = root.joinpath(*relative.parts[: service_index + 1], "__init__.py")
        tree = ast.parse(package.read_text(), filename=str(package))
        for statement in tree.body:
            match statement:
                case ast.ImportFrom(names=aliases) if any(alias.name == name for alias in aliases):
                    return []
        return [f"{path}: injectable {name} is not exported by {package}"]

    def check_composition(self) -> list[str]:
        from wireup import SyncContainer

        from sirenity.wiring import application

        match application.container:
            case SyncContainer():
                return []
            case _:
                return ["Wireup composition did not create a synchronous container."]


if __name__ == "__main__":
    raise SystemExit(ServiceConventionChecker(Path(__file__).parents[1] / "src" / "sirenity").run())
