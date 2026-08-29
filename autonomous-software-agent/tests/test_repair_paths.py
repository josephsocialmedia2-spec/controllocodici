from pathlib import Path
import tempfile
import pytest

from asa.repair import RepairProposal, RepairError, apply_proposal


def test_rejects_path_escape():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        with pytest.raises(RepairError):
            apply_proposal(root, RepairProposal({"../escape.txt": "x"}))
