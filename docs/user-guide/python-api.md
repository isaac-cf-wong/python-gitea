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
