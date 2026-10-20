import os
import csv
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Any, Optional

def read_ods(filepath: str) -> List[List[Any]]:
    """Lit un fichier OpenDocument Spreadsheet (.ods) en pur Python sans dépendance externe."""
    with zipfile.ZipFile(filepath, 'r') as z:
        with z.open('content.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()

    ns = {
        'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
        'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
        'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0'
    }

    tables = root.findall('.//table:table', ns)
    if not tables:
        return []

    # Première feuille
    table = tables[0]
    rows = []
    for row_node in table.findall('table:table-row', ns):
        row_repeat = int(row_node.attrib.get(f"{{{ns['table']}}}number-rows-repeated", "1"))
        # Si répétition énorme (ex. lignes vides jusqu'à la fin de la feuille OpenOffice), on tronque
        if row_repeat > 50:
            continue

        cells = []
        for cell_node in row_node.findall('table:table-cell', ns):
            cell_repeat = int(cell_node.attrib.get(f"{{{ns['table']}}}number-columns-repeated", "1"))
            if cell_repeat > 50:
                continue

            text_nodes = cell_node.findall('.//text:p', ns)
            val = " ".join("".join(p.itertext()).strip() for p in text_nodes if "".join(p.itertext()).strip())
            val = val if val else None

            for _ in range(cell_repeat):
                cells.append(val)

        # Retirer les cellules vides de fin de ligne
        while cells and cells[-1] is None:
            cells.pop()

        for _ in range(row_repeat):
            rows.append(list(cells))

    # Retirer les lignes vides de fin de tableau
    while rows and not any(c is not None for c in rows[-1]):
        rows.pop()

    return rows

def read_xlsx(filepath: str) -> List[List[Any]]:
    """Lit un fichier Excel (.xlsx, .xlsm)."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(filepath, data_only=True)
        ws = wb.active
        rows = []
        for r in ws.iter_rows(values_only=True):
            row_list = list(r)
            while row_list and row_list[-1] is None:
                row_list.pop()
            rows.append(row_list)
        while rows and not any(c is not None for c in rows[-1]):
            rows.pop()
        return rows
    except ImportError:
        # Secours pur Python sans openpyxl via XML direct
        return read_xlsx_xml(filepath)

def read_xlsx_xml(filepath: str) -> List[List[Any]]:
    """Secours pur Python pour XLSX si openpyxl est indisponible."""
    with zipfile.ZipFile(filepath, 'r') as z:
        # Lire sharedStrings
        shared_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            with z.open('xl/sharedStrings.xml') as f:
                root = ET.parse(f).getroot()
                ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                for si in root.findall('.//main:si', ns):
                    shared_strings.append("".join(si.itertext()))

        # Lire la feuille 1
        sheet_path = 'xl/worksheets/sheet1.xml'
        with z.open(sheet_path) as f:
            root = ET.parse(f).getroot()
            ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            rows = []
            for row in root.findall('.//main:row', ns):
                current_row = []
                for c in row.findall('main:c', ns):
                    t = c.attrib.get('t')
                    v_node = c.find('main:v', ns)
                    val = v_node.text if v_node is not None else None
                    if t == 's' and val is not None:
                        idx = int(val)
                        val = shared_strings[idx] if idx < len(shared_strings) else val
                    current_row.append(val)
                rows.append(current_row)
            return rows

def read_csv_file(filepath: str) -> List[List[Any]]:
    """Lit un fichier CSV en détectant l'encodage et le séparateur."""
    with open(filepath, 'rb') as f:
        raw_bytes = f.read(100000)

    encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1']
    content = ""
    for enc in encodings:
        try:
            content = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if not content:
        content = raw_bytes.decode('utf-8', errors='replace')

    # Détection séparateur
    delims = [';', ',', '\t']
    counts = {d: content.count(d) for d in delims}
    best_delim = max(counts, key=counts.get)
    if counts[best_delim] == 0:
        best_delim = ','

    with open(filepath, 'r', encoding=enc, errors='replace') as f:
        reader = csv.reader(f, delimiter=best_delim)
        rows = [list(r) for r in reader]

    return rows

def read_any_file(filepath: str) -> List[List[Any]]:
    """Détecte le format par signature de fichier et le lit."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Fichier introuvable: {filepath}")

    with open(filepath, 'rb') as f:
        magic = f.read(8)

    # ZIP signature (ODS ou XLSX)
    if magic.startswith(b'PK\x03\x04'):
        with zipfile.ZipFile(filepath, 'r') as z:
            names = z.namelist()
            if 'mimetype' in names:
                mimetype = z.read('mimetype').decode('utf-8', errors='ignore')
                if 'opendocument.spreadsheet' in mimetype:
                    return read_ods(filepath)
            if any(n.startswith('xl/') for n in names):
                return read_xlsx(filepath)

    # Par extension
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ('.xlsx', '.xlsm', '.xls'):
        return read_xlsx(filepath)
    if ext == '.ods':
        return read_ods(filepath)
    return read_csv_file(filepath)
