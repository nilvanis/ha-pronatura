# ProNatura for Home Assistant

![ProNatura](logo.png)

> [!NOTE]
> English version [below](#english-version).

Integracja do Home Assistant pobierająca harmonogram wywozu śmieci dla wybranego adresu obsługiwanego przez ProNatura (Bydgoszcz).\
\
🔗 [Strona harmonogramu wywozu odpadów](https://www.pronatura.bydgoszcz.pl/home/uslugi-odbioru-odpadow)

## Funkcje integracji

- Sensor per frakcja z datą najbliższego wywozu śmieci
- Możliwość konfiguracji wielu adresów (harmonogramów)
- Konfiguracja przeez Config Flow (Home Assistant UI)
- Wybór ulicy i adresu spośród listy pobieranej z ProNatura
- Implementacja napraw integracji, cache'owanie danych, możliwość pobierania danych diagnostycznych

## Instalacja

### Przez HACS (zalecana)

Kliknij przycisk poniżej, aby otworzyć stronę integracji w HACS.

[![Otwórz stronę integracji ProNatura w HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nilvanis&repository=ha-pronatura&category=integration)

Możesz też ręcznie wyszukać integrację w HACS wpisując w wyszukiwarkę `ProNatura` lub `ProNatura Garbage Collection Schedules`.

### Ręcznie

1. Pobierz najnowszy release.
2. Skopiuj katalog `custom_components/pronatura` do folderu `custom_components` w Home Assistant.\
   Jeżeli nie ma katalogu `custom_components`, załóż go ręcznie.
   Do skopiowania plików przydatny może okazać się dodatek **Samba Share**.
3. Zrestartuj Home Assistant.

## Konfiguracja

1. W Home Asisstant przejdź do **Ustawienia → Urządzenia oraz Usługi → Dodaj integrację** i znadź **ProNatura**.
2. Wybierz ulicę, a następnie budynek.
3. Potwierdź podsumowanie. Sensory zostały stworzone.

## Dane sensorów

Każda frakcja odpadów znajdująca się w harmonogramie generuje dedyowany sensor, którego wartością jest data (`date`)
najbliższego dnia wywozu danej frakcji. W przypadu, gdy w harmonogramie nie ma już kolejnej daty, sensor pozostawi poprzednią.
W niektórych przypadkach harmonogram dla danej frakcji istnieje, ale ejst pusty - w takim wypadku sensor est tworzony,
ale jego status będzie `unknown`.

Atrybuty:

- `full_address` – Ulica + numer (lub nazwa) budynku
- `fraction_name` – nazwa frakcji (dostarczona przez API ProNatura)
- `area` - obszar wywozu śmieci wg ProNatura
- `building_type` - typ budynku (np. `MIESZKALNA`, `NIEMIESZKALNA`)
- `address_name` - opcjonalne, dostepne gdy ProNatura dostarcza własną, dodatkową nazwę dla nieruchomości
- `days_until_collection` - ilość dni do najbliższej daty wywozu frakcji
- `last_collection` - data ostatniego odbioru frakcji wg harmonogramu

Dane z API odświeżane są raz na dobę, aby niepotrzebnie nie obciążać serwisu.\
Wyątek stanowi: restart Home Assistant, rekonfiguracja integracji oraz komunikat Napraw.

W przypadku, gdy adres nie jest już dostępny w ProNatura API, wyświetlony zostaje komunikat Napraw proszący o wybranie nowego adresu.

## English version

Home Assistant integration that downloads the garbage collection schedule for a selected address serviced by ProNatura (Bydgoszcz).\
\
🔗 [Garbage Collection Schedule Website](https://www.pronatura.bydgoszcz.pl/home/uslugi-odbioru-odpadow)

## Features

- One sensor per waste fraction with the date of the next pickup.
- Possibility to configure multiple addresses (schedules).
- Configuration handled via Config Flow (Home Assistant UI).
- Street and address are chosen from a list downloaded from ProNatura.
- Repairs support, cached data responses, and diagnostics download.

## Installation

### HACS (recommended)

Click the following button to open the integration directly on the HACS integration page.

[![Open ProNatura integration page in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nilvanis&repository=ha-pronatura&category=integration)

You can also find the integration manually in HACS by searching for `ProNatura` or `ProNatura Garbage Collection Schedules`.

### Manual copy

1. Download the latest release.
2. Copy `custom_components/pronatura` into your Home Assistant `custom_components` directory. If the directory does not exist, create it first. The **Samba Share** add-on can help with the file copy.
3. Restart Home Assistant.

## Configuration

1. In Home Assistant go to **Settings → Devices & Services → Add integration** and look for **ProNatura**.
2. Select the street and then the building from the lists provided by the integration.
3. Confirm the summary. Sensors for the configured address will be created automatically.

## Sensor data

Every waste fraction found in the schedule creates a dedicated `date` sensor whose value is the date of the next collection. When there are no further dates in the schedule the sensor keeps showing the previous one. If a fraction exists but its schedule is empty, the sensor is still created but its state remains `unknown`.\

Attributes:

- `full_address` – street and building (or property name).
- `fraction_name` – name of the fraction returned by the ProNatura API.
- `area` – collection zone defined by ProNatura.
- `building_type` – building type (for example `MIESZKALNA`, `NIEMIESZKALNA`).
- `address_name` – optional additional name for the property provided by ProNatura.
- `days_until_collection` - number of days until next collection
- `last_collection` - date of the last collection according to schedule

Data from the API is refreshed once per day so the service is not overloaded.
Exceptions: Home Assistant restart, integration reconfiguration, and Repairs notifications.

If a previously configured address disappears from ProNatura, Home Assistant shows a Repair notification that lets you reopen the ProNatura config flow and pick the address again.
