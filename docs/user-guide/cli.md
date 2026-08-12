# Command-Line Interface

The `gitea-cli` command wraps the Gitea REST API for quick, scriptable
operations. Run `gitea-cli --help` for the full list at any time.

## Global Options

```bash
gitea-cli [OPTIONS] COMMAND [ARGS]...
```

| Option                  | Description                                                                    |
| ----------------------- | ------------------------------------------------------------------------------ |
| `--config-path <path>`  | Config file path; defaults to `PYTHON_GITEA_CONFIG_PATH` or platform location. |
| `-v, --verbose <level>` | Log level; default `INFO`.                                                     |

All resource commands share authentication options:

| Option                  | Description                            |
| ----------------------- | -------------------------------------- |
| `--account-name <name>` | Use the stored account with this name. |
| `--token <token>`       | Token for authentication.              |
| `--base-url <url>`      | Base URL of the Gitea platform.        |

See [Configuration](configuration.md) for how authentication is resolved.

## Commands

### Config - manage accounts

- `gitea-cli config add --name <name> --token <token> [--base-url <url>] [--default]`
- `gitea-cli config list`
- `gitea-cli config update --name <name> [--token] [--base-url] [--default]`
- `gitea-cli config delete --name <name> [--force]`

### Issue - manage issues

- `gitea-cli issue create --owner <owner> --repository <repo> --title <title>`
    - Optional: `--body`, `--assignees`, `--labels`, `--milestone`,
      `--due-date`, `--closed`
- `gitea-cli issue list --owner <owner> --repository <repo>`
    - Optional: `--state`, `--labels`, `--search-string`, `--created-by`,
      `--assigned-by`, `--since`, `--before`, `--page`, `--limit`
- `gitea-cli issue get --owner <owner> --repository <repo> --index <index>`
- `gitea-cli issue edit --owner <owner> --repository <repo> --index <index>`
    - Optional: `--title`, `--body`, `--state`, `--assignees`, `--milestone`,
      `--due-date`
- `gitea-cli issue dependency add --owner <owner> --repository <repo> --index <index>`
    - Required: `--dependency-owner <owner>`, `--dependency-repository <repo>`,
      `--dependency-index <index>`
- `gitea-cli issue dependency list --owner <owner> --repository <repo> --index <index>`
- `gitea-cli issue dependency remove --owner <owner> --repository <repo> --index <index>`
    - Required: `--dependency-owner <owner>`, `--dependency-repository <repo>`,
      `--dependency-index <index>`

### Pull Request - manage pull requests

- `gitea-cli pull-request list --owner <owner> --repository <repo>`
    - Optional: `--state`, `--base-branch`, `--labels`, `--milestone`,
      `--poster`, `--sort`, `--page`, `--limit`

### Comment - manage issue comments

- `gitea-cli comment add --owner <owner> --repository <repo> --index <index> --body <body>`
- `gitea-cli comment list --owner <owner> --repository <repo> --index <index>`
- `gitea-cli comment edit --owner <owner> --repository <repo> --comment-id <id> --body <body>`
- `gitea-cli comment delete --owner <owner> --repository <repo> --comment-id <id>`

### Label - manage labels

- `gitea-cli label create --owner <owner> --repository <repo> --name <name> --color <hex>`
    - Optional: `--description`
- `gitea-cli label list --owner <owner> --repository <repo>`
- `gitea-cli label update --owner <owner> --repository <repo> --label-id <id>`
    - Optional: `--name`, `--color`, `--description`
- `gitea-cli label delete --owner <owner> --repository <repo> --label-id <id>`

### Milestone - manage milestones

- `gitea-cli milestone create --owner <owner> --repository <repo> --title <title>`
    - Optional: `--description`, `--due-on`, `--state`
- `gitea-cli milestone list --owner <owner> --repository <repo>`
    - Optional: `--state`, `--name`, `--page`, `--limit`

### Notification - manage notifications

- `gitea-cli notification list`
    - Optional: `--owner`, `--repository`, `--status-type`, `--subject-type`,
      `--since`, `--before`, `--all`, `--page`, `--limit`
- `gitea-cli notification read`
    - Optional: `--owner`, `--repository`, `--status-type`, `--to-status`,
      `--last-read-at`, `--all`

### Project - manage projects

- `gitea-cli project create --owner <owner> --repository <repo> --title <title>`
    - Optional: `--description`, `--card-type`, `--template-type`
- `gitea-cli project list --owner <owner> --repository <repo>`
- `gitea-cli project get --owner <owner> --repository <repo> --project-id <id>`
- `gitea-cli project edit --owner <owner> --repository <repo> --project-id <id>`
    - Optional: `--title`, `--description`, `--state`, `--card-type`
- `gitea-cli project delete --owner <owner> --repository <repo> --project-id <id>`
- `gitea-cli project column create --owner <owner> --repository <repo> --project-id <id> --title <title>`
    - Optional: `--color`
- `gitea-cli project column list --owner <owner> --repository <repo> --project-id <id>`
- `gitea-cli project issue add --owner <owner> --repository <repo> --project-id <id> --column-id <id> --issue-id <id>`
- `gitea-cli project issue move --owner <owner> --repository <repo> --project-id <id> --column-id <id> --issue-id <id>`
    - Optional: `--sorting`
- `gitea-cli project issue remove --owner <owner> --repository <repo> --project-id <id> --column-id <id> --issue-id <id>`

### User - manage users

- `gitea-cli user get [--username <name>]`
- `gitea-cli user update-settings`
    - Optional: `--full-name`, `--website`, `--location`, `--language`,
      `--theme`, `--diff-view-style`, `--hide-email`, `--hide-activity`

## Examples

List all open issues in a repository:

```bash
gitea-cli issue list --owner my-org --repository my-repo --state open
```

Create an issue with labels and a milestone:

```bash
gitea-cli issue create \
    --owner my-org \
    --repository my-repo \
    --title "Fix the docs" \
    --labels 1,2 \
    --milestone 3
```

Move an issue into a project column:

```bash
gitea-cli project issue add \
    --owner my-org \
    --repository my-repo \
    --project-id 1 \
    --column-id 2 \
    --issue-id 42
```

## See Also

- [Quick Start](quickstart.md)
- [Configuration](configuration.md)
- [Python API](python-api.md)
