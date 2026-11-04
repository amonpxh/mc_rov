"""Pure business quality calculations; source authorization belongs to the adapter."""

from datetime import date, datetime, timedelta


def _date_or_none(value):
    if value is not None and (not isinstance(value, date) or isinstance(value, datetime)):
        raise ValueError("Business quality metrics require civil dates, not instants")
    return value


def _identity(value):
    if value is None or isinstance(value, bool):
        raise ValueError("Missing business evidence identity")
    try:
        hash(value)
    except TypeError as exc:
        raise ValueError("Unhashable business evidence identity") from exc
    return value


def _is_integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _cohort_members(visits, as_of, window_days):
    members = {}
    for row in visits:
        key = _identity(row.get("visit_id"))
        if key in members:
            raise ValueError("Duplicate original visit")
        delivered = _date_or_none(row.get("delivered_on"))
        covered_from = _date_or_none(row.get("coverage_from"))
        covered_until = _date_or_none(row.get("coverage_until"))
        status = "coverage_unknown"
        if delivered is not None and delivered <= as_of:
            try:
                window_end = delivered + timedelta(days=window_days)
            except OverflowError as exc:
                raise ValueError("Return window exceeds supported dates") from exc
            if as_of < window_end:
                status = "following"
            elif (
                covered_from is not None
                and covered_until is not None
                and covered_from <= delivered
                and covered_until >= window_end
            ):
                status = "mature"
        members[key] = {"status": status, "delivered_on": delivered}
    return members


def _return_evidence(return_events, members, as_of):
    """Validate identities before aggregating so a join cannot invent extra returns."""
    seen = {}
    for event in return_events:
        event_id = _identity(event.get("event_id"))
        if event_id in seen:
            if event != seen[event_id]:
                raise ValueError("Conflicting copies of a return event")
            continue
        seen[event_id] = event
        key = _identity(event.get("visit_id"))
        if key not in members:
            raise ValueError("Return event is outside the original visit population")
        relation = event.get("relation")
        if relation not in ("confirmed", "pending", "unrelated"):
            raise ValueError("Unknown technical return relationship")
        returned = _date_or_none(event.get("returned_on"))
        if returned is not None and returned > as_of:
            continue
        member = members[key]
        delivered = member["delivered_on"]
        if returned is not None and delivered is not None and returned < delivered:
            raise ValueError("A linked return precedes the original delivery")
        yield {"visit_id": key, "returned_on": returned, "relation": relation, **member}


def _record_return(result, groups, event, window_days):
    returned, delivered = event["returned_on"], event["delivered_on"]
    relation = event["relation"]
    result["observed_returns"] += 1
    counter = {
        "confirmed": "observed_related_returns",
        "pending": "observed_pending_returns",
        "unrelated": "observed_unrelated_returns",
    }[relation]
    result[counter] += 1
    if returned is None:
        result["unknown_return_dates"] += 1
        result["undated_returns_by_relation"][relation] += 1
        if event["relation"] != "unrelated" and event["status"] == "mature":
            groups["uncertain"].add(event["visit_id"])
        return
    if delivered is None or not 0 <= (returned - delivered).days <= window_days:
        return
    target = {
        ("mature", "confirmed"): "affected_mature",
        ("mature", "pending"): "pending_relation_mature",
        ("following", "confirmed"): "recent_affected",
        ("following", "pending"): "recent_pending",
    }.get((event["status"], event["relation"]))
    if target:
        groups[target].add(event["visit_id"])


def related_return_metrics(visits, return_events, *, as_of, window_days=180):
    """Count affected original visits once, keeping immature and unknown evidence visible.

    Inputs are eligible visits and explicit technical return links, already filtered
    and known at the cutoff supplied by the caller. Descriptive counts preserve
    undated events; those events cannot enter the dated cohort numerator. Dates
    represent closed civil days, not fabricated physical times.
    Coverage describes available own records; this is not a fleet reliability claim.
    """
    if _date_or_none(as_of) is None:
        raise ValueError("A closed reporting date is required")
    if not _is_integer(window_days) or window_days <= 0:
        raise ValueError("Return window must be a positive integer number of days")
    members = _cohort_members(visits, as_of, window_days)
    result = {
        "window_days": window_days,
        "eligible": len(members),
        "mature": 0,
        "following": 0,
        "coverage_unknown": 0,
        "unknown_return_dates": 0,
        "observed_returns": 0,
        "observed_related_returns": 0,
        "observed_pending_returns": 0,
        "observed_unrelated_returns": 0,
        "undated_returns_by_relation": {"confirmed": 0, "pending": 0, "unrelated": 0},
        "value": None,
        "is_minimum": False,
    }
    groups = {
        key: set()
        for key in (
            "affected_mature",
            "pending_relation_mature",
            "recent_affected",
            "recent_pending",
            "uncertain",
        )
    }
    for member in members.values():
        result[member["status"]] += 1
    for event in _return_evidence(return_events, members, as_of):
        _record_return(result, groups, event, window_days)
    for key, affected in groups.items():
        if key != "uncertain":
            result[key] = len(affected)
    result["is_minimum"] = bool(groups["pending_relation_mature"] or groups["uncertain"])
    if result["mature"]:
        result["value"] = 100 * result["affected_mature"] / result["mature"]
    return result


def _adjudicate_valid_attempt(row):
    verdict = row.get("verdict")
    if verdict not in (None, "passed", "failed", "pending"):
        raise ValueError("Unknown formal attempt verdict")
    if verdict == "failed" or any(
        row.get(key) is True
        for key in ("required_failure", "correction_required", "retest_required")
    ):
        return "failed"
    if verdict == "pending":
        return "pending"
    if (
        verdict == "passed"
        and row.get("required_passed") is True
        and row.get("correction_required") is False
        and row.get("retest_required") is False
    ):
        return "passed"
    return "unknown"


def first_pass_status(attempts):
    """Adjudicate the first formal attempt without letting later success replace it.

    All rows belong to one episode. An invalidation flag is evidence supplied by
    a future authorized adapter, never permission to invalidate through this function.
    """
    indexed = {}
    for row in attempts:
        ordinal = row.get("ordinal")
        if not _is_integer(ordinal) or ordinal <= 0 or ordinal in indexed:
            raise ValueError("Formal attempts require unique positive ordinals")
        for key in (
            "required_passed",
            "required_failure",
            "correction_required",
            "retest_required",
        ):
            value = row.get(key)
            if value is not None and not isinstance(value, bool):
                raise ValueError("Formal attempt evidence must be boolean or unknown")
        indexed[ordinal] = row
    for ordinal in sorted(indexed):
        row = indexed[ordinal]
        validity = row.get("validity", "unknown")
        if validity not in ("valid", "invalid", "unknown"):
            raise ValueError("Unknown formal attempt validity")
        # A known real failure cannot be removed from the denominator by invalidation.
        if row.get("required_failure") is True:
            return "failed"
        if validity == "invalid":
            reason = row.get("invalid_reason")
            if (
                row.get("invalidation_confirmed") is not True
                or not isinstance(reason, str)
                or not reason.strip()
            ):
                return "unknown"
            continue
        if validity == "unknown":
            return "unknown"
        return _adjudicate_valid_attempt(row)
    return "invalid_only" if indexed else "unknown"


def release_status(*, tests_passed, documentation_complete, blocking_nc_count):
    """Describe readiness from three independent requirements; never dispatch a unit."""
    for value in (tests_passed, documentation_complete):
        if value is not None and not isinstance(value, bool):
            raise ValueError("Release requirements must be known booleans or unknown")
    if blocking_nc_count is not None and (
        not _is_integer(blocking_nc_count) or blocking_nc_count < 0
    ):
        raise ValueError("Blocking nonconformity count must be a nonnegative integer")
    if (
        tests_passed is False
        or documentation_complete is False
        or (blocking_nc_count is not None and blocking_nc_count > 0)
    ):
        return "blocked"
    if tests_passed is None or documentation_complete is None or blocking_nc_count is None:
        return "unknown"
    return "ready"
