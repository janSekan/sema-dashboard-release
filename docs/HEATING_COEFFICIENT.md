# Koeficient posunu vykurovacej krivky

V Nastaveniach v karte Teplota je pre admina a superadmina pole **Koeficient posunu krivky**.
Predvolená hodnota je **1,0**, minimálna **0,1**, krok **0,1**. Používateľ pole nevidí;
samostatné GET/POST `/device-api/heating-main-temp/coefficient` vyžadujú administrátorskú
rolu aj povolený prístup. LAN ani HA token oprávnenie nenahrádzajú.

Pri uložení novej teploty platí: **posun krivky = (nová teplota − uložená teplota) × koeficient**.
Napríklad zmena z 22 na 23 °C pri koeficiente 2 posunie všetkých šesť bodov o +2 °C.
Platí aj pre teplotu uloženú bežným používateľom. Tlačidlá teploty zostávajú po 0,5 °C.

Čerpadlo kóduje teploty bodov po 0,5 °C. Vypočítaný posun sa preto zaokrúhli na tento
krok a zvyšok sa zachová do ďalšej zmeny. Napríklad pri koeficiente 0,1 nemusí prvá
zmena o 0,5 °C ešte fyzicky posunúť krivku; malé posuny sa postupne spočítajú.
Všetky body sa posúvajú o rovnakú hodnotu. Pri chybe čítania/zápisu čerpadla sa
lokálna referenčná teplota ani zvyšok neuložia. Úspešná HTTP odpoveď čerpadla
nie je nezávislé overenie skutočne aplikovaných parametrov.

**Uložiť koeficient** mení iba lokálne nastavenie, neposúva krivku a nemení referenčnú
teplotu. **Uložiť referenciu** tiež neposúva krivku. Obe akcie začnú nový výpočet bez
predchádzajúceho zlomkového zvyšku. Nové hodnoty sa uchovávajú v existujúcej SQLite
tabuľke app_settings (`heating_curve_shift_coefficient`, `heating_curve_shift_remainder`),
zostávajú po reštarte/update. Netreba migráciu schémy ani nové Python závislosti.

Výpočty a chybové stavy: `tests/test_heating_coefficient.py`, výhradne dočasná DB
a mock čerpadla. Živú zmenu teploty vykonáva používateľ až pri vlastnom testovaní.
