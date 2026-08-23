"""Unit tests for the Actions artifact commands.

The three that read are the usual forwarding checks. `download` is not: it writes
the archive to a path, and the two things it refuses to do - overwrite a file, and
save an artifact whose archive is gone - are the reason it has more tests than its
neighbours. Both refusals are what stands between a caller and a file it did not
mean to have.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from typer.testing import CliRunner

from gitea.cli.actions.artifact.delete import delete_artifact_command
from gitea.cli.actions.artifact.download import download_artifact_command
from gitea.cli.actions.artifact.get import get_artifact_command
from gitea.cli.actions.artifact.list import list_artifacts_command
from gitea.cli.utils.errors import CommandError
from tests.cli.actions.invoking import api_call_of, invoke

OWNER = "owner"
REPOSITORY = "repo"
RUN_ID = 42
ARTIFACT_ID = 9

# Bytes that are not valid UTF-8, so a command that decoded the archive on its way
# to the file would write something other than what it was answered with.
ARCHIVE = b"PK\x03\x04\xff\xfe zip \x00"

CREDENTIALS = {"account_name": "acct", "token": None, "base_url": None}


def test_every_filter_of_the_listing_reaches_the_client() -> None:
    """Both narrowings should be forwarded, since either dropped lists more than was asked."""
    invocation = invoke(
        list_artifacts_command,
        {
            "owner": OWNER,
            "repository": REPOSITORY,
            "run_id": RUN_ID,
            "name": "dist",
            **CREDENTIALS,
        },
        method="list_artifacts",
    )

    assert invocation.command_name == "gitea-cli actions artifact list"
    invocation.client.actions.list_artifacts.assert_called_once_with(
        owner=OWNER, repository=REPOSITORY, run_id=RUN_ID, name="dist"
    )


def test_the_listing_without_a_run_asks_for_the_whole_repository() -> None:
    """Omitting the run should forward None, which is the repository-wide endpoint.

    The two are different endpoints rather than one with a filter, so a command
    substituting anything for the missing run would address the wrong one.
    """
    invocation = invoke(
        list_artifacts_command,
        {"owner": OWNER, "repository": REPOSITORY, "run_id": None, "name": None, **CREDENTIALS},
        method="list_artifacts",
    )

    assert invocation.client.actions.list_artifacts.call_args[1]["run_id"] is None


@pytest.mark.parametrize(
    ("command", "method", "command_name"),
    [
        (get_artifact_command, "get_artifact", "gitea-cli actions artifact get"),
        (delete_artifact_command, "delete_artifact", "gitea-cli actions artifact delete"),
    ],
    ids=["get", "delete"],
)
def test_the_single_artifact_commands_address_the_artifact(command: object, method: str, command_name: str) -> None:
    """Reading and deleting should name the artifact and the repository it belongs to."""
    invocation = invoke(
        command,
        {"owner": OWNER, "repository": REPOSITORY, "artifact_id": ARTIFACT_ID, **CREDENTIALS},
        method=method,
    )

    assert invocation.command_name == command_name
    getattr(invocation.client.actions, method).assert_called_once_with(
        owner=OWNER, repository=REPOSITORY, artifact_id=ARTIFACT_ID
    )


def download_arguments(file: Path, *, force: bool = False) -> dict:
    """Build the options a download is run with.

    Args:
        file: Where the archive is to be written.
        force: Whether an existing file may be overwritten.

    Returns:
        The options, credentials included.

    """
    return {
        "owner": OWNER,
        "repository": REPOSITORY,
        "artifact_id": ARTIFACT_ID,
        "file": file,
        "force": force,
        **CREDENTIALS,
    }


def test_a_download_writes_the_archive_as_it_arrived(tmp_path: Path) -> None:
    """The bytes should reach the file unchanged, and the report should name where they went.

    The archive here is not valid UTF-8, so a command that decoded it - as the job
    log command legitimately does with its own payload - would write a file that
    no longer opens as a zip. Comparing the bytes is what catches that; comparing
    the size alone would not.
    """
    file = tmp_path / "dist.zip"
    invocation = invoke(
        download_artifact_command,
        download_arguments(file),
        method="download_artifact",
        answer=(ARCHIVE, {"status_code": 200}),
        helper="execute_api_call",
    )

    assert file.read_bytes() == ARCHIVE
    data, metadata = invocation.returned
    assert data == {"artifact_id": ARTIFACT_ID, "path": str(file), "size_in_bytes": len(ARCHIVE)}
    assert metadata == {"status_code": 200}


def test_a_download_refuses_to_overwrite_a_file(tmp_path: Path) -> None:
    """An existing file should be left alone unless --force was passed."""
    file = tmp_path / "dist.zip"
    file.write_bytes(b"something else")

    api_call = api_call_of(
        download_artifact_command,
        download_arguments(file),
        method="download_artifact",
        answer=(ARCHIVE, {"status_code": 200}),
        helper="execute_api_call",
    )

    with pytest.raises(CommandError, match="will not overwrite"):
        api_call()

    assert file.read_bytes() == b"something else"


def test_a_download_overwrites_when_it_was_asked_to(tmp_path: Path) -> None:
    """With --force the existing file should be replaced, since that is what was asked."""
    file = tmp_path / "dist.zip"
    file.write_bytes(b"something else")

    invoke(
        download_artifact_command,
        download_arguments(file, force=True),
        method="download_artifact",
        answer=(ARCHIVE, {"status_code": 200}),
        helper="execute_api_call",
    )

    assert file.read_bytes() == ARCHIVE


def test_an_expired_artifact_is_reported_and_nothing_is_written(tmp_path: Path) -> None:
    """An empty answer should be reported rather than saved as an empty archive.

    Gitea keeps the record of an artifact after deleting its archive, and the
    download then answers with no body. Writing that out leaves a zero-byte file
    that looks like an artifact which was empty, so the file is not created at all
    and the message says where to read `expired`.
    """
    file = tmp_path / "dist.zip"

    api_call = api_call_of(
        download_artifact_command,
        download_arguments(file),
        method="download_artifact",
        answer=(b"", {"status_code": 200}),
        helper="execute_api_call",
    )

    with pytest.raises(CommandError, match="expired"):
        api_call()

    assert not file.exists()


# The two output modes of the download, run end to end. This is the one leaf
# command `test_json_mode_routes_every_subcommand_through_a_structured_path`
# cannot walk - a synthesized invocation would write a file into the working
# directory and hand a listing to `Path.write_bytes` - so the walk's two
# assertions are made here instead: that JSON mode emits the envelope and nothing
# else, and that text mode reports where the archive went.

INSTANCE = "https://gitea.invalid"
ACCOUNT = "seed"
ACCOUNT_TOKEN = "seed-token"

runner = CliRunner()


def run_download(tmp_path: Path, *arguments: str) -> tuple[object, Path]:
    """Run the download command against a session that answers with the archive.

    Args:
        tmp_path: The throwaway directory the configuration and the file live in.
        *arguments: Arguments to pass before the credentials.

    Returns:
        The result of the invocation and the path the archive was asked for at.

    """
    from gitea.cli.main import app
    from tests.transport import RawBytes, RecordingSession

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "default_account": ACCOUNT,
                "accounts": {ACCOUNT: {"name": ACCOUNT, "base_url": INSTANCE, "token": ACCOUNT_TOKEN}},
            }
        )
    )
    file = tmp_path / "dist.zip"
    session = RecordingSession(RawBytes(ARCHIVE))

    with patch("gitea.client.gitea.requests.Session", return_value=session):
        result = runner.invoke(
            app,
            [
                "--config-path",
                str(config_path),
                *arguments,
                "actions",
                "artifact",
                "download",
                "--owner",
                OWNER,
                "--repository",
                REPOSITORY,
                "--artifact-id",
                str(ARTIFACT_ID),
                "--file",
                str(file),
                "--account-name",
                ACCOUNT,
            ],
        )

    return result, file


def test_text_mode_names_the_file_and_its_size(tmp_path: Path) -> None:
    """Text output should be a line naming where the archive went, not the archive.

    The zip is never written to stdout: a caller reading stdout gets a
    confirmation, and the archive is at the path they named.
    """
    result, file = run_download(tmp_path)

    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == f"{file} ({len(ARCHIVE)} bytes)"
    assert file.read_bytes() == ARCHIVE


def test_json_mode_emits_the_envelope_and_nothing_else(tmp_path: Path) -> None:
    """JSON output should be the envelope, with the path and the size in its data."""
    from tests.cli.envelope import parse_envelope

    result, file = run_download(tmp_path, "--output", "json")

    assert result.exit_code == 0, result.output
    envelope = parse_envelope(result.stdout)
    assert envelope["data"] == {
        "artifact_id": ARTIFACT_ID,
        "path": str(file),
        "size_in_bytes": len(ARCHIVE),
    }
    assert set(envelope["metadata"]) == {"status_code"}
    assert file.read_bytes() == ARCHIVE
