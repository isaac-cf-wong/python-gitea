"""Unit tests for the cache of issue snapshots a watch run compares against."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import platformdirs
import pytest

from gitea.watch.state import (
    STATE_VERSION,
    default_state_path,
    empty_state,
    load_state,
    record_scope,
    resolve_state_path,
    save_scopes,
    save_state,
    scope_snapshots,
)

SNAPSHOT = {
    "issue_id": 1854,
    "number": 15,
    "title": "Fix the docs",
    "repository": "my-org/my-repo",
    "updated_at": "2026-08-02T10:00:00Z",
    "assignees": ["alice"],
    "labels": ["bug"],
    "comment_hashes": ["0123456789abcdef"],
}


class TestStatePath:
    """Tests for choosing the cache a run reads and writes."""

    def test_the_default_cache_lives_in_the_user_cache_directory(self) -> None:
        r"""The default should be a per-user cache file, not the config directory.

        Where the application's own directory sits inside the cache directory is
        the platform's business and not this library's: POSIX ends the path with
        it (`~/.cache/gitea`), while Windows follows it with a `Cache` component
        (`...\AppData\Local\gitea\gitea\Cache`). So what is asserted is that
        the application names a whole component of the path - a directory merely
        containing those letters is not this application's - and that the cache
        directory is the one the file sits in.

        The cache is not the configuration, which is where this CLI keeps the
        accounts, and that is asserted against the file the config directory
        would hold rather than against the directory: on Windows `user_config_dir`
        is the parent of `user_cache_dir`, so a cache path is under the config
        directory there and asserting otherwise would fail on Windows alone.
        """
        path = default_state_path()

        assert path.name == "watch-state.json"
        assert "gitea" in path.parts
        assert Path(platformdirs.user_cache_dir(appname="gitea")) in path.parents
        assert path != Path(platformdirs.user_config_dir(appname="gitea")) / "watch-state.json"

    def test_a_named_path_wins_over_the_default(self, tmp_path: Path) -> None:
        """Naming a cache should be what decides where the snapshots go."""
        assert resolve_state_path(tmp_path / "elsewhere.json") == tmp_path / "elsewhere.json"

    def test_a_home_relative_path_is_expanded(self) -> None:
        """`~` should name the user's home rather than a directory called `~`."""
        assert resolve_state_path("~/watch.json") == Path.home() / "watch.json"

    def test_no_path_falls_back_to_the_default(self) -> None:
        """Omitting the option should use the default location."""
        assert resolve_state_path(None) == default_state_path()
        assert resolve_state_path("") == default_state_path()


class TestRoundTrip:
    """Tests for writing the cache and reading it back."""

    def test_snapshots_survive_a_write_and_a_read(self, tmp_path: Path) -> None:
        """What one run records should be what the next run compares against."""
        path = tmp_path / "watch-state.json"
        state = empty_state()
        record_scope(state, "repo:my-org/my-repo", {"1854": SNAPSHOT})

        save_state(path, state)

        assert scope_snapshots(load_state(path), "repo:my-org/my-repo") == {"1854": SNAPSHOT}

    def test_the_cache_directory_is_created(self, tmp_path: Path) -> None:
        """A first run should not fail because the cache directory is absent."""
        path = tmp_path / "nested" / "deeper" / "watch-state.json"

        save_state(path, empty_state())

        assert path.exists()

    def test_the_document_records_the_version_it_was_written_by(self, tmp_path: Path) -> None:
        """The version should be stamped, so a future reader can act on it."""
        path = tmp_path / "watch-state.json"

        save_state(path, {"scopes": {}})

        assert json.loads(path.read_text(encoding="utf-8"))["version"] == STATE_VERSION

    def test_several_scopes_are_kept_apart(self, tmp_path: Path) -> None:
        """Watching two scopes should not let one scope's issues answer for the other."""
        path = tmp_path / "watch-state.json"
        state = empty_state()
        record_scope(state, "repo:my-org/my-repo", {"1854": SNAPSHOT})
        record_scope(state, "project:my-org/29", {"1900": {**SNAPSHOT, "issue_id": 1900}})

        save_state(path, state)
        loaded = load_state(path)

        assert list(scope_snapshots(loaded, "repo:my-org/my-repo")) == ["1854"]
        assert list(scope_snapshots(loaded, "project:my-org/29")) == ["1900"]

    def test_recording_one_scope_leaves_the_others_alone(self) -> None:
        """A run watching one scope must not drop the scopes it did not watch."""
        state = empty_state()
        record_scope(state, "repo:my-org/one", {"1": SNAPSHOT})
        record_scope(state, "repo:my-org/two", {"2": SNAPSHOT})

        record_scope(state, "repo:my-org/one", {})

        assert scope_snapshots(state, "repo:my-org/one") == {}
        assert list(scope_snapshots(state, "repo:my-org/two")) == ["2"]

    def test_a_key_this_version_does_not_know_survives_a_write(self, tmp_path: Path) -> None:
        """A cache written by a newer version should not be truncated by an older one."""
        path = tmp_path / "watch-state.json"
        path.write_text(json.dumps({"version": 99, "scopes": {}, "invented_later": {"keep": "me"}}))

        state = load_state(path)
        record_scope(state, "repo:my-org/my-repo", {"1854": SNAPSHOT})
        save_state(path, state)

        assert json.loads(path.read_text(encoding="utf-8"))["invented_later"] == {"keep": "me"}


class TestUnreadableCache:
    """Tests for the caches a run has to recover from rather than fail on."""

    @pytest.mark.parametrize(
        ("name", "content"),
        [
            ("empty", ""),
            ("truncated", '{"version": 1, "scopes": {"repo:my-org/my-repo": {"iss'),
            ("not json", "not json at all"),
            ("a list", "[]"),
            ("an object without scopes", '{"version": 1}'),
            ("scopes that are not a mapping", '{"version": 1, "scopes": []}'),
        ],
    )
    def test_an_unreadable_cache_reads_as_no_cache(self, tmp_path: Path, name: str, content: str) -> None:
        """Anything that is not a cache document should baseline rather than raise.

        Args:
            tmp_path: Directory to write the cache into.
            name: What the content is, for the failure message.
            content: The unreadable cache to write.

        """
        path = tmp_path / "watch-state.json"
        path.write_text(content, encoding="utf-8")

        assert load_state(path) == empty_state(), name

    def test_a_cache_that_is_not_utf_8_reads_as_no_cache(self, tmp_path: Path) -> None:
        """Bytes that are not text at all must re-baseline, not end the run.

        Decoding raises `UnicodeDecodeError`, which is a `ValueError` and not an
        `OSError`, so it escapes a handler catching only the latter - and a
        watchdog that exits on a corrupt cache never recovers from one.
        """
        path = tmp_path / "watch-state.json"
        path.write_bytes(b"\xff\xfe{\x00")

        with patch("gitea.watch.state.logger") as logger:
            assert load_state(path) == empty_state()

        assert logger.warning.call_count == 1

    def test_a_cache_truncated_mid_character_reads_as_no_cache(self, tmp_path: Path) -> None:
        """A write cut short between the bytes of one character is the same case."""
        path = tmp_path / "watch-state.json"
        # The first two bytes of "€" (e2 82 ac), as an interrupted write leaves.
        path.write_bytes(b'{"scopes": {"repo:my-org/my-repo\xe2\x82')

        assert load_state(path) == empty_state()

    def test_a_missing_cache_reads_as_no_cache(self, tmp_path: Path) -> None:
        """The ordinary first run has nothing to read and must not fail."""
        assert load_state(tmp_path / "absent.json") == empty_state()

    def test_a_missing_cache_is_not_worth_a_warning(self, tmp_path: Path) -> None:
        """A first run is expected, so it should say nothing about it."""
        with patch("gitea.watch.state.logger") as logger:
            load_state(tmp_path / "absent.json")

        assert logger.warning.call_count == 0

    def test_losing_a_cache_that_existed_is_worth_a_warning(self, tmp_path: Path) -> None:
        """Re-baselining silently would hide that a window of changes was lost."""
        path = tmp_path / "watch-state.json"
        path.write_text("not json at all", encoding="utf-8")

        with patch("gitea.watch.state.logger") as logger:
            load_state(path)

        assert logger.warning.call_count == 1

    def test_a_cache_that_cannot_be_opened_reads_as_no_cache(self, tmp_path: Path) -> None:
        """A directory where the cache should be is not a reason to fail the run."""
        path = tmp_path / "watch-state.json"
        path.mkdir()

        with patch("gitea.watch.state.logger") as logger:
            assert load_state(path) == empty_state()

        assert logger.warning.call_count == 1


class TestReadingSnapshots:
    """Tests for how leniently a recorded snapshot is read back."""

    def test_a_scope_with_no_entry_is_told_apart_from_an_empty_one(self) -> None:
        """None baselines the scope; an empty mapping reports every issue as gone."""
        state = empty_state()
        record_scope(state, "repo:my-org/my-repo", {})

        assert scope_snapshots(state, "repo:my-org/other") is None
        assert scope_snapshots(state, "repo:my-org/my-repo") == {}

    def test_a_field_added_by_a_newer_version_is_ignored(self, tmp_path: Path) -> None:
        """An unknown field in a snapshot should not be fatal to an older reader."""
        path = tmp_path / "watch-state.json"
        path.write_text(
            json.dumps({"scopes": {"s": {"issues": {"1854": {**SNAPSHOT, "invented_later": ["a", "b"]}}}}}),
            encoding="utf-8",
        )

        assert scope_snapshots(load_state(path), "s") == {"1854": SNAPSHOT}

    def test_a_field_the_document_lacks_reads_as_its_empty_value(self) -> None:
        """A snapshot recorded before a field existed should still compare."""
        state = {"scopes": {"s": {"issues": {"1854": {"assignees": ["alice"]}}}}}

        assert scope_snapshots(state, "s") == {
            "1854": {
                "issue_id": None,
                "number": None,
                "title": "",
                "repository": None,
                "updated_at": "",
                "assignees": ["alice"],
                "labels": [],
                "comment_hashes": [],
            }
        }

    def test_a_malformed_field_reads_as_its_empty_value(self) -> None:
        """A field of the wrong type should narrow the snapshot, not raise."""
        state = {"scopes": {"s": {"issues": {"1854": {"assignees": "alice", "labels": [1, "bug", None]}}}}}

        snapshots = scope_snapshots(state, "s")

        assert snapshots["1854"]["assignees"] == []
        assert snapshots["1854"]["labels"] == ["bug"]

    def test_an_entry_that_is_not_a_snapshot_is_dropped(self) -> None:
        """One unreadable issue should not take the rest of the scope with it."""
        state = {"scopes": {"s": {"issues": {"1854": SNAPSHOT, "1900": "not a snapshot"}}}}

        assert list(scope_snapshots(state, "s")) == ["1854"]

    def test_a_scope_whose_issues_are_not_a_mapping_reads_as_recorded_and_empty(self) -> None:
        """A malformed entry should not be mistaken for a scope never seen."""
        assert scope_snapshots({"scopes": {"s": {"issues": []}}}, "s") == {}

    def test_a_scope_entry_that_is_not_an_object_reads_as_never_recorded(self) -> None:
        """There is nothing to compare against, so the scope is baselined again."""
        assert scope_snapshots({"scopes": {"s": "nonsense"}}, "s") is None

    def test_names_are_read_back_sorted(self) -> None:
        """A hand-edited cache must not report a change on order alone."""
        state = {"scopes": {"s": {"issues": {"1854": {"assignees": ["bob", "alice"]}}}}}

        assert scope_snapshots(state, "s")["1854"]["assignees"] == ["alice", "bob"]


class TestSaveScopes:
    """Tests for recording only the scopes a run watched."""

    def test_the_scopes_given_are_recorded(self, tmp_path: Path) -> None:
        """The ordinary case still writes what it was handed."""
        path = tmp_path / "watch-state.json"

        save_scopes(path, {"repo:my-org/my-repo": {"1854": SNAPSHOT}})

        assert scope_snapshots(load_state(path), "repo:my-org/my-repo") == {"1854": SNAPSHOT}

    def test_a_scope_recorded_while_the_run_was_working_survives(self, tmp_path: Path) -> None:
        """A concurrent run's scope must not be erased by this one's write.

        Writing back the document this run loaded would put back the cache as it
        was when the run started, dropping the scope the other run recorded in
        the meantime - and reporting every issue in it as new on the next run.
        """
        path = tmp_path / "watch-state.json"

        # Another run finished and recorded its own scope after this one loaded
        # the cache and before it came to write.
        concurrent = empty_state()
        record_scope(concurrent, "repo:my-org/two", {"2": SNAPSHOT})
        save_state(path, concurrent)

        save_scopes(path, {"repo:my-org/one": {"1": SNAPSHOT}})

        loaded = load_state(path)
        assert list(scope_snapshots(loaded, "repo:my-org/one")) == ["1"]
        assert list(scope_snapshots(loaded, "repo:my-org/two")) == ["2"]

    def test_the_scopes_given_replace_what_was_recorded_for_them(self, tmp_path: Path) -> None:
        """Merging is per scope, not per issue: a scope is what the run just saw."""
        path = tmp_path / "watch-state.json"
        save_scopes(path, {"repo:my-org/one": {"1": SNAPSHOT, "2": SNAPSHOT}})

        save_scopes(path, {"repo:my-org/one": {"1": SNAPSHOT}})

        assert list(scope_snapshots(load_state(path), "repo:my-org/one")) == ["1"]

    def test_an_unreadable_cache_is_replaced_rather_than_failing_the_write(self, tmp_path: Path) -> None:
        """Re-reading before writing must not make a corrupt cache fatal."""
        path = tmp_path / "watch-state.json"
        path.write_text("not json at all", encoding="utf-8")

        save_scopes(path, {"repo:my-org/one": {"1": SNAPSHOT}})

        assert list(scope_snapshots(load_state(path), "repo:my-org/one")) == ["1"]


class TestAtomicWrite:
    """Tests for a cache write that a reader can never catch half done."""

    def test_the_write_leaves_no_temporary_file_behind(self, tmp_path: Path) -> None:
        """The cache directory should hold the cache and nothing else."""
        path = tmp_path / "watch-state.json"

        save_state(path, empty_state())

        assert [entry.name for entry in tmp_path.iterdir()] == ["watch-state.json"]

    def test_a_failed_write_leaves_the_previous_cache_intact(self, tmp_path: Path) -> None:
        """A run interrupted mid-write must not cost the snapshots already recorded.

        Writing in place would leave a truncated document here, which the next
        run would recover from by baselining - losing the window of changes the
        cache exists to report.
        """
        path = tmp_path / "watch-state.json"
        state = empty_state()
        record_scope(state, "repo:my-org/my-repo", {"1854": SNAPSHOT})
        save_state(path, state)
        recorded = path.read_bytes()

        with (
            patch("gitea.watch.state.json.dump", side_effect=OSError("No space left on device")),
            pytest.raises(OSError, match="No space left on device"),
        ):
            save_state(path, empty_state())

        assert path.read_bytes() == recorded
        assert [entry.name for entry in tmp_path.iterdir()] == ["watch-state.json"]
