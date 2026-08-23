"""Gitea Actions resource.

This package deliberately re-exports nothing, where the other resource packages
re-export their two classes. `Actions` and `AsyncActions` are imported from the
modules they live in:

    from gitea.actions.actions import Actions
    from gitea.actions.async_actions import AsyncActions

The reason is this package's shape. Every other resource is three modules - a
base, a synchronous class and an asynchronous one - while this one is thirteen,
because the Actions API is large enough that a module per family reads better than
one class per client (`gitea.actions.actions` says which families and why). An
eager re-export here would import all thirteen: `import gitea.actions.scope`, which
depends on nothing, would execute every family module and both clients on the way
in.

It would also make each of those modules part of an import cycle. A submodule
importing `gitea.actions.base` imports this package too - that is what executing
`a.b` means - so a package that imports its submodules is a package its submodules
import back. The cycles are harmless here, since nothing imports a name *from*
this package, but they are real, a static analyser is right to report them, and
with thirteen modules there are dozens rather than the two a three-module package
produces.

The other resource packages avoid both costs while keeping their re-exports, by
resolving them on first read through a module-level `__getattr__` that
`gitea._lazy.lazy_reexports` builds. That mechanism would serve thirteen modules as
readily as three, so the empty `__init__` here is a statement about where these two
classes are documented to be imported from, and no longer the only way to avoid
importing a package's worth of modules to reach one of them.

`gitea.resource` and `gitea.user` re-export nothing either, so this is a shape the
package layout already had rather than one introduced for the Actions resource.
"""

from __future__ import annotations
