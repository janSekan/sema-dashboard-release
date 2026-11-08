# Informácie o zariadení

## Zobrazenie verzií – 3. 11. 2026

Zo stránky odstránená položka SEMA OS. Dashboard verzia zobrazuje číslo bez koncového -testing.N (napr. 1.3.0-testing.2 → 1.3.0). Presná verzia v versions.json a odpovedi API zostáva zachovaná pre servis. Táto úprava je iba prezentácia; nemení aktualizačný kanál ani nepovyšuje testovací balík do produkcie.

Prípona testing sa v commitnutej histórii objavila 31. 10. 2026 v 5157e64 pri príprave telemetrického vydania 1.2.0-testing.1. Povýšenie presného otestovaného balíka zachováva jeho verziu; preto môže prípona zostať aj po povýšení do release/main.

Overené frontend buildom. Produkčné zariadenia touto zdrojovou úpravou neboli aktualizované. Existujúca rozpracovaná HA integrácia a hardvérové súbory zostávajú samostatnou prácou.

## Pätička dashboardu – 3. 11. 2026

Meno Jan Sekan v texte Created by © je odkaz na https://sekan.sk, otvorený v novej karte. Overené frontend buildom; zatiaľ iba zdrojová development, bez vydania na zariadenia.

## Testing vydanie pripravené – 3. 11. 2026

Na používateľský pokyn publikovaný iba release/testing `aca54bfb7af86b153daeb88276aae4aae2b7aab0` (1.3.0-testing.3). Oproti 0553775 zmenený iba frontend a verzia balíka; backend/HA/závislosti zachované. Obsahuje odstránenú kartu SEMA OS, zobrazenie verzie bez testing prípony a odkaz Jan Sekan → https://sekan.sk. Frontend build prešiel. Produkčný release/main zostal `154197900c3d1b75b56a94e939bd9f4ba6601e58`.

Okamžité nasadenie na sema-001 zatiaľ **nepotvrdené**: priame SSH aj ProxyJump vypršali, aktuálne lokálne Tailscale pripojenie neobsahovalo sema-001 ani sema-portal. Používateľ požiadaný prepnúť do správnej siete; potom overiť identitu/kanál, vytvoriť zálohu a spustiť existujúcu sema-update.service. Samotný publikovaný testing balík nie je dôkaz aktualizácie zariadenia.

### Nasadenie sema-001 dokončené – 3. 11. 2026

Po prepnutí Tailscale siete overená identita/kanál a pôvodný SHA 0553775. Záloha `/home/jan/sema-backups/before-device-info-testing-20261103-203015`, SQLite backup API/integrity ok. Existujúca sema-update.service úspešne nasadila presný `aca54bfb7af86b153daeb88276aae4aae2b7aab0` (1.3.0-testing.3), Result=success/ExecMainStatus=0. Frontend zobrazuje číselnú verziu bez testing prípony.

Po aktualizácii nginx a nový JS HTTP 200, balík obsahuje https://sekan.sk a nemá označenie SEMA OS. DB integrity_check ok, env/HA úložisko/auth.py.bak zachované podľa súkromných hashov. sema/nginx/timer active, NRestarts=0. Existujúci necommitnutý auth.py.bak zostal nezmenený. Produkčný main zostáva 1541979; žiadne iné zariadenie ani portál neaktualizované. Ovládacie príkazy čerpadlu sa neposielali. Predchádzajúce čakanie na prístup je historické; funkčný náhľad teraz môže vykonať používateľ.
