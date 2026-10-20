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
echo   [1] Portail d'accueil MedCare (Hub complet - Recommande)
echo   [2] Back-office Operateur MedCare (Dossiers, rapprochement, lots)
echo   [3] Assistant Chatbot WhatsApp Secretaire (Scenario V2)
echo   [4] Programme V1 Import direct (Outil historique de reconciliation)
echo   [5] Demarrer le serveur web local Python (http://127.0.0.1:5050)
echo   [6] Executer le test batch en ligne de commande (CLI)
echo   [7] Quitter
echo.
echo ===============================================================================
set /p choix="Votre choix (1-7, defaut: 1) : "

if "%choix%"=="" set choix=1
if "%choix%"=="1" goto OPEN_HUB
if "%choix%"=="2" goto OPEN_BO
if "%choix%"=="3" goto OPEN_CHAT
if "%choix%"=="4" goto OPEN_V1
if "%choix%"=="5" goto START_SERVER
if "%choix%"=="6" goto TEST_CLI
if "%choix%"=="7" goto QUIT

:OPEN_HUB
echo.
echo Ouverture du Portail MedCare dans votre navigateur...
start "" "%~dp0index.html"
goto END

:OPEN_BO
echo.
echo Ouverture du Back-office Operateur dans votre navigateur...
start "" "%~dp0medcare_onboarding.html"
goto END

:OPEN_CHAT
echo.
echo Ouverture de l'Assistant Chatbot dans votre navigateur...
start "" "%~dp0medcare_chat.html"
goto END

:OPEN_V1
echo.
echo Ouverture de l'outil d'import V1 dans votre navigateur...
start "" "%~dp0MedCare_Import_Reconciliation.html"
goto END

:START_SERVER
echo.
echo Demarrage du serveur local Python...
cd /d "%~dp0"
python medcare_importer.py --serve
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
