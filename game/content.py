"""Parser for Athas content files (data/*.txt).

The format is plain text and hand-writable:

    # comment
    [entry_key]
    name: Display Name
    damage: 5
    tags: fire, ice
    boost: damage=1.5, mana_cost=0.9
    desc: A longer line that
        continues on the next line.

Rules:
  * ``[key]`` starts an entry; keys are lower-cased and unique per file.
  * ``field: value`` sets a field; leading/trailing whitespace is stripped.
  * Full-line ``#`` comments and blank lines are ignored.
  * An indented line continues the previous field's value.

Everything stays strings; use the as_* helpers to convert.
"""
import os
import re

_RANGE_RE = re.compile(r"^([^=]+)=\s*(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)$")
_STAT_RE = re.compile(r"^([^=,]+)=\s*(-?\d+(?:\.\d+)?)$")


def parse_file(path):
    """Parse one content file -> {entry_key: {field: value}}.

    Missing files return {} so optional content simply doesn't exist.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return {}

    entries = {}
    current = None
    last_field = None
    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            key = stripped[1:-1].strip().lower()
            current = entries.setdefault(key, {})
            last_field = None
            continue
        if ":" in line:
            field, _, value = line.partition(":")
            field = field.strip().lower()
            if current is not None and field:
                current[field] = value.strip()
                last_field = field
            continue
        if current is not None and last_field and stripped:
            # continuation line: append to the previous field
            current[last_field] = (current[last_field] + " " + stripped).strip()
    return entries


def parse_named(directory, filename):
    """Parse ``directory/filename`` with a friendly error if it's malformed."""
    path = os.path.join(directory, filename)
    if not os.path.isfile(path):
        return {}
    return parse_file(path)


# ------------------------------------------------------------ converters

def as_str(entry, field, default=""):
    value = entry.get(field)
    return value if value not in (None, "") else default


def as_int(entry, field, default=0):
    try:
        return int(float(entry.get(field, default)))
    except (TypeError, ValueError):
        return default


def as_float(entry, field, default=0.0):
    try:
        return float(entry.get(field, default))
    except (TypeError, ValueError):
        return default


def as_bool(entry, field, default=False):
    value = str(entry.get(field, "")).strip().lower()
    if value in ("yes", "true", "1", "on"):
        return True
    if value in ("no", "false", "0", "off", ""):
        return False
    return default


def as_list(entry, field, default=()):
    value = entry.get(field, "")
    if not value:
        return tuple(default)
    return tuple(item.strip() for item in value.split(",") if item.strip())


def as_stat_map(entry, field, default=None):
    """``damage=1.5, mana_cost=0.9`` -> {"damage": 1.5, "mana_cost": 0.9}"""
    value = entry.get(field, "")
    if not value:
        return dict(default or {})
    result = {}
    for chunk in value.split(","):
        match = _STAT_RE.match(chunk.strip())
        if match:
            result[match.group(1).strip().lower()] = float(match.group(2))
    return result or dict(default or {})


def as_range_map(entry, field, default=None):
    """'ATK=10-40, Crit Rate%=0.01-0.03' -> {'ATK': (10, 40), ...}"""
    value = entry.get(field, "")
    if not value:
        return dict(default or {})
    result = {}
    for chunk in value.split(","):
        match = _RANGE_RE.match(chunk.strip())
        if match:
            result[match.group(1).strip()] = (float(match.group(2)), float(match.group(3)))
    return result or dict(default or {})


def as_color(entry, field, default=(200, 200, 200)):
    """``255,120,60`` -> (255, 120, 60)"""
    value = entry.get(field, "")
    try:
        parts = [int(p) for p in value.split(",")]
        if len(parts) == 3:
            return tuple(parts)
    except (ValueError, AttributeError):
        pass
    return default
