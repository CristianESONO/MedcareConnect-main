"""Extrait le JS configurateur ambulance de search.html vers un partial template."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "templates/healthcare/search.html").read_text(encoding="utf-8")
start = src.index("// Ambulance trajet configurator")
end = src.index("// Initial setup", start)
block = src[start:end]
lines = [line[4:] if line.startswith("    ") else line for line in block.splitlines()]
js = "\n".join(lines)
out = ROOT / "templates/healthcare/partials/ambulance_trajet_config_script.html"
content = (
    "{% comment %}Configurateur ambulance — partagé recherche drawer + fiche annuaire.{% endcomment %}\n"
    "<script>\n(function() {\n"
    + js
    + "\n  initAmbulanceTrajetConfig();\n"
    + "{% if auto_init_org_id %}\n"
    + "  initTrajetConfig('{{ auto_init_org_id }}');\n"
    + "{% endif %}\n"
    + "})();\n</script>\n"
)
out.write_text(content, encoding="utf-8")
print("Wrote", out, "bytes", len(content))
