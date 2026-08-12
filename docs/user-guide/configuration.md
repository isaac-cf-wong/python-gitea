# Configuration

`python-gitea` authenticates to Gitea with a personal access token and a base
URL. You can either store named accounts in a configuration file, or pass the
token and base URL directly on every call.

## Configuration File

Named accounts live in a YAML file in the user config directory. The exact path
is platform-dependent (`platformdirs.user_config_dir("gitea")`):

| Platform | Path                                              |
| -------- | ------------------------------------------------- |
| Linux    | `~/.config/gitea/config.yaml`                     |
| macOS    | `~/Library/Application Support/gitea/config.yaml` |
| Windows  | `%APPDATA%\\gitea\\config.yaml`                   |

You can point at a different file with the `PYTHON_GITEA_CONFIG_PATH`
environment variable or the `--config-path` CLI option.

### File Format

```yaml
accounts:
    main:
        name: main
        token: YOUR_API_TOKEN
        base_url: https://gitea.example.com
default_account: main
```

`default_account` selects the account used when no account or token is given.

## Managing Accounts with the CLI

### Add an Account

```bash
gitea-cli config add \
    --name my_account \
    --token YOUR_API_TOKEN \
    --base-url https://gitea.example.com
```

The first account added becomes the default. Pass `--default` to make any
account the default:

```bash
gitea-cli config add --name other --token TOKEN --base-url https://gitea.example.com --default
```

### List Accounts

```bash
gitea-cli config list
```

Output shows the default account and the base URL of each configured account
(tokens are never printed).

### Update an Account

```bash
gitea-cli config update --name my_account --token NEW_TOKEN --base-url https://new.example.com --default
```

Any of `--token`, `--base-url`, or `--default` may be omitted to leave that
value unchanged.

### Delete an Account

```bash
gitea-cli config delete --name my_account
```

The command asks for confirmation unless `--force`/`-f` is passed.

## Authentication without the Configuration File

Every CLI command and the Python client accept a token and base URL directly. On
the CLI:

```bash
gitea-cli issue list \
    --owner my-org \
    --repository my-repo \
    --token YOUR_API_TOKEN \
    --base-url https://gitea.example.com
```

With `--account-name NAME`, the token and base URL are taken from the named
account. Without any of `--account-name`, `--token`, or `--base-url`, the
default account is used.

## Authentication Precedence

The resolution order is:

1. `--account-name NAME` - use the stored account and ignore any
   `--token`/`--base-url`.
2. `--token` and `--base-url` - use them directly; both are required together.
3. Default account - used when neither an account nor a token is given.

If no account matches and no token is given, the CLI raises a clear error.

## Programmatic Configuration

The same file is managed through the `ConfigManager` class:

```python
from gitea.config.manager import ConfigManager

manager = ConfigManager()
manager.add_account(name="main", token="TOKEN", base_url="https://gitea.example.com")
manager.save_config()
```

## See Also

- [Installation](installation.md)
- [Python API](python-api.md)
- [Command-Line Interface](cli.md)
