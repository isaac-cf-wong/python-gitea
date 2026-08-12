# Installation

We recommend using `uv` to manage virtual environments for installing
`python-gitea`.

If you don't have `uv` installed, you can install it with pip. See the project
pages for more details:

- Install via pip: `pip install --upgrade pip && pip install uv`
- Project pages: [uv on PyPI](https://pypi.org/project/uv/) |
  [uv on GitHub](https://github.com/astral-sh/uv)
- Full documentation and usage guide: [uv docs](https://docs.astral.sh/uv/)

## Requirements

- Python 3.12 or higher
- Operating System: Linux, macOS, or Windows

<!-- prettier-ignore -->
!!!note
    The package requires Python 3.12 or later and is built and tested against Python 3.12-3.14. When creating a
    virtual environment with `uv`, specify the Python version to ensure compatibility: `uv venv --python 3.12`
    (replace `3.12` with your preferred supported version: 3.12, 3.13, or 3.14). This avoids potential issues
    with unsupported Python versions.

## Install from PyPI

The recommended way to install `python-gitea` is from PyPI:

```bash
# Create a virtual environment (recommended with uv)
uv venv --python 3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install python-gitea
```

### Optional Dependencies

For development or specific features:

```bash
# Development dependencies (testing, linting, etc.)
uv pip install "python-gitea[dev]"

# Documentation dependencies
uv pip install "python-gitea[docs]"

# All dependencies
uv pip install "python-gitea[dev,docs]"
```

## Install from Source

For the latest development version:

```bash
git clone git@github.com:isaac-cf-wong/python-gitea.git
cd python-gitea
# Create a virtual environment (recommended with uv)
uv venv --python 3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync
```

### Development Installation

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

## Verify Installation

Check that `python-gitea` is installed correctly:

```bash
gitea-cli --help
```

```bash
python -c "import gitea; print(gitea.__version__)"
```

## Getting Help

1. Check the [troubleshooting guide](../dev/troubleshooting.md)
2. Search existing
   [issues](https://github.com/isaac-cf-wong/python-gitea/issues)
3. Create a new issue with:
    - Your operating system and Python version
    - Full error message
    - Steps to reproduce the problem
