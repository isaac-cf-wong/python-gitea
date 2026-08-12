"""Generate API reference pages automatically."""

from __future__ import annotations

from pathlib import Path

import mkdocs_gen_files

PACKAGE_NAME = "gitea"

src = Path(__file__).parent.parent / "src"

# Collect all importable modules. The key is the dotted module path; the value
# is the source file. Packages (directories with __init__.py) are kept in
# `packages` so they render as an index page.
modules: dict[tuple[str, ...], Path] = {}
packages: set[tuple[str, ...]] = set()
for path in sorted(src.rglob("*.py")):
    module_path = path.relative_to(src).with_suffix("")
    parts = tuple(module_path.parts)

    # Skip private modules, test files, and __main__.
    if parts[-1] == "__main__":
        continue

    if parts[-1] == "__init__":
        parts = parts[:-1]
        if not parts:
            continue
        packages.add(parts)

    if any(part.startswith("_") for part in parts):
        continue
    if parts[-1].startswith("test_"):
        continue

    modules[parts] = path

# Generate the reference index page.
with mkdocs_gen_files.open("reference/index.md", "w") as fd:
    fd.write("# API Reference\n\n")
    fd.write("Complete API documentation for the `gitea` package.\n\n")
    fd.write("## Modules\n\n")

    for parts in sorted(modules):
        name = ".".join(parts)
        if parts in packages:
            fd.write(f"- [`{name}`]({name.replace('.', '/')}/index.md)\n")
        else:
            fd.write(f"- [`{name}`]({name.replace('.', '/')}.md)\n")

# Generate a page per module/package, mirroring the module tree.
for parts in sorted(modules):
    indent = ".".join(parts)

    # Packages get an index.md; plain modules get <module>.md, mirroring the
    # layout used by gwmock's reference documentation.
    if parts in packages:
        doc_path = Path("reference", *parts, "index.md")
    else:
        doc_path = Path("reference", *parts).with_suffix(".md")

    with mkdocs_gen_files.open(doc_path, "w") as fd:
        fd.write(f"# `{indent}`\n\n")
        fd.write("::: " + indent + "\n")
        fd.write("    options:\n")
        fd.write("      docstring_style: google\n")
        fd.write("      show_source: true\n")
        fd.write("      show_root_heading: true\n")
        fd.write("      show_object_full_path: true\n")
        fd.write("      members_order: source\n")
        fd.write("      filters:\n")
        fd.write("        - '!^_'\n")

        # List direct child modules so users can navigate the tree.
        children = sorted(p for p in modules if len(p) == len(parts) + 1 and p[:-1] == parts)
        if children:
            fd.write("\n## Modules\n\n")
            for child in children:
                child_name = ".".join(child)
                leaf = child[len(parts) :][0]
                link = leaf + ("/index.md" if child in packages else ".md")
                fd.write(f"- [`{child_name}`]({link})\n")

    mkdocs_gen_files.set_edit_path(doc_path, modules[parts])
