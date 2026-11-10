# Stav a odovzdanie práce – SEMA Dashboard

## Supervízor – 10. 11. 2026, iba lokálne

Nová rola supervisor (Supervízor) má čítanie portálu ako admin, bez zápisu.
Oprávnenie na čítanie a zápis je oddelené na backende, editácie aj akcie sú
skryté v UI a priame edit URL blokované. Nemôže zmeniť vlastnú/cudziu rolu či
heslo, priradenia, zákazníkov, zariadenia, inštalácie, revízie, nastavenia,
tokeny, spustiť ručný sync ani servis. Výnimka je výber dashboardu do session.
Servisný prehľad iba číta uloženú históriu a nesonduje jednotku.

Dashboard rozpoznáva supervisor s admin oprávnením pre prevádzku, parametre,
sieť a HA. Pôvodná pumpová proxy je povolená; servisné maintenance API ostáva
admin/superadmin. Portál prenáša skutočnú aktuálnu DB rolu bez povýšenia na admin.
Oživenie zostáva superadminovi. Schéma DB ani existujúce účty sa nemenia.
Aktualizované obe kópie [manuálu](USER_MANUAL.md) a [kontraktu rolí](ROLES.md).

Prešlo 160 portálových a 67 dashboardových testov, oba frontend buildy,
35 mock browser scenárov vrátane mobilu. Cielený ESLint portálu a dashboardového
helpera prešiel; AuthContext dashboardu má 6 pôvodných lint nálezov, bez nových.
Testy enumerujú všetky portálové zápisy,
kontrolujú zákaz povýšenia vlastnej roly a zachovanie testovacej DB pri čítaní.
Bez príkazov živému čerpadlu, bez pushu, release či nasadenia na testing/produkciu.
Staršie HA/hardvérové rozpracované súbory zostávajú mimo commitov tejto úlohy.
Pred pridelením roly vydať po samostatnom schválení portál aj dashboard.

## Produkčný hotfix TÚV 1.3.1 – 10. 11. 2026

Na výslovný pokyn používateľa publikovaný priamo release/main:
`7f8ef759ad6125b19a2aa302ec32eac546d6e73b`. Obe teplotné polia TÚV od 0 °C,
horná hranica 60 °C, krok 0,5 °C. Izolovaný zdroj `15b790d` z produkčného
východiska; backend, skripty, konfigurácie a závislosti ostali bezo zmeny.
Baseline build bol bajtovo zhodný s produkciou; nový build a kontrola rozsahu prešli.
Testing zostáva bb340d1; superuser a ďalšia rozpracovaná práca sa nevydali.
Jednotky dostanú release vlastným updaterom; okamžitý update nebol spustený.
Zdrojový development nebol pushnutý.

## Superuser a manuál – 10. 11. 2026, iba lokálne

Superuser má prístup ku krivke, sekcii Iné, koeficientu a uloženiu referencie.
Administrácia portálu, sieť, správa HA, servisné akcie a pôvodné rozhranie
čerpadla zostávajú iba adminovi/superadminovi. Portál prenáša aktuálnu DB rolu
iba k priradenému zariadeniu; starý servisný výber nedáva oprávnenie navyše.
Role sa validujú v API aj pri zápise používateľa. Schéma DB sa nemení.

Účty sú odstránené z Nastavení dashboardu; pôvodná správa účtov vracia HTTP 410.
Existujúce lokálne prihlasovanie zostáva zachované, heslá sa z portálu
nesynchronizujú a nevzniká žiadny predvolený superuser účet. Bežný používateľ
ukladá iba základné parametre bez zmeny skrytých technických nastavení.
Prvotné nastavenie Wi-Fi zostáva funkčné.

[Podrobný manuál](USER_MANUAL.md) a [kontrakt rolí](ROLES.md) sú v oboch projektoch.
Overenie: 155 testov portálu, 66 dashboardu, oba frontend buildy, cielený ESLint
upravovaných súborov a 10 scenárov v prehliadači s mock API. Bez príkazov
živému čerpadlu. Lokálne commity; bez pushu, release a nasadenia, aj na sema-001.
Staršie rozpracované HA a hardvérové súbory zostávajú mimo týchto commitov.
Živé testovanie a nasadenie vyžadujú nový konkrétny pokyn používateľa.

## Koeficient posunu krivky – 8. 11. 2026

Pripravený testing 1.3.0-testing.6: admin/superadmin nastavuje koeficient 1,0 po 0,1;
backend ním násobí zmeny teploty všetkých používateľov. Uchováva sa zlomkový posun
kvôli kroku čerpadla 0,5 °C. Uloženie koeficientu nemení krivku ani referenčnú teplotu.
Detaily a testy: [HEATING_COEFFICIENT.md](HEATING_COEFFICIENT.md).

Kandidát bol pripravený vo vetve feature/heating-coefficient na izolovanom východisku
zhodnom s už publikovaným a4c9031 (backend aj frontendový build bajt po bajte).
Samotný koeficient je lokálne commitnutý aj v development; pôvodné rozpracované HA
a hardvérové zmeny zostali mimo commitu. Zdrojový development sa na pokyn používateľa
zatiaľ nepushuje. Testing bb340d1169c07f1f8dc93b6a6b457f7e8cdab700 bol nasadený
iba na sema-001; distribučný main a4c9031 ostal nezmenený. Prešlo 56 lokálnych testov,
UI kontrola troch rolí a 11 izolovaných testov v Python prostredí sema-001.
Verifikácia bola iba na čítanie: default 1, admin/superadmin 200, user 403,
anonym 401, frontend 200; DB/účty/nastavenia/konfigurácia zachované. Záloha a detaily
sú v [HEATING_COEFFICIENT.md](HEATING_COEFFICIENT.md). Živý používateľský test teploty zostáva.

Aktualizované 31. 10. 2026 pri zavedení spoločnej zdrojovej vetvy development. Aktuálny commit over cez git log; stav zariadenia over zvlášť cez SSH.

## Implementované

- V menu návrat Portal iba pre admin/superadmin, vzdialené otvorenie pôvodného rozhrania čerpadla cez portálovú proxy.
- Piata teplotná karta „Aktuálna žiadaná teplota kúrenie“, API equitermTemp a história eqt. Detaily rozloženia: DASHBOARD_TEMPERATURES.md.
- Pozorovanie XML každých 15 s, merania a dávkové zápisy po 5 minútach, stavy/udalosti/poruchy, dostupnosť zdrojov, raw JSON; kritické zmeny vyvolajú skorší commit. RAM buffer šetrí počet transakcií, nie je zárukou fyzického počtu zápisov microSD.
- Sync protokol 2: identita DB, metadata, flush, merania a udalosti, tokenové overenie. Nová DB má novú identitu, reštart ju nemení. Staršie udalosti sa spätne nevytvoria.
- Updater kontroluje vlastníctvo vrátane Git metadát; návod pri montáži je UPDATE_OWNERSHIP.md. Balík vylučuje aj SQLite WAL/SHM/journal. Bootstrap oprava patrí do samostatného projektu, nie je súčasťou tohto pushu.

## Skutočné nasadenie

- Vlastný sema-001: testing release 154197900c3d1b75b56a94e939bd9f4ba6601e58, verzia 1.2.0-testing.1. Záloha, testy a kanál v SEMA_001_TESTING.md.
- Zákazníci: release/main bol na pokyn používateľa povýšený na 154197900c3d1b75b56a94e939bd9f4ba6601e58, rovnaký SHA ako testing. Jednotky ho dostanú pri svojom bežnom update; úspešný update každej jednotky sa týmto nepotvrdzuje. Zdrojový main je tiež zosúladený s development.
- Lokálny portál úspešne ručne stiahol prvých 5 000 meraní a jednu udalosť; historické dávky pokračujú. Tento pôvodný test produkčný portál nemenil; následne bol portál úspešne nasadený na runtime 409749f so schémou 7, pozri portálové docs/PRODUCTION_DEPLOYMENT.md.
- Kontroly zaznamenané v TELEMETRY.md a SEMA_001_TESTING.md: frontend build, release a telemetrické testy, reálny testing update, zachovanie konfigurácie a integrity DB. Pre nový zásah over výsledok znova podľa rozsahu; cloud bez pumpy overuje mock/testy.

## Ďalší smer

Interaktívne historické grafy vytvárať primárne v portáli. Prenos je predvolene hodinový s ručným stiahnutím, limity a protokol v TELEMETRY.md. Retencia/agregácia zatiaľ nie je dohodnutá; nemaž dáta svojvoľne. Nové vydanie najskôr testing a overenie sema-001; produkcia iba samostatným povýšením presného release SHA.

Spustenie/testy: README.md. Synchronizácia: DEVELOPMENT_WORKFLOW.md. Release: RELEASE_WORKFLOW.md. Zmeny sú v zdrojovej development; nezamieňať s distribučným testing.

## Servisné API – vývoj 3. 11. 2026

Nové portal-only endpointy maintenance: reštart dashboardu/RPi a update existujúceho kanála. Trvalé idempotentné UUID mimo checkoutu, kontrola admina aj proxy tokenu, žiadny LAN/HA bypass, ochrana aktívneho updatu a proti opakovaniu po strate odpovede. Kompletných 44 testov dashboardu prešlo. Nasadenie neprebehlo; najskôr samostatne autorizovať testing sema-001. Portál má implementovanú záložku Servis a prídavnú schému 8; docs/DEVICE_MAINTENANCE.md.

## Servisné API na sema-001 – 3. 11. 2026

Testing a82beea/1.3.0-testing.4 nasadený cez existujúci updater, capabilities a roly aj lokálny portál overené. DB/env/HA zachované; zákaznícky main 1541979 nezmenený. Živé servisné akcie zatiaľ nevykonané; podrobnosti v DEVICE_MAINTENANCE.md.

## Falošné zlyhanie self-reštartu – 3. 11. 2026

Potvrdený SIGTERM/-15 pomocného systemctl procesu pri úspešnom reštarte sema.service. Záporný návrat už lokálne neznačí failed; čaká sa na nový proces/boot. Deväť izolovaných servisných testov prešlo. Bez vydania opravy na sema-001; čaká sa na používateľské testy a spoločný release. Podrobnosti docs/DEVICE_MAINTENANCE.md.

## SIGTERM oprava na sema-001 – 3. 11. 2026

Na nový výslovný pokyn nasadený testing a4c9031/1.3.0-testing.5, 9 kandidátskych testov prešlo. API/služby/DB a servisná história/env/HA overené. Záloha before-self-restart-fix-20261103-214456; nový používateľský test zostáva otvorený. Produkcia a iné jednotky nezmenené. Podrobnosti DEVICE_MAINTENANCE.md.

## Produkčný release jednotiek – 4. 11. 2026

Presný otestovaný a4c9031 povýšený do distribučného main cez promote_release.sh; testing rovnaký, sema-001 na ňom stále beží. Starší venv sema-005 overený izolovaným startupom kandidáta bez voliteľných HA discovery závislostí; jej živá služba ani HEAD sa nemenili. Zariadenia dostanú release pri bežnom update. Produkčný portál čaká na sudo deploy 2bf17b4/schému 8. Podrobnosti DEVICE_MAINTENANCE.md.
