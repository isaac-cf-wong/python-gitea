"""What importing part of the Actions resource pulls in with it.

`gitea/actions/__init__.py` re-exports nothing, and that is load-bearing rather
than an oversight. This package is thirteen modules where every other resource is
three, so an eager re-export there would mean two things:

* `import gitea.actions.scope` - a module that depends on nothing - would execute
  every family module and both clients on the way in.
* Each of those modules would sit in an import cycle. Importing
  `gitea.actions.base` imports the package too, so a package that imports its
  submodules is one its submodules import back, and a static analyser reports it.

Both are properties of the package rather than of any one module, so they are
checked here rather than left to a comment in `__init__.py` that nothing enforces.
The check runs in a subprocess because it is about what a *fresh* interpreter
loads: by the time this test module is collected, the suite has imported nearly
everything, so `sys.modules` in this process says nothing.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

# The modules an eager re-export in `__init__.py` would drag in, and which importing one
# leaf must therefore not load. `actions` and `async_actions` are the two the
# re-export named; the families are what those two import in turn.
FAMILY_MODULES = [
    "gitea.actions.actions",
    "gitea.actions.async_actions",
    "gitea.actions.artifact",
    "gitea.actions.async_artifact",
    "gitea.actions.run_management",
    "gitea.actions.async_run_management",
    "gitea.actions.secret",
    "gitea.actions.async_secret",
    "gitea.actions.variable",
    "gitea.actions.async_variable",
    "gitea.actions.runner",
    "gitea.actions.async_runner",
]


def loaded_after_importing(module: str) -> set[str]:
    """Report which `gitea.actions` modules a fresh interpreter loads for one import.

    Args:
        module: The module to import, and nothing else.

    Returns:
        The names of every `gitea.actions` module in `sys.modules` afterwards.

    """
    program = (
        f"import {module}, sys\nprint('\\n'.join(sorted(n for n in sys.modules if n.startswith('gitea.actions'))))\n"
    )
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-c", program], capture_output=True, text=True, check=True
    )
    return set(completed.stdout.split())


@pytest.mark.parametrize("module", ["gitea.actions.scope", "gitea.actions.base"])
def test_importing_a_leaf_module_loads_only_what_it_needs(module: str) -> None:
    """Importing a module low in the package should not execute the whole resource.

    `scope` depends on nothing and `base` depends only on `scope`, so a fresh
    interpreter asked for either has no reason to load a client or a family - and
    would load all of them if the package re-exported its classes eagerly.
    """
    loaded = loaded_after_importing(module)

    assert loaded & set(FAMILY_MODULES) == set(), f"{module} pulled in {sorted(loaded & set(FAMILY_MODULES))}"
    assert module in loaded


def test_importing_one_family_does_not_load_the_others() -> None:
    """One family should not drag its siblings in, nor the class that composes them.

    The composition points one way: `Actions` imports the families, and a family
    imports only `base`. If that ever reversed - a family reaching back for
    `Actions` - the import would still work while making the cycle a real one, and
    this is what would catch it.
    """
    loaded = loaded_after_importing("gitea.actions.secret")

    assert "gitea.actions.secret" in loaded
    assert "gitea.actions.base" in loaded
    assert "gitea.actions.actions" not in loaded
    assert "gitea.actions.variable" not in loaded


def test_the_classes_are_importable_from_the_modules_they_live_in() -> None:
    """The package re-exporting nothing should not mean the classes are hard to reach.

    This is the documented way to import them, so it is worth a test: the reason
    the re-export is absent is the cost of the package importing thirteen modules,
    not any wish to make the two classes awkward to get at.
    """
    from gitea.actions.actions import Actions
    from gitea.actions.async_actions import AsyncActions

    assert Actions.__name__ == "Actions"
    assert AsyncActions.__name__ == "AsyncActions"


def test_the_package_itself_exposes_no_submodule_attributes() -> None:
    """Importing the package alone should give the package and nothing under it.

    Which is the point of the empty `__init__`: a caller that wants a client asks
    for the module it lives in. If a re-export came back, this is the assertion
    that would fail first, before anyone had to notice the cycle.
    """
    loaded = loaded_after_importing("gitea.actions")

    assert loaded == {"gitea.actions"}
