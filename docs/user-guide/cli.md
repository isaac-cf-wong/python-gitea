# Command-Line Interface

The `gitea-cli` command wraps the Gitea REST API for quick, scriptable
operations. Run `gitea-cli --help` for the full list at any time.

## Global Options

```bash
gitea-cli [OPTIONS] COMMAND [ARGS]...
```

| Option                  | Description                                                                             |
| ----------------------- | --------------------------------------------------------------------------------------- |
| `--config-path <path>`  | Config file path; defaults to `PYTHON_GITEA_CONFIG_PATH` or platform location.          |
| `-v, --verbose <level>` | Log level; default `INFO`.                                                              |
| `-o, --output <format>` | Output format, `text` or `json`; default `text`. See [Output formats](#output-formats). |
| `--version`             | Print the installed `python-gitea` version and exit.                                    |

All resource commands share authentication options:

| Option                  | Description                            |
| ----------------------- | -------------------------------------- |
| `--account-name <name>` | Use the stored account with this name. |
| `--token <token>`       | Token for authentication.              |
| `--base-url <url>`      | Base URL of the Gitea platform.        |

See [Configuration](configuration.md) for how authentication is resolved.

## Output formats

`--output` is a **global** option accepted by every subcommand, so a script
never has to know which command renders text and which renders JSON. Because it
belongs to the top-level command, it goes **before** the subcommand:

```bash
gitea-cli --output json config list      # correct
gitea-cli config list --output json      # not a valid option here
```

It can also be set once for a whole session with the `PYTHON_GITEA_OUTPUT`
environment variable; an explicit `--output` on the command line wins.

Two formats are supported:

- `text` (default) — human-readable rendering where a command has one. Commands
  that only report an API result print the JSON envelope below in either format,
  so `text` never loses information.
- `json` — always the same envelope on stdout:

```json
{
  "data": ...,
  "metadata": { ... }
}
```

`data` is the result itself and is never wrapped any further: the object or list
returned by the Gitea API, or - for local commands such as `config` - an object
describing what the command read or changed.

`metadata` describes the call rather than the result, and its keys vary by
command:

- API commands report `status_code`.
- Commands that page through the API add counts, such as `column_count` and
  `issue_count` for `project issues`.
- `config` commands report `config_path`.
- It is `{}` when the command made no call at all.

Errors are not part of the envelope: messages go to stderr and the process exits
non-zero, so nothing is printed on stdout for a failed command. Log output also
goes to stderr in both formats, so stdout stays parsable.

One failure is deliberately not an error: the board lookup that fills in the
`column_id` of `issue get`. A refused, timed-out or otherwise failed lookup logs
a warning to stderr and reports that project's column as `null`, because the
issue the command was asked for has already been retrieved and is not worth
failing over an enrichment of it.

Tokens are never included in the output of `config` commands in either format.

## Commands

### Config - manage accounts

- `gitea-cli config add --name <name> --token <token> [--base-url <url>] [--default]`
- `gitea-cli config list`
- `gitea-cli config update --name <name> [--token <token>] [--base-url <url>] [--default]`
- `gitea-cli config delete --name <name> [--force]`
    - Under `--output json` the confirmation prompt is written to stderr so that
      stdout stays parsable; pass `--force` to skip it entirely.

### Issue - manage issues

- `gitea-cli issue create --owner <owner> --repository <repo> --title <title>`
    - Optional: `--body`, `--assignees`, `--labels`, `--milestone`,
      `--due-date`, `--closed`
- `gitea-cli issue list --owner <owner> --repository <repo>`
    - Optional: `--state`, `--labels`, `--search-string`, `--created-by`,
      `--assigned-by`, `--since`, `--before`, `--page`, `--limit`
- `gitea-cli issue get --owner <owner> --repository <repo> --index <index>`
    - The `comment_count` field is the number of comments on the issue, not the
      comments themselves; use `gitea-cli issue comment list` to read the
      bodies.
    - Each entry of `projects` carries a `column_id`: the column the issue's
      card sits in, or `null` when the issue has no card on that project. Gitea
      does not report it on the issue itself, so it is resolved from each
      project's board, which costs a few extra requests per project.
    - Resolution is best-effort. It reflects the board as it was during the
      walk, not at one instant: a card moved while the columns are being read
      may be reported under either column or as `null`. A lookup that is
      refused, times out, or fails in transport leaves that project's
      `column_id` at `null` and logs a warning rather than failing `issue get` -
      so `null` means "no card here" and "could not tell" alike. The columns of
      a user-owned (individual) project cannot be listed at all, so its
      `column_id` is always `null`.
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

These commands are also available as `gitea-cli issue comment <command>`, which
is the same implementation under a second, more discoverable name.

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
- `gitea-cli project column issues --owner <owner> --repository <repo> --project-id <id> --column-id <id>`
    - Optional: `--page`, `--limit`
- `gitea-cli project issues --owner <owner> --repository <repo> --project-id <id>`
- `gitea-cli project issue add --owner <owner> --repository <repo> --project-id <id> --column-id <id> --issue-id <id>`
    - Optional: `--issue-repository`
- `gitea-cli project issue move --owner <owner> --repository <repo> --project-id <id> --column-id <id> --issue-id <id>`
    - Optional: `--sorting`, `--issue-repository`
- `gitea-cli project issue remove --owner <owner> --repository <repo> --project-id <id> --column-id <id> --issue-id <id>`
    - Optional: `--issue-repository`

The project endpoints identify an issue by its global ID, which is not the
number shown in the web UI: `my-org/my-repo#15` may well be global ID `1854`.
The three `project issue` commands therefore take `--issue-id` as the number
whenever they know which repository holds the issue, and look the global ID up
for you:

- On a repository project, `--repository` already names that repository, so
  `--issue-id 15` means `#15` of it.
- On an organization project, `--repository` is omitted and the issue may come
  from any repository of the organization. Name it with `--issue-repository` to
  address the issue by number; without it, `--issue-id` is read as the global
  ID. `--issue-repository` also overrides `--repository`, for the case of a
  repository project holding an issue from elsewhere.

The global ID the command used comes back as `metadata.resolved_issue_id`. A
number the repository does not have, and a call the project endpoint refuses,
are both reported as errors naming the issue and what to check - never as an
empty result. An instance that cannot be reached at all, whether the connection
fails or times out, is reported as one line naming the base URL rather than as a
traceback. A request that fails before any response for another reason - a
malformed base URL, say - is reported the same way, without claiming the
instance is down.

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

Move an issue into a project column, addressing it by the number shown in the
web UI:

```bash
gitea-cli project issue add \
    --owner my-org \
    --repository my-repo \
    --project-id 1 \
    --column-id 2 \
    --issue-id 42
```

Move `my-repo#42` on an organization project, where the repository holding the
issue has to be named separately:

```bash
gitea-cli project issue move \
    --owner my-org \
    --project-id 1 \
    --column-id 2 \
    --issue-repository my-repo \
    --issue-id 42
```

List the issues sitting in one column of an organization project (omit
`--repository`; it is only needed for repository projects):

```bash
gitea-cli project column issues \
    --owner my-org \
    --project-id 1 \
    --column-id 2
```

Show every card on a project together with the column it is in:

```bash
gitea-cli project issues --owner my-org --project-id 1
```

Read a configured account's base URL from a script, with `jq` unwrapping the
envelope described in [Output formats](#output-formats):

```bash
gitea-cli --output json config list |
    jq -r '.data.accounts[] | select(.name == "my-account") | .base_url'
```

## See Also

- [Quick Start](quickstart.md)
- [Configuration](configuration.md)
- [Python API](python-api.md)
