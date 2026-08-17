"""Unit tests for the snapshot a watch takes of an issue and the comparison of two of them."""

from __future__ import annotations

from typing import Any

import pytest

from gitea.watch.changes import (
    comment_hash,
    detect_changes,
    format_change,
    issue_key,
    issue_snapshot,
    usable_identifier,
)

COMMENT = {
    "id": 7,
    "body": "Looks right to me",
    "user": {"login": "alice"},
    "created_at": "2026-08-01T09:00:00Z",
    "updated_at": "2026-08-01T09:00:00Z",
}

ISSUE = {
    "id": 1854,
    "number": 15,
    "title": "Fix the docs",
    "updated_at": "2026-08-02T10:00:00Z",
    "assignees": [{"login": "alice"}, {"login": "bob"}],
    "labels": [{"name": "bug"}, {"name": "docs"}],
}


def snapshot(**overrides: Any) -> dict[str, Any]:
    """Build a snapshot of `ISSUE`, overriding the fields a test varies.

    Args:
        **overrides: Fields to replace in the snapshot.

    Returns:
        The snapshot.

    """
    return {**issue_snapshot(ISSUE, [COMMENT], repository="my-org/my-repo"), **overrides}


class TestCommentHash:
    """Tests for the hash a comment is recognized by between runs."""

    def test_the_same_comment_hashes_the_same_way(self) -> None:
        """Re-fetching a comment should not make it look like a new one."""
        assert comment_hash(COMMENT) == comment_hash(dict(COMMENT))

    def test_the_hash_is_a_short_hex_digest(self) -> None:
        """The recorded hash should be the documented 16 hex characters."""
        digest = comment_hash(COMMENT)

        assert len(digest) == 16
        assert all(character in "0123456789abcdef" for character in digest)

    def test_the_key_order_of_the_payload_does_not_matter(self) -> None:
        """A payload whose keys arrive in another order is the same comment."""
        reordered = {key: COMMENT[key] for key in reversed(list(COMMENT))}

        assert comment_hash(reordered) == comment_hash(COMMENT)

    def test_each_field_of_the_identity_changes_the_hash(self) -> None:
        """Editing any part of a comment should make it a different one."""
        variants = [
            {**COMMENT, "id": 8},
            {**COMMENT, "body": "Looks wrong to me"},
            {**COMMENT, "user": {"login": "bob"}},
            {**COMMENT, "created_at": "2026-08-01T09:00:01Z"},
            {**COMMENT, "updated_at": "2026-08-03T11:00:00Z"},
        ]

        digests = {comment_hash(variant) for variant in variants}

        assert comment_hash(COMMENT) not in digests
        # Each variant differs from every other, not merely from the original.
        assert len(digests) == len(variants)

    def test_a_body_cannot_be_confused_with_the_next_field(self) -> None:
        """Two comments differing only in where a field ends should hash apart.

        A serialization that joined the fields with a separator would hash these
        two identically, because the body of one ends with what begins the
        author of the other.
        """
        first = {**COMMENT, "body": "text", "user": {"login": "alice"}}
        second = {**COMMENT, "body": "text|alice", "user": {"login": ""}}

        assert comment_hash(first) != comment_hash(second)

    def test_a_payload_missing_every_field_still_hashes(self) -> None:
        """A comment the API answered without the usual fields must not raise."""
        assert len(comment_hash({})) == 16

    def test_a_malformed_author_hashes_as_no_author(self) -> None:
        """An author that is not an object should not fail the hash."""
        assert comment_hash({**COMMENT, "user": "alice"}) == comment_hash({**COMMENT, "user": None})


class TestUsableIdentifier:
    """Tests for the one reading every identifier a watch takes from a payload."""

    def test_a_whole_number_identifies_something(self) -> None:
        """The ordinary case has to come back unchanged."""
        assert usable_identifier(1854) == 1854
        assert usable_identifier(0) == 0

    @pytest.mark.parametrize("value", [None, "1854", 15.0, [1854], {"id": 1854}])
    def test_anything_that_is_not_a_whole_number_identifies_nothing(self, value: Any) -> None:
        """A payload with nonsense in the field should be refused, not coerced.

        Args:
            value: The value the payload carries for the identifier.

        """
        assert usable_identifier(value) is None

    @pytest.mark.parametrize("value", [True, False])
    def test_a_boolean_identifies_nothing(self, value: bool) -> None:
        """`bool` is an `int`, so the refusal has to be explicit about it.

        Every issue whose ID came back as a boolean would otherwise be cached
        under the same entry as every other.

        Args:
            value: The boolean the payload carries for the identifier.

        """
        assert usable_identifier(value) is None


class TestIssueKey:
    """Tests for the key an issue is recorded under."""

    def test_an_issue_is_keyed_by_its_global_id(self) -> None:
        """The key should be the global ID, not the number shown in the web UI."""
        assert issue_key(ISSUE) == "1854"

    def test_an_issue_without_a_usable_id_has_no_key(self) -> None:
        """A payload with no global ID, or a nonsense one, should be unkeyable."""
        assert issue_key({"number": 15}) is None
        assert issue_key({"id": "1854"}) is None
        # bool is an int, and would key two different issues under "True".
        assert issue_key({"id": True}) is None


class TestIssueSnapshot:
    """Tests for the fields a snapshot keeps."""

    def test_a_snapshot_keeps_the_fields_the_comparison_reads(self) -> None:
        """The snapshot should hold exactly what a watch compares and reports."""
        assert issue_snapshot(ISSUE, [COMMENT], repository="my-org/my-repo") == {
            "issue_id": 1854,
            "number": 15,
            "title": "Fix the docs",
            "repository": "my-org/my-repo",
            "updated_at": "2026-08-02T10:00:00Z",
            "assignees": ["alice", "bob"],
            "labels": ["bug", "docs"],
            "comment_hashes": [comment_hash(COMMENT)],
        }

    def test_the_order_the_api_lists_names_in_does_not_matter(self) -> None:
        """Two fetches differing only in order should snapshot identically."""
        reordered = {
            **ISSUE,
            "assignees": [{"login": "bob"}, {"login": "alice"}],
            "labels": [{"name": "docs"}, {"name": "bug"}],
        }

        assert issue_snapshot(reordered, [COMMENT]) == issue_snapshot(ISSUE, [COMMENT])

    def test_malformed_entries_narrow_the_snapshot_rather_than_failing_it(self) -> None:
        """An entry that names nothing should be dropped, not raised over."""
        malformed = {
            **ISSUE,
            "assignees": [{"login": "alice"}, "bob", {"name": "carol"}, None],
            "labels": "bug",
        }

        taken = issue_snapshot(malformed, ["not a comment", COMMENT])

        assert taken["assignees"] == ["alice"]
        assert taken["labels"] == []
        assert taken["comment_hashes"] == [comment_hash(COMMENT)]

    def test_an_identifier_that_is_not_a_whole_number_is_dropped(self) -> None:
        """A nonsense ID or number must not reach the report as if it were one."""
        taken = issue_snapshot({"id": True, "number": "15"}, [])

        assert taken["issue_id"] is None
        assert taken["number"] is None

    def test_a_missing_field_reads_as_its_empty_value(self) -> None:
        """An issue payload without the optional fields should still snapshot."""
        assert issue_snapshot({"id": 1854}, []) == {
            "issue_id": 1854,
            "number": None,
            "title": "",
            "repository": None,
            "updated_at": "",
            "assignees": [],
            "labels": [],
            "comment_hashes": [],
        }


class TestDetectChanges:
    """Tests for the comparison of a scope's snapshots against the recorded ones."""

    def test_a_scope_never_recorded_is_baselined(self) -> None:
        """The first sight of a scope should report nothing, whatever is in it."""
        assert detect_changes({"1854": snapshot()}, None) == []

    def test_an_unchanged_scope_reports_nothing(self) -> None:
        """Re-running against an unchanged scope should produce no records."""
        current = {"1854": snapshot()}

        assert detect_changes(current, {"1854": snapshot()}) == []

    def test_an_issue_absent_from_the_cache_is_new(self) -> None:
        """An issue a recorded scope has not seen should be reported as new."""
        changes = detect_changes({"1854": snapshot()}, {})

        assert [change["kind"] for change in changes] == ["new"]
        assert changes[0]["detail"] == "new issue"
        assert changes[0]["number"] == 15
        assert changes[0]["title"] == "Fix the docs"
        assert changes[0]["added"] == []
        assert changes[0]["removed"] == []

    def test_every_new_issue_is_reported_not_only_the_first(self) -> None:
        """Two issues opened between runs are two changes."""
        current = {"1854": snapshot(), "1900": snapshot(issue_id=1900, number=16)}

        changes = detect_changes(current, {})

        assert [change["number"] for change in changes] == [15, 16]

    def test_a_snapshot_missing_a_field_compares_as_if_it_were_empty(self) -> None:
        """A snapshot built without every field should compare rather than raise.

        The snapshots the cache and `issue_snapshot` produce always carry every
        field, so this is the case a library caller building its own reaches.
        """
        changes = detect_changes({"1854": {"number": 15, "assignees": ["alice"]}}, {"1854": {"number": 15}})

        assert [change["kind"] for change in changes] == ["assignees"]
        assert changes[0]["added"] == ["alice"]
        assert changes[0]["title"] == ""

    def test_an_assignee_change_names_who_arrived_and_who_left(self) -> None:
        """Both halves of an assignment change should be reported."""
        changes = detect_changes({"1854": snapshot(assignees=["alice", "carol"])}, {"1854": snapshot()})

        assert [change["kind"] for change in changes] == ["assignees"]
        assert changes[0]["added"] == ["carol"]
        assert changes[0]["removed"] == ["bob"]
        assert changes[0]["detail"] == "+carol -bob"

    def test_a_label_change_names_the_labels(self) -> None:
        """A label added and one removed should be reported as one record."""
        changes = detect_changes({"1854": snapshot(labels=["bug", "urgent"])}, {"1854": snapshot()})

        assert [change["kind"] for change in changes] == ["labels"]
        assert changes[0]["added"] == ["urgent"]
        assert changes[0]["removed"] == ["docs"]

    def test_a_new_comment_is_reported_by_its_hash(self) -> None:
        """A comment the cache has not seen should be reported as new."""
        added = comment_hash({**COMMENT, "id": 8})
        changes = detect_changes(
            {"1854": snapshot(comment_hashes=sorted([comment_hash(COMMENT), added]))},
            {"1854": snapshot()},
        )

        assert [change["kind"] for change in changes] == ["comments"]
        assert changes[0]["added"] == [added]
        assert changes[0]["removed"] == []
        assert changes[0]["detail"] == "1 new"

    def test_a_deleted_comment_is_reported_too(self) -> None:
        """A comment that went away is a change, not a return to no change."""
        changes = detect_changes({"1854": snapshot(comment_hashes=[])}, {"1854": snapshot()})

        assert [change["kind"] for change in changes] == ["comments"]
        assert changes[0]["removed"] == [comment_hash(COMMENT)]
        assert changes[0]["detail"] == "1 removed"

    def test_a_comment_replaced_by_another_is_two_movements_not_none(self) -> None:
        """Comparing counts rather than hashes would report nothing here."""
        changes = detect_changes(
            {"1854": snapshot(comment_hashes=[comment_hash({**COMMENT, "id": 8})])},
            {"1854": snapshot()},
        )

        assert [change["kind"] for change in changes] == ["comments"]
        assert changes[0]["detail"] == "1 new, 1 removed"

    def test_an_issue_no_longer_listed_is_reported_from_the_cache(self) -> None:
        """An issue that dropped out of the scope should still be nameable."""
        changes = detect_changes({}, {"1854": snapshot()})

        assert [change["kind"] for change in changes] == ["gone"]
        assert changes[0]["detail"] == "no longer listed"
        # The issue is gone, so everything naming it comes from the cache.
        assert changes[0]["number"] == 15
        assert changes[0]["title"] == "Fix the docs"

    def test_an_issue_that_changed_in_several_ways_reports_each_of_them(self) -> None:
        """One record per change reads better in a digest than one naming three."""
        changes = detect_changes(
            {"1854": snapshot(assignees=["alice"], labels=["bug"], comment_hashes=[])},
            {"1854": snapshot()},
        )

        assert [change["kind"] for change in changes] == ["assignees", "labels", "comments"]

    def test_a_report_does_not_depend_on_the_order_the_issues_were_fetched(self) -> None:
        """Two fetches of the same changes should report them in the same order."""
        previous = {"11": snapshot(number=3), "22": snapshot(number=1), "33": snapshot(number=2)}
        current = {key: {**value, "labels": []} for key, value in previous.items()}

        forwards = detect_changes(current, previous)
        backwards = detect_changes(dict(reversed(list(current.items()))), previous)

        assert [change["number"] for change in forwards] == [1, 2, 3]
        assert forwards == backwards

    def test_a_change_record_carries_the_same_keys_whatever_the_kind(self) -> None:
        """A consumer should be able to read `added` without asking the kind first."""
        changes = detect_changes(
            {"1854": snapshot(assignees=["alice"]), "1855": snapshot(issue_id=1855, number=16)},
            {"1854": snapshot(), "1900": snapshot(issue_id=1900, number=17)},
        )

        assert {change["kind"] for change in changes} == {"assignees", "new", "gone"}
        for change in changes:
            assert set(change) == {
                "kind",
                "issue_id",
                "number",
                "title",
                "repository",
                "detail",
                "added",
                "removed",
            }


class TestFormatChange:
    """Tests for the line the human digest prints."""

    def test_a_change_is_named_by_the_reference_a_browser_takes(self) -> None:
        """The line should name the issue the way it is written in prose."""
        change = detect_changes({"1854": snapshot(assignees=["alice"])}, {"1854": snapshot()})[0]

        assert format_change(change) == "my-org/my-repo#15 assignees: -bob · Fix the docs"

    def test_an_issue_of_an_unknown_repository_is_named_by_its_number(self) -> None:
        """A card whose repository could not be determined is still nameable."""
        change = detect_changes({"1854": snapshot(repository=None, assignees=["alice"])}, {"1854": snapshot()})[0]

        assert format_change(change) == "#15 assignees: -bob · Fix the docs"

    def test_an_issue_without_a_number_is_named_by_its_global_id(self) -> None:
        """The last resort names the issue by the only identifier there is."""
        change = detect_changes({"1854": snapshot(number=None, assignees=["alice"])}, {"1854": snapshot()})[0]

        assert format_change(change).startswith("issue 1854 assignees:")

    def test_an_untitled_issue_does_not_trail_a_separator(self) -> None:
        """A missing title should leave the line ending on the change itself."""
        change = detect_changes({"1854": snapshot(title="", assignees=["alice"])}, {"1854": snapshot()})[0]

        assert format_change(change) == "my-org/my-repo#15 assignees: -bob"
