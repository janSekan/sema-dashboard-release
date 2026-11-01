# Spoločná práca: VS Code a Codex Cloud

Stav: 31. 10. 2026. Tento návod je v oboch zdrojových repozitároch. Pri zmene spoločného workflow aktualizovať obe kópie. Detaily projektu sú v README, AGENTS.md a docs/PROJECT_STATUS.md daného repozitára.

## Repozitáre a vetvy

| GitHub repozitár | Účel | Vetvy |
| --- | --- | --- |
| janSekan/sema-portal | Zdrojový centrálny portál | development: spoločná rozpracovaná verzia; main: stabilný základ |
| janSekan/sema | Zdrojový dashboard jednotky | development: spoločná rozpracovaná verzia; main: stabilný základ |
| janSekan/sema-dashboard-release | Distribučný backend a zostavený frontend pre Raspberry Pi | testing: iba sema-001; main: zákaznícke zariadenia |

**development v zdrojovom repozitári nie je testing kanál zariadenia.** Push do zdrojov sám nenasadzuje portál ani nevydáva release pre jednotky. Nezamieňať tri rôzne repozitáre ani ich main vetvy. Bootstrap OS je štvrtý samostatný projekt sema-bootstrap; zmeny v ňom sa týmto workflow automaticky neprenášajú.

Pri zavedení development sa preniesli všetky aktuálne lokálne commity. Vzdialené main vetvy zostali na doterajšom stave. Lokálny main môže ešte obsahovať pôvodné nepushnuté commity; nepushovať ho naslepo a nepoužívať reset --hard. Ďalší vývoj začína na development.

## Prechod z jedného prostredia do druhého

Na začiatku skontrolovať správny repozitár a čistotu:

```bash
git remote -v
git status --short
git fetch origin
git switch development
git pull --ff-only origin development
```

Pri prvom checkoute, ak lokálna vetva neexistuje, namiesto switch použiť:

```bash
git switch --track origin/development
```

Ak origin/development ešte nevidno, overiť správny remote, prístup a obmedzený/shallow checkout; načítať vetvu podľa konfigurácie prostredia. Nestrácať existujúcu prácu pri prepínaní. Ak pull --ff-only zlyhá, prezrieť rozdiely a vyriešiť integráciu; nepoužiť force push ani reset na odstránenie cudzej práce.

Pri odovzdaní dokončiť zmysluplný celok, overiť dotknuté časti, commitnúť explicitné súbory a pushnúť development. Do správy uviesť repo, vetvu, SHA, výsledok testov, čo ostáva a čo bolo skutočne nasadené. Aktualizovať PROJECT_STATUS/TASKS pri zmene stavu. Commit iba v lokálnom cloude ani iba vo VS Code ešte nesprístupní zmeny druhej strane.

## Súbežná práca

Striedanie prostredí môže používať priamo development. Pri súbežných úlohách vytvoriť z aktuálnej development samostatné vetvy, napr. codex/history-charts alebo feature/customer-export. Každá úloha má vlastnú vetvu a ideálne vlastný checkout/worktree. Výsledok pushnúť, skontrolovať a zlúčiť PR do development. Base PR je development, nie predvolene main. Nespúšťať dve nezávislé úlohy zapisujúce do tej istej vetvy/checkoutu.

## Codex Cloud

Nastaviť zdrojový repozitár a development ako východiskovú vetvu, ak to prostredie umožňuje. V existujúcej publikovanej úlohe vždy overiť git branch, git log a dostupný origin/development: publikovanie prostredia samo osebe nepotvrdzuje, že obsahuje posledný push. Podľa možností prostredia načítať aktuálnu vetvu; pri zmene uloženého štartovacieho nastavenia znovu publikovať prostredie.

Úvodné zadanie novej úlohy:

> Pracuj v [sema alebo sema-portal]. Prečítaj AGENTS.md, README.md, docs/PROJECT_STATUS.md a docs/DEVELOPMENT_WORKFLOW.md. Over aktuálny origin/development a stav pracovného adresára. Produkciu a release repozitár nemeň. Úloha: ...

Lokálne absolútne cesty v README sú príklady z Janovho počítača; v cloude použiť skutočný koreň checkoutu. Oba projekty štandardne používajú porty 8000/5173; spustiť ich oddelene alebo zosúladiť porty, proxy a URL.

.env, naplnené SQLite DB, zálohy, SSH kľúče, tokeny, heslá, node_modules ani virtuálne prostredia neprenášať cez Git. Cloud používa vlastnú testovaciu konfiguráciu a DB; tajomstvá iba v určenej konfigurácii prostredia. Prístup cez domáci Tailscale/SSH a bežiace lokálne procesy nie sú súčasťou zdrojového checkoutu. Bez overeného pripojenia netvrdiť, že živé zariadenie bolo otestované.

## Stabilizácia a vydanie

Po kontrole a testoch možno samostatne schváliť zlúčenie development do zdrojového main. To je iný krok než produkčné nasadenie. Dashboard: build/publikovanie iba cez dokumentovaný release workflow, najprv testing, overenie na sema-001 a až potom povýšenie presného otestovaného release SHA do release/main. Portál: samostatné nasadenie, záloha DB/env, migrácie a kontrola služby podľa PRODUCTION_DEPLOYMENT.md v portáli. Aktuálne oprávnenie na commit/push vývoja samo osebe nie je pokyn na nasadenie.
