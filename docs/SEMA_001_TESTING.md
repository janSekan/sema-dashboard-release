# sema-001 – aktivovaný testovací kanál

Overené 30. 10. 2026 cez SSH, používateľ `jan`, Tailscale IP `100.89.145.76`. Hostname aj `DEVICE_ID` sú `sema-001`.

## Aktuálny stav

- Release GitHub repozitár: `janSekan/sema-dashboard-release`.
- Produkčný `main` bol 31. 10. 2026 povýšený na presne otestovaný `7d7b82a641ba9acba7a021bac1ba1afcb04fa4eb` (predtým `4d9078e5d861f9718748741834b93a234cf4bfb2`). Sema-001 naďalej zostáva na kanáli `testing`.
- Prvý publikovaný `testing`: `fbc772a55dec58531a46a3a78bc8b4d335e1cc43`.
- Aktuálne nainštalovaný `testing`: `154197900c3d1b75b56a94e939bd9f4ba6601e58`, verzia dashboardu **1.2.0-testing.1**. Obsahuje piatu teplotnú kartu, rozloženie šiestich kariet, dávkový zber stavov/porúch a nový synchronizačný protokol. Predchádzajúci release bol `7d7b82a641ba9acba7a021bac1ba1afcb04fa4eb`.
- Kanál je v `/home/jan/.config/sema/update-channel`, obsah `testing`.
- `/etc/sema/update-channel` neexistuje. Ak sa neskôr vytvorí, má prednosť.
- `sema` a `sema-update.timer` sú aktívne. Aktualizačná služba po spustení skončila `Result=success`, `ExecMainStatus=0`.
- Lokálna Git vetva na jednotke nemusí mať názov kanála: updater inštaluje commit z explicitne vybraného vzdialeného refu. Rozhoduje súbor kanála a `git rev-parse HEAD`, nie názov lokálnej vetvy.

Staršia nainštalovaná systemd služba spúšťa updater ako root. Nový updater sa cez `runuser` prepína na `jan`, aby Git používal jeho prostredie a prístup. Reštart aplikácie používa už existujúce oprávnenie `sudo systemctl` bez hesla. Systémové sudo oprávnenia ani systemd jednotky neboli menené.

## Ďalší testovací update

Na vývojovom počítači zo zdrojového projektu:

```bash
cd /home/jan/Projects/sema_dashboard/sema
./deploy_release.sh --testing "Popis zmeny"
```

Potom na jednotke:

```bash
ssh jan@100.89.145.76
sudo systemctl start sema-update.service
git -C /home/jan/sema rev-parse HEAD
systemctl show sema-update.service --property=Result --property=ExecMainStatus
```

Publikovať do produkcie až po samostatnom testovaní podľa [release workflow](RELEASE_WORKFLOW.md). Žiadny produkčný release nebol pri aktivácii testovacieho kanála vydaný.

## Záloha pred prepnutím

Súkromný adresár na jednotke:

```text
/home/jan/sema-backups/before-testing-20261030-202004
```

Obsahuje konzistentnú SQLite zálohu cez backup API, lokálne environment súbory, pôvodný updater, existujúci `backend/auth.py.bak` a pôvodný release SHA. Adresár má práva 700, citlivé zálohované súbory 600. Nie je súčasťou Gitu.

Po update sa porovnaním bajtov overilo, že lokálna konfigurácia a `backend/auth.py.bak` zostali nezmenené. Backendový kód ani requirements sa v tomto release nemenili. Konfigurácia nginx sa iba stiahla ako súbor v repozitári; nenainštalovala sa do systému.

## Čo sa overilo

- Štyri lokálne integračné testy release workflow a Bash syntax.
- Reálny update cez existujúcu systemd službu na sema-001.
- GET dashboardu na lokálnom porte 8000 aj cez nginx na porte 80.
- GET nového frontendového assetu, ktorý obsahuje podporu `sema-pump-url`.
- GET autentifikovaného sync/status so zhodou `device_id=sema-001`, bez vypísania tokenu.
- GET access-mode API, aktívna aplikácia aj timer.
- Kontrola vzdialených refov na GitHube: `main` nezmenený, nový commit iba v `testing`.

Nerobili sa POST požiadavky do čerpadla ani zmeny jeho nastavení. Portálový backend nebol nasadený, takže nové otvorenie pumpy cez portál vyžaduje ešte samostatné nasadenie portálovej časti. Zákaznícke jednotky, lokálny checkout `sema-release` a bootstrap neboli upravované.

## Nočné aktualizácie

Overený timer má `OnBootSec=3min`, nie opakovaný nočný interval. Aktuálny boot aplikácie bol o 02:00 a posledný pôvodný update o 02:03. Používateľ `jan` nemá crontab; systémový `/etc/crontab` neobsahoval priamy SEMA update. Rootov crontab nebol prístupný bez hesla, takže presný zdroj nočného rebootu ostáva neoverený. Po ďalšom nočnom cykle je vhodné overiť kanál, SHA a výsledok služby. Bežná bootová aktualizácia cez overenú službu už používa `testing`.

## Návrat na aktuálnu produkciu

Na sema-001, ak stále neexistuje systémový súbor kanála:

```bash
printf '%s\n' main > /home/jan/.config/sema/update-channel
sudo systemctl start sema-update.service
```

Ide o návrat kódu; databázu ani nastavenia tým neobnovuješ. Po nainštalovaní dnešnej starej produkčnej verzie sa môže obnoviť aj starý main-only updater. Pred ďalším prepnutím na testing preto znovu nainštalovať nový updater podľa [návodu](RELEASE_WORKFLOW.md).

## Povýšenie do produkcie 31. 10. 2026

Spustený `promote_release.sh --production 7d7b82a641ba9acba7a021bac1ba1afcb04fa4eb`. GitHub `main` aj `testing` boli overené na rovnakom SHA; nevytváral sa nový build. Pred povýšením bolo cez SSH potvrdené, že sema-001 beží práve na tomto commite a služba je aktívna. Zákaznícke jednotky neboli manuálne aktualizované ani reštartované; získajú release svojím existujúcim najbližším updatom. Vypnuté jednotky až po zapnutí a úspešnom update.


## Testing nasadenie telemetrie – 31. 10. 2026

- Publikovaný iba testing release `154197900c3d1b75b56a94e939bd9f4ba6601e58`. GitHub main zostal `7d7b82a641ba9acba7a021bac1ba1afcb04fa4eb`.
- Pred update vznikla súkromná konzistentná záloha `/home/jan/sema-backups/before-telemetry-testing-20261031-181110`, vrátane 38 554 meraní, existujúcich env súborov, updatera a `backend/auth.py.bak`. Citlivé hodnoty neboli vypisované.
- Existujúca root-run aktualizačná služba použila prepnutie na jan, úspešne stiahla testing a reštartovala dashboard: `Result=success`, `ExecMainStatus=0`. Nové požiadavky Python závislostí nepribudli.
- Po update overené: presný SHA/verzia, aktívna aplikácia a timer, SQLite integrity_check, nové JSON stĺpce a tabuľka udalostí, zachovanie env a auth.py.bak podľa kontrolných súčtov. Počet meraní bol 38 555; začal už nový zber.
- Lokálny portál mal chybu pri ručnom stiahnutí: SQLite Row z autentifikácie nemá metódu `.get()`. Opravené na indexovanie `user['id']`, doplnený regresný test so skutočnou session/databázovým typom a reštartovaný iba lokálny portál.
- Skutočný POST cez lokálny portál na sema-001 vrátil 202. Prvý workerový beh úspešne preniesol 5 000 meraní a jednu udalosť; zvyšok starej histórie pokračuje po dávkach, s minimálnym odstupom 60 s. Nový protokol aj import boli teda overené na vlastnom sema-001, nielen na fixture.
- Do čerpadla sa neposielali riadiace POST príkazy. Interný sync/flush ukladá iba telemetrický buffer. Zákaznícke jednotky, produkčný portál a main release vetva sa nemenili.

Poznámka: balenie release teraz explicitne vylučuje aj `*.db-wal`, `*.db-shm` a `*.db-journal`, nielen samotnú DB. Overené integračným testom, aby lokálny SQLite WAL neunikol do publikovaného balíka.

## Povýšenie telemetrie do produkcie – 31. 10. 2026

Na výslovný pokyn používateľa bol presný overený release `154197900c3d1b75b56a94e939bd9f4ba6601e58` povýšený cez `promote_release.sh --production` do release/main. Pred povýšením SSH potvrdilo tento SHA na sema-001, aktívnu službu, NRestarts=0 a HTTP 200 dashboardu. Znovu prešlo 16 release/telemetrických testov a frontend build (existujúce upozornenie CSS na @property). Nerobil sa nový release build ani ručný update zákazníckych zariadení. Dostanú ho pri vlastnom bežnom update, vypnuté až po zapnutí. Sema-001 ostáva na testing; main aj testing teraz ukazujú na 1541979. Zdrojový main bol zosúladený s development na b4dcf15; neskoršie commity dopĺňajú dokumentáciu. Produkčný portál sa nasadzuje osobitne.

## Testing nasadenie servisného API – 3. 11. 2026

Na výslovný pokyn používateľa nasadené iba na sema-001: release `a82beea67c3d655d12bd85239fc290faf8793ee8`, dashboard 1.3.0-testing.4. Kandidát vytvorený z existujúceho aca54bf; iba nový backend/maintenance.py, zapojenie routera a verzia. Frontend, existujúca HA integrácia a závislosti nezmenené. Osem izolovaných testov presného kandidáta prešlo; systémové príkazy mockované.

Pred update overený hostname/DEVICE_ID/kanál testing. Konzistentná súkromná záloha `/home/jan/sema-backups/before-maintenance-testing-20261103-211723`. Existujúci updater skončil Result=success/ExecMainStatus=0, živý SHA zhodný. Následne DB integrity_check ok, env/HA úložisko/auth.py.bak zachované podľa hashov, sema/nginx/timer active a NRestarts=0.

Živé GET overili tri capabilities, identitu a kanál, oprávnenia admin/superadmin, 401 bez tokenu a 403 pre user/HA credential. Lokálny portál potvrdil available=true a všetky tri akcie. **Žiadna nová servisná akcia sa počas overovania nespustila**; reštart dashboardu vykonal iba existujúci updater pri nasadení. Interaktívne vykonanie reštartu/rebootu/updatu zostáva na používateľský test. Produkčný release/main ostal `154197900c3d1b75b56a94e939bd9f4ba6601e58`; produkčný portál ani iné zariadenia neboli aktualizované. Admin vidí všetky záložky detailu okrem Oživenie; tú má iba superadmin.

## Oprava SIGTERM nasadená iba na sema-001 – 3. 11. 2026

Používateľ následne výslovne autorizoval testing opravu. Release `a4c90312fbbacbd187dec765e56c067917f65978`, dashboard 1.3.0-testing.5, nasadený existujúcou sema-update.service (success/exit 0). Kandidát oproti a82beea mení iba maintenance.py a číslo verzie, frontend/HA bez zmeny. Všetkých 9 servisných testov presného kandidáta prešlo. Záloha `/home/jan/sema-backups/before-self-restart-fix-20261103-214456` zahŕňa DB, servisnú históriu a konfiguráciu.

Po nasadení potvrdené SHA, capabilities API/verzia/kanál testing, DB integrity, nezmenené všetky servisné joby a env/HA/auth.py.bak podľa kontrolných súčtov. sema/nginx/timer active, NRestarts=0. Ďalší servisný príkaz sa pri verifikácii nespúšťal; nasadenie reštartovalo iba dashboard cez existujúci updater. Staré failed joby ostali nezmenené. Používateľ teraz môže vykonať nový živý test z lokálneho portálu.

Staršie poznámky o nenasadenej SIGTERM oprave sú historické. Zákaznícky release/main zostáva 1541979 a produkčný portál sa nemenil. Platí odloženie spoločného produkčného vydania; toto bola samostatne schválená aktualizácia testing sema-001.

## Produkčné povýšenie zariadenového release – 4. 11. 2026

Na používateľský pokyn presný otestovaný release `a4c90312fbbacbd187dec765e56c067917f65978` povýšený cez promote_release.sh --production do distribučného main, bez nového buildu. Pred povýšením potvrdený rovnaký živý SHA na sema-001 a aktívna služba. Main aj testing overené na rovnakom SHA; sema-001 zostáva na testing. Ostatné jednotky neboli ručne aktualizované/reštartované, release dostanú pri bežnom update, vypnuté až po zapnutí.

Preverená kompatibilita s pôvodným venv sema-005: nemá zeroconf/ifaddr. Presný kandidát bol rozbalený iba do dočasného stagingu, startup/shutdown nad vlastnou prázdnou DB a HA úložiskom prešli s mockovanými zberačmi (bez čerpadlových GET/POST). Aj zapnutý discovery worker zvládol chýbajúce voliteľné knižnice bez pádu API. Tieto balíky sú potrebné pre automatické mDNS vyhľadanie HA; bez nich zostáva manuálna adresa dostupná. Existujúci updater ich automaticky neinštaluje. Bežiaca sema-005 ostala aktívna na pôvodnom 1541979; jej env/DB/služba sa nemenili.

Produkčný portál tejto etapy zatiaľ čaká na samostatný sudo deploy so zálohou a migráciou 7 → 8; zdrojový main bol povýšený na kandidáta 2bf17b4. Lokálne testovacie požiadavky sa do produkčnej DB neimportujú.
