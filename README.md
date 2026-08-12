# python-gitea

[![Python CI](https://github.com/isaac-cf-wong/python-gitea/actions/workflows/ci.yml/badge.svg)](https://github.com/isaac-cf-wong/python-gitea/actions/workflows/ci.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/isaac-cf-wong/python-gitea/main.svg)](https://results.pre-commit.ci/latest/github/isaac-cf-wong/python-gitea/main)
[![Documentation Status](https://github.com/isaac-cf-wong/python-gitea/actions/workflows/documentation.yml/badge.svg)](https://isaac-cf-wong.github.io/python-gitea/)
[![codecov](https://codecov.io/gh/isaac-cf-wong/python-gitea/graph/badge.svg?token=COF8341N60)](https://codecov.io/gh/isaac-cf-wong/python-gitea)
[![PyPI Version](https://img.shields.io/pypi/v/python-gitea)](https://pypi.org/project/python-gitea/)
[![Python Versions](https://img.shields.io/pypi/pyversions/python-gitea)](https://pypi.org/project/python-gitea/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/isaac-cf-wong/python-gitea/blob/main/LICENSE)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![DOI](https://zenodo.org/badge/1129170965.svg)](https://doi.org/10.5281/zenodo.18211496)

A Python package for interacting with the Gitea API. It provides a simple,
intuitive interface to access Gitea repositories, users, organizations, issues,
and more, enabling seamless integration with Gitea instances for automation,
data retrieval, and management tasks.

## Features

- **Full API Coverage**: Repositories, users, organizations, issues, pull
  requests, comments, labels, milestones, notifications, and projects.
- **Easy Authentication**: Token-based authentication, with multiple saved
  accounts and a default-account fallback.
- **Asynchronous Support**: Built with `async`/`await` for non-blocking
  operations alongside the synchronous client.
- **Type Hints**: Full type annotations for better IDE support and code
  reliability.
- **Command-Line Interface**: Interact with the Gitea API directly from the
  terminal for quick, scriptable operations without writing code.
- **Comprehensive Documentation**: Detailed guides and a generated API
  reference.

## Quick Start

### 1. Install

```bash
uv venv --python 3.13
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install python-gitea
```

### 2. Configure an account

```bash
gitea-cli config add --name my_account --token YOUR_API_TOKEN --base-url https://gitea.example.com
```

### 3. Use the CLI

```bash
# List issues of a repository
gitea-cli issue list --owner my-org --repository my-repo

# Get a user
gitea-cli user get --username my-org
```

### 4. Use the Python API

```python
from gitea.client.gitea import Gitea

with Gitea(token="YOUR_API_TOKEN", base_url="https://gitea.example.com") as client:
    issues, _ = client.issue.list_issues(owner="my-org", repository="my-repo")
```

For details, see the
[Quick Start](https://isaac-cf-wong.github.io/python-gitea/user-guide/quickstart/),
[Configuration](https://isaac-cf-wong.github.io/python-gitea/user-guide/configuration/),
and
[Python API](https://isaac-cf-wong.github.io/python-gitea/user-guide/python-api/)
guides in the documentation.

## Installation

We recommend using `uv` to manage virtual environments for installing
`python-gitea`.

If you don't have `uv` installed, you can install it with pip. See the project
pages for more details:

- Install via pip: `pip install --upgrade pip && pip install uv`
- Project pages: [uv on PyPI](https://pypi.org/project/uv/) |
  [uv on GitHub](https://github.com/astral-sh/uv)
- Full documentation and usage guide: [uv docs](https://docs.astral.sh/uv/)

### Requirements

- Python 3.12 or higher
- Operating System: Linux, macOS, or Windows

### Install from PyPI

The recommended way to install `python-gitea` is from PyPI:

```bash
# Create a virtual environment (recommended with uv)
uv venv --python 3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install python-gitea
```

#### Optional Dependencies

For development or specific features:

```bash
# Development dependencies (testing, linting, etc.)
uv pip install python-gitea[dev]

# Documentation dependencies
uv pip install python-gitea[docs]

# All dependencies
uv pip install python-gitea[dev,docs]
```

### Install from Source

For the latest development version:

```bash
git clone git@github.com:isaac-cf-wong/python-gitea.git
cd python-gitea
# Create a virtual environment (recommended with uv)
uv venv --python 3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install .
```

#### Development Installation

To set up for development:

```bash
git clone git@github.com:isaac-cf-wong/python-gitea.git
cd python-gitea

# Create a virtual environment (recommended with uv)
uv venv --python 3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync --group dev

# Install pre-commit hooks
uv run prek install
```

### Verify Installation

Check that `python-gitea` is installed correctly:

```bash
gitea-cli --help
```

```bash
python -c "import gitea; print(gitea.__version__)"
```

## Documentation

Full documentation is available at
[https://isaac-cf-wong.github.io/python-gitea](https://isaac-cf-wong.github.io/python-gitea).

## Contributing

Contributions are welcome! Please read the
[Contributing Guide](https://isaac-cf-wong.github.io/python-gitea/contributing/)
before opening a pull request.

## Testing

Run the test suite:

```bash
uv run pytest
```

## License

This project is licensed under the MIT License - see the
[LICENSE](https://github.com/isaac-cf-wong/python-gitea/blob/main/LICENSE) file
for details.

## Support

For questions, issues, or contributions, please:

- Check the [documentation](https://isaac-cf-wong.github.io/python-gitea/)
- Open an issue on
  [GitHub](https://github.com/isaac-cf-wong/python-gitea/issues)
- Join our
  [discussions](https://github.com/isaac-cf-wong/python-gitea/discussions)

## Changelog

See [Release Notes](https://github.com/isaac-cf-wong/python-gitea/releases) for
version history.
