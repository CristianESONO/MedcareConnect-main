import os
import re

ref_dir = r"e:\projets\MedcareConnect-main\MedcareConnect-main\documents\referentiel"
for f in os.listdir(ref_dir):
    if f.endswith('.html'):
        p = os.path.join(ref_dir, f)
        with open(p, 'r', encoding='utf-8') as fp:
            txt = fp.read()
        m_title = re.search(r'<title>(.*?)</title>', txt)
        m_h1 = re.search(r'<h1>(.*?)</h1>', txt)
        m_kick = re.search(r'<p class=["\']kick["\']>(.*?)</p>', txt)
        has_data = 'var DATA' in txt
        data_count = len(re.findall(r'"acte_standardise"', txt))
        title = m_title.group(1) if m_title else "N/A"
        kick = m_kick.group(1) if m_kick else "N/A"
        print(f"{f}:")
        print(f"  Title: {title}")
        print(f"  Kick: {kick}")
        print(f"  Items in DATA: {data_count}")
