# Stav a odovzdanie práce – SEMA Dashboard

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

1. 11. 2026: lokálne pripravené read-only HA API v1, dedikovaný odvolateľný token,
perzistentné UID mimo telemetrickej DB a admin UI v Informáciách o zariadení.
Podrobný kontrakt a hranice: [HOME_ASSISTANT_API.md](HOME_ASSISTANT_API.md).
Následne doplnený mDNS publisher `_sema._tcp.local.` na povolenom LAN rozhraní
(predvolene wlan0:80), aktívny iba pri zapnutom HA API. Po odvolaní tokenu
oznam stiahne. Do oznamu nepatria token/hash ani údaje pumpy. HA integrácia
má zodpovedajúci discovery flow s tokenovým potvrdením a overením UID.
UI má tlačidlo kopírovania tokenu aj fallback pre HTTP a manuálne označenie.
Pred testing release treba nainštalovať nové zeroconf/ifaddr závislosti do runtime
venv (updater ich neinštaluje); žiadne nasadenie zatiaľ neprebehlo.
Zatiaľ nenasadené; nemení vyššie uvedené release SHA. HA integrácia sa vyvíja
samostatne v sema-home-assistant; pred testing release overiť obidve strany.
Lokálne kontroly tejto zmeny: 32 unittest testov (API/discovery/telemetria/release),
frontend production build a git diff --check prešli. Build hlási CSS upozornenie
na DaisyUI @property. Kopírovanie tokenu je overené lokálnym Chromium testom
s mock API. Živý multicast, HA webUI a zariadenie sa netestovali.

Interaktívne historické grafy vytvárať primárne v portáli. Prenos je predvolene hodinový s ručným stiahnutím, limity a protokol v TELEMETRY.md. Retencia/agregácia zatiaľ nie je dohodnutá; nemaž dáta svojvoľne. Nové vydanie najskôr testing a overenie sema-001; produkcia iba samostatným povýšením presného release SHA.

Spustenie/testy: README.md. Synchronizácia: DEVELOPMENT_WORKFLOW.md. Release: RELEASE_WORKFLOW.md. Zmeny sú v zdrojovej development; nezamieňať s distribučným testing.
