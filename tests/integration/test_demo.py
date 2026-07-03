"""Integration smoke test for the flagship demo."""

from plainbench import demo


def test_demo_runs_quickly_on_fast_profiles(monkeypatch):
    """The demo pipeline works end to end (restricted to fast profiles)."""
    monkeypatch.setattr(demo, "PROFILES", ["in_process", "same_host"])
    monkeypatch.setattr(demo, "USERS", 5)
    monkeypatch.setattr(demo, "ORDERS_PER_USER", 5)

    matrix = demo.run(runs=1, warmup=0)

    assert matrix.profiles == ["in_process", "same_host"]
    winners = matrix.winners()
    assert set(winners) == {"in_process", "same_host"}
    for result in matrix.results.values():
        assert set(result.candidates) == {"n_plus_one", "batched", "cached"}
    # The table renders without error and mentions every design
    table = matrix.table()
    for name in ["n_plus_one", "batched", "cached"]:
        assert name in table
