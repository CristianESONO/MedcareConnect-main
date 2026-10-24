@echo off
chcp 65001 > nul
title MedCare Connect - Plateforme d'Onboarding
cls
echo ===============================================================================
echo   MEDCARE CONNECT - SUITE D'ONBOARDING ET RECONCILIATION DE CATALOGUES
echo ===============================================================================
echo.
echo   Choisissez l'application a lancer :
echo.
echo   [1] Lancer la Plateforme Unifiee MedCare Onboarding Suite (Recommande)
echo   [2] Ouvrir le portail d'accueil (index.html)
echo   [3] Executer la suite de tests du Manuel d'Architecture (test_onboarding.py)
echo   [4] Quitter
echo.
echo ===============================================================================
set /p choix="Votre choix (1-4, defaut: 1) : "

if "%choix%"=="" set choix=1
if "%choix%"=="1" goto OPEN_SUITE
if "%choix%"=="2" goto OPEN_INDEX
if "%choix%"=="3" goto TEST_CLI
if "%choix%"=="4" goto QUIT

:OPEN_SUITE
echo.
echo Ouverture de la Suite d'Onboarding MedCare dans votre navigateur...
start "" "%~dp0medcare_onboarding_suite.html"
goto END

:OPEN_INDEX
echo.
echo Ouverture de l'accueil MedCare dans votre navigateur...
start "" "%~dp0index.html"
goto END

:TEST_CLI
echo.
echo Execution de la suite de tests du Manuel d'Architecture...
cd /d "%~dp0"
python test_onboarding.py
echo.
echo Appuyez sur une touche pour continuer...
pause > nul
goto END

:END
exit /b 0

:QUIT
exit /b 0
