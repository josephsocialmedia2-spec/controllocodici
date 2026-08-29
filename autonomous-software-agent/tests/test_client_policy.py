from pathlib import Path

from asa.orchestrator import Orchestrator
from asa.repair import RepairBackend, RepairProposal


class DecisionBackend(RepairBackend):
    def propose(self, prompt, project_root, failures, iteration):
        assert "CLIENT REQUEST" in prompt
        assert "Mantieni il pulsante verde" in prompt
        return RepairProposal({}, "Scelta con impatto funzionale", True, ["A", "B"], 0.9)


def test_client_requirements_are_injected_into_repair_prompt(tmp_path: Path):
    o = Orchestrator(tmp_path)
    prompt = o._client_prompt({
        "goal": "Correggi senza perdere funzioni",
        "instructions": ["Mantieni il pulsante verde"],
        "acceptance": ["Tutti i test devono passare"],
    })
    assert "Correggi senza perdere funzioni" in prompt
    assert "Mantieni il pulsante verde" in prompt
    assert "Tutti i test devono passare" in prompt


def test_material_choice_is_explicit():
    proposal = RepairProposal({}, "Scelta con impatto funzionale", True, ["A", "B"], 0.9)
    assert proposal.requires_user_choice is True
    assert proposal.choices == ["A", "B"]
