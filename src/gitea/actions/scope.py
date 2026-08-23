"""Which scope a set of Actions coordinates addresses, and where that scope lives.

Most of the Actions API exists several times over. A secret, a variable and a
runner each belong to a repository, to an organization, to the account making the
request, or - for a runner - to the instance as a whole, and Gitea gives each of
those its own path:

    /repos/{owner}/{repository}/actions/...
    /orgs/{owner}/actions/...
    /user/actions/...
    /admin/actions/...

The paths are otherwise identical, so which one a call means is decided by which
coordinates it was given rather than by which method was called. That is the
convention the CLI already documents - `--repository` narrows an owner to one of
its repositories and omitting it asks for the owner's own target - and this module
is that convention written once, for the client and the CLI both.

Two consequences worth knowing before reading the resources:

* Not every family offers every scope. A secret cannot be *listed* for the
  authenticated account, though one can be set and deleted there, and neither
  secrets nor variables have an instance-wide form at all. Asking for a scope an
  endpoint does not have would otherwise reach a URL that answers `404`, and the
  `404` would read as "no secrets" rather than as "no such endpoint", so each
  caller declares the scopes its endpoint offers and `resolve_scope` refuses the
  rest by name.
* `/orgs/{owner}/...` is the organization form and not a generic owner form:
  Gitea answers it only for an organization. A repository owned by a user is
  still addressed as a repository; the user's own scope is `/user/actions/...`,
  which is the *authenticated* account and takes no name.
"""

from __future__ import annotations

REPOSITORY = "repository"
ORGANIZATION = "organization"
USER = "user"
ADMIN = "admin"

# Every scope, in the order the messages below name them: narrowest first, so a
# refusal reads as a widening list rather than as an arbitrary one.
SCOPE_ORDER = (REPOSITORY, ORGANIZATION, USER, ADMIN)

EVERY_SCOPE = frozenset(SCOPE_ORDER)
REPOSITORY_ONLY = frozenset({REPOSITORY})

# How each scope is named in an error, in prose rather than as the constant: the
# reader of the message is holding a command line or a keyword argument, not this
# module.
_DESCRIPTIONS = {
    REPOSITORY: "a repository",
    ORGANIZATION: "an organization",
    USER: "the authenticated account",
    ADMIN: "the whole instance",
}


def _as_prose(scopes: frozenset[str]) -> str:
    """Name a set of scopes in the order `SCOPE_ORDER` gives them.

    Args:
        scopes: The scopes to name.

    Returns:
        The scopes as a phrase, such as `a repository or an organization`.

    """
    described = [_DESCRIPTIONS[scope] for scope in SCOPE_ORDER if scope in scopes]
    if len(described) == 1:
        return described[0]
    return f"{', '.join(described[:-1])} or {described[-1]}"


def resolve_scope(
    owner: str | None = None,
    repository: str | None = None,
    admin: bool = False,
    *,
    offered: frozenset[str] = EVERY_SCOPE,
) -> tuple[str, str]:
    """Name the scope these coordinates address, and the path its endpoints sit under.

    The coordinates decide the scope: a repository and its owner address the
    repository, an owner alone addresses that organization, neither addresses the
    authenticated account, and `admin` addresses the instance.

    Args:
        owner: The owner of the repository, or the organization itself.
        repository: The name of the repository, which narrows the owner to one of
            its repositories.
        admin: Whether to address the instance-wide endpoints, which answer only
            to an administrator's token.
        offered: The scopes the endpoint being addressed has a form for. The
            default is all four; a caller whose endpoint has fewer passes them,
            so that asking for a scope Gitea does not offer is refused here
            rather than answered `404` by a URL that does not exist.

    Returns:
        A tuple containing the name of the scope and the path its `actions`
        endpoints sit under, without a trailing slash.

    Raises:
        ValueError: If the coordinates name no scope - a repository without its
            owner, or the instance together with an owner - or if they name a
            scope the endpoint does not offer.

    """
    if admin:
        if owner is not None or repository is not None:
            raise ValueError(
                "the instance-wide Actions endpoints belong to no owner: pass `admin` on its own, "
                "or pass `owner` (and `repository`) instead of it."
            )
        scope, endpoint = ADMIN, "/admin/actions"
    elif repository is not None:
        if owner is None:
            raise ValueError(
                f"the repository {repository!r} is addressed by its owner as well: pass `owner` too. "
                f"Omitting both asks for the Actions endpoints of the authenticated account."
            )
        scope, endpoint = REPOSITORY, f"/repos/{owner}/{repository}/actions"
    elif owner is not None:
        scope, endpoint = ORGANIZATION, f"/orgs/{owner}/actions"
    else:
        scope, endpoint = USER, "/user/actions"

    if scope not in offered:
        raise ValueError(
            f"Gitea has no Actions endpoint here for {_DESCRIPTIONS[scope]}; "
            f"this one is offered for {_as_prose(offered)}."
        )

    return scope, endpoint
