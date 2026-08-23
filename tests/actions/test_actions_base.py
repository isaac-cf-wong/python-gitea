"""Unit tests for the BaseActions class."""

from __future__ import annotations

import pytest

from gitea.actions.base import (
    LISTING_SCOPES,
    RUNNER_SCOPES,
    SECRET_ENTRY_SCOPES,
    SECRET_SCOPES,
    VARIABLE_SCOPES,
    BaseActions,
    _query_flag,
)
from gitea.actions.scope import ADMIN, EVERY_SCOPE, ORGANIZATION, REPOSITORY, USER


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

    @pytest.mark.parametrize(
        ("coordinates", "path"),
        [
            ({"owner": "o"}, "/orgs/o/actions/runs"),
            ({}, "/user/actions/runs"),
            ({"admin": True}, "/admin/actions/runs"),
        ],
        ids=["organization", "account", "instance"],
    )
    def test_the_listing_exists_at_every_scope(self, coordinates: dict[str, object], path: str) -> None:
        """The same listing is offered for an owner, an account and the instance."""
        endpoint, _ = BaseActions()._list_workflow_runs_helper(**coordinates)

        assert endpoint == path

    def test_only_a_repository_can_be_narrowed_to_one_workflow(self) -> None:
        """Naming a workflow outside a repository should be refused, not ignored.

        There is no organization-wide endpoint for the runs of one workflow - two
        organizations' repositories can hold two files of the same name - so a
        `workflow_id` that reached the wider path would list every run of the
        organization and look like a filter that matched everything.
        """
        with pytest.raises(ValueError, match="narrowed to one workflow"):
            BaseActions()._list_workflow_runs_helper(owner="o", workflow_id="build.yml")

    @pytest.mark.parametrize(
        "coordinates",
        [{"owner": "o"}, {}, {"admin": True}],
        ids=["organization", "account", "instance"],
    )
    def test_only_a_repository_can_leave_out_the_pull_requests(self, coordinates: dict[str, object]) -> None:
        """The wider listings do not take the parameter, so asking for it should be refused.

        Sending it anyway would be quietly ignored by Gitea: the listing would
        answer with the `pull_requests` of every run filled in, and a caller that
        asked for a smaller response would get the larger one with nothing to say
        the request had been dropped.
        """
        with pytest.raises(ValueError, match="leave out the pull requests"):
            BaseActions()._list_workflow_runs_helper(**coordinates, exclude_pull_requests=True)

    def test_the_pull_request_flag_is_accepted_by_the_repository_listing(self) -> None:
        """The refusal above should be about the scope and not about the flag itself."""
        _, params = BaseActions()._list_workflow_runs_helper(owner="o", repository="r", exclude_pull_requests=True)

        assert params == {"exclude_pull_requests": "true"}


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


class TestListWorkflowJobsHelper:
    """The listing of every job of a scope, which is not the jobs of one run."""

    @pytest.mark.parametrize(
        ("coordinates", "path"),
        [
            ({"owner": "o", "repository": "r"}, "/repos/o/r/actions/jobs"),
            ({"owner": "o"}, "/orgs/o/actions/jobs"),
            ({}, "/user/actions/jobs"),
            ({"admin": True}, "/admin/actions/jobs"),
        ],
        ids=["repository", "organization", "account", "instance"],
    )
    def test_the_listing_exists_at_every_scope(self, coordinates: dict[str, object], path: str) -> None:
        """Each scope has its own path for the same listing."""
        endpoint, _ = BaseActions()._list_workflow_jobs_helper(**coordinates)

        assert endpoint == path

    def test_it_is_not_the_jobs_of_one_run(self) -> None:
        """The wide listing and the run's own listing should be different paths.

        They answer different questions - what is queued across the scope, and how
        one run went - and a caller reaching the run's path expecting the wide one
        would see only the run it named.
        """
        wide, _ = BaseActions()._list_workflow_jobs_helper(owner="o", repository="r")
        of_one_run, _ = BaseActions()._list_workflow_run_jobs_helper(owner="o", repository="r", run_id=42)

        assert wide != of_one_run

    def test_every_filter_is_forwarded(self) -> None:
        """Each filter reaches the query string under the API's own name."""
        _, params = BaseActions()._list_workflow_jobs_helper(
            owner="o", repository="r", status="queued", page=2, limit=5
        )

        assert params == {"status": "queued", "page": 2, "limit": 5}

    def test_no_filters_asks_for_nothing(self) -> None:
        """A listing with no filters carries no query parameters."""
        _, params = BaseActions()._list_workflow_jobs_helper(owner="o", repository="r")

        assert params == {}


class TestRunManagementEndpoints:
    """The paths the endpoints that act on a run are addressed by."""

    def test_cancelling_and_forcing_are_different_endpoints(self) -> None:
        """The flag chooses a path, and the two are not the same request.

        `cancel` waits for the run's jobs to notice; `force-cancel` marks the run
        cancelled regardless. A flag that did not reach the path would ask
        politely for a run whose runner has gone away, report success, and leave
        the run exactly as it was.
        """
        actions = BaseActions()

        assert actions._cancel_workflow_run_endpoint("o", "r", 42) == "/repos/o/r/actions/runs/42/cancel"
        assert (
            actions._cancel_workflow_run_endpoint("o", "r", 42, force=True) == "/repos/o/r/actions/runs/42/force-cancel"
        )

    def test_rerunning_everything_and_the_failures_are_different_endpoints(self) -> None:
        """The flag chooses a path here too, and the milder one is not a subset."""
        actions = BaseActions()

        assert actions._rerun_workflow_run_endpoint("o", "r", 42) == "/repos/o/r/actions/runs/42/rerun"
        assert (
            actions._rerun_workflow_run_endpoint("o", "r", 42, failed_jobs_only=True)
            == "/repos/o/r/actions/runs/42/rerun-failed-jobs"
        )

    def test_approving_a_run(self) -> None:
        """An approval sits under the run."""
        assert BaseActions()._approve_workflow_run_endpoint("o", "r", 42) == "/repos/o/r/actions/runs/42/approve"

    def test_rerunning_one_job_goes_through_its_run(self) -> None:
        """This is the one job endpoint addressed through the run rather than directly.

        Reading a job takes the job alone; the rerun takes both, so a path built
        from the job alone would not exist.
        """
        assert (
            BaseActions()._rerun_workflow_job_endpoint("o", "r", 42, 118) == "/repos/o/r/actions/runs/42/jobs/118/rerun"
        )

    def test_deleting_a_run_is_the_run_itself(self) -> None:
        """A delete addresses the run, so it shares the path a read uses."""
        assert BaseActions()._get_workflow_run_endpoint("o", "r", 42) == "/repos/o/r/actions/runs/42"


class TestArtifactEndpoints:
    """The paths the artifact endpoints are addressed by."""

    def test_the_repository_wide_listing(self) -> None:
        """Without a run, every artifact of the repository is listed."""
        assert BaseActions()._list_artifacts_endpoint("o", "r") == "/repos/o/r/actions/artifacts"

    def test_naming_a_run_addresses_the_run(self) -> None:
        """With a run, the endpoint is the run's own artifacts path.

        As with the run listing, the two are different endpoints rather than one
        with a filter - so a `run_id` reaching the wider path would list the
        artifacts of every run and look like a filter that does nothing.
        """
        assert BaseActions()._list_artifacts_endpoint("o", "r", 42) == "/repos/o/r/actions/runs/42/artifacts"

    def test_the_name_is_a_query_parameter(self) -> None:
        """The name narrows the listing rather than addressing one artifact."""
        endpoint, params = BaseActions()._list_artifacts_helper("o", "r", name="dist")

        assert endpoint == "/repos/o/r/actions/artifacts"
        assert params == {"name": "dist"}

    def test_no_name_asks_for_nothing(self) -> None:
        """Without a name the listing carries no query parameters."""
        _, params = BaseActions()._list_artifacts_helper("o", "r")

        assert params == {}

    def test_one_artifact(self) -> None:
        """An artifact is addressed by its ID, under the repository."""
        assert BaseActions()._get_artifact_endpoint("o", "r", 9) == "/repos/o/r/actions/artifacts/9"

    def test_the_archive_sits_under_the_artifact(self) -> None:
        """The archive is a path of its own, so reading an artifact never downloads it."""
        assert BaseActions()._download_artifact_endpoint("o", "r", 9) == "/repos/o/r/actions/artifacts/9/zip"


class TestSecretEndpoints:
    """The paths the secret endpoints are addressed by, and the bodies they carry."""

    @pytest.mark.parametrize(
        ("coordinates", "path"),
        [
            ({"owner": "o", "repository": "r"}, "/repos/o/r/actions/secrets"),
            ({"owner": "o"}, "/orgs/o/actions/secrets"),
        ],
        ids=["repository", "organization"],
    )
    def test_the_listing_exists_for_a_repository_and_an_organization(
        self, coordinates: dict[str, object], path: str
    ) -> None:
        """Both scopes that have a listing should reach their own path."""
        endpoint, _ = BaseActions()._list_secrets_helper(**coordinates)

        assert endpoint == path

    def test_the_account_has_no_listing(self) -> None:
        """Gitea offers no listing of the authenticated account's secrets.

        The path would exist and answer `404`, which reads as "no secrets" rather
        than as "no such endpoint" - so the request is refused before it is made.
        """
        with pytest.raises(ValueError, match="for the authenticated account"):
            BaseActions()._list_secrets_helper()

    def test_the_pagination_is_forwarded(self) -> None:
        """The page and the limit reach the query string."""
        _, params = BaseActions()._list_secrets_helper(owner="o", repository="r", page=2, limit=5)

        assert params == {"page": 2, "limit": 5}

    @pytest.mark.parametrize(
        ("coordinates", "path"),
        [
            ({"owner": "o", "repository": "r"}, "/repos/o/r/actions/secrets/TOKEN"),
            ({"owner": "o"}, "/orgs/o/actions/secrets/TOKEN"),
            ({}, "/user/actions/secrets/TOKEN"),
        ],
        ids=["repository", "organization", "account"],
    )
    def test_one_secret_exists_at_three_scopes(self, coordinates: dict[str, object], path: str) -> None:
        """Setting and deleting are offered for the account too, where listing is not."""
        assert BaseActions()._secret_endpoint("TOKEN", **coordinates) == path

    def test_the_value_is_the_whole_body_by_default(self) -> None:
        """A secret set without a description sends the value alone."""
        endpoint, payload = BaseActions()._create_or_update_secret_helper("TOKEN", "hunter2", owner="o", repository="r")

        assert endpoint == "/repos/o/r/actions/secrets/TOKEN"
        assert payload == {"data": "hunter2"}

    def test_a_description_is_sent_when_it_was_given(self) -> None:
        """The description reaches the body under the API's own name."""
        _, payload = BaseActions()._create_or_update_secret_helper(
            "TOKEN", "hunter2", owner="o", repository="r", description="for deploys"
        )

        assert payload == {"data": "hunter2", "description": "for deploys"}

    def test_an_empty_description_is_still_sent(self) -> None:
        """An explicitly empty description clears the one the secret had, where None does not.

        `None` means the caller said nothing about the description; `""` means it
        asked for it to be empty. Collapsing the two would make clearing a
        description impossible, and would silently clear one on every plain value
        replacement if it went the other way.
        """
        _, payload = BaseActions()._create_or_update_secret_helper(
            "TOKEN", "hunter2", owner="o", repository="r", description=""
        )

        assert payload == {"data": "hunter2", "description": ""}


class TestVariableEndpoints:
    """The paths the variable endpoints are addressed by, and the bodies they carry."""

    @pytest.mark.parametrize(
        ("coordinates", "path"),
        [
            ({"owner": "o", "repository": "r"}, "/repos/o/r/actions/variables"),
            ({"owner": "o"}, "/orgs/o/actions/variables"),
            ({}, "/user/actions/variables"),
        ],
        ids=["repository", "organization", "account"],
    )
    def test_the_listing_exists_at_three_scopes(self, coordinates: dict[str, object], path: str) -> None:
        """A variable listing is offered for the account, where a secret listing is not."""
        endpoint, _ = BaseActions()._list_variables_helper(**coordinates)

        assert endpoint == path

    def test_one_variable(self) -> None:
        """A variable is addressed by name, since Gitea gives it no numeric ID."""
        assert BaseActions()._variable_endpoint("ENV", owner="o", repository="r") == (
            "/repos/o/r/actions/variables/ENV"
        )

    def test_creating_sends_the_value(self) -> None:
        """A create without a description sends the value alone."""
        endpoint, payload = BaseActions()._create_variable_helper("ENV", "staging", owner="o", repository="r")

        assert endpoint == "/repos/o/r/actions/variables/ENV"
        assert payload == {"value": "staging"}

    def test_updating_sends_the_rename_under_the_api_name(self) -> None:
        """`new_name` reaches the body as `name`, which is what Gitea calls it.

        Two names for the same thing is exactly what would go unnoticed: the
        request would succeed, having renamed nothing.
        """
        _, payload = BaseActions()._update_variable_helper(
            "ENV", "staging", owner="o", repository="r", new_name="TARGET"
        )

        assert payload == {"value": "staging", "name": "TARGET"}

    def test_an_update_without_a_rename_sends_no_name(self) -> None:
        """Omitting the rename leaves the field out, rather than sending it empty.

        Gitea documents an empty `name` as leaving the name alone, so both would
        work - but only one of them says what it means, and a caller reading the
        request should not have to know that rule.
        """
        _, payload = BaseActions()._update_variable_helper("ENV", "staging", owner="o", repository="r")

        assert payload == {"value": "staging"}

    def test_the_description_is_sent_when_it_was_given(self) -> None:
        """A description reaches both bodies."""
        _, created = BaseActions()._create_variable_helper("ENV", "staging", description="the target")
        _, updated = BaseActions()._update_variable_helper("ENV", "staging", description="the target")

        assert created == {"value": "staging", "description": "the target"}
        assert updated == {"value": "staging", "description": "the target"}


class TestRunnerEndpoints:
    """The paths the runner endpoints are addressed by, and the bodies they carry."""

    @pytest.mark.parametrize(
        ("coordinates", "path"),
        [
            ({"owner": "o", "repository": "r"}, "/repos/o/r/actions/runners"),
            ({"owner": "o"}, "/orgs/o/actions/runners"),
            ({}, "/user/actions/runners"),
            ({"admin": True}, "/admin/actions/runners"),
        ],
        ids=["repository", "organization", "account", "instance"],
    )
    def test_the_listing_exists_at_every_scope(self, coordinates: dict[str, object], path: str) -> None:
        """Runners are the one family Gitea offers at all four scopes."""
        endpoint, _ = BaseActions()._list_runners_helper(**coordinates)

        assert endpoint == path

    @pytest.mark.parametrize(("asked", "sent"), [(True, "true"), (False, "false")])
    def test_the_disabled_filter_is_spelled_for_the_api(self, asked: bool, sent: str) -> None:
        """The filter is a query parameter, so it is written as the API writes it."""
        _, params = BaseActions()._list_runners_helper(owner="o", repository="r", disabled=asked)

        assert params == {"disabled": sent}

    def test_the_filter_is_omitted_when_it_was_not_asked_about(self) -> None:
        """None leaves the parameter out, which is what lists both states."""
        _, params = BaseActions()._list_runners_helper(owner="o", repository="r")

        assert params == {}

    def test_one_runner(self) -> None:
        """A runner is addressed through the scope it is registered to."""
        assert BaseActions()._runner_endpoint(7, owner="o", repository="r") == "/repos/o/r/actions/runners/7"
        assert BaseActions()._runner_endpoint(7, admin=True) == "/admin/actions/runners/7"

    @pytest.mark.parametrize("disabled", [True, False])
    def test_an_update_sends_the_state_as_a_json_boolean(self, disabled: bool) -> None:
        """`disabled` is a body field here, so it is a boolean and not the query spelling.

        The same word is a query parameter on the listing, where it has to be
        `true` or `false` because neither HTTP client can carry a `bool` in a URL.
        Sending the string here would be a different value, and Gitea would reject
        it - or worse, read it as truthy either way.
        """
        endpoint, payload = BaseActions()._update_runner_helper(7, disabled, owner="o", repository="r")

        assert endpoint == "/repos/o/r/actions/runners/7"
        assert payload == {"disabled": disabled}

    @pytest.mark.parametrize(
        ("coordinates", "path"),
        [
            ({"owner": "o", "repository": "r"}, "/repos/o/r/actions/runners/registration-token"),
            ({"owner": "o"}, "/orgs/o/actions/runners/registration-token"),
            ({}, "/user/actions/runners/registration-token"),
            ({"admin": True}, "/admin/actions/runners/registration-token"),
        ],
        ids=["repository", "organization", "account", "instance"],
    )
    def test_the_registration_token_belongs_to_the_scope(self, coordinates: dict[str, object], path: str) -> None:
        """The token is the scope's, so each scope has one of its own.

        A token taken from the wrong scope registers a runner to the wrong scope,
        and the runner then works - for somebody else's jobs.
        """
        assert BaseActions()._runner_registration_token_endpoint(**coordinates) == path


def test_the_scopes_each_family_declares() -> None:
    """Each family should declare the scopes Gitea really offers it at, and no more.

    These sets are what the refusals are built from, so a scope added to one by
    mistake turns a clear "no such endpoint" into a `404` from a path that does not
    exist - and a scope missing from one refuses a call that would have worked.
    They are asserted here rather than only exercised through the helpers, because
    the two that differ from their neighbours are the point: a secret can be set
    for the authenticated account but not listed there, and neither secrets nor
    variables have an instance-wide form at all.
    """
    assert {REPOSITORY, ORGANIZATION} == SECRET_SCOPES
    assert {REPOSITORY, ORGANIZATION, USER} == SECRET_ENTRY_SCOPES
    assert {REPOSITORY, ORGANIZATION, USER} == VARIABLE_SCOPES
    assert RUNNER_SCOPES == EVERY_SCOPE
    assert LISTING_SCOPES == EVERY_SCOPE

    assert ADMIN not in SECRET_ENTRY_SCOPES
    assert ADMIN not in VARIABLE_SCOPES
    assert USER not in SECRET_SCOPES


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
        BaseActions()._list_runners_helper(owner="o", repository="r", disabled=True)[1],
        BaseActions()._list_workflow_jobs_helper(owner="o", repository="r", status="queued", page=2, limit=5)[1],
        BaseActions()._list_secrets_helper(owner="o", repository="r", page=2, limit=5)[1],
        BaseActions()._list_artifacts_helper(owner="o", repository="r", name="dist")[1],
    ],
    ids=["dispatch", "runs", "runners", "jobs", "secrets", "artifacts"],
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
