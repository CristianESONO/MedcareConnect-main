import json

# Charge le fichier d'export
with open('full_export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Filtre les OrganismeDeSante
organismes = [item for item in data if item.get('model') == 'healthcare.organismedesante']

print(f"Total établissements : {len(organismes)}\n")

verified = []
not_verified = []

for org in organismes:
    name = org.get('fields', {}).get('name', 'N/A')
    is_verified = org.get('fields', {}).get('is_verified', False)
    
    if is_verified:
        verified.append(name)
    else:
        not_verified.append(name)

print(f"✓ VÉRIFIÉS ({len(verified)}):")
for name in sorted(verified):
    print(f"  ✓ {name}")

print(f"\n✗ NON VÉRIFIÉS ({len(not_verified)}):")
for name in sorted(not_verified):
    print(f"  ✗ {name}")
