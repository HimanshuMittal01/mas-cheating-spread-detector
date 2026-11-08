import os
import pytest

pytestmark = [pytest.mark.daytona,
              pytest.mark.skipif(os.environ.get("SANDBOX") != "daytona", reason="needs SANDBOX=daytona")]


def test_isolation_check_passes():
    from swarm2.checks import check_isolation
    assert check_isolation() == []
