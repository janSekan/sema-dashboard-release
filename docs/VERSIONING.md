# Verzie dashboardu a porovnanie vydaní

Stav 10. 11. 2026: implementované lokálne, bez vydania na zariadenia alebo produkčný portál.

## Čo sa zobrazuje

- **Verzia** – čitateľné číslo, napríklad 1.3.2. Úplné číslo z versions.json
  (vrátane testing.2) zostáva v API a evidencii. V Info sa používa čitateľná verzia.
- **Zostavenie** – prvých osem znakov SHA distribučného Git commitu; celé SHA
  sa prenáša a porovnáva. Rozlíši aj dve vydania s rovnakým číslom verzie.
- **Kanál** – Produkčný (main) alebo Testovací (testing), vychádza z lokálneho
  konfiguračného súboru jednotky. Číslo verzie nikdy neprepína kanál.
- **Čas potvrdenia** – kedy portál naposledy prijal túto informáciu od jednotky.
  Nezamieňať s dátumom inštalácie. Offline zariadenie ukazuje posledný známy stav.

Dashboard Info ukazuje verziu a zostavenie; kanál vidia admin/superadmin a
Supervízor. Portál → Zariadenie → Servis má panel s nainštalovaným a dostupným
vydaním pri akciách aktualizácie. Supervízor ho iba číta.

## Prenos a zdroj údajov

Zariadenie pridáva `software` k existujúcemu `/device-api/sync/status`,
`/device-api/device-info` a servisným capabilities. Obsah: version,
release_commit, channel, built_at. Nie sú potrebné ďalšie heartbeat spojenia.
SHA a verzia sa zmrazia pre život procesu pri štarte; reset súborov updaterom
pred reštartom tak nepomieša identitu starého a nového procesu. V dev režime
sa zdrojový commit nevydáva za nainštalované produkčné zostavenie.

Balenie `make_release.sh` generuje release.json s verziou, UTC built_at a
kontrolným súčtom obsahu (artifact_id). Rovnaký obsah ponechá pôvodný built_at;
opakovaný nezmenený build zbytočne nevytvorí nový release. Finálny rsync porovnáva
obsah, aby nepreskočil rýchlo zmenený súbor s rovnakou veľkosťou/časom.
Git SHA konkrétneho distribučného commitu sa číta až na jednotke; manifest ho
nemôže obsahovať pred vlastným commitom. Chýbajúce údaje zostávajú NULL.

Portál ukladá overené hlásenie do device_software a aktualizuje existujúce
`devices.dashboard_version` v rovnakej transakcii ako heartbeat. Najprv kontroluje
token a identitu zariadenia. Starší heartbeat bez software údaje nevymaže;
čas posledného potvrdenia softvéru sa tým nepredĺži.

## Dostupné vydanie

GET `/api/admin/devices/{device_id}/software` je iba čítanie pre admin,
superadmin a Supervízor. Nespúšťa update ani spojenie s jednotkou.
Pevný verejný zdroj je GitHub janSekan/sema-dashboard-release: ref main/testing
cez GitHub API a versions.json zo získaného presného commitu. Verejný prístup
bol overený bez tokenu. Nepridávajú sa prihlasovacie údaje ani ľubovoľné URL.

Cache je spoločná pre proces a všetky zariadenia, 10 minút na kanál, s jedným
súbežným načítaním. Dve HTTP požiadavky na načítanie kanála znamenajú pri dvoch
kanáloch najviac približne 24 požiadaviek za hodinu pri ustálenej prevádzke.
Pri viacerých procesoch by každý mal vlastnú cache; projekt používa jeden worker.
Aj neúspech sa cacheuje. Pri výpadku alebo rate limite ostane posledný dostupný
údaj označený ako starší; nepovažuje sa za čerstvo overený.

Porovnanie je podľa plného SHA, nie reťazca verzie:

- current: potvrdené zostavenie sa rovná dostupnému vydaniu kanála;
- different: kanál obsahuje iné zostavenie, nie nevyhnutne novšie;
- unknown: chýba SHA/kanál/report alebo katalóg nemožno čerstvo overiť.

Rovnaké číslo verzie pri odlišnom SHA neznamená rovnakú aktualizáciu.
Výslovný rollback v kanáli je tiež odlišné vydanie, preto UI nesľubuje „novšie“.
Tlačidlo Aktualizovať naďalej používa aktuálny kanál a existujúce potvrdenie;
nezamyká konkrétne SHA z náhľadu. Ak sa kanál medzitým zmení, updater vezme
jeho aktuálne vydanie. Nie je to nové automatické aktualizovanie z portálu.

## Migrácia a budúce vydanie

Portál má prídavnú opakovateľnú schému 9 (nová device_software). Pred migráciou
vždy SQLite backup API; existujúce zariadenia, účty, história a konfigurácie
zostávajú. Lokálny preview používa vlastnú súkromnú kópiu DB. Živá DB sa nemení.

Nový portál zvládne staršie jednotky: zobrazí známu verziu zo servisného API,
ale nevymyslí chýbajúce zostavenie/kanál. Plná evidencia sa naplní po schválenom
vydaní nového dashboardu a prvom platnom heartbeate. Vydať až samostatným pokynom,
najprv testing sema-001, potom schválená produkcia. Doterajšia autorizácia tooltipov
nie je autorizáciou tohto vydania.

Číslovanie: patch pre opravy (1.3.1 → 1.3.2), minor pre funkcie, major pre
nekompatibilné zmeny. Testing používa napr. 1.4.0-testing.1. Pred prípravou
kandidáta treba zvoliť nové číslo vo versions.json; automatické zvyšovanie nie je
zavedené. Jednoznačnú identitu každého vydania zabezpečuje distribučný SHA.

Overenie: 168 portálových a 73 dashboardových testov, oba buildy, cielený ESLint,
12 mock browser scenárov (rovnaké/odlišné/staré/neznáme zostavenie, offline cache,
roly a mobil). Testy migrácie/DB sú izolované; žiadne riadiace príkazy čerpadlu.

Lokálny preview bol po konzistentnej zálohe
`~/.local/state/sema-portal-preview/backups/before-versioning-20261110-182415.db`
obnovený so schémou 9. Overené zachovanie účtov, zákazníkov, jednotiek a revízií,
integrita DB a prihlásené software API cez Vite HTTP 200. Sema-001 zatiaľ neposiela
nové polia, preto je porovnanie unknown; nejde o chybný odhad aktuálnej verzie.
