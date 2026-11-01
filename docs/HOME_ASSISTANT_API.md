# Lokálne read-only API pre Home Assistant

Stav 1. 11. 2026: implementované a lokálne testované v zdrojoch, **nenasadené**.
Read-only HA prototyp v samostatnom projekte sema-home-assistant má klienta,
formulár, koordinátor a entity, zatiaľ je overený iba proti mock dátam.
Prvý cieľ HA: Container/Core 2026.9.4. Nevytvárať produkčný release bez testing kroku.

## Zapnutie a identita

Administrátor/superadmin otvorí Informácie o zariadení → Home Assistant.
Vytvorenie tokenu zároveň zapne API; nový token okamžite odvolá starý.
Token sa ukáže iba v odpovedi pri vytvorení, UI ho neukladá do browser storage.
Tlačidlo Skopírovať token používa Clipboard API, pre lokálne HTTP má záložné
kopírovanie označeného poľa. Ak prehliadač oboje odmietne, pole ostane označené
na ručné skopírovanie; UI nehlási falošný úspech. Skrytie/odvolanie stav kopírovania zmaže.
Vypnutie odstráni hash. Správa používa existujúce dashboardové admin prihlásenie
alebo portálovú admin proxy; pri LAN locku použi portál/Tailscale existujúcim
postupom, LAN_ACCESS kvôli HA nezapínaj.

Správa: GET `/device-api/integrations/home-assistant` (enabled, device_uid, scope),
POST a DELETE `/device-api/integrations/home-assistant/token`.
Tieto volania nie sú oprávnením HA tokenu. Administrátorské oprávnenia sa nemenia.

Predvolené úložisko je `~/.config/sema/ha-api.json` používateľa backend služby,
prípadne absolútna cesta cez `SEMA_HA_STORE_PATH`. Súbor má mód 0600, obsahuje
náhodné UUID fyzickej jednotky, scope read a iba SHA-256 hash náhodného 256-bit
tokenu. Zápisy pri inicializácii/rotácii/odvolaní sú zamknuté a atomické.
GET neprepisuje súbor ani telemetrickú DB. UID prežije reset DB aj zmenu IP/DEVICE_ID;
poškodená identita sa automaticky nenahrádza. Súbor zálohuj súkromne; strata
znamená novú identitu a opätovné párovanie. Nesmie byť v Gite ani v továrenskom image.
Pri príprave nového image odstráň tento súbor aj susedný `.lock` z obrazu ešte
pred jeho klonovaním; na už spárovanom zariadení ich pri update zachovaj.

## Kontrakt v1

GET `/device-api/v1/info` a `/device-api/v1/state` vždy vyžadujú
`Authorization: Bearer <HA_TOKEN>`, aj cez LAN/Tailscale, LAN_ACCESS=true a portál.
Vypnuté/neplatné/odvolané poverenie → 401 s WWW-Authenticate: Bearer.
HA token má prefix `sema_ha_`; mimo týchto dvoch ciest ho middleware odmietne
403 vrátane provisioning, účtov, konfigurácie a staršieho API.
POST/PUT/PATCH/DELETE na read endpointoch → 405. Odpovede majú Cache-Control: no-store.
HTTP je iba lokálny prototyp pre dôveryhodnú LAN; token nie je pri prenose šifrovaný.
TLS/párovanie a limity požiadaviek zostávajú pred verejným vydaním otvorené.

Info obsahuje api_version=1, device_uid, device_id/name, manufacturer/model,
firmware_version z versions.json (null ak neznáma), capabilities, polling 30 s
a max_age_seconds=60. Capabilities sú aktuálne polia dekódované backendom,
nie záruka, že konkrétne čerpadlo vždy poskytne všetky hodnoty.

State: api_version, device_uid, generated_at, observed_at, pump_available,
temperatures, power_percent, states, errors. Zdroj je výlučne zamknutá kópia
collector.last_observed; nikdy collector.previous ani nové čítanie XML.
Časy sú UTC; generated_at nikdy neomladzuje observed_at. HA musí sám odmietnuť
snapshot starší ako 60 s, aj keď pump_available v historickom snapshote ostal true.

| API temperatures | snapshot values | XML zdroj |
| --- | --- | --- |
| outdoor_temp, indoor_temp, water_temp, heat_temp | ot, it, wt, ht | status |
| equitherm_temp, exchanger_temp, e_temp, f_temp, g_temp | eqt, ext, et, ft, gt | temperatures |

power_percent je values.pr zo status, nie W. States sú heating, dhw, defrost,
fault z aktuálneho state; heating je odhad backendu, nie potvrdenie relé.
Neznáme/neplatné hodnoty sú null, 0/false zostávajú platné.

- Bez snapshotu: observed_at=null, pump_available=null, všetky hodnoty null.
- Zlyhanie status XML: pump_available=false, všetky hodnoty čerpadla null;
  observed_at je čas posledného dokončeného pokusu, nie posledného úspechu.
- Status úspešný, temperatures zlyhali: pump_available=true, použiteľné sú len
  aktuálne status polia. Ostatné teploty null. Control XML tieto entity neblokuje.
- Errors obsahuje len general_fault pri aktuálnom známom fault=true; žiadne raw XML.

## Automatické objavenie

Po zapnutí HA API sa oznamuje služba `_sema._tcp.local.`. Inštancia je
`SEMA <device_uid>._sema._tcp.local.`, server `sema-<UUID bez pomlčiek>.local.`.
TXT obsahuje iba device_uid (UUID), api_version (`1`) a scheme (`http`/`https`).
Neobsahuje token/hash, zákaznícke meno, pumpové heslá ani konfiguráciu.
IP a port sú štandardné DNS-SD polia. API zostáva vždy chránené tokenom.

Publisher beží v lifespan backendu, prebúdza sa pri zmene tokenu a každých 30 s
kontroluje adresy. Rotácia tokenu nezmení identitu ani nevyvolá nové oznamovanie;
vypnutie/odvolanie službu stiahne. Pri zmene IP sa oznam obnoví. Sieťové chyby
neblokujú ručné API; objavovanie po chybe skúša neskôr.

Predvolená zákaznícka LAN je `wlan0`; pumpový Ethernet a Tailscale sa automaticky
neoznamujú. IPv4 adresy sa filtrujú, loopback/link-local/multicast/VPN sa nepoužívajú.
Nastavenia prostredia (príklad v backend/.env.example):

| Premenná | Predvolené |
| --- | --- |
| SEMA_HA_DISCOVERY_INTERFACES | wlan0; povolené názvy LAN rozhraní, oddelené čiarkou |
| SEMA_HA_DISCOVERY_PORT | 80 (nginx); pre priamy dev backend nastaviť 8000 |
| SEMA_HA_DISCOVERY_SCHEME | http; https len so skutočným TLS endpointom |

HA s nainštalovanou integráciou SEMA a zapnutým Zeroconf ponúkne nájdenú jednotku
a vyžiada iba token. Potom overí autentifikované info/state a zhodu UID s oznamom.
mDNS nie je dôkaz identity servera. Existujúci uložený token sa na základe mDNS
nikam neposiela a existujúca adresa sa automaticky neprepisuje; zmena IP sa rieši
cez Reconfigure. Ručné pridanie ostáva zálohou pri neprechodnom multicast/Docker sieti.

### Závislosti pri testing release

Pridané sú `zeroconf==0.151.1` a `ifaddr==0.2.0` do requirements.txt.
Pred autorizovaným prvým testing nasadením treba tieto závislosti nainštalovať
do `/home/jan/sema/.venv` a overiť port/interface/nginx na sema-001.
Bežný updater nové balíky neinštaluje. Bez nich discovery zapíše statickú chybu,
ale ručné HA API ostáva použiteľné. Inštalácia do lokálneho backend/.venv nie je
inštalácia na zariadenie. Nový image nesmie obsahovať cudzí HA store/UID/token.

## Overovanie

`backend/.venv/bin/python -m unittest discover -s tests -v` používa dočasné DB,
identitu a mock snapshoty, bez lifespan spúšťajúceho zberač a bez živého čerpadla.
Nové testy overujú HTTP/ASGI kontrakt, oddelenie poverení, LAN lock, rotáciu,
odvolanie, zachovanie identity pri výmene DB, partial/offline/stale aj nulové hodnoty.
Testy discovery používajú reálne ServiceInfo záznamy s mock socketmi/rozhraniami,
overujú enable/rotation/revoke, zmeny IP, chýbajúcu LAN a shutdown.
`npm run build` vo frontend overí zostavenie UI. Lokálny Chromium test s fiktívnymi
API overil kopírovanie cez Clipboard API, HTTP fallback, odmietnutie kopírovania,
hide/revoke a neprítomnosť HA tokenu v storage. HA webUI a skutočný LAN multicast
ani sema-001 sa týmto netestovali; nasadenie vyžaduje autorizovaný testing krok.
