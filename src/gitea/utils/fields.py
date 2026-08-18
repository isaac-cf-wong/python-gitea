"""The field names this library hands back, and the names it still answers to.

Every payload a client method returns is the JSON the Gitea API sent, keyed as
the API keys it. Nothing here renames a field and nothing drops one: a project
column is `title` because that is what `/projects/{id}/columns` answers with, so
a caller reading a payload looks the key up in Gitea's own API reference rather
than in this library's source.

That rule is written down rather than left as a habit because breaking it is
invisible from the outside. A wrapper that renames one field of one resource -
`title` to `name`, because a column reads more naturally as having a name - is
indistinguishable, to the caller, from an API that spells it that way. The
caller writes `column["name"]`, it works, and it breaks on the version that
notices the rename and removes it. Worse, a rename applied in one path and not
the other - in a CLI command that rebuilds a payload but not in the client
method feeding it - makes the same value arrive under two names depending on
which door it came through, which is the shape the friction was reported in
(management/weave-workspace#34).

So the canonical name is the API's, everywhere, in the client dictionaries and
in the CLI's JSON envelope alike. What this module adds is the other half of
that: a name callers already write can go on being read without becoming a
second spelling of the field.

A field the API does not send may still be *added*, where it carries something
the API has no way of saying: `column_id` on the project entries of an issue is
resolved from the board, because the issue payload names the projects without
saying where on them its cards sit. Such a field is documented where the command
adding it is documented, and it is never another name for a field already in the
payload - which is the line between filling a gap and inventing a synonym.

## Aliases

An alias is a name a payload can be *read* by. It is not a key: it is absent
from `keys()`, from iteration, from `len()`, and therefore from anything that
serializes the payload, so the JSON the CLI prints carries the canonical name
alone and no consumer can come to depend on the alias by reading the output.

`AliasedDict` is otherwise a `dict` - it compares equal to the plain dictionary
of the same items, and unpacking one with `{**payload}` gives that plain
dictionary back, alias-free.

The bar for adding an entry is a name callers have actually written, not a name
that reads well: every alias is a second way to spell one field, which is the
thing this module exists to prevent. The one recorded today is `name` on a
project column, because that is what code written against this library reached
for first.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar, Self

# The convention, in one place, for a caller or a reviewer who needs to know
# what a payload's keys are before reading one. The prose above is the argument
# for it; this is the rule itself.
FIELD_NAME_POLICY = (
    "Payloads carry the field names the Gitea API sends: nothing is renamed and nothing is dropped, in client "
    "dictionaries and in the CLI's JSON envelope alike. A field the API cannot send may be added where it is "
    "documented alongside what adds it, and never as a second name for a field already there. A name callers wrote "
    "before that rule was recorded stays readable as an alias of the canonical field, declared in the `_ALIASES` of "
    "the record type for its resource. An alias is readable but never emitted, so serialized output carries the "
    "canonical name alone."
)


class AliasedDict(dict[str, Any]):
    """An API payload readable by its canonical field names and by their aliases.

    Reading is widened and nothing else is: `payload["name"]`,
    `payload.get("name")` and `"name" in payload` all resolve an alias to the
    field it aliases, while `keys()`, iteration, `len()` and every serialization
    see the canonical fields alone.

    Subclasses declare the aliases of one resource. A subclass declaring none
    behaves as a plain dictionary, which is what makes this usable as the base
    of a record type before anyone has needed an alias for it.
    """

    _ALIASES: ClassVar[Mapping[str, str]] = {}

    def __missing__(self, key: str) -> Any:
        """Resolve a key that is not a field of this payload.

        `dict.__getitem__` calls this only once the key has been looked up and
        not found, so a canonical field is read at the speed of a dictionary and
        the alias table is consulted for nothing else.

        Args:
            key: The key that was asked for and is not a field.

        Returns:
            The value of the field the key is an alias of.

        Raises:
            KeyError: If the key is not an alias, or is an alias of a field this
                payload does not carry - a response that omitted it, say. The
                error names the key the caller asked for rather than the one it
                resolved to, since the caller never wrote the latter.

        """
        canonical = self._ALIASES.get(key)
        if canonical is not None and dict.__contains__(self, canonical):
            return dict.__getitem__(self, canonical)
        raise KeyError(key)

    def get(self, key: Any, default: Any = None) -> Any:
        """Read a field or an alias of one, falling back to a default.

        `dict.get` never reaches `__missing__`, so it is widened here for the
        same reason `__getitem__` did not have to be: a caller reading an alias
        defensively is the same caller.

        Args:
            key: The canonical field name, or an alias of one.
            default: What to answer when the payload carries neither.

        Returns:
            The value of the field, or `default`.

        """
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: object) -> bool:
        """Report whether a payload can be read by a key.

        An alias answers True, so the `"name" in payload` that guards a read of
        `payload["name"]` agrees with the read it guards. `keys()` is untouched,
        so what is enumerable is still the canonical fields alone.

        Args:
            key: The canonical field name, or an alias of one.

        Returns:
            True when reading the key yields a value.

        """
        if dict.__contains__(self, key):
            return True
        canonical = self._ALIASES.get(key)
        return canonical is not None and dict.__contains__(self, canonical)

    def copy(self) -> Self:
        """Copy the payload, keeping the aliases readable.

        `dict.copy` answers with a plain dictionary, which would quietly drop
        the aliases from the copy of a payload that had them.

        Returns:
            A shallow copy of the same record type.

        """
        return type(self)(self)


class ProjectColumn(AliasedDict):
    """A project column as the API returns it.

    Gitea names a column with `title`. `name` reads it too, because that is the
    key code written against this library reached for before the convention was
    recorded, and breaking it would buy nothing.
    """

    _ALIASES: ClassVar[Mapping[str, str]] = {"name": "title"}


def as_records(data: Any, record: type[AliasedDict]) -> Any:
    """Wrap the objects of a payload in the record type carrying their aliases.

    Args:
        data: The payload a client method is about to return: one object, a
            listing of them, or whatever an empty or unparsable response left in
            its place.
        record: The record type of the resource the payload describes.

    Returns:
        The payload with each object in it wrapped in `record`. Anything that is
        not an object is handed back untouched, so a body that did not come back
        in the endpoint's shape reaches the caller as it arrived rather than
        being turned into an error by the wrapping of it.

    """
    if isinstance(data, dict):
        return record(data)
    if isinstance(data, list):
        return [record(item) if isinstance(item, dict) else item for item in data]
    return data
