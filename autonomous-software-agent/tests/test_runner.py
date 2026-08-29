from asa.runner import command_is_safe


def test_blocks_destructive_commands():
    assert not command_is_safe("shutdown /s /t 0")
    assert not command_is_safe("reg delete HKCU\\Software\\X /f")
    assert command_is_safe("python -m pytest -q")
