"""The machinery behind a package re-exporting a name only when it is first read.

Every resource package here is a `base` module plus a synchronous class and an
asynchronous one, and each of those classes imports the base - `gitea/issue/issue.py`
starts `from gitea.issue.base import BaseIssue`. Importing a dotted name executes the
package on the way in, so a package that re-exports its submodules at module level is
a package its submodules import back: the `__init__` imports `issue.py`, and `issue.py`
asks for `gitea.issue.base` and so imports the `__init__` again. That is an import
cycle, one per class per direction, and the twelve packages that re-export accounted for
forty-four of them.

The cycles were harmless, because no module here reads a name *out of* its own package
`__init__`, so the `__init__` always finished before anything wanted one. They cost
something separately, though: `import gitea.issue.base` executed both clients on the way
in, and with them `requests`, `aiohttp` and the whole of `gitea.resource`.

Both go away if the re-export happens when the name is first read rather than when the
package is imported, which is what a module-level `__getattr__` (PEP 562) is for.
`lazy_reexports` builds one, so each package spends a line on it rather than a
hand-rolled copy of the same lookup:

    __getattr__, __dir__ = lazy_reexports(__name__, {"Issue": "gitea.issue.issue"})

`from gitea.issue import Issue` runs that `__getattr__`, so every name stays importable
exactly where it was and this is invisible from outside. What it is not is visible to a
*static* reader, which is why the packages keep a `TYPE_CHECKING` block naming the same
imports: type checkers and editors resolve the names from there, and the block does not
execute, so it reintroduces no cycle.

One caveat worth knowing before reaching for this to quiet a static analyser: CodeQL's
`py/cyclic-import` counts an import statement anywhere in a file, inside a function body
or a `TYPE_CHECKING` block alike, and never counts a package as the *target* of an edge.
So it never reported this idiom and this module does not change what it reports. The
cycles removed here are the ones Python itself has.
"""

from __future__ import annotations

import sys
from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


def lazy_reexports(package: str, origins: Mapping[str, str]) -> tuple[Callable[[str], Any], Callable[[], list[str]]]:
    """Build the `__getattr__` and `__dir__` with which a package re-exports on first read.

    Args:
        package: The name of the package doing the re-exporting - `__name__` at the
            call site. Used to find the module to cache onto, and to word the
            `AttributeError` the way the interpreter would have.
        origins: The public name of each re-export, against the dotted name of the
            module it lives in.

    Returns:
        The `__getattr__` that serves those names, and the `__dir__` that reports them -
        which is needed because a name nobody has read yet is absent from the module's
        `__dict__`, and so from an unaided `dir()`.

    """

    def __getattr__(name: str) -> Any:  # noqa: N807
        try:
            origin = origins[name]
        except KeyError:
            raise AttributeError(f"module {package!r} has no attribute {name!r}") from None
        value = getattr(import_module(origin), name)
        # Bind it on the package, so later reads take the ordinary attribute path rather
        # than coming back here. This is also what keeps the semantics identical to the
        # eager re-export it replaces: that bound the name once, at import, and a test
        # patching the origin module afterwards did not change what the package exposed.
        setattr(sys.modules[package], name, value)
        return value

    def __dir__() -> list[str]:  # noqa: N807
        return sorted(origins)

    return __getattr__, __dir__
