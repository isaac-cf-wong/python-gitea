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

| Client attribute      | Gitea domain                          |
| --------------------- | ------------------------------------- |
| `client.issue`        | Issues and issue dependencies         |
| `client.pull_request` | Pull requests                         |
| `client.repository`   | Repositories                          |
| `client.user`         | Users and user settings               |
| `client.comment`      | Issue comments                        |
| `client.label`        | Issue labels                          |
| `client.milestone`    | Milestones                            |
| `client.notification` | Notifications                         |
| `client.project`      | Projects, columns, and project issues |

Each resource is implemented in a synchronous class (e.g. `gitea.issue.Issue`)
and an async class (e.g. `gitea.issue.AsyncIssue`); some modules re-export them
from the package `__init__` (e.g. `from gitea.issue import Issue`). See the
[API Reference](../reference/index.md) for the full method list and signatures.

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
snapshots live in. `save_scopes` re-reads the cache and replaces only the scopes
it is given, so it does not erase what another run recorded; `save_state` writes
a whole document, for a caller that has one. Both write atomically, and reading
tolerates a cache that is missing or unreadable. The
[CLI documentation](cli.md#the-cache) describes what that tolerance costs.
