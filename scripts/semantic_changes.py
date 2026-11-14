"""Offline semantic Gate4 trigger classification for dependency configuration."""

import re
import tomllib
from collections import defaultdict, deque
from pathlib import PurePosixPath

from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

_STATIC_TOOLS = {
    "black", "codespell", "coverage", "isort", "markdown_toc_creator", "mypy", "pylint", "pymarkdown", "pyright",
    "pytest", "ruff", "tomlsort", "ty", "typos",
}
_PROSE_FIELDS = {
    "authors", "classifiers", "description", "keywords", "license",
    "maintainers", "readme", "urls",
}
_ROOT_CONFIGS = {"pyproject.toml", "uv.lock", "requirements-runtime.in", "requirements-runtime.lock"}
_PACKAGE_CONFIG = re.compile(r"packages/[^/]+/(?:pyproject\.toml|uv\.lock)\Z")
_EXTRA_MARKER = re.compile(r"\bextra\s*==\s*(['\"])([^'\"]+)\1", re.IGNORECASE)


def _requirements(values):
    if not isinstance(values, list):
        raise ValueError("invalid requirement list")
    result = []
    for value in values:
        req = Requirement(value)
        result.append((canonicalize_name(req.name), tuple(sorted(canonicalize_name(x) for x in req.extras)),
                       str(req.specifier), req.url, str(req.marker) if req.marker else ""))
    return tuple(sorted(result))


def _manifest(text):
    data = tomllib.loads(text)
    project = data.get("project", {})
    if not isinstance(project, dict):
        raise ValueError("invalid project table")
    result = dict(data)
    project = dict(project)
    for key in _PROSE_FIELDS:
        project.pop(key, None)
    if "name" in project:
        project["name"] = canonicalize_name(project["name"])
    if "dependencies" in project:
        project["dependencies"] = _requirements(project["dependencies"])
    optional = project.get("optional-dependencies", {})
    if not isinstance(optional, dict):
        raise ValueError("invalid optional dependencies")
    normalized_optional = {}
    for name, values in optional.items():
        normalized_name = canonicalize_name(name)
        if normalized_name != "dev":
            normalized_optional[normalized_name] = _requirements(values)
    if "optional-dependencies" in project:
        project["optional-dependencies"] = normalized_optional
    result["project"] = project
    groups = result.get("dependency-groups")
    if groups is not None:
        if not isinstance(groups, dict):
            raise ValueError("invalid dependency groups")
        result["dependency-groups"] = {k: v for k, v in groups.items() if canonicalize_name(k) != "dev"}
    tools = result.get("tool", {})
    if not isinstance(tools, dict):
        raise ValueError("invalid tool table")
    tools = dict(tools)
    for name in list(tools):
        if name.lower() in _STATIC_TOOLS:
            if not isinstance(tools[name], dict):
                raise ValueError("invalid static tool table")
            tools.pop(name)
    result["tool"] = tools
    return result


def _logical_requirements(text):
    lines, pending, continued = [], "", False
    for raw in text.splitlines():
        line = re.sub(r"(?<!\S)#.*$", "", raw).strip()
        if not line:
            continue
        pending = (pending + " " + line).strip() if pending else line
        continued = pending.endswith("\\")
        if continued:
            pending = pending[:-1].rstrip()
        else:
            lines.append(re.sub(r"\s+", " ", pending))
            pending = ""
    if continued:
        raise ValueError("unfinished requirement continuation")
    return tuple(lines)


def _freeze(value):
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _active_edge(edge, extras):
    marker = edge.get("marker", "")
    if not isinstance(marker, str):
        raise ValueError("invalid dependency marker")
    if marker:
        Marker(marker)  # Validate without selecting away other supported environments.
    if "extra" not in marker.lower() or re.search(r"\bor\b", marker, re.IGNORECASE):
        return True
    names = [canonicalize_name(match[1]) for match in _EXTRA_MARKER.findall(marker)]
    return not names or bool(set(names) & extras)


def _edge_extras(edge):
    values = edge.get("extra", [])
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise TypeError("invalid locked extras")
    return {canonicalize_name(value) for value in values}


def _lock_signature(lock_text, manifest_text):
    lock, project = tomllib.loads(lock_text), tomllib.loads(manifest_text)
    name = canonicalize_name(project["project"]["name"])
    project_optional = {
        canonicalize_name(key): values
        for key, values in project.get("project", {}).get("optional-dependencies", {}).items()
    }
    extras = set(project_optional) - {"dev"}
    packages = lock.get("package")
    if not isinstance(packages, list):
        raise ValueError("invalid lock package list")
    nodes, by_name = {}, defaultdict(list)
    for package in packages:
        if not isinstance(package, dict) or not isinstance(package.get("name"), str):
            raise ValueError("invalid lock package")
        package_name = canonicalize_name(package["name"])
        source = package.get("source", {})
        if not isinstance(source, dict):
            raise ValueError("invalid package source")
        key = (package_name, package.get("version"), _freeze(source))
        if key in nodes:
            raise ValueError("duplicate lock package")
        for field in ("dependencies", "optional-dependencies", "dev-dependencies"):
            if field in package and not isinstance(package[field], (list, dict)):
                raise ValueError("invalid lock dependencies")
        deps = package.get("dependencies", [])
        if not isinstance(deps, list) or any(not isinstance(dep, dict) or not isinstance(dep.get("name"), str) for dep in deps):
            raise ValueError("invalid lock dependency edge")
        optional = package.get("optional-dependencies", {})
        if not isinstance(optional, dict) or any(not isinstance(items, list) or any(not isinstance(dep, dict) or not isinstance(dep.get("name"), str) for dep in items) for items in optional.values()):
            raise ValueError("invalid lock optional dependencies")
        nodes[key] = package
        by_name[package_name].append(key)
    roots = [key for key, package in nodes.items() if key[0] == name and
             (package.get("source", {}).get("editable") == "." or package.get("source", {}).get("directory") == ".")]
    if not roots:
        roots = by_name.get(name, [])
    if len(roots) != 1:
        raise ValueError("unambiguous lock root required")
    root = roots[0]
    root_package = nodes[root]
    root_optional = {canonicalize_name(key): values for key, values in root_package.get("optional-dependencies", {}).items()}
    for extra in extras:
        if project_optional[extra] and extra not in root_optional:
            raise ValueError("missing locked project extra")

    def targets(edge):
        name = canonicalize_name(edge["name"])
        candidates = by_name.get(name, [])
        if "version" in edge:
            candidates = [key for key in candidates if key[1] == edge["version"]]
        if "source" in edge:
            source = _freeze(edge["source"])
            candidates = [key for key in candidates if key[2] == source]
        if not candidates:
            raise ValueError("unresolved lock dependency")
        return candidates

    active, seen, queue = defaultdict(set), set(), deque([(root, extras)])
    while queue:
        key, requested = queue.popleft()
        state = (key, frozenset(requested))
        if state in seen:
            continue
        seen.add(state)
        active[key].update(requested)
        package = nodes[key]
        for edge in package.get("dependencies", []):
            if _active_edge(edge, requested):
                next_extras = _edge_extras(edge)
                queue.extend((target, next_extras) for target in targets(edge))
        optional = {canonicalize_name(extra): edges for extra, edges in package.get("optional-dependencies", {}).items()}
        for extra in requested:
            for edge in optional.get(extra, []):
                if _active_edge(edge, requested):
                    next_extras = _edge_extras(edge)
                    queue.extend((target, next_extras) for target in targets(edge))

    snapshots = []
    for key, requested in active.items():
        package = dict(nodes[key])
        package.pop("dev-dependencies", None)
        if "metadata" in package:
            metadata = dict(package["metadata"])
            groups = metadata.get("requires-dev", {})
            metadata["requires-dev"] = {group: edges for group, edges in groups.items() if canonicalize_name(group) != "dev"}
            metadata["requires-dist"] = [edge for edge in metadata.get("requires-dist", []) if _active_edge(edge, requested)]
            if "provides-extras" in metadata:
                metadata["provides-extras"] = [extra for extra in metadata["provides-extras"] if canonicalize_name(extra) != "dev"]
            package["metadata"] = metadata
        package["dependencies"] = sorted((_freeze(edge) for edge in package.get("dependencies", [])
                                          if _active_edge(edge, requested)), key=repr)
        optional = {canonicalize_name(extra): edges for extra, edges in package.get("optional-dependencies", {}).items()}
        package["optional-dependencies"] = {
            extra: sorted((_freeze(edge) for edge in optional[extra]), key=repr)
            for extra in requested if extra in optional
        }
        snapshots.append((key, _freeze(package)))
    globals_ = {key: lock.get(key) for key in ("version", "revision", "requires-python", "resolution-markers")}
    return _freeze(globals_), tuple(sorted(snapshots, key=repr))


def configuration_changed(ctx, path):
    """Return whether a supported configuration diff can affect runtime/model behavior.

    Unknown, missing, or malformed inputs fail closed. This function is entirely offline.
    """
    path = str(PurePosixPath(path))
    if path not in _ROOT_CONFIGS and not _PACKAGE_CONFIG.fullmatch(path):
        return False
    try:
        old, new = ctx.read(path, ref=ctx.base), ctx.read(path)
        if not isinstance(old, str) or not isinstance(new, str):
            return True
        if path.endswith(("requirements-runtime.in", "requirements-runtime.lock")):
            return _logical_requirements(old) != _logical_requirements(new)
        if path.endswith("pyproject.toml"):
            return _manifest(old) != _manifest(new)
        project_path = str(PurePosixPath(path).with_name("pyproject.toml"))
        old_project, new_project = ctx.read(project_path, ref=ctx.base), ctx.read(project_path)
        return _lock_signature(old, old_project) != _lock_signature(new, new_project)
    except Exception:
        return True
