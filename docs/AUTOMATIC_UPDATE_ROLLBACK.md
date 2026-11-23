Aktualizácia23.11.2026: kandidát súčasťou vydania1.4.3 do main na výslovný pokyn;
živé testing/001 kolo sa preskočilo. Presný výsledok publikovania v WATCHDOG_RELEASE_143.md.
Pôvodný návrh a jeho limity nasledujú.

# Chránený update a automatický návrat

Stav 23. 11. 2026: **pripravené iba lokálne**, bez commit/pushu, vydania alebo
nasadenia na jednotku. Živý main/testing naďalej obsahuje predchádzajúci 1.4.2.
Toto nie je päťminútová kontrola vydaní; tá sa v tejto etape nepridáva.

## Priebeh

`update.sh` zachová kontrolu jan/vlastníctva/kanála/sudo a read-only --check.
Skutočnú aktualizáciu vykonáva štandardný Python `scripts/update_manager.py`:

1. Získa existujúci `.git/sema-update.lock`; recovery používa rovnaký zámok.
2. Dokončí prípadný prerušený návrat. Pred novým update vyžaduje zdravú starú
   aplikáciu; už nefunkčná verzia nie je považovaná za bezpečný návratový bod.
3. Vyžaduje funkčnú nezávislú recovery službu/timer mimo checkoutu. Jej
   jednorazová inštalácia používa existujúce sudo systemctl a dočasnú runtime
   root unit, podobne ako watchdog. Git vždy beží pod janom. Bundle pochádza
   z presného aktuálneho Git commitu, nie necommitnutého worktree.
4. Stiahne iba main/testing. Rovnaké SHA = bez zastavenia aplikácie, novej
   zálohy či resetu. Predtým zlyhaný SHA je blokovaný; nový SHA sa môže skúsiť.
5. Odmietne balík s .env, DB, venv alebo node_modules a overí miestne dáta.
6. **Pred zastavením/resetom** atómovo rezervuje transakciu s predchádzajúcim
   SHA. Zastaví aplikáciu a vytvorí konzistentnú SQLite zálohu a súkromnú
   kópiu .env. Kontroluje voľné miesto (aspoň 64 MB alebo dvojnásobok DB).
7. Prepne kód, spustí aplikáciu a čaká na zdravý backend, HTML cez nginx a
   skutočný JS asset. Vyžaduje tri po sebe idúce zdravé kontroly, odstup 2 s,
   rozbeh približne do 90 s (jednotlivé sondy/príkazy majú vlastné timeouty).
8. Pri úspechu potvrdí commit. Až potom volá voliteľnú migráciu watchdogu;
   jej samostatne ošetrené zlyhanie nevracia zdravú aplikáciu.
9. Pri neúspechu zastaví chybnú aplikáciu, vráti pôvodný Git commit a overí
   jeho štart rovnakými sondami. Update skončí neúspešne s jasným záznamom
   `rollback_succeeded`, nie ako úspešné nainštalovanie novej verzie.

Nemení kanál, neinštaluje Python balíky, nesiaha na čerpadlo, sieť, sudoers
ani neriadi reboot RPi. Root watchdog ostáva samostatná infraštruktúra;
app rollback ho nevracia. Jeho inštalátor má vlastný rollback.

## Prerušený proces a boot

Root-owned `/usr/local/lib/sema-update/update_manager.py` a systémová
`sema-update-recovery.service` (User=jan) nie sú súčasťou meneného checkoutu.
Timer kontroluje pending transakciu po boote približne od 30 s a potom po
60 s neaktivity služby. Pri boote je služba zoradená za network-online.target,
ktorý už používa sema.service, aby štart starej aplikácie nepredbiehal prípravu
lokálnej siete. Recovery nevyžaduje GitHub ani fungujúci internet.

Bez pending transakcie sa nevykonáva kontrola HTTP, Git, záloha ani reštart.
Pri živom updateri je zámok obsadený a recovery nezasahuje. Po SIGKILL,
prerušení SSH alebo výpadku napájania ostáva rezervácia a ochrana vie obnoviť
starý commit, aj keď kandidát pokazil svoj update.sh/update_manager.py.
Pending stav sa kontroluje aj pred ďalším ručným/nočným update.

Najviac tri rozbehnuté pokusy rollbacku na transakciu; neúspech sa označí
`rollback_failed` a vyžaduje človeka. Nevyvoláva slučku reštartov. Ručne
vypnutý recovery timer sa automaticky nezapína; nový update sa bezpečne odmietne.
Chýbajúce oprávnenia, poškodená recovery metadáta alebo chýbajúci helper rovnako
blokujú zmenu aplikácie. --check sám guard neinštaluje ani neoveruje zdravie API.

## Dáta a hranice záruky

**Automatický návrat mení kód, nie aktuálnu databázu ani konfiguráciu.** Nové
merania či používateľské zmeny počas skúšobného behu zostanú. Staré DB/env
snímky sú pre odôvodnenú ručnú obnovu, nie automatické prepisovanie novších dát.
Najviac tri transakčné zálohy, priečinky 0700 a citlivé súbory 0600.

Úložisko stavu: `/home/jan/.local/state/sema-update/transaction.json`, zálohy
v `backups/<transaction-id>/`. Atómový zápis + fsync. Súbor obsahuje iba SHA,
fázu/čas a blokované commity (najviac 20), nie tokeny alebo .env hodnoty.

Rollback predpokladá **spätne kompatibilné/prídavné DB migrácie**. Destruktívna
migrácia môže znemožniť štart starého kódu a automatický návrat to z dátovej
straty nezachráni; taký release musí mať samostatný migračný/návratový postup.
Rovnako nejde o ochranu pred nefunkčným diskom, zničenou SD alebo ľubovoľnou
logickou chybou, ktorú zdravé API/HTML/asset neodhaľujú. Po prijatí verzie
sa už nevykonáva neobmedzený dlhodobý aplikačný rollback podľa týchto sond.

Pri rollback_failed najprv zachovať transaction.json a zálohy, skontrolovať
journal a dôvod. Poškodený stav ani DB nemaž naslepo. Neobnovovať starú DB
bez posúdenia novších meraní a účtov. Recovery služba používa existujúce
oprávnenia jan → systemctl; nezavádza nové všeobecné sudo oprávnenie.

## Obsluha po budúcom nasadení

```bash
/home/jan/sema/scripts/update.sh --check
/home/jan/sema/scripts/update.sh
# Výslovný opakovaný pokus rovnakého odmietnutého release:
/home/jan/sema/scripts/update.sh --retry-failed
journalctl -u sema-update -u sema-update-recovery --no-pager
```

--retry-failed neobchádza zdravotné kontroly, zámky ani nefunkčný návratový
stav. Zdroj pravdy je SHA; rovnaké číslo verzie môže znamenať iný commit.

## Zavedenie na existujúce jednotky

Prvý update vykonaný ešte starým 1.4.2 updaterom nie je spätne chránený.
Preto adopčný release najprv otestovať na sema-001 a nepribaliť deštruktívne
migrácie alebo nové závislosti. Ďalšie spustenie nového update.sh nainštaluje
nezávislý guard aj keď už nie je nový commit; až potom sú ďalšie pokusy chránené.
Nespoliehať sa na pokračovanie prepisovaného Bash súboru pri prvom prenose.
Zariadenie bez nového managera odmietne nový wrapper pred fetch/reset.

Až na samostatný pokyn: testing release → 001, overiť root service/timer,
bežný a nezmenený update, kontrolovaný chybný kandidát so záložným prístupom,
prerušovaný proces aj ďalší boot. Až potom povýšiť presný release do main.
Päťminútové kontroly/centrálny rollout zostávajú ďalšia etapa.

## Lokálne overenie

- 27 testov managera, vrátane reálneho lokálneho Git/SQLite, rollbacku so
  zachovaním nových meraní, SIGKILL procesu a obnovy z oddelenej kópie,
  karantény SHA, zámku, retencie, ochrany lokálnych dát a root bridge/installeru.
- 38 testov watchdogu vrátane DERP a preferencie portálu.
- 31 testov event spoolu/watchdog rollout/installer a 12 release/wrapper testov.
- Bash syntax, Python syntax a systemd verify nových jednotiek prešli.

Služby/systemctl sú v testoch nahradené; nejde o dôkaz skutočnej boot obnovy
na RPi. Živé jednotky, produkčný portál ani GitHub sa v tejto etape nemenili.
