"""Unit tests for the field-name convention and its compatibility aliases."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from typing import ClassVar

import pytest

from gitea.utils.fields import FIELD_NAME_POLICY, AliasedDict, ProjectColumn, as_records

# A column as `/projects/{id}/columns` answers with one, keyed as the API keys it.
COLUMN = {
    "id": 117,
    "title": "Working",
    "default": False,
    "sorting": 0,
    "project_id": 31,
    "created_at": "2026-08-17T06:53:32+02:00",
    "updated_at": "2026-08-18T12:46:48+02:00",
}


class Aliased(AliasedDict):
    """Record type standing in for a resource with one alias of its own."""

    _ALIASES: ClassVar[Mapping[str, str]] = {"alias": "canonical"}


class TestAliasedDict:
    """The reads an alias widens, and the ones it leaves alone."""

    def test_canonical_field_is_read_as_from_a_dict(self) -> None:
        """A field the payload carries reads as it would from a plain dictionary."""
        assert Aliased({"canonical": "value"})["canonical"] == "value"

    def test_alias_reads_the_field_it_aliases(self) -> None:
        """An alias reads the value of the canonical field."""
        assert Aliased({"canonical": "value"})["alias"] == "value"

    def test_alias_of_an_absent_field_raises_naming_the_key_asked_for(self) -> None:
        """An alias of a field the payload omits raises, naming the alias."""
        with pytest.raises(KeyError) as error:
            _ = Aliased({"other": "value"})["alias"]

        assert error.value.args == ("alias",)

    def test_unknown_key_raises(self) -> None:
        """A key that is neither a field nor an alias raises, as on a dictionary."""
        with pytest.raises(KeyError) as error:
            _ = Aliased({"canonical": "value"})["absent"]

        assert error.value.args == ("absent",)

    def test_get_reads_an_alias(self) -> None:
        """`get` resolves an alias, which `dict.get` alone would not."""
        assert Aliased({"canonical": "value"}).get("alias") == "value"

    def test_get_reads_a_canonical_field(self) -> None:
        """`get` still reads a field the payload carries."""
        assert Aliased({"canonical": "value"}).get("canonical") == "value"

    def test_get_falls_back_to_the_default(self) -> None:
        """`get` answers with the default when neither a field nor an alias matches."""
        assert Aliased({"canonical": "value"}).get("absent", "fallback") == "fallback"

    def test_get_defaults_to_none(self) -> None:
        """`get` answers with None when no default is given, as `dict.get` does."""
        assert Aliased({"canonical": "value"}).get("absent") is None

    def test_get_falls_back_for_an_alias_of_an_absent_field(self) -> None:
        """An alias of an omitted field falls back rather than raising through `get`."""
        assert Aliased({"other": "value"}).get("alias", "fallback") == "fallback"

    def test_alias_is_reported_as_readable(self) -> None:
        """`in` agrees with the read it guards: an alias is there to be read."""
        assert "alias" in Aliased({"canonical": "value"})

    def test_canonical_field_is_reported_as_readable(self) -> None:
        """`in` reports a field the payload carries."""
        assert "canonical" in Aliased({"canonical": "value"})

    def test_alias_of_an_absent_field_is_not_reported_as_readable(self) -> None:
        """An alias of an omitted field is not readable, so `in` says so."""
        assert "alias" not in Aliased({"other": "value"})

    def test_unknown_key_is_not_reported_as_readable(self) -> None:
        """A key that is neither a field nor an alias is not readable."""
        assert "absent" not in Aliased({"canonical": "value"})

    def test_alias_is_not_a_key(self) -> None:
        """An alias is absent from `keys()`, so nothing enumerates it."""
        assert list(Aliased({"canonical": "value"}).keys()) == ["canonical"]

    def test_alias_is_not_iterated(self) -> None:
        """An alias is absent from iteration and from `len`."""
        payload = Aliased({"canonical": "value"})

        assert list(payload) == ["canonical"]
        assert len(payload) == 1

    def test_alias_is_not_serialized(self) -> None:
        """Serialized output carries the canonical name alone.

        This is what keeps an alias a compatibility read rather than a second
        spelling of the field: no consumer of the CLI's JSON can come to depend
        on a name the API does not use, because it never reaches them.
        """
        assert json.loads(json.dumps(Aliased({"canonical": "value"}))) == {"canonical": "value"}

    def test_equals_the_plain_dictionary_of_the_same_fields(self) -> None:
        """A record compares equal to the payload it wraps."""
        assert Aliased({"canonical": "value"}) == {"canonical": "value"}

    def test_unpacking_drops_the_aliases(self) -> None:
        """`{**payload}` gives the plain, alias-free dictionary back."""
        unpacked = {**Aliased({"canonical": "value"})}

        assert unpacked == {"canonical": "value"}
        assert "alias" not in unpacked

    def test_copy_keeps_the_aliases_readable(self) -> None:
        """A copy is the same record type, so it still reads an alias."""
        copied = Aliased({"canonical": "value"}).copy()

        assert isinstance(copied, Aliased)
        assert copied["alias"] == "value"

    def test_copy_is_a_separate_payload(self) -> None:
        """A copy does not share its fields with the payload it was copied from."""
        payload = Aliased({"canonical": "value"})
        copied = payload.copy()
        copied["canonical"] = "other"

        assert payload["canonical"] == "value"

    def test_deep_copy_keeps_the_aliases_readable(self) -> None:
        """A deep copy is the same record type, so it still reads an alias."""
        copied = copy.deepcopy(Aliased({"canonical": ["value"]}))

        assert isinstance(copied, Aliased)
        assert copied["alias"] == ["value"]

    def test_a_record_without_aliases_behaves_as_a_dictionary(self) -> None:
        """The base type declares no alias, so it widens nothing."""
        payload = AliasedDict({"canonical": "value"})

        assert payload["canonical"] == "value"
        assert "alias" not in payload
        with pytest.raises(KeyError):
            _ = payload["alias"]


class TestProjectColumn:
    """The alias recorded for a project column."""

    def test_title_is_the_canonical_field(self) -> None:
        """A column is keyed by `title`, as the API keys it."""
        column = ProjectColumn(COLUMN)

        assert column["title"] == "Working"
        assert set(column) == set(COLUMN)

    def test_name_reads_the_title(self) -> None:
        """`name` reads the title, which is the compatibility the shim exists for."""
        assert ProjectColumn(COLUMN)["name"] == "Working"
        assert ProjectColumn(COLUMN).get("name") == "Working"
        assert "name" in ProjectColumn(COLUMN)

    def test_name_is_not_emitted(self) -> None:
        """The serialized column carries `title` alone."""
        emitted = json.loads(json.dumps(ProjectColumn(COLUMN)))

        assert emitted == COLUMN
        assert "name" not in emitted

    def test_title_is_not_read_back_as_a_name(self) -> None:
        """The alias is one-way: a column carrying only `name` is not readable by `title`.

        Nothing produces such a payload - it is the shape the API stopped short
        of - and reading it either way would make the two names interchangeable,
        which is what the convention rules out.
        """
        with pytest.raises(KeyError):
            _ = ProjectColumn({"id": 1, "name": "Working"})["title"]


class TestAsRecords:
    """What the wrapping applies to, and what it hands back untouched."""

    def test_wraps_one_object(self) -> None:
        """A single payload is wrapped in the record type."""
        wrapped = as_records(COLUMN, ProjectColumn)

        assert isinstance(wrapped, ProjectColumn)
        assert wrapped["name"] == "Working"

    def test_wraps_every_object_of_a_listing(self) -> None:
        """Each object of a listing is wrapped, and the listing stays a list."""
        wrapped = as_records([COLUMN, {**COLUMN, "id": 118, "title": "Done"}], ProjectColumn)

        assert [column["name"] for column in wrapped] == ["Working", "Done"]
        assert all(isinstance(column, ProjectColumn) for column in wrapped)

    def test_passes_a_non_object_entry_of_a_listing_through(self) -> None:
        """An entry that is not an object is handed back as it arrived."""
        assert as_records([COLUMN, "nonsense"], ProjectColumn)[1] == "nonsense"

    def test_passes_a_payload_that_is_not_an_object_through(self) -> None:
        """A body that did not come back in the endpoint's shape is not turned into an error."""
        assert as_records(None, ProjectColumn) is None
        assert as_records("nonsense", ProjectColumn) == "nonsense"

    def test_leaves_the_payload_it_wrapped_alone(self) -> None:
        """Wrapping copies the payload's fields rather than mutating it."""
        payload = {"title": "Working"}
        wrapped = as_records(payload, ProjectColumn)
        wrapped["title"] = "Done"

        assert payload == {"title": "Working"}


def test_the_policy_is_written_down() -> None:
    """The convention is stated in one place, naming what it rules out.

    A constant nothing reads is a constant that goes stale, so the policy is
    asserted on: it has to name the canonical source of a field name and say
    that an alias is not emitted.
    """
    assert "Gitea API" in FIELD_NAME_POLICY
    assert "never emitted" in FIELD_NAME_POLICY


class TestWritesAreNotAliased:
    """An alias widens reading. Writing through one is writing a field of that name.

    Which is worth pinning rather than asserting in prose: an implementation that
    resolved a write would let `column["name"] = x` change a column's title
    through a name Gitea does not use, and would put the alias into the payload's
    keys - and so into the JSON - by a route the read-side tests never take.
    """

    def test_assigning_an_alias_writes_a_field_of_that_name(self) -> None:
        """An assigned alias becomes a key, as it would on any dictionary."""
        payload = Aliased({"canonical": "value"})
        payload["alias"] = "written"

        assert payload["canonical"] == "value"
        assert sorted(payload) == ["alias", "canonical"]
        assert json.loads(json.dumps(payload)) == {"canonical": "value", "alias": "written"}

    def test_popping_an_alias_of_a_present_field_raises(self) -> None:
        """`pop` does not resolve an alias, so the canonical field survives it."""
        payload = Aliased({"canonical": "value"})

        with pytest.raises(KeyError):
            payload.pop("alias")

        assert payload["canonical"] == "value"

    def test_deleting_an_alias_of_a_present_field_raises(self) -> None:
        """`del` does not resolve an alias either."""
        payload = Aliased({"canonical": "value"})

        with pytest.raises(KeyError):
            del payload["alias"]

        assert payload["canonical"] == "value"
