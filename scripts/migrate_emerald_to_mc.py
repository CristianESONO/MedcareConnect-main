#!/usr/bin/env python3
"""Remplace emerald/green Tailwind et #10b981 par classes/tokens charte mc-*."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"

# Ordre important : motifs les plus longs / spécifiques en premier
REPLACEMENTS: list[tuple[str, str]] = [
    ("#10b981", "var(--mc-accent)"),
    # Boutons action
    (
        "rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-emerald-700",
        "mc-btn-primary rounded-xl px-4 py-2.5 text-sm font-bold",
    ),
    (
        "inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 px-3 py-1.5 text-[11px] font-bold text-white hover:bg-emerald-600",
        "mc-btn-primary mc-btn-primary--sm inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[11px] font-bold",
    ),
    (
        "rounded-xl bg-emerald-500 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-600",
        "mc-btn-primary mc-btn-primary--sm rounded-xl px-3 py-2 text-xs font-bold",
    ),
    (
        "rounded-md bg-green-50 px-2 py-1 text-[11px] font-medium text-green-700 hover:bg-green-100",
        "mc-badge mc-badge--accent rounded-md px-2 py-1 text-[11px] font-medium hover:opacity-90",
    ),
    (
        "inline-flex items-center gap-1 rounded-full bg-emerald-500 px-2 py-0.5 text-[9px] font-bold text-white",
        "mc-badge mc-badge--accent-solid inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-bold",
    ),
    (
        "action-btn inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2.5 py-1 text-[10px] font-semibold text-emerald-800 hover:bg-emerald-100",
        "action-btn mc-badge mc-badge--accent inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-[10px] font-semibold hover:opacity-90",
    ),
    (
        "action-btn inline-flex items-center gap-1 rounded-md bg-emerald-100 px-2.5 py-1 text-[10px] font-semibold text-emerald-900 hover:bg-emerald-500 hover:text-white",
        "action-btn mc-btn-primary mc-btn-primary--xs inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-[10px] font-semibold",
    ),
    (
        "block rounded-xl border border-emerald-100 bg-emerald-50/50 px-3 py-2 text-[11px] font-semibold text-emerald-800 hover:border-emerald-200 hover:bg-emerald-50",
        "mc-card-accent block rounded-xl px-3 py-2 text-[11px] font-semibold mc-text-accent-dark hover:border-[var(--mc-accent)]",
    ),
    # Dégradés
    (
        "bg-gradient-to-br from-primary-700 via-primary-600 to-emerald-700",
        "mc-gradient-brand bg-gradient-to-br from-primary-700 via-primary-600 to-[var(--mc-accent-dark)]",
    ),
    ("to-emerald-700", "to-[var(--mc-accent-dark)]"),
    # Fond semi-transparent
    ("bg-emerald-50/50", "mc-bg-accent-light"),
    ("bg-emerald-50/40", "mc-bg-accent-light"),
    # Hover (retirer — géré par mc-btn-primary / mc-card-accent)
    (" hover:bg-emerald-700", ""),
    (" hover:bg-emerald-600", ""),
    (" hover:bg-emerald-500", ""),
    (" hover:bg-emerald-100", ""),
    (" hover:bg-green-100", ""),
    (" hover:border-emerald-200", ""),
    # Texte
    ("text-emerald-900", "mc-text-accent-dark"),
    ("text-emerald-800", "mc-text-accent-dark"),
    ("text-emerald-700", "mc-text-accent-dark"),
    ("text-emerald-600", "mc-text-accent"),
    ("text-emerald-500", "mc-text-accent"),
    ("text-emerald-400", "mc-text-accent"),
    ("text-emerald-300", "text-[var(--mc-cyan-bright)]"),
    ("text-green-900", "mc-text-accent-dark"),
    ("text-green-800", "mc-text-accent-dark"),
    ("text-green-700", "mc-text-accent-dark"),
    ("text-green-600", "mc-text-accent"),
    ("text-green-500", "mc-text-accent"),
    # Fond
    ("bg-emerald-100", "mc-bg-accent-light"),
    ("bg-emerald-50", "mc-bg-accent-light"),
    ("bg-green-100", "mc-bg-accent-light"),
    ("bg-green-50", "mc-bg-accent-light"),
    # Bordures
    ("border-emerald-200", "border-[var(--mc-border)]"),
    ("border-emerald-100", "border-[var(--mc-border)]"),
    ("border-emerald-300", "border-[var(--mc-accent)]"),
    ("border-green-200", "border-[var(--mc-border)]"),
    # Solides (barres, points)
    ("bg-emerald-600", "mc-bg-accent"),
    ("bg-emerald-500", "mc-bg-accent"),
    ("bg-green-500", "mc-bg-accent"),
    ("bg-green-400", "mc-bg-accent"),
    # JS classList
    ("'text-emerald-700'", "'mc-text-accent-dark'"),
    ('"text-emerald-700"', '"mc-text-accent-dark"'),
    ("'rounded-full bg-emerald-50 px-3 py-1 text-[11px] font-bold text-emerald-700'", "'mc-badge mc-badge--accent rounded-full px-3 py-1 text-[11px] font-bold'"),
    ("? '#10b981'", "? 'var(--mc-accent)'"),
    ("style=\"background:#10b981\"", "style=\"background:var(--mc-accent)\""),
]

# WhatsApp : ne pas toucher #25d366 ni classes explicites wa
WA_SKIP_PATTERNS = ("#25d366", "mc-wa-btn", "25D366", "25d366")


def migrate_content(text: str) -> tuple[str, int]:
    count = 0
    for old, new in REPLACEMENTS:
        if old in text:
            n = text.count(old)
            text = text.replace(old, new)
            count += n
    # Nettoyer espaces doubles dans class=""
    text = re.sub(r'class="([^"]*)"', lambda m: 'class="' + re.sub(r"\s+", " ", m.group(1)).strip() + '"', text)
    return text, count


def main() -> None:
    total_files = 0
    total_repl = 0
    for path in sorted(TEMPLATES.rglob("*")):
        if path.suffix not in (".html", ".js"):
            continue
        raw = path.read_text(encoding="utf-8")
        if not any(x in raw for x in ("emerald", "green-", "#10b981")):
            continue
        new, n = migrate_content(raw)
        if n:
            path.write_text(new, encoding="utf-8")
            print(f"{path.relative_to(ROOT)}: {n} remplacement(s)")
            total_files += 1
            total_repl += n
    print(f"\nTerminé : {total_repl} remplacements dans {total_files} fichier(s).")


if __name__ == "__main__":
    main()
