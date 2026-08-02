from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from f1.session import CallSession


class SessionTests(unittest.TestCase):
    def test_session_writes_all_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            session = CallSession("Mario Rossi", "+39 333 0000000", "Susa", "01_primo_contatto.txt", base_dir=Path(temporary))
            session.add_turn("JOSEPH", "Buongiorno.")
            session.add_turn("CLIENTE", "Non sono interessato.")
            session.add_suggestion("Le invio una presentazione.", "NON_INTERESSATO")
            folder = session.finish("Da richiamare", "Tra sette giorni")
            self.assertTrue((folder / "sessione.json").exists())
            self.assertTrue((folder / "trascrizione.txt").exists())
            self.assertTrue((folder / "riepilogo.txt").exists())
            payload = json.loads((folder / "sessione.json").read_text(encoding="utf-8"))
            self.assertEqual(len(payload["turns"]), 2)


if __name__ == "__main__":
    unittest.main()
