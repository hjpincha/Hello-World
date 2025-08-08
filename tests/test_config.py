import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import POSITION_SIZE, TAKE_PROFIT, STOP_LOSS


def test_risk_parameters():
    assert 0 < POSITION_SIZE < 1
    assert TAKE_PROFIT > 0
    assert STOP_LOSS < 0
