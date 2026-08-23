"""What a package re-exporting lazily has to keep true.

The twelve packages listed below re-export their public names through a module-level
`__getattr__` (PEP 562) rather than importing them in `__init__.py`. Two things follow,
and neither is visible in the `__init__` on its own:

* **No import cycle.** A submodule reaching a sibling by its dotted name - `issue.py`
  asking for `gitea.issue.base` - imports its package on the way in. A package that
  imports its submodules is therefore one its submodules import back, which was 44
  cycles across these twelve packages before the re-exports became lazy.
* **A leaf import stays a leaf import.** `import gitea.issue.base` used to execute both
  `issue.py` and `async_issue.py`, and with them `requests`, `aiohttp` and the whole of
  `gitea.resource`.

Both are properties of the package rather than of any one module, so they are checked
here rather than left to a comment nothing enforces. The checks that ask what a *fresh*
interpreter loads run in a subprocess: by the time this module is collected the suite
has imported nearly everything, so `sys.modules` in this process says nothing.

`RE_EXPORTS` is written out rather than read from each package's `_ORIGINS`, so that the
assertions do not agree with the implementation by construction - a test that derives its
expectation from the code under test cannot fail when that code is wrong. That the two
agree is itself one of the assertions below.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pytest

import gitea

# Every package that re-exports lazily, against the public names it re-exports and the
# module each one lives in.
RE_EXPORTS: dict[str, dict[str, str]] = {
    "gitea.cli.utils": {
        "execute_api_command": "gitea.cli.utils.api",
        "get_auth_params": "gitea.cli.utils.auth",
    },
    "gitea.client": {
        "AsyncGitea": "gitea.client.async_gitea",
        "Gitea": "gitea.client.gitea",
    },
    "gitea.comment": {
        "AsyncComment": "gitea.comment.async_comment",
        "Comment": "gitea.comment.comment",
    },
    "gitea.config": {
        "AccountConfig": "gitea.config.model",
        "Config": "gitea.config.model",
        "ConfigManager": "gitea.config.manager",
    },
    "gitea.issue": {
        "AsyncIssue": "gitea.issue.async_issue",
        "Issue": "gitea.issue.issue",
        "async_column_holds_card": "gitea.issue.project_column",
        "column_holds_card": "gitea.issue.project_column",
        "find_async_card_column_id": "gitea.issue.project_column",
        "find_card_column_id": "gitea.issue.project_column",
        "resolve_async_project_column_ids": "gitea.issue.project_column",
        "resolve_project_column_ids": "gitea.issue.project_column",
    },
    "gitea.label": {
        "AsyncLabel": "gitea.label.async_label",
        "Label": "gitea.label.label",
    },
    "gitea.milestone": {
        "AsyncMilestone": "gitea.milestone.async_milestone",
        "Milestone": "gitea.milestone.milestone",
    },
    "gitea.notification": {
        "AsyncNotification": "gitea.notification.async_notification",
        "Notification": "gitea.notification.notification",
    },
    "gitea.organization": {
        "AsyncOrganization": "gitea.organization.async_organization",
        "Organization": "gitea.organization.organization",
    },
    "gitea.project": {
        "AsyncProject": "gitea.project.async_project",
        "Project": "gitea.project.project",
    },
    "gitea.pull_request": {
        "AsyncPullRequest": "gitea.pull_request.async_pull_request",
        "PullRequest": "gitea.pull_request.pull_request",
    },
    "gitea.repository": {
        "AsyncRepository": "gitea.repository.async_repository",
        "Repository": "gitea.repository.repository",
    },
}

# The ten packages shaped as `base` plus a synchronous and an asynchronous class. These
# are the ones where a leaf import is worth asserting about: `base` is what the two
# classes import, so nothing that imports it has any reason to load them.
PACKAGES_WITH_A_BASE = sorted(
    name for name in RE_EXPORTS if (Path(gitea.__file__).parent / Path(*name.split(".")[1:]) / "base.py").is_file()
)

NAMES = sorted((package, name) for package, origins in RE_EXPORTS.items() for name in origins)


def loaded_under(package: str, statement: str) -> set[str]:
    """Report which of `package`'s modules a fresh interpreter loads for one import.

    Args:
        package: The package whose modules are of interest.
        statement: The import to run, and nothing else.

    Returns:
        The names of every module under `package` in `sys.modules` afterwards.

    """
    program = f"{statement}\nimport sys\nprint(' '.join(n for n in sys.modules if n.startswith({package!r})))\n"
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-c", program], capture_output=True, text=True, check=True
    )
    return set(completed.stdout.split())


def module_level_import_cycles() -> set[tuple[str, ...]]:
    """Find every cycle in the graph of module-level imports within `gitea`.

    Only statements at a module's top level are edges, because only those run when the
    module is imported - an import inside a function body, or under `if TYPE_CHECKING`,
    does not. Importing a dotted name executes each package along it, so an import of
    `gitea.issue.base` is an edge to `gitea.issue` as well as to the module itself; that
    is the edge the eager re-exports closed into a cycle.

    Returns:
        Each cycle found, as the tuple of module names it runs through.

    """
    root = Path(gitea.__file__).parent
    modules: dict[str, Path] = {}
    for path in root.rglob("*.py"):
        parts = ["gitea", *path.relative_to(root).with_suffix("").parts]
        if parts[-1] == "__init__":
            parts = parts[:-1]
        modules[".".join(parts)] = path

    def prefixes(dotted: str) -> set[str]:
        pieces = dotted.split(".")
        return {".".join(pieces[:i]) for i in range(1, len(pieces) + 1)}

    edges: defaultdict[str, set[str]] = defaultdict(set)
    for name, path in modules.items():
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.Import):
                targets = {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                targets = {node.module} | {f"{node.module}.{alias.name}" for alias in node.names}
            else:
                continue
            for target in targets:
                edges[name] |= {p for p in prefixes(target) if p in modules and p != name}

    cycles: set[tuple[str, ...]] = set()

    def walk(node: str, stack: list[str], seen: set[str]) -> None:
        for nxt in sorted(edges[node]):
            if nxt in stack:
                cycles.add((*stack[stack.index(nxt) :], nxt))
            elif nxt not in seen:
                seen.add(nxt)
                walk(nxt, [*stack, nxt], seen)

    for name in sorted(modules):
        walk(name, [name], {name})
    return cycles


def test_the_package_has_no_module_level_import_cycles() -> None:
    """Nothing in `gitea` should import itself, however indirectly, at import time.

    This is the assertion the lazy re-exports exist to satisfy, and it is deliberately
    about the whole package rather than about the twelve: a cycle reintroduced anywhere,
    by any idiom, fails here.
    """
    cycles = module_level_import_cycles()

    assert cycles == set(), "\n".join(sorted(" -> ".join(cycle) for cycle in cycles))


@pytest.mark.parametrize("package", sorted(RE_EXPORTS))
def test_importing_a_package_loads_none_of_its_submodules(package: str) -> None:
    """Asking for the package alone should give the package and nothing under it.

    Which is what makes the re-export lazy: the names arrive when they are read. If an
    eager re-export came back this is the assertion that would fail first, before anyone
    had to notice the cycle it brought with it.
    """
    loaded = loaded_under(package, f"import {package}")

    assert loaded == {package}, f"{package} also loaded {sorted(loaded - {package})}"


@pytest.mark.parametrize("package", PACKAGES_WITH_A_BASE)
def test_importing_a_base_module_does_not_load_the_classes_built_on_it(package: str) -> None:
    """A module low in the package should not drag the whole resource in with it.

    `base` is what the synchronous and asynchronous classes import, so an interpreter
    asked for it has no reason to load either - and would load both, along with
    `requests` and `aiohttp`, if the package re-exported them eagerly.
    """
    origins = set(RE_EXPORTS[package].values())

    loaded = loaded_under(package, f"import {package}.base")

    assert loaded & origins == set(), f"{package}.base pulled in {sorted(loaded & origins)}"
    assert f"{package}.base" in loaded


@pytest.mark.parametrize(("package", "name"), NAMES)
def test_every_re_exported_name_is_importable_from_its_package(package: str, name: str) -> None:
    """The public API must be exactly what it was before the re-exports became lazy.

    These names are released, so `from gitea.issue import Issue` and its siblings have to
    keep working; the whole point of `__getattr__` over deleting the re-exports is that
    this test can stay green.
    """
    module = __import__(package, fromlist=[name])

    assert getattr(module, name).__name__ == name


@pytest.mark.parametrize("package", sorted(RE_EXPORTS))
def test_the_origins_table_agrees_with_all_and_with_this_test(package: str) -> None:
    """`__all__`, the package's own `_ORIGINS`, and `RE_EXPORTS` here must say the same.

    Three places name the same set, and a name added to one of them and forgotten in
    another would otherwise go unnoticed: missing from `_ORIGINS` it is unreachable
    despite `__all__` promising it, and missing from `__all__` it escapes the test above.
    """
    module = __import__(package, fromlist=["__all__"])

    assert sorted(module.__all__) == sorted(RE_EXPORTS[package])
    assert RE_EXPORTS[package] == module._ORIGINS


@pytest.mark.parametrize("package", sorted(RE_EXPORTS))
def test_dir_adds_the_re_exports_to_the_ordinary_names_without_loading_them(package: str) -> None:
    """`dir()` must gain the lazy names without losing the ones it already reported.

    Two halves, and the second is the easier one to get wrong. A lazy name is absent from
    the module's `__dict__` until something asks for it, so without a `__dir__` the
    package would look empty to anything that introspects it - but a module `__dir__`
    *replaces* the default listing rather than adding to it, so one that returns only the
    re-exports drops `__name__`, `__doc__`, `__all__` and everything else the module
    really has. Both halves are asserted here, against the module's own `__dict__` rather
    than a fixed list, so nothing the package holds can go unlisted.

    Listing the names must also not be what loads them, which is why `__dir__` reads
    `vars()` rather than reaching through `getattr`.
    """
    expected = set(RE_EXPORTS[package])
    origins = set(RE_EXPORTS[package].values())

    # One interpreter, so that what `dir()` listed and what the module then held cannot
    # come from two different states. `bound` is read after the `dir()` call on purpose.
    program = (
        f"import json, sys\n"
        f"import {package}\n"
        f"listed = dir({package})\n"
        f"bound = list(vars({package}))\n"
        f"loaded = [n for n in sys.modules if n.startswith({package!r})]\n"
        f"print(json.dumps({{'listed': listed, 'bound': bound, 'loaded': loaded}}))\n"
    )
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-c", program], capture_output=True, text=True, check=True
    )
    result = json.loads(completed.stdout)
    listed, bound, loaded = set(result["listed"]), set(result["bound"]), set(result["loaded"])

    # The lazy names are listed...
    assert expected <= listed, f"dir({package}) omitted {sorted(expected - listed)}"
    # ...and so is everything the module actually holds, dunders included.
    assert bound <= listed, f"dir({package}) omitted {sorted(bound - listed)}"
    for ordinary in ("__name__", "__doc__", "__all__", "__file__", "__package__", "__path__", "__spec__"):
        assert ordinary in listed, f"dir({package}) omitted {ordinary}"
    # Listing them neither imported an origin nor bound a name.
    assert loaded & origins == set(), f"dir({package}) loaded {sorted(loaded & origins)}"
    assert bound & expected == set(), f"dir({package}) bound {sorted(bound & expected)}"


@pytest.mark.parametrize("package", sorted(RE_EXPORTS))
def test_dir_and_attribute_access_survive_the_module_leaving_sys_modules(package: str) -> None:
    """A module object outlives its `sys.modules` entry, and both hooks run on it.

    `monkeypatch.delitem(sys.modules, ...)` is the usual way to arrange that, and a
    reference to the module kept across it is still a live module whose `__dir__` and
    `__getattr__` a caller may reach. Both find the module through `sys.modules`, so
    neither may assume the entry is still there - `dir()` in particular should never
    raise, which a bare subscript would have made it do.
    """
    name = min(RE_EXPORTS[package])

    program = (
        f"import sys\n"
        f"import {package} as m\n"
        f"del sys.modules[{package!r}]\n"
        f"listed = dir(m)\n"
        f"assert {name!r} in listed, 'the re-export went missing from dir()'\n"
        f"assert '__name__' in listed, 'the ordinary names went missing from dir()'\n"
        f"assert getattr(m, {name!r}).__name__ == {name!r}, 'the re-export stopped resolving'\n"
        "print('ok')\n"
    )
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-c", program], capture_output=True, text=True, check=False
    )

    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("package", sorted(RE_EXPORTS))
def test_an_attribute_the_package_does_not_have_still_raises(package: str) -> None:
    """A missing name must fail the way it would without a `__getattr__` in the way.

    A module `__getattr__` that raised anything else - or returned None for an unknown
    name - would turn a typo into a much later failure, and would break `hasattr`.
    """
    module = __import__(package, fromlist=["__name__"])

    with pytest.raises(AttributeError, match=f"module '{package}' has no attribute 'NotAName'"):
        _ = module.NotAName

    assert not hasattr(module, "NotAName")


@pytest.mark.parametrize("package", sorted(RE_EXPORTS))
def test_reading_a_name_binds_it_on_the_package(package: str) -> None:
    """The first read should bind the name, so later reads take the ordinary path.

    This is also what keeps the semantics identical to the eager re-export it replaced:
    that bound the name once, at import time, so the package kept handing out the same
    object no matter what happened to the module it came from afterwards.
    """
    name = min(RE_EXPORTS[package])

    program = (
        f"import {package}\n"
        f"assert {name!r} not in vars({package}), 'bound before it was read'\n"
        f"first = {package}.{name}\n"
        f"assert vars({package})[{name!r}] is first, 'not bound after being read'\n"
        f"assert {package}.{name} is first\n"
        "print('ok')\n"
    )
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-c", program], capture_output=True, text=True, check=False
    )

    assert completed.returncode == 0, completed.stderr
