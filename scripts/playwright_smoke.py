#!/usr/bin/env python3
"""Tests navigateur (Playwright) — flux publics, zones protégées, connexion patient / prestataire."""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = os.environ.get("MEDCARE_BASE", "http://127.0.0.1:8765")
E2E_DB = Path(__file__).resolve().parent.parent / ".cache" / "e2e_playwright.sqlite3"


def _e2e_env():
    env = os.environ.copy()
    env["MEDCARE_TESTING"] = "1"
    env.setdefault("DEBUG", "True")
    return env


def _prepare_e2e_database(project_dir: Path) -> None:
    """Base SQLite jetable : migrate + comptes de test, sans toucher db.sqlite3."""
    if E2E_DB.exists():
        E2E_DB.unlink()
    E2E_DB.parent.mkdir(parents=True, exist_ok=True)
    env = _e2e_env()
    subprocess.run(
        [sys.executable, "manage.py", "migrate", "--noinput"],
        cwd=project_dir,
        env=env,
        check=True,
    )
    subprocess.run(
        [sys.executable, "manage.py", "seed_e2e_users"],
        cwd=project_dir,
        env=env,
        check=True,
    )


def _cleanup_e2e_database() -> None:
    if E2E_DB.exists():
        try:
            E2E_DB.unlink()
        except OSError:
            pass


def main():
    global BASE
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP: playwright non installé (pip install -r requirements-dev.txt && playwright install chromium)")
        return 0

    proc = None
    project_dir = Path(__file__).resolve().parent.parent
    if os.environ.get("MEDCARE_START_SERVER") == "1":
        _prepare_e2e_database(project_dir)
        env = _e2e_env()
        proc = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", "127.0.0.1:8765", "--noreload"],
            cwd=project_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)
        BASE = "http://127.0.0.1:8765"
    else:
        BASE = os.environ.get("MEDCARE_BASE", BASE)

    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(locale="fr-SN", viewport={"width": 1280, "height": 800})
            page = context.new_page()

            def check(name, fn):
                try:
                    fn()
                    print("OK ", name)
                except Exception as e:
                    errors.append(f"{name}: {e}")
                    print("FAIL", name, e)

            # ── Public ───────────────────────────────────────────────────────────
            check("accueil", lambda: page.goto(f"{BASE}/", wait_until="domcontentloaded"))
            check("recherche", lambda: page.goto(f"{BASE}/healthcare/search/", wait_until="domcontentloaded"))
            check("centres", lambda: page.goto(f"{BASE}/healthcare/centres/", wait_until="domcontentloaded"))
            check("parcours bundle", lambda: page.goto(f"{BASE}/healthcare/parcours/", wait_until="domcontentloaded"))
            check("panier (invité)", lambda: page.goto(f"{BASE}/cart/", wait_until="domcontentloaded"))
            check("api geocode", lambda: (
                page.goto(f"{BASE}/healthcare/api/geocode/?q=Dakar"),
                page.wait_for_load_state("networkidle"),
                assert_json_has_results(page),
            ))
            check("recherche proximité", lambda: page.goto(
                f"{BASE}/healthcare/search/?lat=14.7&lng=-17.5&proximity=1&radius_km=100"
            ) or True)

            # Zones réservées → page de connexion (redirection suivie par Playwright)
            check("messagerie anonyme → login", lambda: (
                _anon_context(page),
                page.goto(f"{BASE}/messaging/", wait_until="domcontentloaded"),
                assert_url_has_login(page),
            ))
            check("dashboard admin anonyme → login", lambda: (
                _anon_context(page),
                page.goto(f"{BASE}/dashboard/", wait_until="domcontentloaded"),
                assert_url_has_login(page),
            ))

            # Inscription (formulaire affiché)
            check("register", lambda: page.goto(f"{BASE}/inscription/") or True)
            check("prestataire fields visible", lambda: (
                page.select_option("#id_user_type", "prestataire"),
                page.wait_for_timeout(200),
                page.locator("#prestataire-fields").wait_for(state="visible"),
            ))

            # Login patient (compte seed E2E jetable)
            check("login patient", lambda: (
                _anon_context(page),
                page.goto(f"{BASE}/connexion/"),
                page.fill("#username", "testpatient"),
                page.fill("#password", "testpass123"),
                page.click('button[type="submit"]'),
                page.wait_for_load_state("networkidle"),
                assert_logged_in(page),
            ))

            check("profil patient", lambda: page.goto(f"{BASE}/users/profile/") or True)
            check("mon compte patient", lambda: page.goto(f"{BASE}/users/compte/") or True)
            check("préférences notifications patient", lambda: page.goto(f"{BASE}/notifications/preferences/") or True)

            _anon_context(page)
            prest_user = os.environ.get("MEDCARE_PREST_USER", "polyclinique_de_libe")
            prest_pass = os.environ.get("MEDCARE_PREST_PASS", "medcare2024")
            check("login prestataire", lambda: (
                page.goto(f"{BASE}/connexion/"),
                page.fill("#username", prest_user),
                page.fill("#password", prest_pass),
                page.click('button[type="submit"]'),
                page.wait_for_load_state("networkidle"),
            ))

            check("dashboard prestataire", lambda: page.goto(f"{BASE}/healthcare/prestataire/dashboard/") or True)
            check("liste actes prestataire", lambda: page.goto(f"{BASE}/healthcare/prestataire/actes/") or True)

            _anon_context(page)
            check("login superadmin", lambda: (
                page.goto(f"{BASE}/connexion/"),
                page.fill("#username", "qa_superadmin"),
                page.fill("#password", "Admin-E2E-123!"),
                page.click('button[type="submit"]'),
                page.wait_for_load_state("networkidle"),
            ))
            check("dashboard admin index", lambda: page.goto(
                f"{BASE}/dashboard/", wait_until="domcontentloaded"
            ) or True)
            check("admin liste organismes", lambda: page.goto(
                f"{BASE}/dashboard/organismes/", wait_until="domcontentloaded"
            ) or True)
            check("admin avis plateforme", lambda: page.goto(
                f"{BASE}/dashboard/reviews/", wait_until="domcontentloaded"
            ) or True)

            browser.close()

    finally:
        if proc:
            proc.terminate()
            proc.wait(timeout=5)
        if os.environ.get("MEDCARE_START_SERVER") == "1":
            _cleanup_e2e_database()

    if errors:
        print("\n--- Erreurs ---")
        for e in errors:
            print(e)
        return 1
    return 0


def _anon_context(page):
    """Repart sur une session invité (évite de traîner le cookie patient)."""
    page.context.clear_cookies()


def assert_json_has_results(page):
    txt = page.inner_text("body")
    if "results" not in txt:
        raise AssertionError("pas de JSON results")


def assert_logged_in(page):
    if not re.search(r"déconnexion|Déconnexion", page.content(), re.I):
        raise AssertionError("utilisateur non connecté")


def assert_url_has_login(page):
    url = (page.url or "").lower()
    if "connexion" not in url:
        raise AssertionError(f"attendu URL connexion, obtenu: {page.url!r}")


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    sys.exit(main())
