# Development ProNatura

## Uruchomienie HA

1. Uruchom Docker i otwórz repozytorium w VS Code z rozszerzeniem **Dev Containers**.
2. Wybierz **Dev Containers: Reopen in Container** i poczekaj na instalację zależności.
3. W **Run and Debug** wybierz **Home Assistant: ProNatura** i naciśnij **F5**.
   Start z terminala: `bash scripts/develop.sh`.
4. Otwórz <http://localhost:8123> lub adres wskazany w panelu **Ports**. Instalacja
   zależności i dodawanie integracji wymagają internetu.
5. Utwórz konto i dodaj **ProNatura** przez **Ustawienia → Urządzenia oraz usługi →
   Dodaj integrację**. Wybór ulicy i budynku korzysta z rzeczywistego API ProNatura.

Kod w `custom_components/pronatura/` jest podłączony do HA dowiązaniem. Tam ustawiaj
breakpointy. Po zmianach w Pythonie zatrzymaj HA (`Shift+F5` lub `Ctrl+C`) i uruchom
ponownie. Restart z UI również wymaga ponownego uruchomienia procesu.

Lokalne konto, konfiguracja i baza danych pozostają w ignorowanym przez Git `config/`.
[Szablon konfiguracji](configuration.yaml) jest kopiowany tylko przy pierwszym setupie;
zawiera logowanie debug dla ProNatura. Logi znajdziesz w `config/home-assistant.log`.
Kontener trzyma `.venv` w wolumenie Dockera, oddzielonym od hostowej `.venv`. Jeśli
VS Code wybrał inny interpreter, ustaw `${workspaceFolder}/.venv/bin/python` przez
**Python: Select Interpreter**.

## Setup i zależności

Devcontainer i CI korzystają z tego samego `bash scripts/setup.sh` oraz plików
[requirements_test.txt](../requirements_test.txt) i
[requirements_dev.txt](../requirements_dev.txt). Wersja bazowa to Python 3.14
(co najmniej 3.14.2) i HA 2026.10.4. Setup tworzy `.venv` i instaluje zależności;
integracja działa ze źródeł repo.

Przy przejściu z Pythona 3.13 wybierz **Dev Containers: Rebuild Container**.
Kontener utworzy osobny wolumen `python314-venv`, aby zainstalować pakiety dla nowego
Pythona. Konto, konfiguracja i baza HA w katalogu `config/` pozostają na miejscu.

Zależności deweloperskie obejmują też pakiety importowane przez panel usług HA
i kreator pierwszego uruchomienia oraz `isal`, który przyspiesza kompresję HTTP
i usuwa ostrzeżenie `aiohttp_fast_zlib` o używaniu standardowego `zlib`. Sama instalacja `homeassistant` i narzędzi
testowych nie wystarcza do korzystania z całego panelu. Kontener zawiera również
bibliotekę `libturbojpeg0`, wymaganą przy ładowaniu komponentu kamer, oraz program
`ffmpeg`, używany przez domyślną integrację syntezy mowy dodawaną podczas onboardingu.

Po zmianie zależności uruchom `bash scripts/setup.sh` lub przebuduj devcontainer.
Poza kontenerem potrzebny jest Python co najmniej 3.14.2, program `ffmpeg` i biblioteka TurboJPEG
(na Debianie 12: `sudo apt-get install ffmpeg libturbojpeg0`). Następnie uruchom:

```bash
bash scripts/setup.sh
```

## Testy i kontrola kodu

W terminalu kontenera lub lokalnie uruchom:

```bash
bash scripts/run_checks.sh
```

Skrypt używa repozytoryjnej `.venv` i sprawdza Ruff, formatowanie oraz testy jednostkowe.
Same testy uruchomisz przez `.venv/bin/python -m pytest tests`, panel **Testing** albo
**Pytest: unit tests** w debuggerze (bez coverage, żeby działały breakpointy).
Domyślnie testy nie łączą się z API. Testy rzeczywistego API wymagają jawnego uruchomienia:

```bash
.venv/bin/python -m pytest -m integration tests/integration
```

Hassfest uruchamiaj osobno na hoście z Dockerem: `bash scripts/run_hassfest.sh`.

## Zmiana wersji HA

W `requirements_test.txt` zmień razem wersje `homeassistant`,
`pytest-homeassistant-custom-component` oraz wersję w adresie `package_constraints.txt`.
Następnie przebuduj devcontainer. Gdy HA wymaga nowszego Pythona, zmień też obraz
w [Dockerfile](Dockerfile), wersję w CI i nazwę wolumenu `.venv`
w [devcontainer.json](devcontainer.json), aby utworzyć nowe środowisko.
