from asa.selftest import run_self_test


def test_end_to_end_repair_cycle():
    assert run_self_test() is True
