from valopoint.brackets import pick_event, resolve_teams


def test_pick_event_prefers_ongoing_international_then_region():
    ev = [{"event_id": "a", "region": "PAC", "start": "2026-07-16", "complete": False},
          {"event_id": "b", "region": "INTL", "start": "2026-09-24", "complete": False},
          {"event_id": "c", "region": "INTL", "start": "2026-06-06", "complete": True}]
    assert pick_event(ev)["event_id"] == "b"
    assert pick_event([ev[0], ev[2]])["event_id"] == "a"
    assert pick_event([{"event_id": "x", "region": "PAC", "start": "2025-07-01", "complete": True},
                       {"event_id": "y", "region": "PAC", "start": "2026-07-01", "complete": True}])["event_id"] == "y"


def test_resolve_teams_follows_winners_and_losers():
    br = {"matches": [{"id": "SF1", "a": "A", "b": "B"}, {"id": "SF2", "a": "C", "b": "D"},
                      {"id": "F", "a": "W:SF1", "b": "W:SF2"}, {"id": "3rd", "a": "L:SF1", "b": "L:SF2"}],
          "results": {"SF1": "B", "SF2": "C"}}
    t = resolve_teams(br)
    assert t["F"] == ("B", "C") and t["3rd"] == ("A", "D")


def test_results_due_after_start_until_result():
    from datetime import datetime, timedelta, timezone
    from valopoint.brackets import results_due
    now = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
    t = lambda h: (now - timedelta(hours=h)).isoformat()
    br = {"matches": [{"id": "a", "time": t(2)}, {"id": "b", "time": t(0.5)}, {"id": "c", "time": t(3)},
                      {"id": "d", "time": t(72)}, {"id": "e", "time": t(-2)}], "results": {"c": "X"}}
    assert results_due(br, now) == ["a"]
