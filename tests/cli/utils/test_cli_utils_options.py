"""Unit tests for the readers of the options every resource command shares."""

from __future__ import annotations

import logging

import pytest

from gitea.cli.utils.errors import CommandError
from gitea.cli.utils.options import reporting_scope_errors, require_repository, resolve_issue_id


class TestRequireRepository:
    """Test cases for `require_repository`."""

    def test_returns_the_repository_it_was_given(self):
        """A repository the user named should come back unchanged."""
        assert require_repository("my-repo", command="gitea-cli issue get") == "my-repo"

    def test_omitted_repository_is_an_actionable_error(self):
        """Omitting --repository should say what to pass, and for which command."""
        with pytest.raises(CommandError) as excinfo:
            require_repository(None, command="gitea-cli label list")

        message = str(excinfo.value)
        assert "gitea-cli label list" in message
        assert "--repository REPOSITORY" in message
        # The user is told why the option looked optional in the first place.
        assert "gitea-cli project" in message

    def test_omitted_repository_does_not_raise_a_bare_error(self):
        """The error should be the kind the CLI reports without a traceback."""
        with pytest.raises(CommandError):
            require_repository(None, command="gitea-cli issue get")


class TestResolveIssueId:
    """Test cases for `resolve_issue_id`."""

    def test_returns_the_issue_id_it_was_given(self, caplog: pytest.LogCaptureFixture):
        """--issue-id alone should be used as-is and warn about nothing."""
        with caplog.at_level(logging.WARNING, logger="gitea"):
            assert resolve_issue_id(issue_id=15, index=None, command="gitea-cli issue get") == 15

        assert caplog.records == []

    def test_accepts_the_deprecated_index(self, caplog: pytest.LogCaptureFixture):
        """--index should still name the issue, so existing scripts keep working."""
        with caplog.at_level(logging.WARNING, logger="gitea"):
            assert resolve_issue_id(issue_id=None, index=15, command="gitea-cli issue get") == 15

        assert [record.levelname for record in caplog.records] == ["WARNING"]
        message = caplog.records[0].getMessage()
        assert "--index is deprecated" in message
        assert "--issue-id" in message

    def test_warns_even_when_both_names_agree(self, caplog: pytest.LogCaptureFixture):
        """Passing both names should still report that one of them is deprecated."""
        with caplog.at_level(logging.WARNING, logger="gitea"):
            assert resolve_issue_id(issue_id=15, index=15, command="gitea-cli issue get") == 15

        assert len(caplog.records) == 1

    def test_both_names_with_different_values_is_an_error(self):
        """Two values for one issue should be refused rather than silently picked between."""
        with pytest.raises(CommandError) as excinfo:
            resolve_issue_id(issue_id=15, index=16, command="gitea-cli issue get")

        message = str(excinfo.value)
        assert "15" in message
        assert "16" in message
        assert "--issue-id" in message
        assert "--index" in message

    def test_neither_name_is_an_actionable_error(self):
        """Naming no issue at all should say which option names one."""
        with pytest.raises(CommandError) as excinfo:
            resolve_issue_id(issue_id=None, index=None, command="gitea-cli issue edit")

        message = str(excinfo.value)
        assert "gitea-cli issue edit" in message
        assert "--issue-id" in message

    def test_reports_the_option_names_it_was_given(self, caplog: pytest.LogCaptureFixture):
        """A second issue in the same command should be reported by its own option names."""
        with caplog.at_level(logging.WARNING, logger="gitea"):
            resolved = resolve_issue_id(
                issue_id=None,
                index=7,
                command="gitea-cli issue dependency add",
                option="--dependency-issue-id",
                deprecated_option="--dependency-index",
            )

        assert resolved == 7
        message = caplog.records[0].getMessage()
        assert "--dependency-index is deprecated" in message
        assert "--dependency-issue-id" in message
        # The primary issue's options must not be named in the secondary one's warning.
        assert "--index is" not in message

    def test_missing_second_issue_names_its_own_option(self):
        """The error for a missing second issue should name that issue's option."""
        with pytest.raises(CommandError) as excinfo:
            resolve_issue_id(
                issue_id=None,
                index=None,
                command="gitea-cli issue dependency add",
                option="--dependency-issue-id",
                deprecated_option="--dependency-index",
            )

        assert "--dependency-issue-id" in str(excinfo.value)


class TestReportingScopeErrors:
    """Test cases for `reporting_scope_errors`."""

    def test_a_block_that_succeeds_is_left_alone(self):
        """The conversion should be invisible when nothing was refused."""
        with reporting_scope_errors("gitea-cli actions secret list"):
            outcome = "done"

        assert outcome == "done"

    def test_a_refused_scope_becomes_a_reportable_error(self):
        """A `ValueError` from the client should become the kind of error the CLI reports.

        The distinction matters: a `CommandError` reaches the user as its message,
        and anything else reaches them as a traceback. The rule about which scopes
        exist lives in the client, so this conversion is the whole of the CLI's
        part in it.
        """
        with pytest.raises(CommandError) as excinfo, reporting_scope_errors("gitea-cli actions secret list"):
            raise ValueError("Gitea has no Actions endpoint here for the authenticated account.")

        message = str(excinfo.value)
        assert "gitea-cli actions secret list" in message
        assert "the authenticated account" in message

    def test_the_original_message_is_carried_through_verbatim(self):
        """The client's sentence should not be paraphrased, since it names what to pass instead."""
        with (
            pytest.raises(CommandError, match="offered for a repository or an organization"),
            reporting_scope_errors("gitea-cli actions secret list"),
        ):
            raise ValueError("this one is offered for a repository or an organization")

    def test_other_failures_are_left_to_be_reported_as_failures(self):
        """Only a `ValueError` is converted; a real fault should still raise as itself.

        Converting everything would turn a bug into a one-line message with no
        traceback, which is exactly the case where the traceback is what is
        wanted.
        """
        with pytest.raises(RuntimeError), reporting_scope_errors("gitea-cli actions secret list"):
            raise RuntimeError("something is actually broken")

    def test_the_refusal_keeps_its_cause(self):
        """The original error should be chained, so a debugger can still reach it."""
        original = ValueError("no such scope")

        with pytest.raises(CommandError) as excinfo, reporting_scope_errors("gitea-cli actions runner list"):
            raise original

        assert excinfo.value.__cause__ is original
