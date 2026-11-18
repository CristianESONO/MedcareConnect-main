import importlib.util
from pathlib import Path


_legacy_tests_path = Path(__file__).resolve().parent.parent / "tests.py"
_legacy_spec = importlib.util.spec_from_file_location(
    "dashboard._legacy_tests", _legacy_tests_path
)
_legacy_tests = importlib.util.module_from_spec(_legacy_spec)
_legacy_spec.loader.exec_module(_legacy_tests)

for _name in dir(_legacy_tests):
    if _name.endswith("Tests"):
        globals()[_name] = getattr(_legacy_tests, _name)
