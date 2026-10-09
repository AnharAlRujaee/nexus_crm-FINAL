"""Pure filtering helpers shared by the data pages (no Qt imports)."""


def _words(text) -> str:
    return " ".join(str(text).casefold().split())


def name_matches(query: str, *names) -> bool:
    """True when ``query`` is the start of a name or surname.

    'as' matches 'asiye turan' and 'ahmet as', but not 'mehmet kirmizi'.
    An empty query matches everything.
    """
    q = _words(query)
    if not q:
        return True
    for name in names:
        if name and (" " + q) in (" " + _words(name)):
            return True
    return False


def duplicate_flags(rows, name_idx: int, email_idx: int):
    """Find records registered more than once (same name AND same e-mail).

    Returns two lists aligned with ``rows``:
      is_duplicate - the record belongs to a group of 2+ identical registrations
      is_first     - the first occurrence of its registration (what stays when
                     duplicates are filtered out)
    """
    def key(row):
        name = row[name_idx] if name_idx >= 0 else ""
        email = row[email_idx] if email_idx >= 0 else ""
        return _words(name or ""), _words(email or "")

    keys = [key(r) for r in rows]
    counts = {}
    for k in keys:
        counts[k] = counts.get(k, 0) + 1

    seen, is_duplicate, is_first = set(), [], []
    for k in keys:
        is_duplicate.append(counts[k] > 1)
        is_first.append(k not in seen)
        seen.add(k)
    return is_duplicate, is_first


def _norm_option(text) -> str:
    return _words(text or "").rstrip(". ")


def same_option(option: str, value) -> bool:
    """Does a recommendation cell match a chosen category?

    Tolerant of a trailing full stop and of the shorter wording used in a few
    rows ('...straight to ITPH' vs '...straight to ITPH within the VIT project.').
    """
    a, b = _norm_option(option), _norm_option(value)
    if not a or not b:
        return False
    return a == b or a.startswith(b) or b.startswith(a)
