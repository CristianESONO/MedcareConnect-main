"""
Patch _normalize_catalog_label dans views.py pour ignorer les emojis.
Les noms des ServiceMedical en BDD contiennent des emojis (ex: '🧬 Biologie médicale')
qui empêchent le match avec les clés de ACTES_ORDER.
"""
import io, re, sys

path = "healthcare/views.py"

with io.open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Chercher et remplacer la fonction
pattern = re.compile(
    r"def _normalize_catalog_label\(name: str\) -> str:\n"
    r"    if not name:\n"
    r"        return \"\"\n"
    r"    return \(\n"
    r"        name\.replace\([^\n]+\n"
    r"        \.replace\([^\n]+\n"
    r"        \.replace\([^\n]+\n"
    r"        \.lower\(\)\n"
    r"    \)",
    re.MULTILINE,
)

NEW_FUNC = '''def _normalize_catalog_label(name: str) -> str:
    if not name:
        return ""
    import unicodedata as _ud
    # Retirer les emojis/symboles Unicode (So, Sm, Sk, Sc, Cs, Co, Cn)
    # Ex: "\U0001f9ec Biologie medicale" -> "Biologie medicale"
    cleaned = "".join(
        c for c in name
        if _ud.category(c) not in ("So", "Sm", "Sk", "Sc", "Cs", "Co", "Cn")
    )
    return (
        cleaned.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace(" ", "")
        .lower()
        .strip()
    )'''

m = pattern.search(content)
if m:
    content = content[:m.start()] + NEW_FUNC + content[m.end():]
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: _normalize_catalog_label patched.")
else:
    print("PATTERN NOT FOUND - trying exact match")
    # Show what the function looks like
    idx = content.find("def _normalize_catalog_label")
    if idx >= 0:
        print("Found at index", idx)
        print(repr(content[idx:idx+300]))
    else:
        print("Function not found at all!")
    sys.exit(1)
