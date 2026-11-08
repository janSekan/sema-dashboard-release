# Servisné akcie zariadení

Implementované vo vývoji 3. 11. 2026. **Portál zatiaľ iba lokálne; API na sema-001 nasadené do testing podľa záznamu nižšie.**

## Používanie

V detaile zariadenia je pre admina/superadmina záložka **Servis**. Ponúka reštart dashboardu, reboot Raspberry Pi a aktualizáciu. Pred odoslaním zobrazí potvrdenie s ID zariadenia a vysvetlením dopadu. Pri aktualizácii ukazuje aktuálny kanál aj presnú servisnú verziu. Kanál sa požiadavkou nemení. Offline, nekompatibilné a nenainštalované jednotky nemožno takto ovládať.

Počas reštartu je dočasná nedostupnosť očakávaná. UI overuje stav približne každých 5 sekúnd, bez prekrývajúcich sa pollov. Posledných desať požiadaviek zobrazuje akciu, používateľa, čas a výsledok. Zatvorením záložky sa už prijatá akcia nezruší; stav sa znovu načíta pri návrate. Pri stratenej odpovedi sa akcia automaticky neopakuje.

## Protokol a oprávnenia

Portál: GET/POST `/api/admin/devices/{public_device_id}/maintenance`. POST vyžaduje session admin/superadmin, JSON s UUID a akciou a hlavičku `X-SEMA-Confirm` zhodnú s ID zariadenia; cudzie Origin odmieta. Zariadenie vyberá server podľa DB, nikdy podľa URL dodanej klientom. Bežný používateľ je odmietnutý aj na backende.

Jednotka: GET `/device-api/maintenance` (capabilities/verzia/kanál), POST `/device-api/maintenance/jobs` a GET `/device-api/maintenance/jobs/{uuid}`. Vždy vyžaduje platný `X-SEMA-Proxy-Token`, proxy rolu admin/superadmin a proxy identitu. Samotný LAN/Tailscale prístup, lokálne JWT ani HA token nestačia. Žiadne tajomstvá sa nevracajú do prehliadača.

Povolené iba tri pevné akcie:

| Akcia | Systémový príkaz jednotky |
| --- | --- |
| restart_dashboard | sudo -n /usr/bin/systemctl restart --no-block sema.service |
| reboot | sudo -n /usr/bin/systemctl reboot --no-block |
| update | sudo -n /usr/bin/systemctl start --no-block sema-update.service |

Bez shell interpolácie, ľubovoľných príkazov alebo zmeny aktualizačného kanála. Existujúce bezheslové sudo pre systemctl musí byť funkčné. Nepovoľovať nové všeobecné sudo ako riešenie chyby. Zariadenie odmieta ďalšiu servisnú akciu pri aktívnom jobe, počas bežiacej aktualizačnej služby a pri intervale kratšom ako 60 sekúnd od predchádzajúcej požiadavky.

## Trvalý stav a výsledok

Portálová schéma **8** pridáva `device_maintenance_jobs` a index; cudzie kľúče na zariadenie a aktéra. Vytvorenie požiadavky a audit `DEVICE_MAINTENANCE_REQUEST` je jedna transakcia. Zmeny stavov sa zapisujú spolu s auditom `DEVICE_MAINTENANCE_STATUS`. Chyba uloženia pred odoslaním zablokuje vykonanie. Časy sú UTC epoch sekundy.

Jednotka ukladá joby do `~/.config/sema/maintenance.db` (0600), mimo aktualizovaného checkoutu. UUID je idempotentné; opakované rovnaké ID nevyvolá ďalší príkaz. Nárok na vykonanie sa uloží ešte pred systémovým príkazom. Po páde sa nerozbehnutý/nejasný job znovu nevykonáva. Zámok SQLite serializuje prijímanie požiadaviek.

Reboot je potvrdený zmenou boot ID, reštart dashboardu zmenou identity procesu/bootu po odoslaní. Update vyžaduje novú inštanciu sema-update.service so success výsledkom na rovnakom boote; starý úspech služby nestačí. Počas behu sa ukazuje running/waiting; po 10 minútach bez potvrdenia jednotka vráti unknown, portál po 11 minútach bez overenia tiež. Nepotvrdené vykonanie nie je automaticky označené za úspech ani za bezpečne odmietnutú požiadavku. Po dlhšej nedostupnosti môže akcia prebehnúť bez možnosti jej neskoršieho potvrdenia; pred novým pokusom treba stav overiť.

## Kompatibilita a nasadenie

Staršia jednotka môže vrátiť 404/HTML bez tohto API; portál vypne tlačidlá a zobrazí informáciu o nedostupnej funkcii/odpovedi. Iné API zostávajú použiteľné. Pripraviť najskôr testing release iba na sema-001, overiť capabilities a zachovanie env/HA údajov. Živý test rebootu/updatu musí byť vedomou súčasťou schváleného testovania, nevykonávať ho počas diagnostického GET.

Pred produkčnou migráciou zálohovať DB SQLite backup API a overiť opakovateľnú migráciu 7 → 8 na jej kópii. Historický deploy verifier viazaný na schému 7 sa pri budúcom vydaní musí aktualizovať na 8. Zdrojový push nie je nasadenie. SEMA jednotka nepotrebuje novú Python runtime závislosť ani novú systémovú službu; využíva existujúcu sema-update.service a oprávnenie systemctl. Pri vrátení staršieho zariadenového release endpoint zmizne a výsledok môže zostať unknown; nové príkazy sa automaticky neopakujú.

## Overenie

Portál: kompletných **93 testov** prešlo vrátane 8 servisných testov (oprávnenia, audit, strata odpovede, duplicita, potvrdené odmietnutie, nesprávna identita a migrácia 7 → 8). Frontend build a ESLint nových komponentov prešli. Dashboard: kompletných **44 testov** prešlo vrátane 8 servisných testov. Žiadny test nevykonáva skutočné sudo, systemctl ani ovládanie čerpadla.

Headless Chromium v tomto prostredí neposkytol DOM; automatický browserový test preto nie je potvrdený. Produkčný portál, zákaznícke zariadenia ani sema-001 sa pri tejto implementácii neaktualizovali a nereštartovali.

## Testing nasadenie servisného API – 3. 11. 2026

Na výslovný pokyn používateľa nasadené iba na sema-001: release `a82beea67c3d655d12bd85239fc290faf8793ee8`, dashboard 1.3.0-testing.4. Kandidát vytvorený z existujúceho aca54bf; iba nový backend/maintenance.py, zapojenie routera a verzia. Frontend, existujúca HA integrácia a závislosti nezmenené. Osem izolovaných testov presného kandidáta prešlo; systémové príkazy mockované.

Pred update overený hostname/DEVICE_ID/kanál testing. Konzistentná súkromná záloha `/home/jan/sema-backups/before-maintenance-testing-20261103-211723`. Existujúci updater skončil Result=success/ExecMainStatus=0, živý SHA zhodný. Následne DB integrity_check ok, env/HA úložisko/auth.py.bak zachované podľa hashov, sema/nginx/timer active a NRestarts=0.

Živé GET overili tri capabilities, identitu a kanál, oprávnenia admin/superadmin, 401 bez tokenu a 403 pre user/HA credential. Lokálny portál potvrdil available=true a všetky tri akcie. **Žiadna nová servisná akcia sa počas overovania nespustila**; reštart dashboardu vykonal iba existujúci updater pri nasadení. Interaktívne vykonanie reštartu/rebootu/updatu zostáva na používateľský test. Produkčný release/main ostal `154197900c3d1b75b56a94e939bd9f4ba6601e58`; produkčný portál ani iné zariadenia neboli aktualizované. Admin vidí všetky záložky detailu okrem Oživenie; tú má iba superadmin.

## Oprava falošného zlyhania pri reštarte vlastnej služby – 3. 11. 2026

Používateľské pokusy na sema-001 o 22:23:48 a 22:26:50 CET neboli odmietnuté intervalom: oba dostali HTTP 202 a sudo systemctl restart --no-block sema.service bol vykonaný. Journal potvrdil zastavenie/nový štart služby. Pomocný sudo/systemctl proces v rovnakej systemd cgroup skončil pri self-reštarte signálom SIGTERM (subprocess returncode -15). Pôvodný kód považoval každý nenulový návrat za failed a tým zablokoval neskoršie potvrdenie nového procesu. Konkrétne joby cf2ac62a-8181-4d47-9753-2982eba3af50 a 0c11412e-b7a1-41c6-b9f5-fff59bb676f0.

Lokálna oprava: záporný návratový kód znamená prerušený pomocný proces, zostane running a čaká na zmenu identity procesu/bootu. Samotný signál neznamená success; bez potvrdenia zostáva pôvodný timeout/unknown. Kladný návratový kód príkazu je naďalej failed. Žiadne automatické opakovanie akcie. Regresný test simuluje SIGTERM pri reštarte dashboardu aj reboote, potvrdzuje running → success až po zmene identity a jediné vykonanie príkazu. Všetkých 9 servisných testov dashboardu prešlo.

Na pokyn používateľa **bez release alebo nasadenia opravy**. Živá sema-001 zatiaľ zostáva na a82beea a túto chybu vyhodnotenia ešte obsahuje; ďalší live reštart môže mať opäť nesprávny výsledok. Existujúce failed záznamy sa spätne neprepisovali a počas diagnostiky nebol vyvolaný ďalší reštart. Do spoločného vydania zaradiť opravu spolu s portálovými hláseniami/intervalom.

## Oprava SIGTERM nasadená iba na sema-001 – 3. 11. 2026

Používateľ následne výslovne autorizoval testing opravu. Release `a4c90312fbbacbd187dec765e56c067917f65978`, dashboard 1.3.0-testing.5, nasadený existujúcou sema-update.service (success/exit 0). Kandidát oproti a82beea mení iba maintenance.py a číslo verzie, frontend/HA bez zmeny. Všetkých 9 servisných testov presného kandidáta prešlo. Záloha `/home/jan/sema-backups/before-self-restart-fix-20261103-214456` zahŕňa DB, servisnú históriu a konfiguráciu.

Po nasadení potvrdené SHA, capabilities API/verzia/kanál testing, DB integrity, nezmenené všetky servisné joby a env/HA/auth.py.bak podľa kontrolných súčtov. sema/nginx/timer active, NRestarts=0. Ďalší servisný príkaz sa pri verifikácii nespúšťal; nasadenie reštartovalo iba dashboard cez existujúci updater. Staré failed joby ostali nezmenené. Používateľ teraz môže vykonať nový živý test z lokálneho portálu.

Staršie poznámky o nenasadenej SIGTERM oprave sú historické. Zákaznícky release/main zostáva 1541979 a produkčný portál sa nemenil. Platí odloženie spoločného produkčného vydania; toto bola samostatne schválená aktualizácia testing sema-001.

## Produkčné povýšenie zariadenového release – 4. 11. 2026

Na používateľský pokyn presný otestovaný release `a4c90312fbbacbd187dec765e56c067917f65978` povýšený cez promote_release.sh --production do distribučného main, bez nového buildu. Pred povýšením potvrdený rovnaký živý SHA na sema-001 a aktívna služba. Main aj testing overené na rovnakom SHA; sema-001 zostáva na testing. Ostatné jednotky neboli ručne aktualizované/reštartované, release dostanú pri bežnom update, vypnuté až po zapnutí.

Preverená kompatibilita s pôvodným venv sema-005: nemá zeroconf/ifaddr. Presný kandidát bol rozbalený iba do dočasného stagingu, startup/shutdown nad vlastnou prázdnou DB a HA úložiskom prešli s mockovanými zberačmi (bez čerpadlových GET/POST). Aj zapnutý discovery worker zvládol chýbajúce voliteľné knižnice bez pádu API. Tieto balíky sú potrebné pre automatické mDNS vyhľadanie HA; bez nich zostáva manuálna adresa dostupná. Existujúci updater ich automaticky neinštaluje. Bežiaca sema-005 ostala aktívna na pôvodnom 1541979; jej env/DB/služba sa nemenili.

Produkčný portál tejto etapy zatiaľ čaká na samostatný sudo deploy so zálohou a migráciou 7 → 8; zdrojový main bol povýšený na kandidáta 2bf17b4. Lokálne testovacie požiadavky sa do produkčnej DB neimportujú.
