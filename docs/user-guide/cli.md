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
  so `text` never loses information. One command prints nothing at all in this
  format when it has nothing to say: see
  [Watch](#watch---report-what-changed-since-the-last-run).
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

## Field names

Every field of `data` is named as the Gitea API names it. Nothing is renamed and
nothing is dropped on the way out, so a key can be looked up in
[Gitea's own API reference](https://docs.gitea.com/api/1.24/) rather than in
this CLI's source, and the same value never arrives under two names depending on
which command fetched it.

A field the API cannot send is added only where it carries something the API has
no way of saying, and is documented with the command that adds it: `column_id`
on the project entries of `issue get` is the one today. It is never a second
name for a field already in the payload.

Two consequences worth knowing:

- A project column is `title`, not `name`:

    ```console
    $ gitea-cli --output json project column list --owner my-org --project-id 31
    {
      "data": [{ "id": 117, "title": "Working", "default": false, "sorting": 0, ... }],
      "metadata": { "status_code": 200 }
    }
    ```

- A field whose name misleads is documented rather than renamed. `comments` on
  an issue is the _number_ of comments; `gitea-cli issue comment list` reads the
  bodies.

The Python client follows the same convention and additionally keeps a field
name callers already wrote readable as an alias - `column["name"]` reads the
title - which the [Python API guide](python-api.md#field-names) describes. An
alias is never emitted, so it cannot appear in the JSON above.

## Option naming

Every resource command addresses its target the same way, so an invocation can
be written without reading `--help` first:

| Option          | Meaning                                                  |
| --------------- | -------------------------------------------------------- |
| `--owner`       | The user or organization that owns the target. Required. |
| `--repository`  | Narrows the target to one repository of that owner.      |
| `--<entity>-id` | Names the entity acted on.                               |

The entity options are `--issue-id`, `--project-id`, `--column-id`, `--label-id`
and `--comment-id`.

Omitting `--repository` asks for the target that belongs to the owner itself
rather than to one of its repositories. The `project` commands have both forms:

```bash
gitea-cli project get --owner my-org --project-id 1                      # organization project
gitea-cli project get --owner my-org --repository my-repo --project-id 1  # repository project
```

The other families have no owner-wide endpoint - an issue, a comment, a label, a
milestone and a pull request all live in a repository - so omitting
`--repository` there is reported as an error naming the option to pass:

```console
$ gitea-cli issue get --owner my-org --issue-id 42
ERROR  'gitea-cli issue get' needs a repository: pass --repository REPOSITORY.
       Omitting --repository asks for the target of the owner itself, which only
       the 'gitea-cli project' commands have.
```

A second target named in the same command carries its own coordinates, and those
are required together because there is no scope for them to fall back to:
`issue dependency add` takes `--dependency-owner`, `--dependency-repository` and
`--dependency-issue-id`.

`notification` is the one family where `--owner` is optional as well: given
neither `--owner` nor `--repository` it acts on the authenticated user's
notifications, and the two must be passed together or not at all.

### Deprecated option names

`--index` has been renamed to `--issue-id`, so that one option name means "which
issue" in every family. The old names are still accepted and log a deprecation
warning naming their replacement, so existing scripts keep working; they are
hidden from `--help` and will be removed in a future release.

| Deprecated           | Use instead             |
| -------------------- | ----------------------- |
| `--index`            | `--issue-id`            |
| `--dependency-index` | `--dependency-issue-id` |

`--index` is still accepted by `issue get`, `issue edit`, the three
`issue dependency` commands and `comment add`/`comment list` - and by the same
commands under the `issue comment` alias. `--dependency-index` is still accepted
by `issue dependency add` and `issue dependency remove`.

Passing both names for the same issue is accepted while they agree, and is an
error when they disagree.

## Commands

An option written bare below has to be passed; one written `[--like this]` may
be omitted. `--repository` is bare outside the `project` and `notification`
families: those commands accept the invocation without it - the option is
optional everywhere, as the convention above says - but they have no owner-wide
endpoint to serve it with, so they answer by naming the option to pass.

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
- `gitea-cli issue get --owner <owner> --repository <repo> --issue-id <number>`
    - The `comments` field is the number of comments on the issue, not the
      comments themselves; use `gitea-cli issue comment list` to read the
      bodies. The field keeps the API's name, as
      [the field-name convention](#field-names) requires: this command used to
      rename it to `comment_count` and was alone in doing so.
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
- `gitea-cli issue edit --owner <owner> --repository <repo> --issue-id <number>`
    - Optional: `--title`, `--body`, `--state`, `--assignees`, `--milestone`,
      `--due-date`
- `gitea-cli issue close --owner <owner> --repository <repo> --issue-id <number>`
    - Optional: `--comment`
    - Closes the issue, which `issue edit --state closed` also does; this is the
      shorter way to say it and the one that takes a `--comment`.
    - `--comment` posts that body on the issue after it is closed. The issue is
      closed first, so a comment that is refused leaves the issue closed rather
      than the close undone; the result is the closed issue either way.
- `gitea-cli issue dependency add --owner <owner> --repository <repo> --issue-id <number>`
    - Required: `--dependency-owner <owner>`, `--dependency-repository <repo>`,
      `--dependency-issue-id <number>`
- `gitea-cli issue dependency list --owner <owner> --repository <repo> --issue-id <number>`
- `gitea-cli issue dependency remove --owner <owner> --repository <repo> --issue-id <number>`
    - Required: `--dependency-owner <owner>`, `--dependency-repository <repo>`,
      `--dependency-issue-id <number>`

### Pull Request - manage pull requests

- `gitea-cli pull-request list --owner <owner> --repository <repo>`
    - Optional: `--state`, `--base-branch`, `--labels`, `--milestone`,
      `--poster`, `--sort`, `--page`, `--limit`

### Comment - manage issue comments

- `gitea-cli comment add --owner <owner> --repository <repo> --issue-id <number> --body <body>`
- `gitea-cli comment list --owner <owner> --repository <repo> --issue-id <number>`
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

Every command here takes `--repository` as an option rather than a requirement:
passing it acts on that repository's project, omitting it acts on the
organization's own project. It is written `[--repository <repo>]` below to say
so.

```bash
gitea-cli project list --owner my-org                       # the organization's projects
gitea-cli project list --owner my-org --repository my-repo  # that repository's projects
```

- `gitea-cli project create --owner <owner> [--repository <repo>] --title <title>`
    - Optional: `--description`, `--card-type`, `--template-type`
- `gitea-cli project list --owner <owner> [--repository <repo>]`
- `gitea-cli project get --owner <owner> [--repository <repo>] --project-id <id>`
- `gitea-cli project edit --owner <owner> [--repository <repo>] --project-id <id>`
    - Optional: `--title`, `--description`, `--state`, `--card-type`
- `gitea-cli project delete --owner <owner> [--repository <repo>] --project-id <id>`
- `gitea-cli project column create --owner <owner> [--repository <repo>] --project-id <id> --title <title>`
    - Optional: `--color`
- `gitea-cli project column list --owner <owner> [--repository <repo>] --project-id <id>`
- `gitea-cli project column issues --owner <owner> [--repository <repo>] --project-id <id> --column-id <id>`
    - Optional: `--page`, `--limit`
- `gitea-cli project issues --owner <owner> [--repository <repo>] --project-id <id>`
- `gitea-cli project issue add --owner <owner> [--repository <repo>] --project-id <id> --column-id <id> --issue-id <id>`
    - Optional: `--issue-repository`
- `gitea-cli project issue move --owner <owner> [--repository <repo>] --project-id <id> --column-id <id> --issue-id <id>`
    - Optional: `--sorting`, `--issue-repository`
- `gitea-cli project issue remove --owner <owner> [--repository <repo>] --project-id <id> --column-id <id> --issue-id <id>`
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

### Watch - report what changed since the last run

Every other command answers a question about the instance now. `watch` answers
what moved since you last looked: it keeps a local cache of issue snapshots and
reports the difference between that cache and the instance, then records the
instance as the new baseline.

The family is called `watch` because that is what it is for. `state` names the
cache rather than the purpose, and `diff` suggests comparing two things you
name, where this compares the present against whatever was last seen.

- `gitea-cli watch list --owner <owner> [--repository <repo>] [--project-id <id>]`
    - Optional: `--state-file`, `--dry-run`

Each `--repository` watches the open issues of that repository, and each
`--project-id` watches the cards on that board. Both may be repeated, and both
may be given together, so one invocation reports what changed across several
repositories and boards:

```bash
gitea-cli watch list --owner my-org --repository api --repository web --project-id 29
```

A project is resolved the way every other `project` command resolves one:
against `--repository` when exactly one is named, and against the owner itself
when none is. Naming projects alongside several repositories is an error,
because there is no single scope left for them to belong to.

#### What counts as a change

Per issue, four things: it appeared, its assignees changed, its labels changed,
or its comments changed. An issue that dropped out of what is being watched -
closed, deleted, or moved off the board - is reported as `gone`. An issue that
changed in more than one way is reported once per way.

Comments are compared by a stable hash of each comment rather than by counting
them, so a comment edited in place is reported, and a comment added while
another was deleted is two movements rather than none.

A title or body edited on its own is **not** reported. Gitea bumps an issue's
`updated_at` for every edit, including ones there is nothing to say about, so
comparing it would report far more than it is worth.

#### The cache

The cache lives in the user cache directory (`~/.cache/gitea/watch-state.json`
on Linux) unless `--state-file` or `PYTHON_GITEA_WATCH_STATE_FILE` names
another; the option wins over the variable. Each repository and each project is
cached separately, so watching several of them keeps their deltas apart, and a
scope added later does not disturb the ones already recorded.

Three behaviours of it are worth knowing before it surprises you:

- **The first run against a scope reports nothing.** It records what is there
  and reports from the second run onwards, so pointing this at a repository with
  200 open issues does not announce all 200.
- **An unreadable cache is treated as no cache.** A missing, empty, corrupt or
  not-even-text file baselines every scope again rather than failing, so a
  scheduled run recovers by itself - at the cost of never reporting what changed
  while the cache was gone. The recovery is logged.
- **A run writes only the scopes it watched.** The cache is written by renaming
  a temporary file over it, so an interrupted run cannot leave a half-written
  one, and it is re-read immediately before that so only the scopes of this run
  are replaced. The re-read and the write are held under a lock on a `.lock`
  file beside the cache, so two runs that overlap - a timer shorter than a run
  takes is enough - record both their scopes instead of the later one erasing
  the earlier one's. The lock is released if a run is killed, so a crash cannot
  wedge the runs after it, and a filesystem that will not lock is logged and
  watched anyway. Two runs watching the _same_ scope still end with the later
  one's snapshots, which is what watching one thing twice means.
- **A cache from an older version is recorded afresh.** Upgrading to a release
  that changed how a comment is recognised makes one run silent, rather than
  announcing every comment on every watched issue as rewritten. It is logged,
  and it happens once.

`--dry-run` reports the changes and leaves the cache untouched, so the same
changes come back on the next run. Everything else about the run is unchanged,
including the requests it makes.

A cache that cannot be written fails the run: the changes it reported would
otherwise be reported again forever, which is worth an error rather than a
silent one-line difference. As with every other failure, nothing is printed on
stdout.

#### Output

In `text` - the default - the command prints one line per change and **nothing
at all when nothing changed**:

```console
$ gitea-cli watch list --owner my-org --repository my-repo
my-org/my-repo#15 comments: 1 new · Fix the docs
my-org/my-repo#16 assignees: +alice -bob · Ship the release
$ gitea-cli watch list --owner my-org --repository my-repo
$
```

That empty tick is the point: a `cron` entry mailing its output sends nothing on
a quiet run, and a watchdog reading its output has nothing to act on.

In `json` it is the usual envelope, always present whether or not anything
changed. `data` is the list of changes, each naming the scope it was seen in,
what kind of change it was, and what was added and removed:

```json
{
    "kind": "assignees",
    "scope": "repo:my-org/my-repo",
    "issue_id": 1900,
    "number": 16,
    "title": "Ship the release",
    "repository": "my-org/my-repo",
    "detail": "+alice -bob",
    "added": ["alice"],
    "removed": ["bob"]
}
```

`metadata` names the scopes watched, the ones baselined by this run,
`issue_count`, `change_count`, `state_file` and `dry_run`, so a run that
reported nothing still says why.

#### Cost

A run lists every page of each scope, and then every page of the comments of
every issue in it. That is one request per page of issues plus one per page of
comments per issue, which is what makes comment edits detectable and what makes
a large repository worth a longer interval.

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

Report what changed across two repositories and a board since the last run,
quietly enough to be worth a `cron` entry:

```bash
gitea-cli watch list \
    --owner my-org \
    --repository api \
    --repository web \
    --project-id 29
```

Read the same digest from a script, listing the issues that gained a comment:

```bash
gitea-cli --output json watch list --owner my-org --repository my-repo |
    jq -r '.data[] | select(.kind == "comments") | "\(.repository)#\(.number)"'
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
