# Quick Start

This guide will help you use `python-gitea` in just a few minutes. It covers the
two ways to interact with Gitea: the command-line interface and the Python API.

## 1. Install

See [Installation](installation.md) for the full guide, including development
setups. The short version:

```bash
uv venv --python 3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install python-gitea
```

## 2. Configure an account

Both the CLI and the Python API authenticate with a personal access token. The
easiest way is to store accounts in the configuration file once:

```bash
gitea-cli config add \
    --name my_account \
    --token YOUR_API_TOKEN \
    --base-url https://gitea.example.com \
    --default
```

The first account added becomes the default automatically, so `--default` is
only needed to switch the default later. See [Configuration](configuration.md)
for all config commands and for how to pass a token without storing it.

## 3. Use the CLI

```bash
# List issues of a repository
gitea-cli issue list --owner my-org --repository my-repo

# Get a user
gitea-cli user get --username my-org

# Create an issue
gitea-cli issue create \
    --owner my-org \
    --repository my-repo \
    --title "My first issue" \
    --body "Created with python-gitea."
```

Repository-backed commands accept `--owner`/`--repository`. Resource commands
also accept the authentication flags `--account-name`, `--token`, and
`--base-url`. When no authentication flag is given, the default account from the
configuration file is used.

## 4. Use the Python API

```python
from gitea.client.gitea import Gitea

with Gitea(token="YOUR_API_TOKEN", base_url="https://gitea.example.com") as client:
    # List issues
    issues, _ = client.issue.list_issues(owner="my-org", repository="my-repo")

    # Get a user
    user, _ = client.user.get_user(username="my-org")

    # Create an issue
    client.issue.create_issue(
        owner="my-org",
        repository="my-repo",
        title="My first issue",
        body="Created with python-gitea.",
    )
```

For high-throughput or concurrent workloads, use the async client:

```python
import asyncio

from gitea.client.async_gitea import AsyncGitea


async def main() -> None:
    async with AsyncGitea(token="YOUR_API_TOKEN", base_url="https://gitea.example.com") as client:
        issues, _ = await client.issue.list_issues(owner="my-org", repository="my-repo")


asyncio.run(main())
```

## 5. Next Steps

- [Installation](installation.md) - Detailed installation instructions.
- [Configuration](configuration.md) - Manage accounts, tokens, and defaults.
- [Python API](python-api.md) - The full Python client, sync and async.
- [Command-Line Interface](cli.md) - Every CLI command and its options.
- [API Reference](../reference/index.md) - Generated API documentation.
