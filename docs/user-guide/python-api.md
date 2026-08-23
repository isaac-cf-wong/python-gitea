# Python API

`python-gitea` exposes a synchronous client and an `asyncio`-based async client.
Both are thin wrappers around the
[Gitea REST API](https://docs.gitea.com/api/1.0) with the same structure: the
top-level client holds one resource object per Gitea domain (issues, pull
requests, repositories, users, comments, labels, milestones, notifications, and
projects).

## Synchronous Client

Use the `Gitea` client as a context manager. It must be used inside a `with`
block so its HTTP session is cleaned up:

```python
from gitea.client.gitea import Gitea

with Gitea(token="YOUR_API_TOKEN", base_url="https://gitea.example.com") as client:
    issues, _ = client.issue.list_issues(owner="my-org", repository="my-repo")
```

List-style methods return a tuple `(data, status)` where `data` is a list of
dictionaries (or the response payload) and `status` holds metadata such as the
HTTP status code:

```python
with Gitea(token="TOKEN", base_url="https://gitea.example.com") as client:
    repositories, status = client.repository.list_repositories(username="my-org")
    print(repositories[0]["name"])
    print(status["status_code"])
```

Mutating operations return the same `(data, status)` shape. For example,
`create_issue` returns the created issue as a dictionary plus metadata:

```python
with Gitea(token="TOKEN", base_url="https://gitea.example.com") as client:
    issue, status = client.issue.create_issue(
        owner="my-org",
        repository="my-repo",
        title="Hello",
        body="Created with python-gitea.",
    )
    print(issue["number"])
    print(status["status_code"])
```

## Where an Issue Sits on a Board

An issue payload lists the projects the issue is on, but Gitea's project objects
carry no column, so the issue alone does not say where on a board its card sits.
`resolve_project_column_ids` fills that in, giving every project of the issue a
`column_id` — the column holding its card, or `None` when the issue has no card
on that project:

```python
from gitea.client.gitea import Gitea
from gitea.issue import resolve_project_column_ids

with Gitea(token="TOKEN", base_url="https://gitea.example.com") as client:
    issue, _ = client.issue.get_issue(owner="my-org", repository="my-repo", index=15)
    issue = resolve_project_column_ids(
        client=client,
        owner="my-org",
        repository="my-repo",
        issue=issue,
    )
    for project in issue["projects"]:
        print(project["id"], project["column_id"])
```

The columns of each project are walked until the one holding the card is found,
so the cost grows with the size of the board rather than of the repository. The
`gitea-cli issue get` command does this for you.
`resolve_async_project_column_ids` is the `await`-based twin for `AsyncGitea`.

Both are best-effort, and `column_id` should be read with that in mind:

- The walk is a sequence of requests, not a snapshot. `column_id` reflects the
  board as it was while the walk ran, so a card moved during it may come back
  under either column, or as `None`.
- A lookup that fails - refused, timed out, or lost in transport - is logged as
  a warning on the `gitea` logger and leaves that project's `column_id` at
  `None`. The issue itself is returned; the exception is not re-raised, on the
  synchronous and asynchronous paths alike. `None` therefore means "no card on
  this project" and "could not be resolved" alike.
- `column_id` is present on every project entry the functions return, including
  when the issue payload carries no global ID for the columns to be matched by,
  in which case every column is `None`.
- The columns of a user-owned (individual) project live under endpoints this
  library does not wrap, so such a project's `column_id` is always `None`.

That last point is about the enrichment and not about the walk itself.
`find_card_column_id` is the walk on its own — one project, one issue, the
column holding its card or `None` when no column of the board lists it — and it
raises what the lookup raised rather than logging it, for a caller that has to
tell "no card" apart from "could not be read":

```python
from gitea.client.gitea import Gitea
from gitea.issue import find_card_column_id

with Gitea(token="TOKEN", base_url="https://gitea.example.com") as client:
    column_id = find_card_column_id(
        client=client,
        owner="my-org",
        repository=None,  # the organization's own project; a repository's names it
        project_id=1,
        issue_id=1854,  # the global ID, which is what the columns list their issues by
    )
    print("not on the board" if column_id is None else column_id)
```

`find_async_card_column_id` is its `await`-based twin. Asking this before moving
a card is what `gitea-cli project issue move` does: Gitea's move endpoint moves
the row relating an issue to a project, and for an issue that is not on the
project there is none to move, so the call comes back a success having done
nothing. `gitea-cli project issue remove` asks it for the other reason — the
removal endpoint takes the column the card is in, and this is what answers that
when the caller passes no `--column-id`. That command asks it a second time
after removing the card, expecting no column at all: a card moved between the
two calls leaves the removal naming a column that no longer holds it, and the
whole board has to be walked to tell that from a removal that worked.

`column_holds_card` is the same question about a single named column, at the
cost of that column's listing rather than the board's — which is what the walk
above asks per column, and what the same command asks again after the move to
confirm the card arrived. `async_column_holds_card` is its `await`-based twin.

## Asynchronous Client

The `AsyncGitea` client has the same structure but `await`-based, and it uses
`aiohttp`:

```python
import asyncio

from gitea.client.async_gitea import AsyncGitea


async def main() -> None:
    async with AsyncGitea(token="YOUR_API_TOKEN", base_url="https://gitea.example.com") as client:
        issues, _ = await client.issue.list_issues(owner="my-org", repository="my-repo")
        print(len(issues))


asyncio.run(main())
```

Use the async client for concurrent workloads; otherwise the synchronous client
is simpler and sufficient.

## Available Resources

| Client attribute      | Gitea domain                                                           |
| --------------------- | ---------------------------------------------------------------------- |
| `client.actions`      | Actions: workflows, runs, jobs, artifacts, secrets, variables, runners |
| `client.issue`        | Issues and issue dependencies                                          |
| `client.pull_request` | Pull requests                                                          |
| `client.repository`   | Repositories                                                           |
| `client.user`         | Users and user settings                                                |
| `client.comment`      | Issue comments                                                         |
| `client.label`        | Issue labels                                                           |
| `client.milestone`    | Milestones                                                             |
| `client.notification` | Notifications                                                          |
| `client.project`      | Projects, columns, and project issues                                  |
| `client.organization` | Organizations                                                          |

Each resource is implemented in a synchronous class (e.g. `gitea.issue.Issue`)
and an async class (e.g. `gitea.issue.AsyncIssue`); some modules re-export them
from the package `__init__` (e.g. `from gitea.issue import Issue`). See the
[API Reference](../reference/index.md) for the full method list and signatures.

Those package-level re-exports are resolved when the name is first read rather
than when the package is imported, so both spellings work and neither costs more
than it needs to: `from gitea.issue import Issue` imports `gitea.issue.issue` at
that moment, and `import gitea.issue.base` imports neither class. The only way
to notice is by introspection - a name is absent from the package's `__dict__`
until something reads it, though `dir()` still lists it.

`gitea.actions` is the one package that re-exports nothing, so import its two
classes from the modules they live in -
`from gitea.actions.actions import Actions`. It is thirteen modules where the
others are three, and an eager re-export would make `import gitea.actions.scope`
execute all thirteen.

## Actions

`client.actions` wraps the Actions endpoints: the workflows of a repository and
dispatching one, the runs and their status, the jobs of a run with their logs,
the artifacts a run produced, and the secrets, variables and runners a workflow
runs against.

Four things about it differ from every other resource here, all because the
endpoints themselves differ:

**Most listings answer with an object, not an array.** `total_count` sits
alongside `workflows`, `workflow_runs`, `jobs`, `artifacts` or `runners`, which
is what Gitea sends, so it is what these methods hand back - keyed as the API
keys it, as [the field-name convention](#field-names) requires. The secret and
variable listings are the exception: those two really do answer with a bare
array, so they hand back a list and fall back to the empty one.

```python
runs, _ = client.actions.list_workflow_runs(
    owner="my-org", repository="my-repo", status="failure", limit=10
)
print(runs["total_count"])
for run in runs["workflow_runs"]:
    print(run["run_number"], run["status"], run["conclusion"])
```

**Two endpoints answer with a file.** `get_workflow_job_logs` hands back the log
as a string, decoded as UTF-8, and the empty string for a job that has produced
no output yet. `download_artifact` hands back the zip archive as **bytes**,
undecoded: decoding it would replace every byte that is not valid UTF-8 and
produce an archive that no longer opens.

```python
logs, metadata = client.actions.get_workflow_job_logs(owner="my-org", repository="my-repo", job_id=118)
print(logs, end="")

from pathlib import Path

archive, metadata = client.actions.download_artifact(owner="my-org", repository="my-repo", artifact_id=9)
Path("dist.zip").write_bytes(archive)
```

An artifact whose archive has expired answers with no body, so empty bytes mean
the archive is gone rather than empty; `expired` on the artifact itself is what
says which. Uploading an artifact is not offered, and is not an omission: Gitea
has no REST endpoint for it - an artifact is uploaded from inside a running job,
by the runner, over the Actions protocol.

<a id="actions-scopes"></a> **Most of the API exists at four scopes.** Secrets,
variables, runners and the run and job listings belong to a repository, to an
organization, to the authenticated account or to the instance, at paths that
differ while the request does not. Which one a call means is decided by the
coordinates it was given, not by the method name:

| Arguments                | Scope                     | Path                                |
| ------------------------ | ------------------------- | ----------------------------------- |
| `owner` and `repository` | that repository           | `/repos/{owner}/{repo}/actions/...` |
| `owner` alone            | that organization         | `/orgs/{owner}/actions/...`         |
| neither                  | the authenticated account | `/user/actions/...`                 |
| `admin=True`             | the whole instance        | `/admin/actions/...`                |

```python
client.actions.list_runners(owner="my-org", repository="my-repo")  # the repository's own
client.actions.list_runners(owner="my-org")  # the organization's
client.actions.list_runners()  # the authenticated account's
client.actions.list_runners(admin=True)  # the instance's
```

`owner` alone is the **organization** form, not a generic owner form: Gitea
answers it only for an organization.

Not every family offers every scope. A secret cannot be _listed_ for the
authenticated account, and neither secrets nor variables have an instance-wide
form. Asking for one that does not exist raises `ValueError` naming the scopes
that would have worked, rather than reaching a URL that answers `404` - which
would read as "no secrets" instead of "no such endpoint".

**Several endpoints answer without a body.** Setting a secret answers `201` when
it was new and `204` when it replaced one; deleting anything answers `204`;
rerunning only the failed jobs of a run answers `201` with nothing. In each case
the payload is the empty object and `metadata["status_code"]` is what says what
happened.

```python
_, metadata = client.actions.create_or_update_secret(
    secret_name="DEPLOY_TOKEN", data=token, owner="my-org", repository="my-repo"
)
created = metadata["status_code"] == 201
```

A secret is write-only: nothing reads its value back, which is why there is no
`get_secret`. A variable is its readable counterpart, with the value under
`data` - and where a secret has one endpoint that both creates and replaces, a
variable has two: `create_variable` refuses a name that exists, and
`update_variable` replaces one that does. `update_variable` requires the value
even when only the name is changing, so read it first rather than guessing it.

Dispatching answers `204` with no body, which says the request was accepted but
not which run it started. Ask for the run to be named when you mean to follow
it; an instance too old to know the parameter answers without a body as before,
so an empty payload is "accepted, run not named" rather than a failure.

```python
details, metadata = client.actions.dispatch_workflow(
    owner="my-org",
    repository="my-repo",
    workflow_id="build.yml",  # the file name, which is what the endpoint takes
    ref="refs/heads/main",
    inputs={"environment": "staging"},
    return_run_details=True,
)
run_id = details.get("workflow_run_id")
```

Cancelling a run has two endpoints and not one, chosen by an argument rather
than by a method of its own: `cancel_workflow_run` asks the run's jobs to stop
and waits for them to notice, which a job whose runner has gone away never does,
and `force=True` marks the run cancelled regardless. Rerunning is the same
shape: `failed_jobs_only=True` is a different endpoint, and the one to reach for
when a long run failed on one flaky job.

```python
run, _ = client.actions.cancel_workflow_run(owner="my-org", repository="my-repo", run_id=42)
print(run["status"])  # says whether the cancellation has taken effect yet

client.actions.cancel_workflow_run(owner="my-org", repository="my-repo", run_id=42, force=True)
client.actions.rerun_workflow_run(owner="my-org", repository="my-repo", run_id=42, failed_jobs_only=True)
```

`delete_workflow_run` deletes the run's jobs, logs and artifacts with it, which
is how a repository is cleared of those rather than only of the run's entry; a
run that has not finished cannot be deleted.

## Field Names

A payload returned by a client method is the JSON the Gitea API sent, keyed as
the API keys it. Nothing is renamed and nothing is dropped, in the client
dictionaries and in [the CLI's JSON envelope](cli.md#field-names) alike, so a
key is looked up in Gitea's API reference and not in this library's source.

A project column is therefore `title`:

```python
columns, _ = client.project.list_project_columns(owner="my-org", repository=None, project_id=31)
print(columns[0]["title"])  # 'Working'
```

`name` reads it too. It is an alias, not a second key: reading a payload by it
works, and enumerating or serializing the payload sees `title` alone, so nothing
downstream can come to depend on a name the API does not use.

```python
column = columns[0]
column["name"]        # 'Working' - reads the title
column.get("name")    # 'Working'
"name" in column      # True
list(column)          # ['id', 'title', 'default', 'sorting', ...] - no 'name'
json.dumps(column)    # {"id": 117, "title": "Working", ...} - no 'name'
```

Only reading is widened. `column["name"] = x` writes a field called `name`, as
it would on any dictionary, rather than changing the title through a name Gitea
does not use.

`gitea.utils.fields` holds the convention itself, the record types declaring the
aliases of a resource, and the bar an alias has to clear to be added: a name
callers have written, not a name that reads well. Today there is one, `name` on
a project column.

## Detecting What Changed

`gitea.watch` is not a resource: it holds the change detection that
[`gitea-cli watch list`](cli.md#watch---report-what-changed-since-the-last-run)
is built on, for a caller wanting the same comparison without the command's
choices about scopes and output.

Both listings below are walked with `collect_all_pages`, as the command walks
them. A single call returns one page, so comparing against `list_issues(...)[0]`
would report every issue past the first page as gone, and every comment past the
first page of an issue's comments would never be seen at all.

```python
from gitea.client.gitea import Gitea
from gitea.utils.pagination import PAGE_SIZE, collect_all_pages
from gitea.watch import detect_changes, issue_key, issue_snapshot, load_state, save_scopes, scope_snapshots

OWNER, REPOSITORY = "my-org", "my-repo"
SCOPE = f"repo:{OWNER}/{REPOSITORY}"

state = load_state("watch-state.json")

with Gitea(token="your-token", base_url="https://gitea.example.com") as client:
    issues, _ = collect_all_pages(
        lambda page: client.issue.list_issues(
            owner=OWNER, repository=REPOSITORY, state="open", page=page, limit=PAGE_SIZE
        )
    )

    current = {}
    for issue in issues:
        comments, _ = collect_all_pages(
            lambda page, index=issue["number"]: client.comment.list_comments(
                owner=OWNER, repository=REPOSITORY, index=index, page=page, limit=PAGE_SIZE
            )
        )
        current[issue_key(issue)] = issue_snapshot(issue, comments, repository=f"{OWNER}/{REPOSITORY}")

# None - a scope never recorded - baselines it, so nothing is reported the
# first time round.
for change in detect_changes(current, scope_snapshots(state, SCOPE)):
    print(change["kind"], change["number"], change["detail"])

save_scopes("watch-state.json", {SCOPE: current})
```

`issue_snapshot` reduces an issue to the fields the comparison reads,
`comment_hash` identifies a comment stably across re-fetches - by the author's
ID rather than their login, so renaming a user does not look like every comment
they wrote being replaced - and the state helpers read and write the cache the
snapshots live in.

`save_scopes` re-reads the cache and replaces only the scopes it is given, under
a lock on a `.lock` file beside it, so a caller running concurrently with
another does not erase what the other recorded. Prefer it to `save_state`, which
writes a whole document unlocked and is for a caller that has one - a caller
holding the whole cache is claiming every scope in it. Both write atomically.

Reading tolerates a cache that is missing or unreadable, and discards one
written by an older version of this library rather than comparing against
digests taken over something else. The [CLI documentation](cli.md#the-cache)
describes what those cost.
