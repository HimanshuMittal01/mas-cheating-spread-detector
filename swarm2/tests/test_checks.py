from swarm2 import checks


def test_check_tasks_clean():
    assert checks.check_tasks() == []
