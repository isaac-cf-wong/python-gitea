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

    __getattr__, __dir__ = lazy_reexports(globals(), {"Issue": "gitea.issue.issue"})

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

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, MutableMapping


def lazy_reexports(
    namespace: MutableMapping[str, Any], origins: Mapping[str, str]
) -> tuple[Callable[[str], Any], Callable[[], list[str]]]:
    """Build the `__getattr__` and `__dir__` with which a package re-exports on first read.

    Args:
        namespace: The namespace of the package doing the re-exporting - `globals()` at
            the call site, which is the module's own `__dict__`. Both hooks work on it
            directly: reading a name binds it here, and `__dir__` reports what it holds.
            Taking the namespace rather than looking the module up in `sys.modules` is
            what makes both correct for a module that has outlived its entry there.
        origins: The public name of each re-export, against the dotted name of the
            module it lives in.

    Returns:
        The `__getattr__` that serves those names, and the `__dir__` that adds them to
        what the module would report anyway - which is needed because a name nobody has
        read yet is absent from the module's `__dict__`, and so from an unaided `dir()`.

    """
    package = namespace["__name__"]

    def __getattr__(name: str) -> Any:  # noqa: N807
        try:
            origin = origins[name]
        except KeyError:
            raise AttributeError(f"module {package!r} has no attribute {name!r}") from None
        value = getattr(import_module(origin), name)
        # Bind it, so later reads take the ordinary attribute path rather than coming back
        # here. This is also what keeps the semantics identical to the eager re-export it
        # replaces: that bound the name once, at import, and a test patching the origin
        # module afterwards did not change what the package exposed.
        namespace[name] = value
        return value

    def __dir__() -> list[str]:  # noqa: N807
        # A module `__dir__` *replaces* the default listing rather than extending it, so
        # this has to put back what the default would have said: everything already bound
        # on the module - `__name__`, `__doc__`, `__all__`, the imported submodules - and
        # not only the re-exports. The namespace is read directly rather than through
        # `getattr`, so that listing the names is not what loads them; a re-export already
        # read is in both halves, which the union collapses.
        return sorted(namespace.keys() | origins.keys())

    return __getattr__, __dir__
