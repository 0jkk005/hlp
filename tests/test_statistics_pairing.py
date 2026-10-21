import pandas as pd
import pytest
from experiments.run_statistical_experiments import _paired_values


def test_comparisons_pair_by_replicate_not_row_position():
    df = pd.DataFrame([
        {"method": "HLP (Original)", "replicate": 2, "score": 0.8},
        {"method": "TA-HLP (Proposed)", "replicate": 1, "score": 0.4},
        {"method": "HLP (Original)", "replicate": 1, "score": 0.3},
        {"method": "TA-HLP (Proposed)", "replicate": 2, "score": 0.9},
    ])
    a, b = _paired_values(df, "score")
    assert list(b - a) == pytest.approx([0.1, 0.1])


def test_comparisons_reject_ambiguous_or_unpaired_cells():
    df = pd.DataFrame([
        {"method": "HLP (Original)", "replicate": 1, "score": 0.3},
        {"method": "TA-HLP (Proposed)", "replicate": 2, "score": 0.9},
    ])
    with pytest.raises(ValueError, match="Unpaired"):
        _paired_values(df, "score")
    with pytest.raises(ValueError, match="Duplicate"):
        _paired_values(pd.concat([df, df.iloc[:1]]), "score")
