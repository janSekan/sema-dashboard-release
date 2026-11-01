# Zber histórie a sťahovanie zo zariadení

Stav po nasadení 31. 10. 2026: portálový runtime `409749f` je v produkcii so schémou 7. Dashboard release/main aj testing sú `1541979` (1.2.0-testing.1), overený na sema-001. Ostatné jednotky získajú release pri svojom automatickom update. Interaktívne grafy a retencia ostávajú ďalšou etapou.

## Predvolené frekvencie

| Činnosť | Predvolene | Poznámka |
| --- | --- | --- |
| Pozorovanie čerpadla | 15 sekúnd | Čítanie status.xml, temperatures.xml a control.xml; samotné čítanie nezapisuje meranie do SQLite. |
| Historické meranie | 5 minút | Deväť teplôt, percentá výkonu, stavy a všetky načítané XML polia. |
| Bežné udalosti | Pri zistenej zmene, do RAM | Zapnutie/vypnutie, zmena režimu, TÚV, odmrazovanie, stupeň kompresora/bivalentu, útlm, tarifa a ďalšie nekmitajúce stavové polia. |
| Zápis dávky na zariadení | 5 minút | Merania a udalosti v jednej transakcii, aj pri normálnom ukončení služby. |
| Chyba alebo dostupnosť XML | Hneď po zistenej zmene | Vznik aj zánik chyby a výpadok/obnova komunikácie vyvolajú skorší zápis celej čakajúcej dávky. |
| Prenos histórie do portálu | 1 hodina | Nastaviteľné aj na 7200/10800 sekúnd. Stabilné časové sloty podľa ID rozložia jednotky v rámci intervalu. |
| Ručné stiahnutie | Na požiadanie | Front pre konkrétne zariadenie; opakované požiadavky sa zlučujú, minimálne 60 s od posledného pokusu. |

Bežný päťminútový rytmus je približne 288 intervalov denne; **nejde o záruku 288 fyzických zápisov na kartu**. SQLite zapisuje stránky, WAL a checkpointy; zapisujú aj ostatné časti OS. Chyby, plný buffer, ukončenie služby a ručný prenos môžu vyvolať ďalšie transakcie. Presnú životnosť karty z tohto intervalu nemožno určiť.

Na zariadení zostáva WAL a `synchronous=FULL`; bezpečnosť DB sa neznižuje cez `OFF`/vypnutý journaling. Znižujeme frekvenciu transakcií zoskupovaním, nie vynechaním synchronizácie. Kontext: [SQLite WAL](https://www.sqlite.org/wal.html), [synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous).

## Čo sa zbiera

Zachovávajú sa existujúce stĺpce `ot,it,wt,ht,ext,eqt,et,ft,gt,pr`. Nové merania navyše obsahujú `state_json` a `raw_json` z troch uvedených XML odpovedí. Pôvodné riadky ostávajú zachované, doplnené polia majú NULL. Prázdne/neplatné hodnoty nového zberu sú NULL, nie vymyslená nula. Každý XML zdroj má samostatný príznak dostupnosti.

`telemetry_events` zaznamenáva začiatok pozorovania a zmeny stavov s časom UTC, úrovňou, kódom, pôvodnou/novou hodnotou, kontextom stavov a percentami výkonu pri udalosti. Percentá sa pravidelne ukladajú päťminútovo; nejde o presnú sekundovú krivku každého pohybu výkonu.

- `status.st1`: kúrenie/chladenie/vypnuté/odmrazovanie/všeobecná chyba.
- `status.st2`: kompresor, bivalent 1/2 alebo letný režim podľa existujúceho mapovania.
- `status.st3`: ohrev TÚV, elektrický ohrev TÚV alebo pokojový stav.
- `status.st4/st5`: útlm a vysoká tarifa.
- `control.st1/st2/st3`: povolenie prevádzky, nastavený režim a sezóna.
- Ďalšie polia sa zachovajú bez domýšľania ich významu. Dynamické teploty, percentá a hodiny nespúšťajú novú udalosť pri každom čítaní.

Pomocný príznak `heating` vychádza z režimu kúrenia, neprítomnosti ohrevu TÚV a nenulového percenta výkonu. **Nie je to samostatné potvrdenie fyzického kontaktu relé/kompresora.** Uchovávajú sa aj pôvodné kódy, aby graf vedel ukázať, z čoho bol stav odvodený.

Aktuálne overené XML neposkytlo podrobný chybový text/kód. Preto sa neinventujú konkrétne poruchy: zaznamenáva sa všeobecný stav `st1=5`, jeho zánik, dostupnosť odpovedí a všetky skutočne poskytnuté polia. Pri začiatku zberu sa už aktívna chyba uloží okamžite, ale nepredstiera sa známy začiatok jej trvania. Pri výpadku komunikácie sa posledný známy režim neprepne na vypnutý.

Čas udalosti je čas jej pozorovania, nie presný čas zopnutia v regulátore. Stav kratší než interval čítania môže uniknúť medzi dvoma pozorovaniami.

Pri výpadku napájania môžu chýbať bežné udalosti čakajúce v RAM od posledného zápisu, typicky do 5 minút pri zdravom úložisku. Aj kritická udalosť sa môže stratiť, ak napájanie vypadne pred zistením/úspešným commitom. Pri zaplnení úložiska sa buffer nevymazáva; po dosiahnutí limitu sa ďalšie pozorovanie pozastaví a skúša sa uloženie. Vzniknutá medzera sa nesmie v grafe interpretovať ako súvislá potvrdená prevádzka. SQLite operácie a HTTP čítanie neblokujú ASGI event loop.

## Konfigurácia zariadenia

Premenné `.env` (nemení ich webový formulár):

```dotenv
TELEMETRY_POLL_SECONDS=15
TELEMETRY_SAMPLE_SECONDS=300
TELEMETRY_FLUSH_SECONDS=300
```

Minimá sú 5/60/30 sekúnd; neplatné hodnoty použijú predvolené nastavenie. Na produkčnom zariadení beží jeden backendový proces a jeden zberač. Pri viacerých Uvicorn workeroch by sa zberač spustil viackrát; takú konfiguráciu nepoužiť bez oddelenia zberača do samostatnej služby.

Lokálna migrácia zariadenia je prídavná: nové JSON stĺpce, tabuľka udalostí a jedinečná identita zdrojovej DB v `app_settings`. Reštart identitu nemení, nová čistá DB dostane inú. Nekopírovať naplnenú telemetrickú DB/jej identitu pri príprave továrenského image.

## Konfigurácia a škálovanie portálu

```dotenv
TELEMETRY_SYNC_SECONDS=3600
# Alebo 7200 / 10800. Minimum je hodina.
TELEMETRY_AUTO_SYNC=true
```

V produkcii je automatické sťahovanie predvolene zapnuté, vo vývoji vypnuté. Worker aj vo vývoji spracuje výslovne zaradené ručné požiadavky. Nezapínať vývojovú automatiku nad zákazníckymi záznamami bez zámeru ich synchronizovať.

Worker obsluhuje najviac tri zariadenia naraz, uprednostní ručné požiadavky a každé zariadenie má DB lease proti súbežnému prenosu. Po neúspechu automatika opakuje pokus najskôr za päť minút. Prvý automatický prenos môže čakať na pridelený slot až celý interval. Jeden beh prenáša najviac 10 strán po 500 riadkov na každý stream; nedokončená zásoba sa znovu zaradí. Prenos má limit 240 sekúnd, HTTP timeouty a limit 4 MiB na rozbalenú odpoveď; priveľká dávka sa odmietne bez posunutia kurzora. Časové sloty, kurzory a stav sú nezávislé od otvorenia grafu.

Predpoklad súbehu tri platí pre **jeden workerový proces**. Aktuálny portál používa jeden Uvicorn worker. Pri škálovaní webu treba automatický worker oddeliť alebo koordinovať globálny limit. Test s frontom 300 simulovaných zariadení overuje limit súbehu a ukončenie úloh; nie je to záťažový test produkčného servera ani záruka kapacity SQLite/úložiska pri mnohoročnej histórii.

Kontrola dostupnosti je samostatná: existujúci heartbeat ostáva každých 15 sekúnd. Pre 300 zariadení je to priemerne približne 20 malých požiadaviek za sekundu. Hodinová história túto existujúcu prevádzku neodstraňuje; ide o dva nezávislé účely. Interval heartbeat sa nemenil, aby ostal zosúladený s 45-sekundovým zobrazením online stavu.

## Portálové UI a protokol

**Zariadenia → detail → História → Stiahnuť dáta** zaradí konkrétnu jednotku do frontu, ukáže úspech/chybu, posledný úspešný prenos a počty uložených meraní/udalostí. Tlačidlo nemení nastavenia čerpadla. Podrobný graf a jeho filtre ostávajú ďalšou etapou.

Admin/superadmin:

- `GET /api/admin/devices/{id}/telemetry-sync`
- `POST /api/admin/devices/{id}/telemetry-sync` → 202, nie blokujúci hromadný prenos.

Interné zariadenie, všetko chránené existujúcim `X-SEMA-Proxy-Token`:

- `GET /device-api/sync/status`: identita, stav všeobecnej chyby, dostupnosť čerpadla a čas posledného pozorovania.
- `GET /device-api/sync/metadata`: verzia protokolu 2 a identita zdrojovej DB.
- `POST /device-api/sync/flush`: uloží čakajúci RAM buffer aj posledný pozorovaný bod, ak ešte nebol zaradený. Aktuálny bod je typicky najviac 15 sekúnd starý, pri výpadku môže byť starší (čas/príznak dostupnosti to odlišuje). Neovláda čerpadlo.
- `GET /device-api/sync/measurements?after_id=…&limit=…`
- `GET /device-api/sync/events?after_id=…&limit=…`

Portál pred prenosom overí `device_id`, pri každej novej dávke aj zdrojovú DB. Dávku validuje celú a v jednej transakcii uloží dáta aj kurzor streamu. Unikátne indexy chránia `(device,source_db_id,source_id)`. Pri chybe neskoršej dávky ostávajú predchádzajúce commitnuté dávky a opakovanie neduplikuje dáta. Merania a udalosti majú oddelené kurzory. `sync_batches` uchováva audit pokusov; posledný stav a čakajúce požiadavky majú samostatné tabuľky.

Starý dashboard bez metadata/events endpointov naďalej poskytuje merania cez starý protokol; UI upozorní na chýbajúcu históriu udalostí. Pri upgrade sa identické staršie merania z legacy generácie prepoja iba pri zhode ID, času a všetkých číselných údajov. Odlišné merania sa neprepisujú. Staré zariadenie bez identity DB nedokáže spoľahlivo rozlíšiť reset svojej DB; nová verzia toto rieši identitou generácie.

## Uchovávanie a nasadenie

Zatiaľ sa história automaticky nemaže, nepredstierame hotovú retenčnú politiku. Pred dlhodobou prevádzkou stoviek jednotiek treba dohodnúť uchovávanie surových XML/udalostí a agregácie starších teplôt. Základné merania sú 288 denne na zariadenie, približne 31,5 milióna za rok pre 300 jednotiek; raw JSON a udalosti zvyšujú objem. Mazanie na zariadení sa nesmie zaviesť bez potvrdenia úspešného prenosu a dohodnutej rezervy pri výpadku.

Lokálne zálohy pred prídavnými migráciami, s právami 600:

- portál: `/tmp/sema-portal-before-telemetry-2kiaozu3.db`, schéma 7,
- vývojový dashboard: `/tmp/sema-device-before-telemetry-e78oapqe.db`.

Overené zachovanie pôvodných riadkov, opakované migrácie a `foreign_key_check`. Pred produkciou vytvoriť novú trvalú zálohu aktuálnych DB; tieto /tmp sú iba lokálne.

Aktualizované bolo iba testovacie sema-001; produkčný portál a zákaznícke jednotky sa neaktualizovali. Nové stavy sa začnú zbierať až po vydaní/nasadení nového dashboardu; staršie udalosti spätne nevzniknú. Najprv overiť release na sema-001, potom publikovať produkciu podľa existujúceho kanálového workflow.


## Záverečné testy

Overené: 49 existujúcich + 11 portálových telemetrických testov, 8 release + 8 zariadenových telemetrických testov; spolu 76. Frontend build oboch projektov a ESLint upravených komponentov prešli. Pri dashboard builde zostáva pôvodné upozornenie optimalizátora CSS na `@property --radialprogress`.

Koncová kontrola použila reálne nové dashboard API, lokálne HTTP a samostatnú portálovú DB: tokenové oprávnenie, merania/udalosti, generáciu zdroja, flush, opakovaný prenos bez duplicít a audit dávok. Prehliadačová kontrola overila nový tab História, zaradenie ručnej požiadavky a následné zobrazenie výsledku/počtov na mobilnej šírke. Produkčné jednotky sa pri týchto testoch nepoužili.


### Oprava ručného stiahnutia

Pri reálnej session vracia autentifikácia `sqlite3.Row`, nie dict. Endpoint používa
`user['id']`; predchádzajúce `.get('id')` spôsobovalo HTTP 500 ešte pred zaradením
požiadavky. Regresný test používa reálnu session cookie a databázový riadok.
Skutočné stiahnutie sema-001 cez lokálny portál potom vrátilo 202 a prvá dávka
uložila 5 000 meraní a jednu udalosť. Počas prvého historického importu sa ďalšie
dávky radia automaticky, preto môže tlačidlo zobraziť čakanie až do dobehnutia zásoby.
