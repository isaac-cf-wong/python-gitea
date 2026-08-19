# Contributing to python-gitea

🎉 Thank you for your interest in contributing to `python-gitea`! Your ideas,
fixes, and improvements are welcome and appreciated.

Whether you’re fixing a typo, reporting a bug, suggesting a feature, or
submitting a pull request—this guide will help you get started.

## How to Contribute

<!-- prettier-ignore-start -->

1. Open an Issue

    - Have a question, bug report, or feature suggestion?
    [Open an issue](https://github.com/isaac-cf-wong/python-gitea/issues/new/choose)
    and describe your idea clearly.
    - Check for existing issues before opening a new one.

2. Fork and Clone the Repository

    ```shell
    git clone git@github.com:<username>/python-gitea.git
    cd python-gitea
    ```

3. Set Up Your Environment

    We recommend using uv to manage virtual environments for installing `python-gitea`.
    If you don't have uv installed, you can install it with pip. See the project pages for more details:

    - Install via pip: `pip install --upgrade pip && pip install uv`
    - Project pages: [uv on PyPI](https://pypi.org/project/uv/) | [uv on GitHub](https://github.com/astral-sh/uv)
    - Full documentation and usage guide: [uv docs](https://docs.astral.sh/uv/)

    ```shell
    # Create a virtual environment (recommended with uv)
    uv venv --python 3.12
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    uv pip install -e .
    ```

4. Set Up Pre-commit Hooks

    We use **pre-commit** to ensure code quality and consistency.
    After syncing dependencies, run:

    ```shell
    uv run prek install
    ```

    This installs hooks so formatting, linting, and other checks run when you
    commit.

    Pull request titles are validated in GitHub Actions (see
    `.github/workflows/semantic_pull_request.yml`) using the same Conventional
    Commit vocabulary described under [Commit Message Guidelines](#commit-message-guidelines).

    !!!important
        The changelog is auto-generated from commits. Use Conventional Commits
        locally so `git-cliff` can classify changes, and match that style in PR
        titles so CI passes.

5. Create a New Branch

    Give it a meaningful name like fix-typo-in-docs or feature-add-summary-option.

6. Make Changes

    - Write clear, concise, and well-documented code.
    - Follow [PEP 8](https://pep8.org/) style conventions.
    - Add or update unit tests when applicable.
    - **Keep changes atomic and focused**: one type of change per commit
      (e.g., do not mix refactoring with feature addition).

7. Run Tests

    Ensure that all tests pass before opening a pull request:

    ```shell
    pytest
    ```

    Mutation testing runs the suite again for each deliberate alteration of the
    source, and reports the alterations no test noticed:

    ```shell
    uv run mutmut run                  # every module
    uv run mutmut run "gitea.cli.*"    # one subtree, while iterating
    uv run mutmut results              # what survived
    ```

    A survivor is a change to the code that every test tolerated. Some cannot be
    killed - a rewritten `typing.cast`, or anything in a `register_commands()`
    that runs at import time - so read the diff `uv run mutmut show <mutant>`
    prints before writing a test for one.

    A filter selects which mutants are _run_, not which are written: every module
    is mutated either way, so a scoped run still reports mutating the whole tree
    and its progress counter reads `46/9042`, where the denominator counts every
    mutant written and the numerator counts the ones the filter selected and
    checked. Take the result of a scoped run from `uv run mutmut results` rather
    than from that counter: it lists every mutant that was not killed, labelling
    each as `survived` or as `not checked`, and naming the module it belongs to,
    so the survivors of a scope are the `survived` entries whose names begin with
    it. A filter matching no mutant stops the run with an error instead of
    quietly widening it, so a scoped run that gets as far as testing is one that
    scoped.

    To scope what is _written_ as well, and get a counter whose denominator is
    the scope, point `source_paths` at the modules and let `also_copy` carry the
    rest of the package that the tests import:

    ```toml
    [tool.mutmut]
    source_paths = ["src/gitea/project/project.py"]
    also_copy = ["scripts/", "src/"]
    ```

8. Open a Pull Request

    Clearly describe the motivation and scope of your change. Link it to the relevant issue if applicable.
    The pull request titles should match the [Conventional Commits spec](https://www.conventionalcommits.org/).

<!-- prettier-ignore-end -->

## Commit Message Guidelines

**Why this matters:** Our changelog is automatically generated from commit
messages using git-cliff. Commit messages must follow the Conventional Commits
format and adhere to strict rules.

### Rules

<!-- prettier-ignore-start -->

1. **One type of change per commit**

    - Do not mix different types of changes (e.g., bug fixes, features, refactoring) in a single commit.
    - Example: if you refactor code AND add a feature, make two separate commits.

2. **Descriptive and meaningful messages**

    - Describe _what_ changed and _why_, not just _what_ was edited.
    - Avoid vague messages like "fix bug" or "update code";
      instead use "fix: prevent signal saturation in noise simulation" or "feat: add support for multi-detector frame merging".

3. **Follow Conventional Commits format**

    - All commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) standard.
    - Format: `<type>(<scope>): <subject>`
    - Allowed types:
        - build: Changes that affect the build system or external dependencies
        - ci: Changes to our CI configuration files and scripts
        - docs: Documentation only changes
        - feat: A new feature
        - fix: A bug fix
        - perf: A code change that improves performance
        - refactor: A code change that neither fixes a bug nor adds a feature
        - style: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc.)
        - test: Adding missing tests or correcting existing tests
    - Example:

        ```text
        feat(signal): add BBH waveform generation for aligned-spin systems

        This commit introduces support for aligned-spin binary black hole
        waveforms using PyCBC, enabling more realistic simulations.
        ```

    - Pull request titles are validated by the semantic PR action (see
      `.github/workflows/semantic_pull_request.yml`).

<!-- prettier-ignore-end -->

### Examples

✅ **Good commits:**

```text
feat(parser): add support for YAML configuration files
fix(logger): prevent crash on empty log messages
docs(readme): update installation instructions for clarity
refactor(utils): simplify data processing pipeline
```

❌ **Bad commits:**

```text
fixed stuff
wip: many changes
update code
more fixes (no type/scope)
```

## 💡 Tips

- Be kind and constructive in your communication.
- Keep PRs focused and atomic—smaller changes are easier to review.
- Document new features and update existing docs if needed.
- Tag your PR with relevant labels if you can.

## Licensing

By contributing, you agree that your contributions will be licensed under the
project’s MIT License.

---

Thanks again for being part of the `python-gitea` community!

---
