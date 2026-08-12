# Troubleshooting

This guide covers common issues you might encounter when installing,
configuring, or using `python-gitea`, and how to resolve them.

## Setup Issues

### Virtual Environment Issues

**Problem:** Packages can't be found or dependencies conflict.

**Solutions:**

<!-- prettier-ignore-start -->

1. Create a fresh virtual environment with `uv` (`--clear` replaces the
   existing one and works on all platforms, removing the need for
   `rm -rf .venv`):

    ```bash
    uv venv --clear --python 3.12
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

2. Install the project and its development dependencies:

    ```bash
    uv sync --group dev
    ```

3. Verify the installation:

    ```bash
    python -c "import gitea; print(gitea.__version__)"
    ```

4. If you installed with `pip` instead, upgrade it first:

    ```bash
    pip install --upgrade pip uv
    ```

<!-- prettier-ignore-end -->

For details, see the [Installation Guide](../user-guide/installation.md).

### Python Version Mismatch

**Problem:** `uv venv` fails or tests don't run with the wrong Python version.

**Solutions:**

<!-- prettier-ignore-start -->

1. Check your Python version:

    ```bash
    python --version
    ```

2. `python-gitea` requires Python 3.12 or later and is built and tested against
   Python 3.12-3.14.
3. Create the virtual environment with a supported version:

    ```bash
    uv venv --python 3.12  # 3.12, 3.13, or 3.14
    source .venv/bin/activate
    ```

<!-- prettier-ignore-end -->

### Pre-commit Hooks Not Installed

**Problem:** Formatting and linting hooks don't run when you commit.

**Solutions:**

<!-- prettier-ignore-start -->

1. Ensure you're in the project root directory (must be a git repository).
2. Install the hooks with `prek`:

    ```bash
    uv run prek install
    ```

3. Run all hooks manually:

    ```bash
    uv run prek run --all-files
    ```

4. Check which hooks are configured in `.pre-commit-config.yaml`.

<!-- prettier-ignore-end -->

Pull request titles are validated in CI
(`.github/workflows/semantic_pull_request.yml`), not locally.

## Configuration Issues

### Account Not Found

**Problem:** A command fails with
`Account 'name' does not exist in the configuration.`

**Solutions:**

<!-- prettier-ignore-start -->

1. List your configured accounts:

    ```bash
    gitea-cli config list
    ```

2. Add the missing account:

    ```bash
    gitea-cli config add --name name --token YOUR_API_TOKEN --base-url https://gitea.example.com
    ```

3. Pass the account explicitly with `--account-name name`, or use a token and
   base URL directly.

<!-- prettier-ignore-end -->

See [Configuration](../user-guide/configuration.md) for the full account
workflow.

### No Default Account Available

**Problem:** A command fails with
`No default account available for authentication.`

**Solutions:**

<!-- prettier-ignore-start -->

1. Set a default account:

    ```bash
    gitea-cli config update --name name --default
    ```

2. Or pass credentials on the command line:

    ```bash
    gitea-cli issue list --owner my-org --repository my-repo --token YOUR_API_TOKEN --base-url https://gitea.example.com
    ```

<!-- prettier-ignore-end -->

The first account added becomes the default automatically.

### Duplicate Account

**Problem:** Adding an account fails with
`Account 'name' already exists in the configuration.`

**Solutions:**

<!-- prettier-ignore-start -->

1. Update the existing account instead:

    ```bash
    gitea-cli config update --name name --token NEW_TOKEN
    ```

2. Or delete it first if you want to recreate it. Include the original
   `--base-url` so the account is recreated against the same Gitea instance:

    ```bash
    gitea-cli config delete --name name
    gitea-cli config add --name name --token YOUR_API_TOKEN --base-url https://gitea.example.com
    ```

<!-- prettier-ignore-end -->

### Invalid Configuration File

**Problem:** Loading the config file fails with `Invalid configuration format`.

**Solutions:**

<!-- prettier-ignore-start -->

1. Check the config file for syntax errors and that the account fields
   (`name`, `token`, `base_url`) are valid YAML.
2. The default location is platform-dependent (see
   [Configuration](../user-guide/configuration.md)).
3. Remove or rename the broken file and reconfigure:

    ```bash
    gitea-cli config add --name name --token YOUR_API_TOKEN --base-url https://gitea.example.com
    ```

<!-- prettier-ignore-end -->

## API Issues

### Authentication Failed (401)

**Problem:** Requests return `401 Unauthorized`.

**Solutions:**

<!-- prettier-ignore-start -->

1. Verify the token is valid for the target Gitea instance.
2. Check the base URL points at your Gitea instance (not the repo web UI).
3. Confirm the token has the required scopes for the operation.

<!-- prettier-ignore-end -->

### Resource Not Found (404)

**Problem:** Requests return `404 Not Found`.

**Solutions:**

<!-- prettier-ignore-start -->

1. Verify `--owner`/`--repository` point at an existing repository.
2. Check issue/PR indices, label and milestone IDs, and project/column IDs
   exist.
3. Confirm the authenticated account has access to the resource.

<!-- prettier-ignore-end -->

### JSON Parsing Errors

**Problem:** Logs show `Failed to parse JSON response` and methods return empty
data.

**Solutions:**

<!-- prettier-ignore-start -->

1. Confirm the base URL points at a Gitea API endpoint, e.g.
   `https://gitea.example.com` (the client appends `/api/v1`).
2. Test the endpoint with a manual request, for example by calling
   `https://gitea.example.com/api/v1/user` with your token in the authorization
   header.

<!-- prettier-ignore-end -->

## Testing Issues

### Pytest Fails to Collect Tests

**Problem:** `pytest` returns "no tests collected" or import errors.

**Solutions:**

<!-- prettier-ignore-start -->

1. Verify test file naming: pytest discovers `test_*.py` and `*_test.py` by
   default.
2. Verify test function naming: names must start with `test` (e.g. `test_list_issues`
   or `test_list`); this project uses `test_`-prefixed names.
3. Run from the project root:

    ```bash
    uv run pytest -vv
    ```

4. Check test discovery:

    ```bash
    uv run pytest --collect-only
    ```

<!-- prettier-ignore-end -->

### Import Errors in Tests

**Problem:** Tests can't import `gitea` modules.

**Solutions:**

<!-- prettier-ignore-start -->

1. Ensure development dependencies are installed:

    ```bash
    uv sync --group dev
    ```

2. Verify the `src` layout is correct (package lives in `src/gitea/`) and that
   `[tool.pytest.ini_options].pythonpath` includes `src`.
3. Run from the project root directory.

<!-- prettier-ignore-end -->

### Coverage Report Issues

**Problem:** Coverage report shows 0% or missing files.

**Solutions:**

<!-- prettier-ignore-start -->

1. Run pytest with coverage:

    ```bash
    uv run pytest --cov-report=html
    ```

2. Coverage is configured in `pyproject.toml` under `[tool.coverage]`; the
   default `addopts` already enables coverage on `src`.
3. Verify test files import from the `src/` layout correctly.

<!-- prettier-ignore-end -->

## Pre-commit Hook Issues

### Hooks Running Too Slowly

**Problem:** Pre-commit takes a very long time or times out.

**Solutions:**

<!-- prettier-ignore-start -->

1. Check which hooks are slow:

    ```bash
    uv run prek run --all-files --verbose
    ```

2. Run specific hooks:

    ```bash
    uv run prek run ruff --all-files
    uv run prek run prettier --all-files
    ```

<!-- prettier-ignore-end -->

### Formatting Changes After Commit

**Problem:** Pre-commit auto-fixes files, but you didn't expect it.

**Solutions:**

<!-- prettier-ignore-start -->

1. This is normal behavior - review the changes.
2. Stage the new changes and commit again:

    ```bash
    git add .
    git commit -m "your message"
    ```

3. Modify the tool settings if the behavior is unwanted (e.g. in
   `.pre-commit-config.yaml` or `pyproject.toml`).

<!-- prettier-ignore-end -->

### "Unstaged Changes" After Running Hooks

**Problem:** Pre-commit modified files but they're not staged.

**Solutions:**

<!-- prettier-ignore-start -->

1. This is expected - review the changes:

    ```bash
    git diff
    ```

2. Stage and commit:

    ```bash
    git add .
    git commit -m "your message"
    ```

<!-- prettier-ignore-end -->

## Getting Help

If you encounter issues not listed here:

<!-- prettier-ignore-start -->

1. **Check existing issues**: Search
   [GitHub Issues](https://github.com/isaac-cf-wong/python-gitea/issues) for
   your problem.
2. **Review logs carefully**: Run with verbose logging to see request details:

    ```bash
    gitea-cli --verbose DEBUG issue list --owner my-org --repository my-repo
    ```

3. **Try a minimal reproduction**: Isolate the problem to a single command.
4. **Ask for help**: Open an
   [issue](https://github.com/isaac-cf-wong/python-gitea/issues/new/choose) with:
   - Your environment (Python version, OS)
   - Steps to reproduce
   - Full error message/logs
   - What you've already tried

<!-- prettier-ignore-end -->
