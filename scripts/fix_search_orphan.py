"""Supprime le JS ambulance dupliqué après le premier {% endblock %} dans search.html."""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "templates/healthcare/search.html"
text = path.read_text(encoding="utf-8")
marker = "{% endblock %}"
first = text.find(marker)
if first == -1:
    raise SystemExit("endblock not found")
end_first = first + len(marker)
rest = text[end_first:]
if rest.strip():
    path.write_text(text[:end_first] + "\n", encoding="utf-8")
    print("Removed", len(rest), "orphan chars")
else:
    print("No orphan content")
