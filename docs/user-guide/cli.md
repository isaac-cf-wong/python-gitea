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
  `issue_count` for `project issues` and `project show`.
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
on the project entries of `issue get`, and `issue_count` and `issue_ids` on the
columns of `project show`, are the ones today. Such a field is never a second
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

Every command that addresses something an account owns names its target the same
way, so an invocation can be written without reading `--help` first:

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

A command whose target is an account rather than something an account owns takes
no `--owner` at all, and names the account with `--username` instead: `org list`
lists an account's organizations and `user get` reads an account's profile, both
answering for the account the token belongs to when `--username` is omitted.

`repo list` is the one command where the _kind_ of owner matters: Gitea serves
an organization's repositories and a user's at different endpoints, so
`--owner-type` says which of the two `--owner` names. It defaults to
`organization`.

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

### Actions - run and inspect workflows

A workflow is the file in the repository and what is dispatched, a run is one
execution of it and what carries the status, and a job is a part of a run and
what carries the logs. The commands are grouped that way.

`--workflow-id` is the workflow's **file name** - `build.yml` - and not a
number: that is what Gitea's endpoint takes. `--run-id` and `--job-id` are IDs,
as everywhere else.

- `gitea-cli actions workflow list --owner <owner> --repository <repo>`
- `gitea-cli actions workflow get --owner <owner> --repository <repo> --workflow-id <file>`
- `gitea-cli actions workflow dispatch --owner <owner> --repository <repo> --workflow-id <file> --ref <ref>`
    - Optional: `--input KEY=VALUE` (repeatable), `--return-run-details`
    - The workflow has to declare a `workflow_dispatch` trigger: that is the
      trigger a dispatch fires, so a workflow without one has nothing for this
      to start.
    - Gitea accepts a dispatch with `204` and no body, which says the request
      was taken but not which run it started. `--return-run-details` asks the
      response to name the run - `workflow_run_id`, `run_url`, `html_url` - so a
      script can follow the run it dispatched instead of guessing which of the
      runs that appeared is its own. An instance too old to know the parameter
      answers without a body as before, so treat an empty `data` as "accepted,
      run not named" rather than as a failure.
    - Only the first `=` of an `--input` divides the name from the value, so
      `--input query=a=b` sets `query` to `a=b`. An input given twice with two
      different values is refused rather than one of them silently kept.
- `gitea-cli actions run list --owner <owner> --repository <repo>`
    - Optional: `--workflow-id`, `--event`, `--branch`, `--status`, `--actor`,
      `--head-sha`, `--exclude-pull-requests`, `--page`, `--limit`
    - `--status` is one of `pending`, `queued`, `in_progress`, `failure`,
      `success`, `skipped`.
    - `--workflow-id` asks a different endpoint - the workflow's own runs -
      rather than filtering the repository's.
- `gitea-cli actions run get --owner <owner> --repository <repo> --run-id <id>`
    - `status` says how far the run has got, `conclusion` how it ended. A run
      still going has no conclusion yet.
- `gitea-cli actions run jobs --owner <owner> --repository <repo> --run-id <id>`
    - Optional: `--status`, `--page`, `--limit`
- `gitea-cli actions job get --owner <owner> --repository <repo> --job-id <id>`
    - The job carries its `steps`, each with a `status` and a `conclusion`,
      which is where a failure is narrowed to the step that failed.
- `gitea-cli actions job logs --owner <owner> --repository <repo> --job-id <id>`
    - Text output is the log itself, so it can be piped, grepped or redirected
      like the file it is; `--output json` wraps it in the envelope instead,
      with the log as a string under `logs` and `job_id` alongside it. A job
      that has produced nothing yet prints nothing.

The three listings here answer with an **object** and not with the bare array
the other listings in this CLI return: `total_count` alongside `workflows`,
`workflow_runs` or `jobs`. That is the shape Gitea's Actions endpoints send, and
[the field-name convention](#field-names) is why it is passed through rather
than flattened. So a script reads `.data.workflow_runs[]` where it would read
`.data[]` for issues. One page is fetched per invocation; `--page` and `--limit`
walk a long history.

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
- `gitea-cli project show --owner <owner> [--repository <repo>] --project-id <id>`
    - Optional: `--full`
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
    - Optional: `--sorting`, `--issue-repository`, `--add-if-missing`
    - Moves the card the issue already has on the project, and confirms it
      arrived in `--column-id`. An issue with no card there is reported as an
      error naming `project issue add`; `--add-if-missing` has this command put
      it in `--column-id` instead.
- `gitea-cli project issue remove --owner <owner> [--repository <repo>] --project-id <id> --issue-id <id>`
    - Optional: `--column-id`, `--issue-repository`
    - Takes the issue's card off the project. `--column-id` is the column the
      card is in, and is found on the board when it is omitted; an issue with no
      card there is reported as having none.

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

`--column-id` does not mean the same thing to all three commands. For `add` and
`move` it is where the card is going, which only the caller can say. For
`remove` it is where the card already is, which the board can be asked - so the
option is optional there, and omitting it has the project's columns walked to
find the card:

```console
$ gitea-cli project issue remove --owner my-org --project-id 1 \
      --issue-repository my-repo --issue-id 42
```

The column the card was taken off comes back as `metadata.resolved_column_id`,
and an issue with no card on the project is reported as having none rather than
removed from a column chosen for it.

A column found that way is read back as well: the board is walked again after
the removal, and a zero exit status says that no column of the project holds a
card for the issue afterwards, rather than that a request to take one off was
accepted. The walk and the removal are separate requests, so a card moved in
between leaves the removal addressed to a column the card has left, which is a
removal with nothing to do — and whether the instance refuses that call or
answers it with a success, the status code is an answer about the request and
not about the card. It is the whole board that is read back rather than the
column the removal named, because that column holds no card whether the removal
took it off or the card had already moved elsewhere. The window is narrowed and
not closed: Gitea has no conditional delete, so a card put back on the board
after the confirming walk is one the command has already reported on.

A `--column-id` that is passed is used as it stands, and nothing is read back
for it: a column that does not hold the card is the caller's call to make rather
than something quietly corrected here, and whatever the instance answers such a
removal with is reported as it came.

`add` and `move` are not two ways of doing the same thing. `add` puts an issue
on a board, giving it a card in a column; `move` relocates the card it already
has there, and an issue with no card has nothing to relocate. Gitea's move
endpoint does not say so - it moves the row relating the issue to the project,
of which there is none, and answers with a success and an empty body having
moved nothing - so the command finds the card first and reports its absence
itself:

```console
$ gitea-cli project issue move --owner my-org --project-id 1 --column-id 2 \
      --issue-repository my-repo --issue-id 42
No column of project 1 holds issue #42 of my-org/my-repo (global ID 1854), so there is
no card to move. [...] Put the issue on the board with 'gitea-cli project issue add
--owner my-org --project-id 1 --column-id 2 --issue-id 42 --issue-repository my-repo',
or pass --add-if-missing to have this command do that when there is no card yet.
```

`--add-if-missing` makes the one call do either, which is what a script
advancing cards through columns wants: the card is moved when it exists and
created in `--column-id` when it does not. `--sorting` is refused on that second
path rather than dropped, since the endpoint putting a card on a board takes no
position within the column. A board that cannot be read is reported as such and
stops the move: a failed lookup is not evidence that the issue has no card.

Whichever call is made, `--column-id` is then read back, because the success the
endpoint answers with has already been shown not to mean the card went anywhere.
A zero exit status therefore says the card was seen in that column, rather than
that Gitea accepted a request to put it there - and the three ways that can fail
are reported apart: the issue has no card at all, the card is not in the column
it was sent to, or the reading back could not be done and it is unknown which.
It does not say the card is still there: the calls are separate requests, and
Gitea has no conditional move to make them one, so a card taken off the board
after the command read it is outside what any client can report on.

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

### Org - discover organizations

- `gitea-cli org list`
    - Optional: `--username`, `--page`, `--limit`
    - Lists the organizations of the account the token belongs to; `--username`
      lists those of another account instead.
    - Gitea also has a site-wide listing of every organization, which a token
      that is not scoped for it is refused. This command does not read from it,
      so it answers with the organizations of an account and never with the
      instance's.

### Repo - discover repositories

- `gitea-cli repo list --owner <owner>`
    - Optional: `--owner-type`, `--page`, `--limit`
    - `--owner-type` is `organization` (the default) or `user`: Gitea serves the
      two at different endpoints - `/orgs/<owner>/repos` and
      `/users/<owner>/repos` - and an owner's name does not say which of the two
      it is.

```bash
gitea-cli repo list --owner my-org                     # an organization's repositories
gitea-cli repo list --owner alice --owner-type user    # a user's repositories
```

### Watch - report what changed since the last run

Every other command answers a question about the instance now. `watch` answers
what moved since you last looked: it keeps a local cache of issue snapshots and
reports the difference between that cache and the instance, then records the
instance as the new baseline. `list` does both in one run; `--no-advance` and
`advance` pull them apart, for a caller that wants a change to survive until it
has been acted on rather than until it has been reported.

The family is called `watch` because that is what it is for. `state` names the
cache rather than the purpose, and `diff` suggests comparing two things you
name, where this compares the present against whatever was last seen.

- `gitea-cli watch list --owner <owner> [--repository <repo>] [--project-id <id>]`
    - Optional: `--state-file`, `--dry-run` (also spelled `--no-advance`)
- `gitea-cli watch advance --owner <owner> [--repository <repo>] [--project-id <id>]`
    - Optional: `--state-file`

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

#### Detecting a change without consuming it

By default `list` does both at once: it reports the difference and advances the
cache past it, so a change is announced exactly once whether or not anyone was
in a position to act on it. A consumer that was busy - its previous run still in
flight, its queue full - drops the change, and the next run has nothing to say
about it.

`--dry-run`, also spelled `--no-advance`, reports the changes and leaves the
cache exactly as it was, so they come back on the next run. Everything else
about the run is unchanged, including the requests it makes. `watch advance`
then records the current state as the new baseline, which is how a caller
commits the cache once it has actually handled what it was told about:

```bash
changes=$(gitea-cli --output json watch list --owner my-org --repository my-repo --no-advance)
if handle "$changes"; then
    gitea-cli watch advance --owner my-org --repository my-repo
fi
```

`advance` names its scopes exactly as `list` does, reads the same
`--state-file`, and reports one line per scope rather than one per change:

```console
$ gitea-cli watch advance --owner my-org --repository my-repo --project-id 29
repo:my-org/my-repo: recorded 12 issues, 1 change baselined
project:my-org/29: recorded 5 issues, unchanged since the cache
```

In `json` its `data` is one record per scope - `scope`, `issue_count`,
`change_count` and `baselined` - and its `metadata` carries `scopes`,
`baselined_scopes`, `issue_count`, `change_count` and `state_file`.

What it commits is the state of the instance **now**, not the state the dry run
saw: the dry run deliberately wrote nothing down, so there is nothing else left
to commit. That leaves one window the pair does not close - a change landing
between the two calls is baselined without ever having been reported.
`change_count` is how far the baseline moved, so an advance reporting more
changes than its dry run did is that window showing; keeping the two calls close
together is what keeps it small.

#### Cost

A run lists every page of each scope, and then every page of the comments of
every issue in it. That is one request per page of issues plus one per page of
comments per issue, which is what makes comment edits detectable and what makes
a large repository worth a longer interval.

`advance` costs exactly what `list` costs: it walks the same pages, and only
what it does with them differs. Pairing a dry run with an advance therefore
doubles the requests of the tick it replaces.

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

Start a workflow, then follow the run it started:

```bash
run=$(gitea-cli --output json actions workflow dispatch \
    --owner my-org \
    --repository my-repo \
    --workflow-id build.yml \
    --ref main \
    --input environment=staging \
    --return-run-details |
    jq -r '.data.workflow_run_id')

gitea-cli --output json actions run get --owner my-org --repository my-repo --run-id "$run" |
    jq -r '.data | "\(.status) \(.conclusion // "-")"'
```

Read the log of the job that failed:

```bash
gitea-cli --output json actions run jobs \
    --owner my-org --repository my-repo --run-id 42 |
    jq -r '.data.jobs[] | select(.conclusion == "failure") | .id' |
    while read -r job; do
        gitea-cli actions job logs --owner my-org --repository my-repo --job-id "$job"
    done
```

Put an issue on a project board, in a column of it, addressing the issue by the
number shown in the web UI:

```bash
gitea-cli project issue add \
    --owner my-org \
    --repository my-repo \
    --project-id 1 \
    --column-id 2 \
    --issue-id 42
```

Move the card of `my-repo#42` on an organization project, where the repository
holding the issue has to be named separately, and put it on the board if it is
not there yet:

```bash
gitea-cli project issue move \
    --owner my-org \
    --project-id 1 \
    --column-id 2 \
    --issue-repository my-repo \
    --issue-id 42 \
    --add-if-missing
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

Read a board's shape in one call - the project, its columns, and how many cards
sit in each of them. `project get` answers with the project alone, which says
nothing about where the cards are:

```console
$ gitea-cli --output json project show --owner my-org --project-id 31
{
  "data": {
    "project": { "id": 31, "title": "Board", "state": "open", ... },
    "columns": [
      { "id": 117, "title": "Working", ..., "issue_count": 2, "issue_ids": [1873, 1874] }
    ]
  },
  "metadata": { "status_code": 200, "column_count": 1, "issue_count": 2 }
}
```

Each column is the columns endpoint's own object with `issue_count` and
`issue_ids` added to it, and `issue_ids` holds the global issue IDs the project
endpoints take - `--issue-id` without `--issue-repository`. Add `--full` to have
each column carry its issues themselves, under `issues`, rather than their IDs
alone. Every page of columns, and of each column's issues, is walked, so the
counts describe the whole board.

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
