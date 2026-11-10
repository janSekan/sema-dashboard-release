# SEMA Dashboard – používateľský návod

Verzia návodu: 10. 11. 2026. Opisuje lokálne pripravené správanie s rolou
**Superuser**, **Supervízor** a bez sekcie Účty v dashboarde. Tieto zmeny ešte neboli nasadené;
na starších zariadeniach sa ponuka a oprávnenia môžu líšiť.

## 1. Čo ovládate

SEMA Dashboard je rozhranie konkrétneho tepelného čerpadla. SEMA Portal zabezpečuje
prihlásenie, priradenie zariadenia a administratívnu správu. Zmena hodnôt na
dashboarde môže skutočne zmeniť chod čerpadla. Samotné otvorenie stránky alebo
zmena hodnoty v editore ešte neznamenajú uloženie: používajte príslušné tlačidlo
Uložiť. Výnimkou sú hlavné prepínače Zapnuté/Vypnuté, Leto/Zima a Kúrenie/Chladenie,
ktoré posielajú požiadavku hneď po prepnutí.

## 2. Prihlásenie, účet a odhlásenie

1. Otvorte prihlasovaciu stránku SEMA Portalu a zadajte pridelený e-mail a heslo.
2. Používateľ aj Superuser sú po prihlásení presmerovaní na dashboard priradeného
   zariadenia. Nie sú oprávnení vstupovať do administrácie portálu.
3. Ak zariadenie nie je dostupné, zobrazí sa stránka nedostupnosti. Používateľ
   a Superuser sa môžu odhlásiť. Správca môže preveriť pripojenie zariadenia.
4. Prácu ukončite odhlásením, najmä na zdieľanom počítači.

Bez „Zapamätať si ma“ trvá portálová session 8 hodín. Pri zapamätanom prihlásení
sa obnovuje pri platných požiadavkách a zanikne po 30 dňoch bez aktivity. Otvorená
stránka môže požiadavky vykonávať automaticky.

**Mená, heslá a roly portálových účtov spravuje administrátor v portáli.**
V dashboarde už nie je sekcia Účty a jej pôvodné API neumožňuje údaje meniť.
Zmena hesla portálového účtu sama osebe nesynchronizuje heslo lokálneho záložného
účtu na Raspberry Pi. Existujúce lokálne účty zostávajú zachované pre priamy
prístup, keď je povolený a dostupný; ich obnovu rieši poverený správca servisným
postupom. Nová rola nezakladá na zariadení žiadny účet s predvoleným heslom.

## 3. Rozdiely medzi rolami

| Funkcia dashboardu | Používateľ | Superuser | Supervízor | Admin / superadmin |
| --- | --- | --- | --- | --- |
| Zobrazenie meraní a bežné ovládanie | Áno | Áno | Áno | Áno |
| Nastavenie hlavnej teploty, teplotných limitov a útlmu | Áno | Áno | Áno | Áno |
| Vykurovacia krivka a technické parametre v sekcii Iné | Nie | Áno | Áno | Áno |
| Koeficient posunu krivky a Uložiť referenciu | Nie | Áno | Áno | Áno |
| Zmena sieťovej konfigurácie pri bežnej prevádzke | Nie | Nie | Áno | Áno |
| Správa Home Assistant integrácie | Nie | Nie | Áno | Áno |
| Pôvodné rozhranie čerpadla | Nie | Nie | Áno | Áno |
| Portál | Nie | Nie | Iba čítanie | Správa |
| Zmena prihlasovacích údajov priamo v dashboarde | Nie | Nie | Nie | Nie |

Superuser je rozšírený používateľ vlastného priradeného zariadenia. Nezískava
prístup k cudzím zariadeniam, zákazníkom, účtom ani servisným akciám portálu.
Reštart dashboardu, reštart Raspberry Pi a aktualizácia zostávajú adminovi/superadminovi.
Rozdiel medzi adminom a superadminom v portáli, napríklad záložka Oživenie,
sa zavedením Superusera nemení.

## 4. Prehľad meraní

Na úvodnej obrazovke sú vonkajšia a vnútorná teplota, teplota TÚV, teplota kúrenia
a aktuálna žiadaná teplota kúrenia. Posledná hodnota je požiadavka regulátora
na vykurovaciu vodu; nie je to požadovaná teplota miestnosti. Krátke grafy
zobrazujú posledné dostupné merania. Karta Systém dopĺňa prevádzkový stav a výkon.

Hodnoty meraní nemusia reagovať okamžite po zmene nastavenia. Rozlišujte medzi
uloženým nastavením, požiadavkou regulátora a skutočne nameranou teplotou.
Pri nedostupnom čerpadle neposudzujte jeho aktuálny chod iba podľa staršieho grafu.

## 5. Základné prevádzkové prepínače

- **Zapnuté / Vypnuté:** požiadavka na zapnutie alebo vypnutie čerpadla.
- **Leto / Zima:** voľba prevádzkového obdobia. V letnom režime sa karta hlavnej
  vykurovacej teploty a vykurovacej krivky nezobrazujú.
- **Kúrenie / Chladenie:** v zimnom režime je dostupné iba kúrenie; v letnom
  režime ovládanie ponúka povolenie alebo vypnutie chladenia podľa stavu čerpadla.

Po prepnutí počkajte na dokončenie načítavania a obnovenie stavu, bežne približne
10 sekúnd. Pri chybe neposielajte opakovane protichodné príkazy; najskôr obnovte
zobrazenie a skontrolujte skutočný stav. Samotná HTTP požiadavka nie je nezávislým
potvrdením fyzického zopnutia čerpadla.

## 6. Nastavenia dostupné každému používateľovi

### Hlavná teplota

1. V zimnom režime otvorte Nastavenia a kartu Teplota.
2. Tlačidlami − a + upravte hodnotu po 0,5 °C.
3. Stlačte **Uložiť** a počkajte na dokončenie.

Táto funkcia posúva vykurovaciu krivku oproti predchádzajúcej uloženej hodnote.
Veľkosť posunu závisí od koeficientu nastaveného technikom alebo Superuserom.
Nie je to záruka, že zmena hodnoty o 1 °C zvýši skutočnú teplotu miestnosti
presne o 1 °C. Reakcia závisí od vykurovacej sústavy a budovy.

### Teplotné limity

V sekcii Vnútorná teplota sa nastavuje minimálna teplota pre chladenie a maximálna
pre kúrenie. V sekcii Ohrev vody (TÚV) sú minimálna a maximálna teplota vody.
Ovládacie prvky uvádzajú rozsahy:

| Nastavenie | Rozsah editora |
| --- | --- |
| Minimálna vnútorná teplota – chladenie | 16–30 °C |
| Maximálna vnútorná teplota – kúrenie | 21–30 °C |
| Minimálna teplota TÚV | 0–60 °C |
| Maximálna teplota TÚV | 0–60 °C |

Úpravy týchto sekcií potvrďte spodným tlačidlom **Uložiť nastavenia**. Menšie
a vyššie limity nastavujte vo vzájomne zmysluplnom poradí podľa odporúčania
inštalatéra a dokumentácie konkrétneho čerpadla. Označenie rozsahu v editore
nenahrádza prevádzkové obmedzenia výrobcu.

## 7. Vykurovacia krivka – Superuser

Krivka určuje požiadavku na vykurovaciu vodu podľa vonkajšej teploty. Editor má
šesť bodov pre vonkajšie teploty **−20, −12, −4, +4, +12 a +20 °C**. Hodnota pri
každom bode je teplota vykurovacej vody, nie teplota miestnosti.

1. Pred zmenou si zaznamenajte pôvodných šesť hodnôt.
2. Ak je chladno iba pri nízkych vonkajších teplotách, zvažujte príslušnú časť
   krivky s inštalatérom; celoplošný posun mení všetky body naraz.
3. Upravte hodnoty po primeraných krokoch; editor používa krok 0,5 °C.
4. Stlačte **Uložiť nastavenia**. Sledujte výsledok za porovnateľných podmienok
   a dajte budove čas reagovať. Nemeňte naraz viac nesúvisiacich parametrov.

Spôsob interpolácie medzi bodmi a ochranné limity určuje regulátor čerpadla.
SEMA nenahrádza jeho výrobcom stanovené pravidlá.

## 8. Koeficient posunu krivky – Superuser

Predvolený koeficient je **1,0**, minimálny **0,1**, nastaviteľný po **0,1**.
Platí pre zmeny hlavnej teploty vykonané všetkými používateľmi zariadenia.

**Posun krivky = (nová hlavná teplota − predchádzajúca uložená teplota) × koeficient.**

| Zmena hlavnej teploty | Koeficient | Vypočítaný posun všetkých bodov |
| --- | --- | --- |
| 22 → 23 °C | 1,0 | +1 °C |
| 22 → 23 °C | 2,0 | +2 °C |
| 22 → 22,5 °C | 2,0 | +1 °C |
| 23 → 22 °C | 2,0 | −2 °C |

Do poľa zadajte hodnotu a stlačte **Uložiť koeficient**. Toto tlačidlo uloží
iba koeficient: existujúcu krivku ani hlavnú teplotu neposunie. Až ďalšie
uloženie zmenenej hlavnej teploty použije nový násobok. Neuložená úprava poľa
koeficientu sa pri použití tlačidla Uložiť hlavnej teploty automaticky nepreberá.

Regulátor prijíma body po 0,5 °C. Vypočítaný posun sa zaokrúhli na tento krok;
malý zvyšok sa uchová do ďalšej zmeny. Preto veľmi malá zmena nemusí krivku
posunúť okamžite. Uloženie nového koeficientu začína nový výpočet bez starého
zlomkového zvyšku. Koeficient zostáva uložený aj po reštarte a aktualizácii.

## 9. Uložiť referenciu – Superuser

**Uložiť referenciu neposúva vykurovaciu krivku.** Mení iba východiskovú hodnotu
hlavnej teploty, voči ktorej sa vypočíta ďalší posun. Zároveň vynuluje zlomkový zvyšok.

Príklad: krivka je vhodne nastavená, ale hlavná teplota ukazuje 22 °C a chcete
ju používať s referenciou 20 °C. Nastavte kartu na 20 °C a stlačte **Uložiť
referenciu**. Body zostanú rovnaké. Ak potom zmeníte 20 → 21 °C a stlačíte
obyčajné **Uložiť**, krivka sa posunie podľa koeficientu.

Referenciu nepoužívajte namiesto bežného zvýšenia teploty: sama osebe nezvýši
požiadavku na vykurovaciu vodu. Ak meníte priamo body krivky, zvážte s technikom,
či treba nanovo stanoviť aj referenciu a koeficient.

## 10. Sekcia Iné – Superuser

| Parameter | Jednotka / význam v rozhraní |
| --- | --- |
| Obmedzenie výkonu ohrev TÚV | % – limit výkonu pre ohrev vody |
| Obmedzenie výkonu kúrenie | % – limit výkonu pri kúrení |
| Obmedzenie výkonu chladenie | % – limit výkonu pri chladení |
| Teplota chladiacej vody | °C – nastavenie chladiacej vody |
| Bivalentná teplota | °C – parameter bivalentného režimu regulátora |
| Časové obmedzenie ohrevu TÚV | min – časový parameter ohrevu vody |
| Regulačná konštanta | bez jednotky – parameter regulácie |

Zmeny sa posielajú cez **Uložiť nastavenia**. Význam hraničných hodnôt, napríklad
0 min alebo 0 %, ani presný regulačný algoritmus neodvodzujte len z názvu poľa.
Pri bivalentnej teplote a regulačnej konštante postupujte podľa konkrétnej
regulácie a odporúčania inštalatéra. Univerzálne odporúčané čísla tento návod neurčuje.

## 11. Teplotný útlm

V menu otvorte stránku teplotného útlmu, zvoľte deň a pridajte intervaly Od–Do.
Na jeden deň možno uložiť najviac štyri intervaly. Časy editor ponúka po
10 minútach, koniec dňa môže byť 24:00. Intervaly sa nesmú prekrývať a koniec
musí byť neskôr než začiatok. Nastavte požadovaný útlm kúrenia a potvrďte uloženie.
Skontrolujte správny čas regulátora, v ktorom sa plán vykonáva. Po úprave obnovte
stránku a overte, čo sa skutočne načítalo zo zariadenia.

## 12. Čo robiť pri probléme

- **Uloženie nastavení zlyhalo:** zmena nie je potvrdená. Formulár zostáva upravený;
  skontrolujte spojenie a oprávnenie. Pri chybe sieťových nastavení môže byť časť
  požiadavky už uložená, čo hlásenie výslovne uvedie.
- **Hodnota sa po obnovení vrátila:** porovnajte ju s tým, čo prijal regulátor;
  samotná hodnota ponechaná v editore nie je potvrdenie zápisu.
- **Chýba technická sekcia:** skontrolujte rolu účtu a verziu dashboardu. Superuser
  na starom dashboarde ešte nemusí mať novú ponuku. Oprávnenie prideľuje správca.
- **Nedostupné zariadenie:** overte pripojenie alebo kontaktujte správcu. Bežný
  používateľ ani Superuser nemajú servisné tlačidlá na reštart alebo update.
- **Zabudnuté heslo:** obráťte sa na administrátora portálu. Účty na zariadení
  sa cez dashboard neupravujú.

Pri hlásení problému uveďte ID SEMA, čas, obrazovku a zobrazené hlásenie. Heslá
ani prístupové tokeny do správy neprikladajte.

## 13. Pokyny pre administrátora portálu

V menu **Používatelia** otvorte existujúci účet alebo Pridať používateľa.
V poli Rola vyberte **Superuser**, uložte a overte jeho priradenie k zariadeniu.
Zmena roly sama nepriradí nové zariadenie ani nezmení zákazníka či inštaláciu.
Superuser je dostupný aj vo filtri a v radení zoznamu používateľov.

Používateľ sa po prihlásení dostane do dashboardu priradeného zariadenia.
Ak má pridelených viac zariadení, súčasný vstupný mechanizmus otvára prvé aktívne
priradené zariadenie; táto zmena nepridáva používateľský výber zariadení.
Pri návrate zo Superusera na Používateľa sa technické oprávnenia odoberú.
Prihlásenie cez portál používa aktuálnu rolu z databázy pri každej požiadavke;
pri otvorenom staršom zobrazení odporučte obnoviť stránku.


## 14. Supervízor – prehľad portálu a plné ovládanie čerpadla

Supervízor sa prihlasuje do portálu a vidí rovnaké zoznamy a detaily ako admin:
zákazníkov, zariadenia, používateľov, inštalácie, revízie, grafy, nastavenia a
servisnú históriu. Oživenie zostáva iba superadminovi. Oznam nad obsahom pripomína,
že portál je iba na čítanie. Vyhľadávanie, filtre, radenie, taby a stránkovanie fungujú.

Supervízor nemôže vytvárať, upravovať, deaktivovať ani prepájať záznamy, meniť
heslá, účty či roly (ani vlastnú), zapisovať revízie, meniť nastavenia portálu,
obnovovať tokeny, ručne spúšťať stiahnutie dát ani servisný reštart alebo update.
Zakázané akcie nie sú zobrazené; ich priame API volanie server zamietne.
Servisný prehľad iba číta uložené záznamy a neposiela servisné sondy zariadeniu.

Cez **Pripojiť sa** môže otvoriť dashboard zariadenia ako admin. Tam môže meniť
prevádzku, krivku, technické parametre, koeficient, referenciu, sieť aj HA integráciu
alebo otvoriť pôvodné rozhranie čerpadla. Ide o skutočné zásahy do zariadenia.
Zákaz zmien na portáli sa tým neruší. Návrat zabezpečuje položka **Portal** v menu.

Rolu **Supervízor** prideľuje admin/superadmin cez používateľa v portáli. Supervízor
si ju sám nemôže povýšiť. Nové oprávnenia vyžadujú aktualizovaný portál aj dashboard;
na starých zariadeniach sa táto rola ešte nemusí rozpoznať. Lokálna príprava sama
osebe rolu na zákazníckych zariadeniach neaktivuje.
