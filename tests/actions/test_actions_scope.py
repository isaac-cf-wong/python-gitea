"""Which scope a set of Actions coordinates addresses, over the whole domain.

The coordinates are three booleans' worth of input - an owner or not, a repository
or not, the instance or not - so there are eight combinations and all eight are
enumerated below rather than sampled. Two of them name no scope at all, and those
are the ones a convenient choice of test values would miss: a repository without
its owner would otherwise reach `/repos/None/r/actions`, which is a URL that fails
far from the mistake.

The scope a caller gets wrong is not a caller that fails. It is a caller that
lists somebody else's secrets, or writes one to the wrong place, so the paths are
asserted in full rather than checked for the fragment that distinguishes them.
"""

from __future__ import annotations

import pytest

from gitea.actions.scope import (
    ADMIN,
    EVERY_SCOPE,
    ORGANIZATION,
    REPOSITORY,
    REPOSITORY_ONLY,
    SCOPE_ORDER,
    USER,
    resolve_scope,
)

OWNER = "o"
NAME = "r"

# Every combination of the three coordinates, and what it means. The two that mean
# nothing are declared as `None` and asserted on separately.
COMBINATIONS = [
    ((None, None, False), (USER, "/user/actions")),
    ((OWNER, None, False), (ORGANIZATION, f"/orgs/{OWNER}/actions")),
    ((OWNER, NAME, False), (REPOSITORY, f"/repos/{OWNER}/{NAME}/actions")),
    ((None, NAME, False), None),
    ((None, None, True), (ADMIN, "/admin/actions")),
    ((OWNER, None, True), None),
    ((OWNER, NAME, True), None),
    ((None, NAME, True), None),
]


@pytest.mark.parametrize(("coordinates", "expected"), COMBINATIONS)
def test_every_combination_of_coordinates(
    coordinates: tuple[str | None, str | None, bool], expected: tuple[str, str] | None
) -> None:
    """Each of the eight combinations should name its scope, or be refused outright."""
    owner, repository, admin = coordinates

    if expected is None:
        with pytest.raises(ValueError, match="owner"):
            resolve_scope(owner=owner, repository=repository, admin=admin)
        return

    assert resolve_scope(owner=owner, repository=repository, admin=admin) == expected


def test_the_four_paths_are_all_different() -> None:
    """No two scopes should resolve to the same path.

    Which is the property the rest of the resource rests on: the same request goes
    to whichever of these the coordinates chose, so two of them colliding would
    silently send one scope's writes to another's.
    """
    paths = {
        resolve_scope(**coordinates)[1]
        for coordinates in (
            {},
            {"owner": OWNER},
            {"owner": OWNER, "repository": NAME},
            {"admin": True},
        )
    }

    assert len(paths) == len(EVERY_SCOPE)


def test_a_repository_without_its_owner_names_the_repository_in_the_refusal() -> None:
    """The message should say which repository could not be addressed.

    A script that passes the repository and forgets the owner usually passes
    several, so the one that was refused is worth naming.
    """
    with pytest.raises(ValueError, match=f"'{NAME}'"):
        resolve_scope(repository=NAME)


class TestTheScopesAnEndpointOffers:
    """Refusing a scope the endpoint being addressed does not have."""

    def test_a_scope_outside_the_offer_is_refused(self) -> None:
        """A scope the endpoint has no form of should be refused before the request."""
        with pytest.raises(ValueError, match="no Actions endpoint here for an organization"):
            resolve_scope(owner=OWNER, offered=REPOSITORY_ONLY)

    def test_the_refusal_names_what_is_offered(self) -> None:
        """The message should say which scopes would have worked, not only which did not.

        A caller reading "there is no such endpoint" learns nothing about what to
        pass instead, and the answer - a repository, an organization - is right
        here.
        """
        with pytest.raises(ValueError, match="offered for a repository or an organization"):
            resolve_scope(offered=frozenset({REPOSITORY, ORGANIZATION}))

    def test_a_single_offer_is_named_without_a_conjunction(self) -> None:
        """One scope should read as one, rather than as a list of one."""
        with pytest.raises(ValueError, match=r"offered for a repository\.$"):
            resolve_scope(offered=REPOSITORY_ONLY)

    def test_the_offer_is_named_in_a_fixed_order(self) -> None:
        """The order should come from `SCOPE_ORDER` and not from the set's iteration.

        A set has no order, so a message built from one differs between runs -
        which makes it untestable and, worse, makes the same mistake read
        differently each time it is made.
        """
        offered = frozenset({ADMIN, USER, ORGANIZATION})

        with pytest.raises(ValueError, match="an organization, the authenticated account or the whole instance"):
            resolve_scope(owner=OWNER, repository=NAME, offered=offered)

    def test_every_scope_is_offered_by_default(self) -> None:
        """The default should be all four, so a caller that names none is not narrowed."""
        for coordinates in ({}, {"owner": OWNER}, {"owner": OWNER, "repository": NAME}, {"admin": True}):
            resolve_scope(**coordinates)


def test_the_order_covers_every_scope_exactly_once() -> None:
    """`SCOPE_ORDER` should be the scopes themselves, so no message can omit one.

    The prose helper walks the order and keeps whatever is in the offered set, so a
    scope missing from the order would be silently dropped from every message it
    belongs in.
    """
    assert set(SCOPE_ORDER) == EVERY_SCOPE
    assert len(SCOPE_ORDER) == len(EVERY_SCOPE)
