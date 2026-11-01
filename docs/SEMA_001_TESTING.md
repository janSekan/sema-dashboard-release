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

## Testing nasadenie Home Assistant API – 1. 11. 2026

- Výslovne autorizované používateľom iba pre sema-001; hostname aj DEVICE_ID overené pred zásahom. Kanál testing zachovaný.
- Dashboard **1.3.0-testing.1**, release **e3b749744888df28a65d918f09c6bf8d872220c0**, publikovaný cez deploy_release.sh --testing a nainštalovaný existujúcou sema-update.service. Result=success, ExecMainStatus=0; živý HEAD sa zhoduje.
- Distribučný main zostal **154197900c3d1b75b56a94e939bd9f4ba6601e58**. Žiadna aktualizácia ostatných zariadení, portálu alebo používateľovho HA.
- Súkromná záloha: `/home/jan/sema-backups/before-ha-testing-20261101-133037`. SQLite backup API, integrity_check=ok, 38 817 meraní a 311 udalostí; zálohované env, auth.py.bak, predchádzajúce requirements/verzie/updater a inventár balíkov. Žiadne tajomstvá neboli vypisované.
- Pred aktualizáciou osobitne nainštalované zeroconf 0.151.1 a ifaddr 0.2.0 do /home/jan/sema/.venv (Python 3.13.5/aarch64). pip check bez problémov. Updater závislosti neinštaluje automaticky.
- Zdrojové kontroly: 32 testov cez backend/.venv/bin/python, frontend build, shell syntax release skriptov. Systémový python3 bez projektových závislostí nie je testovacie prostredie. Existujúce CSS upozornenie DaisyUI na @property zostáva.
- Živé info/state cez nginx: správna verzia API/firmvéru a spoločné UID, snapshot s explicitným UTC, dostupné čerpadlo. Bez tokenu 401 na nginx aj backend porte, neplatný token 401; HA token na správu/konfiguráciu/provisioning/sync dostane 403.
- mDNS `_sema._tcp.local.` overené na wlan0 (192.168.0.86:80): iba verejné device_uid/api_version/scheme a dosiahnuteľná LAN adresa. Po odvolaní tokenu oznam zmizol. Ide o overenie na LAN rozhraní zariadenia, nie discovery z HA/OMV.
- Testovací token zostal iba v pamäti kontrolného procesu, po teste odvolaný. API je vypnuté do vytvorenia vlastného tokenu v Informáciách o zariadení → Home Assistant. UID súbor zostal 0600, bez aktívneho token hash. Tokeny ani UID sa nepridávajú do Gitu.
- Po reštarte integrity_check=ok, env a auth.py.bak zhodné so zálohou, účty aj app_settings zhodné podľa súkromných kontrolných súčtov. Služby sema/nginx aktívne, NRestarts=0, pôvodný sema-update.timer obnovený. Existujúci LAN_ACCESS sa nemenil. Do čerpadla sa neposielali riadiace príkazy.
- Zostáva integračný test párovania a entít v HA Container/Core 2026.9.4 na OMV/RPi5. Živé browserové tlačidlo kopírovania na zariadení zatiaľ netestované (lokálny browser test s mock API prešiel).
