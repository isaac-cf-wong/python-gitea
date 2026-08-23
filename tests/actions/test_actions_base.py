"""Unit tests for the BaseActions class."""

from __future__ import annotations

import pytest

from gitea.actions.base import BaseActions, _query_flag


class TestActionsEndpoints:
    """The paths the Actions endpoints are addressed by."""

    def test_list_workflows_endpoint(self) -> None:
        """The workflows of a repository sit under its actions path."""
        assert BaseActions()._list_workflows_endpoint("o", "r") == "/repos/o/r/actions/workflows"

    def test_get_workflow_endpoint(self) -> None:
        """A workflow is addressed by its file name, not by a number."""
        assert BaseActions()._get_workflow_endpoint("o", "r", "build.yml") == "/repos/o/r/actions/workflows/build.yml"

    def test_dispatch_workflow_endpoint(self) -> None:
        """A dispatch is a POST to the workflow's dispatches path."""
        assert (
            BaseActions()._dispatch_workflow_endpoint("o", "r", "build.yml")
            == "/repos/o/r/actions/workflows/build.yml/dispatches"
        )

    def test_list_workflow_runs_endpoint_for_the_repository(self) -> None:
        """Without a workflow, the runs of every workflow are listed."""
        assert BaseActions()._list_workflow_runs_endpoint("o", "r") == "/repos/o/r/actions/runs"

    def test_list_workflow_runs_endpoint_for_one_workflow(self) -> None:
        """With a workflow, the endpoint is the workflow's own runs path.

        The two are different endpoints rather than the same one with a filter,
        so a `--workflow-id` that reached the repository-wide path would list
        every run of the repository and look like a filter that does nothing.
        """
        assert (
            BaseActions()._list_workflow_runs_endpoint("o", "r", "build.yml")
            == "/repos/o/r/actions/workflows/build.yml/runs"
        )

    def test_get_workflow_run_endpoint(self) -> None:
        """A run is addressed by its ID."""
        assert BaseActions()._get_workflow_run_endpoint("o", "r", 42) == "/repos/o/r/actions/runs/42"

    def test_list_workflow_run_jobs_endpoint(self) -> None:
        """The jobs of a run sit under the run."""
        assert BaseActions()._list_workflow_run_jobs_endpoint("o", "r", 42) == "/repos/o/r/actions/runs/42/jobs"

    def test_get_workflow_job_endpoint(self) -> None:
        """A job is addressed by its ID, under the repository rather than the run.

        Gitea addresses a job directly, so reading one takes no run ID - which
        is why `job get` and `job logs` ask for `--job-id` alone.
        """
        assert BaseActions()._get_workflow_job_endpoint("o", "r", 118) == "/repos/o/r/actions/jobs/118"

    def test_get_workflow_job_logs_endpoint(self) -> None:
        """The logs of a job sit under the job."""
        assert BaseActions()._get_workflow_job_logs_endpoint("o", "r", 118) == "/repos/o/r/actions/jobs/118/logs"


class TestDispatchWorkflowHelper:
    """What a dispatch asks for, and what it sends."""

    def test_the_ref_is_the_whole_body_by_default(self) -> None:
        """A dispatch with no inputs sends the ref alone, and no parameters."""
        endpoint, params, payload = BaseActions()._dispatch_workflow_helper(
            owner="o", repository="r", workflow_id="build.yml", ref="refs/heads/main"
        )

        assert endpoint == "/repos/o/r/actions/workflows/build.yml/dispatches"
        assert params == {}
        assert payload == {"ref": "refs/heads/main"}

    def test_inputs_are_sent_as_given(self) -> None:
        """Inputs reach the body under `inputs`, keyed as the workflow declares them."""
        _, _, payload = BaseActions()._dispatch_workflow_helper(
            owner="o",
            repository="r",
            workflow_id="build.yml",
            ref="main",
            inputs={"environment": "staging"},
        )

        assert payload == {"ref": "main", "inputs": {"environment": "staging"}}

    def test_empty_inputs_are_still_sent(self) -> None:
        """An explicitly empty mapping is sent, where None is not.

        `None` means the caller passed no inputs; `{}` means it passed a mapping
        that happens to be empty. Collapsing the two would make an inputs
        dictionary built up by a caller - and found to be empty - indistinguishable
        from one never offered.
        """
        _, _, payload = BaseActions()._dispatch_workflow_helper(
            owner="o", repository="r", workflow_id="build.yml", ref="main", inputs={}
        )

        assert payload == {"ref": "main", "inputs": {}}

    @pytest.mark.parametrize(("asked", "sent"), [(True, "true"), (False, "false")])
    def test_the_run_details_flag_is_spelled_for_the_api(self, asked: bool, sent: str) -> None:
        """The flag reaches the query string as `true` or `false`, never as a Python bool.

        `yarl`, which the asynchronous client builds its URLs with, refuses a
        `bool` outright, so a flag passed through as one fails there while
        working through `requests` - which would send `True`. Both clients send
        the API's own spelling instead.
        """
        _, params, _ = BaseActions()._dispatch_workflow_helper(
            owner="o", repository="r", workflow_id="build.yml", ref="main", return_run_details=asked
        )

        assert params == {"return_run_details": sent}

    def test_the_run_details_flag_is_omitted_when_not_asked_about(self) -> None:
        """None leaves the parameter out, so the request is the one older instances know."""
        _, params, _ = BaseActions()._dispatch_workflow_helper(
            owner="o", repository="r", workflow_id="build.yml", ref="main", return_run_details=None
        )

        assert params == {}


class TestListWorkflowRunsHelper:
    """What a run listing asks for."""

    def test_no_filters_asks_for_nothing(self) -> None:
        """A listing with no filters carries no query parameters."""
        endpoint, params = BaseActions()._list_workflow_runs_helper(owner="o", repository="r")

        assert endpoint == "/repos/o/r/actions/runs"
        assert params == {}

    def test_every_filter_is_forwarded(self) -> None:
        """Each filter reaches the query string under the API's own name."""
        endpoint, params = BaseActions()._list_workflow_runs_helper(
            owner="o",
            repository="r",
            workflow_id="build.yml",
            event="push",
            branch="main",
            status="in_progress",
            actor="someone",
            head_sha="deadbeef",
            exclude_pull_requests=True,
            page=2,
            limit=5,
        )

        assert endpoint == "/repos/o/r/actions/workflows/build.yml/runs"
        assert params == {
            "event": "push",
            "branch": "main",
            "status": "in_progress",
            "actor": "someone",
            "head_sha": "deadbeef",
            "exclude_pull_requests": "true",
            "page": 2,
            "limit": 5,
        }

    @pytest.mark.parametrize(("asked", "sent"), [(True, "true"), (False, "false")])
    def test_the_pull_request_flag_is_spelled_for_the_api(self, asked: bool, sent: str) -> None:
        """The flag is written as the API writes it, for the reason above."""
        _, params = BaseActions()._list_workflow_runs_helper(owner="o", repository="r", exclude_pull_requests=asked)

        assert params == {"exclude_pull_requests": sent}


class TestListWorkflowRunJobsHelper:
    """What a job listing asks for."""

    def test_no_filters_asks_for_nothing(self) -> None:
        """A listing with no filters carries no query parameters."""
        endpoint, params = BaseActions()._list_workflow_run_jobs_helper(owner="o", repository="r", run_id=42)

        assert endpoint == "/repos/o/r/actions/runs/42/jobs"
        assert params == {}

    def test_every_filter_is_forwarded(self) -> None:
        """Each filter reaches the query string under the API's own name."""
        _, params = BaseActions()._list_workflow_run_jobs_helper(
            owner="o", repository="r", run_id=42, status="failure", page=3, limit=7
        )

        assert params == {"status": "failure", "page": 3, "limit": 7}


@pytest.mark.parametrize(("value", "spelling"), [(True, "true"), (False, "false")])
def test_query_flag_spells_a_boolean_for_a_query_string(value: bool, spelling: str) -> None:
    """A flag is written lowercase, which is what both HTTP clients can carry."""
    assert _query_flag(value) == spelling


@pytest.mark.parametrize(
    "params",
    [
        BaseActions()._dispatch_workflow_helper(
            owner="o", repository="r", workflow_id="build.yml", ref="main", return_run_details=True
        )[1],
        BaseActions()._list_workflow_runs_helper(owner="o", repository="r", exclude_pull_requests=True, page=2)[1],
    ],
    ids=["dispatch", "runs"],
)
def test_the_parameters_can_be_carried_by_the_asynchronous_client(params: dict[str, object]) -> None:
    """Every query parameter should be a value the asynchronous client can put in a URL.

    `aiohttp` builds its URLs with `yarl`, which refuses a `bool` rather than
    encoding it, so a flag left as one raises there while going out as `True`
    through `requests` - a resource that works in one client and not the other.
    Building the URL here is what makes that a failure rather than a rationale
    written in a comment.
    """
    from yarl import URL

    url = URL("https://gitea.invalid/api/v1/repos/o/r/actions/runs").with_query(params)

    assert dict(url.query) == {name: str(value) for name, value in params.items()}
