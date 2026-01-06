# Development Tools

This guide covers the development tools configured in this template,
including pre-commit hooks, code quality tools, and how to use them effectively.

## Overview

The template includes a comprehensive set of tools for maintaining code quality, consistency, and reliability:

- **Pre-commit hooks**: Automated checks before commits
- **Code formatting**: Black for consistent style
- **Linting**: Ruff and Pylint for code quality
- **Type checking**: Pyright for static analysis
- **Spell checking**: CSpell for documentation
- **Security scanning**: Bandit for vulnerability detection

## Pre-commit Hooks

Pre-commit runs automated checks before each commit to catch issues early.

### Setup

```bash
pre-commit install
pre-commit install --hook-type commit-msg  # For commit message validation
```

### Configuration (`.pre-commit-config.yaml`)

The configuration includes hooks for:

- **Code formatting**: Black, isort
- **Linting**: Ruff, Pylint
- **Type checking**: Pyright
- **Security**: Bandit
- **Spell checking**: CSpell
- **General**: Trailing whitespace, end-of-file fixes

### Running Pre-commit

```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files

# Run on staged files (automatic on commit)
pre-commit run
```

## Code Formatting

### Black

Black is an uncompromising code formatter that ensures consistent style.

**Configuration** (in `pyproject.toml`):

```toml
--8<-- "pyproject.toml:77:79"
```

**Usage**:

```bash
# Format files
black src/ tests/

# Check formatting without changes
black --check src/ tests/
```

### Ruff

Ruff is a fast Python linter and formatter, alternative to Flake8.

**Configuration** (in `pyproject.toml`):

```toml
--8<-- "pyproject.toml:287:289"
```

**Usage**:

```bash
# Lint and fix
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

## Linting and Code Quality

### Pylint

Pylint provides detailed code analysis and style checking.

**Configuration** (in `pyproject.toml`):

```toml
--8<-- "pyproject.toml:161:178"
```

**Usage**:

```bash
pylint src/your_package/
```

### Flake8

Flake8 combines PyFlakes, pycodestyle, and McCabe for comprehensive checking.

**Configuration** (in `pyproject.toml`):

```toml
--8<-- "pyproject.toml:87:102"
```

**Usage**:

```bash
flake8 src/ tests/
```

## Type Checking

### Pyright

Pyright provides static type checking for Python.

**Configuration** (in `pyproject.toml`):

```toml
--8<-- "pyproject.toml:104:115"
```

**Usage**:

```bash
pyright
```

## Spell Checking

### CSpell

CSpell checks spelling in code comments, documentation, and strings.

**Configuration** (`cspell.json`):

```json
--8<-- "cspell.json:5:12"
```

**Usage**:

```bash
cspell "**/*.{py,md}"
```

## Security Scanning

### Bandit

Bandit finds common security issues in Python code.

**Configuration** (in `pyproject.toml`):

```toml
--8<-- "pyproject.toml:71:75"
```

**Usage**:

```bash
bandit -r src/
```

## Testing Tools

### Pytest

Pytest is the testing framework with coverage reporting.

**Configuration** (in `pyproject.toml`):

```toml
--8<-- "pyproject.toml:117:129"
```

**Usage**:

```bash
# Run tests
pytest

# Run specific test
pytest tests/test_specific.py::test_function
```

### Coverage

Coverage.py measures code coverage.

**Configuration** (in `pyproject.toml`):

```toml
--8<-- "pyproject.toml:81:85"
```

The default minimum coverage is set to 0%.
You should aim for higher coverage as you add tests.

## Additional Tools

### Commitlint

Validates commit messages follow conventional commits format.

**Configuration** (`commitlint.config.js`):

```javascript
--8<-- "commitlint.config.js:2:3"
```

### ShellCheck

Checks shell scripts for common issues.

**Usage**:

```bash
shellcheck scripts/*.sh
```

## Customizing Tool Configurations

### Modifying Rules

Edit configurations in `pyproject.toml`:

```toml
--8<-- "pyproject.toml:77:78"

--8<-- "pyproject.toml:287:289"
```

### Adding New Tools

1. Add to `pyproject.toml` or separate config files
2. Include in `.pre-commit-config.yaml` if applicable
3. Update CI workflows

### Disabling Tools

Comment out or remove from `.pre-commit-config.yaml`:

```yaml
# - repo: https://github.com/psf/black
#   ...
```

## CI/CD Integration

All tools run automatically in GitHub Actions:

- **Validation workflow**: Runs on PRs and pushes
- **Publish workflow**: Runs on releases

Check `.github/workflows/` for details.

## Troubleshooting

### Pre-commit Issues

- **Hook fails**: Run `pre-commit run --all-files` locally first
- **Slow commits**: Some hooks may be slow; consider selective running

### Tool Conflicts

- **Multiple formatters**: Choose one (Black recommended)
- **Conflicting rules**: Adjust configurations to avoid conflicts

### Performance

- **Slow linting**: Use Ruff instead of Flake8 for speed
- **Large codebase**: Configure excludes for generated files

## Best Practices

- **Run tools locally**: Fix issues before committing
- **Consistent configuration**: Keep settings in `pyproject.toml`
- **Regular updates**: Update tool versions periodically
- **Team alignment**: Ensure all developers use the same tools

For more information, see the [Pre-commit documentation](https://pre-commit.com/) and individual tool docs.
