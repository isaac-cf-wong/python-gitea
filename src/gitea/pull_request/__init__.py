"""Pull request API for Gitea."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gitea._lazy import lazy_reexports

if TYPE_CHECKING:
    from gitea.pull_request.async_pull_request import AsyncPullRequest
    from gitea.pull_request.pull_request import PullRequest

__all__ = ["AsyncPullRequest", "PullRequest"]

# Re-exported when a name is first read, not imported here: a submodule reaching a
# sibling by its dotted name imports its package on the way in, so importing them here
# would put each of them in an import cycle. `gitea._lazy` carries the reasoning.
_ORIGINS = {
    "AsyncPullRequest": "gitea.pull_request.async_pull_request",
    "PullRequest": "gitea.pull_request.pull_request",
}

__getattr__, __dir__ = lazy_reexports(globals(), _ORIGINS)
