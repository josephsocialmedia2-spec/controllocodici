from pathlib import Path

from asa.orchestrator import Orchestrator
from asa.repair import RepairBackend, RepairProposal


class DecisionBackend(RepairBackend):
    def propose(self, prompt, project_root, failures, iteration):
        assert "CLIENT REQUEST" in prompt
        return RepairProposal({}, "Scelta con impatto funzionale", True, ["A", "B"], 0.9)


class RequestedChangeBackend(RepairBackend):
    def propose(self, prompt, project_root, failures, iteration):
        assert "CAMBIA" in prompt
        return RepairProposal({"main.py": "print('CAMBIA')\n"}, "Applica richiesta cliente", False, [], 0.99)


class NoChangeAuditBackend(RepairBackend):
    def __init__(self):
        self.calls = 0

    def propose(self, prompt, project_root, failures, iteration):
        self.calls += 1
        assert "green syntax/build baseline does NOT prove" in prompt
        return RepairProposal({}, "Compila, ma non esiste una verifica funzionale affidabile", False, [], 0.99)


class AddFunctionalTestBackend(RepairBackend):
    def propose(self, prompt, project_root, failures, iteration):
        return RepairProposal(
            {"tests/test_main.py": "def test_value():\n    assert 2 + 2 == 4\n"},
            "Aggiunge una verifica funzionale automatica",
            False,
            [],
            0.99,
        )


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


def test_green_baseline_is_not_accepted_before_client_change(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("print('ORIGINALE')\n", encoding="utf-8")
    job = {
        "name": "requested-change",
        "source": {"type": "local", "path": str(project)},
        "goal": "CAMBIA il comportamento richiesto dal cliente",
        "test_commands": ["python -m py_compile main.py"],
        "run_command": "python main.py",
        "verify_run": True,
    }
    report = Orchestrator(tmp_path / "home", RequestedChangeBackend(), "master", max_iterations=2).process(job)
    assert report["status"] == "OK"
    assert report["request_satisfied"] is True
    assert report["functional_verified"] is True
    assert report["best_revision"] == 1
    assert (Path(report["best"]) / "main.py").read_text(encoding="utf-8") == "print('CAMBIA')\n"


def test_compile_only_green_baseline_is_not_ok(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("print('compila soltanto')\n", encoding="utf-8")
    backend = NoChangeAuditBackend()
    report = Orchestrator(tmp_path / "home", backend, "master", max_iterations=2).process({
        "name": "compile-only",
        "source": {"type": "local", "path": str(project)},
    })
    assert backend.calls == 1
    assert report["status"] == "PARZIALE"
    assert report["functional_verified"] is False
    assert report["validation_level"] == "syntax_only"
    assert report["audit_evaluated"] is True
    assert report["best_score"] == 70


def test_autonomous_audit_can_create_functional_verification(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("VALUE = 4\n", encoding="utf-8")
    report = Orchestrator(tmp_path / "home", AddFunctionalTestBackend(), "master", max_iterations=2).process({
        "name": "audit-adds-tests",
        "source": {"type": "local", "path": str(project)},
    })
    assert report["status"] == "OK"
    assert report["functional_verified"] is True
    assert report["validation_level"] == "functional"
    assert report["best_revision"] == 1
    assert (Path(report["best"]) / "tests" / "test_main.py").exists()
