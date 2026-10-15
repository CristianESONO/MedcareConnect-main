@echo off
chcp 65001 > nul
title MedCare Connect — Import & Réconciliation
cls
echo ===============================================================================
echo   MEDCARE CONNECT — PROGRAMME D'IMPORT ET RÉCONCILIATION DE CATALOGUES
echo ===============================================================================
echo.
echo   Choisissez votre mode de lancement :
echo.
echo   [1] Ouvrir l'application graphique directement dans votre navigateur (Recommandé)
echo   [2] Démarrer le serveur local autonome Python (http://127.0.0.1:5050)
echo   [3] Tester la réconciliation en ligne de commande (catalogue de démo)
echo   [4] Quitter
echo.
echo ===============================================================================
set /p choix="Votre choix (1-4, defaut: 1) : "

if "%choix%"=="" set choix=1
if "%choix%"=="1" goto OPEN_HTML
if "%choix%"=="2" goto START_SERVER
if "%choix%"=="3" goto TEST_CLI
if "%choix%"=="4" goto QUIT

:OPEN_HTML
echo.
echo Ouverture de l'interface graphique dans votre navigateur par defaut...
start "" "%~dp0index.html"
goto END

:START_SERVER
echo.
echo Demarrage du serveur local Python...
cd /d "%~dp0"
python medcare_importer.py --serve
goto END

:TEST_CLI
echo.
echo Execution du test CLI sur le catalogue de demonstration...
cd /d "%~dp0"
python medcare_importer.py catalogue_test_bionissa_clinique.xlsx
echo.
echo Appuyez sur une touche pour continuer...
pause > nul
goto END

:END
exit /b 0

:QUIT
exit /b 0
