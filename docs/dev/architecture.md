# Architecture

This document describes the high-level architecture and design of
`python-gitea`: how the package is laid out, how the client and CLI relate, and
the design principles behind them.

## Overview

`python-gitea` is a thin, typed wrapper around the
[Gitea REST API](https://docs.gitea.com/api/1.0). It provides two user-facing
surfaces that share the same domain model:

- **Python client** - synchronous (`Gitea`) and asynchronous (`AsyncGitea`)
  clients with one resource object per Gitea domain.
- **CLI** - `gitea-cli`, a Typer application with one command group per domain.

Both surfaces authenticate to Gitea with a personal access token and base URL.
The CLI resolves configured accounts through `cli/utils/auth.py`
([Configuration](../user-guide/configuration.md)), while Python callers pass
their credentials directly to the `Gitea` or `AsyncGitea` constructor.

## Package Layout

```text
src/gitea/
├── __init__.py              # Top-level package (exports __version__)
├── __main__.py              # python -m gitea
├── version.py               # Version information
├── client/                  # Client classes
│   ├── base.py              # Client base class (token, base_url, URL building)
│   ├── gitea.py             # Synchronous Gitea client
│   └── async_gitea.py       # Asynchronous AsyncGitea client (aiohttp)
├── config/                  # Configuration layer
│   ├── model.py             # Pydantic models (AccountConfig, Config)
│   └── manager.py           # ConfigManager (load/save/CRUD accounts)
├── resource/                # Resource base class
│   └── resource.py          # Shared request helpers for resources
├── actions/                 # Actions resource (sync + async), composed per family
│   ├── base.py              # Every Actions path and query parameter
│   ├── scope.py             # Which scope a set of coordinates addresses
│   ├── actions.py           # Workflows, runs, jobs; composes the families below
│   ├── run_management.py    # Cancel, approve, rerun, delete a run
│   ├── artifact.py          # The files a run produced, archive included
│   ├── secret.py            # Write-only secrets of a scope
│   ├── variable.py          # Their readable counterpart
│   └── runner.py            # Runners of a scope, and the registration token
├── issue/                   # Issue resource (sync + async)
├── pull_request/            # Pull request resource (sync + async)
├── repository/              # Repository resource (sync + async)
├── user/                    # User resource (sync + async)
├── comment/                 # Comment resource (sync + async)
├── label/                   # Label resource (sync + async)
├── milestone/               # Milestone resource (sync + async)
├── notification/            # Notification resource (sync + async)
├── project/                 # Project resource (sync + async)
├── organization/            # Organization resource (sync + async)
├── cli/                     # Typer CLI application
│   ├── main.py              # gitea-cli entry point, command registration
│   ├── config/              # config commands
│   ├── actions/             # actions workflow, run, job, artifact, secret, variable, runner commands
│   ├── issue/               # issue + issue dependency commands
│   ├── pull_request/        # pull-request commands
│   ├── comment/             # comment commands
│   ├── label/               # label commands
│   ├── milestone/           # milestone commands
│   ├── notification/        # notification commands
│   ├── project/             # project, column, and project-issue commands
│   ├── organization/        # org commands
│   ├── repository/          # repo commands
│   ├── user/                # user commands
│   └── utils/               # auth resolution, API helpers, conversions
└── utils/                   # Logging, field names, pagination, and response helpers
    ├── fields.py            # Field-name convention and compatibility aliases
    ├── log.py               # Logger setup
    ├── pagination.py        # Paginated-listing walkers
    └── response.py          # Response processing helpers
```

## Client Layer

The client layer is the programmatic interface. Both clients inherit from
`Client`, which stores the token and base URL and builds API URLs.

- `gitea.client.gitea.Gitea` uses `requests` and must be used as a context
  manager so its HTTP session is closed.
- `gitea.client.async_gitea.AsyncGitea` uses `aiohttp` and must be used as an
  async context manager.

Each client exposes one attribute per resource:

```python
with Gitea(token="...", base_url="...") as client:
    client.actions        # Actions
    client.issue          # Issue
    client.pull_request   # PullRequest
    client.repository     # Repository
    client.user           # User
    client.comment        # Comment
    client.label          # Label
    client.milestone      # Milestone
    client.notification   # Notification
    client.project        # Project
    client.organization   # Organization
```

## Resource Layer

Each resource module contains a synchronous class (e.g. `gitea.issue.Issue`) and
an asynchronous class (e.g. `gitea.issue.AsyncIssue`) with the same method
names. Methods map one-to-one onto Gitea REST endpoints and return either:

- a `(data, status)` tuple for list/get operations, where `data` is the decoded
  JSON payload and `status` carries metadata such as the HTTP status code, or
- the raw HTTP response for mutating operations.

Work that spans several endpoints lives beside the resource rather than inside
it, so the resource methods stay one-to-one with the API. For example,
`gitea.issue.project_column` resolves the board column an issue's card sits in,
which Gitea only reveals through the project's column listings.

`actions` is the one resource split further, into a module per family - runs,
artifacts, secrets, variables, runners - which `Actions` and `AsyncActions`
compose. Gitea's Actions API is large enough that one class per client would be
a file nobody reads end to end, and the families differ from each other in ways
worth writing down beside their own methods: which listings answer with an
object and which with a bare array, which endpoints answer with a file rather
than a document, and which scopes each family exists at. The path building for
all of them stays in one `base.py`, so every URL the resource can address is in
one place.

## CLI Layer

The CLI is a single Typer application registered in `cli/main.py`. Each resource
has a command group (e.g. `gitea-cli issue`, `gitea-cli project`), and nested
groups exist where the domain nests (e.g. `project column`, `issue dependency`).

CLI commands reuse the client through thin helper functions in `cli/utils/`
(`auth.py` resolves authentication, `api.py` and `convert.py` handle requests
and option conversion), so the CLI and the Python API stay in sync with the same
endpoint definitions.

## Configuration Layer

The `config/` module stores named accounts in a YAML file:

- `model.py` defines the Pydantic models `AccountConfig` and `Config`.
- `manager.py` provides `ConfigManager` for loading, saving, and CRUD on
  accounts, including the default-account concept.

The CLI resolves authentication through `cli/utils/auth.py`, which implements
the precedence rules documented in
[Configuration](../user-guide/configuration.md). Python callers instead pass
credentials directly to the client constructor; they can use `ConfigManager` to
load stored accounts programmatically.

## Design Principles

1. **Thin wrappers, no business logic.** The package mirrors the Gitea API
   surface instead of abstracting it, keeping behavior predictable.
2. **Synchronous and asynchronous parity.** Sync and async classes expose the
   same methods, so switching between them only changes the client and awaits.
3. **One source of endpoint definitions.** CLI and client share the request
   layer, avoiding drift between the two surfaces.
4. **Type hints and validation everywhere.** Pydantic models for config, full
   type annotations on all public methods, and validated option types on the
   CLI.

## See Also

- [Contributing](../contributing.md)
- [API Reference](../reference/index.md)
