import pytest

from corpus import BUGS
from nudge import exercises as exlib
from nudge.diagnose import diagnose
from nudge.runner import run

EXS = exlib.load_all()


@pytest.mark.parametrize("eid,why,src,accept", BUGS, ids=[f"{b[0]}:{b[1]}" for b in BUGS])
def test_classic_mistake_gets_a_fitting_top_hint(eid, why, src, accept):
    ex = EXS[eid]
    res = run(src, ex, limit=0.5)
    assert not res.passed, "the mistake should fail the tests (otherwise the tests are too weak)"
    top = diagnose(src, ex, res)[0]
    assert top.code in accept, f"top hint was {top.code!r}, expected one of {sorted(accept)}"
