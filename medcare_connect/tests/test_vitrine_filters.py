from medcare_connect.views import is_excluded_pillar_service


class DummyService:
    def __init__(self, name, slug=""):
        self.name = name
        self.slug = slug


def test_excluded_pillar_service_blocks_hematology_and_hemostase():
    assert is_excluded_pillar_service(DummyService("Hématologie", "hematologie")) is True
    assert is_excluded_pillar_service(DummyService("Hémostase / Coagulation", "hemostase-coagulation")) is True
    assert is_excluded_pillar_service(DummyService("Hématologie clinique", "hematologie-clinique")) is True


def test_excluded_pillar_service_keeps_main_pillars():
    assert is_excluded_pillar_service(DummyService("Biologie médicale", "biologie-medicale")) is False
    assert is_excluded_pillar_service(DummyService("Imagerie médicale", "imagerie-medicale")) is False
    assert is_excluded_pillar_service(DummyService("Soins spécialisés", "soins-specialises")) is False
