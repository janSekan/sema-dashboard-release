# Texty tooltipov – Nastavenia SEMA Dashboard

Stav: zapojené do dashboardu, 10. 11. 2026. Texty sú zahrnuté do frontendového
buildu; zmena súboru sa prenesie na zariadenia s novým vydaním.

Každý nadpis `## settings.…` je stály identifikátor jedného tooltipu. Text pod
ním je obsah tooltipu. Pri úprave stačí prepísať text; identifikátory zachovajte.
Aplikácia načítava tieto sekcie z Markdown súboru pri zostavení.
Aktualizovaný text sa dostane na zariadenia až s vydaním, ktoré tento súbor obsahuje.
Pri lokálnom vývoji sa úprava načíta cez Vite. Na zariadení obnovte stránku po
aktualizácii. Samotná editácia súboru na zariadení bez nového buildu nestačí.

Bublina sa zobrazí pri prejdení myšou alebo pri zaostrení klávesnicou. Kliknutie
na názov ju otvorí natrvalo; ďalšie kliknutie, kliknutie mimo alebo Escape ju
zatvorí. Pri akčných tlačidlách slúži samostatná ikona ?, ktorá akciu nespúšťa.
Tooltipy obsahujú obyčajný text, nie HTML. Nadpisy a poznámky sa nezobrazujú.

# Prevádzkové prepínače

## settings.power

Zapne alebo vypne čerpadlo prostredníctvom regulátora. Požiadavka sa odošle hneď po prepnutí, bez tlačidla Uložiť. Počkajte na obnovenie stavu.

## settings.season

Prepína letný a zimný režim. V zimnom režime je dostupné kúrenie, v letnom možno ovládať chladenie. Požiadavka sa odošle hneď po prepnutí.

## settings.coolingEnabled

V letnom režime povoľuje alebo vypína chladenie. V zimnom režime tento prepínač nie je dostupný. Požiadavka sa odošle hneď po prepnutí.

# Karta Teplota

## settings.heatingMainTemp

Zmenou tejto hodnoty posúvate celú vykurovaciu krivku nahor alebo nadol. Veľkosť posunu určuje koeficient. Zvýšenie o 1 °C nemusí zvýšiť skutočnú teplotu miestnosti presne o 1 °C.

## settings.saveHeatingMainTemp

Uloží zvolenú teplotu a posunie všetky body vykurovacej krivky o zmenu teploty násobenú uloženým koeficientom. Napríklad zvýšenie o 1 °C pri koeficiente 2 posunie krivku o 2 °C.

## settings.saveHeatingReference

Nastaví novú východiskovú hodnotu hlavnej teploty bez posunutia vykurovacej krivky. Ďalšia zmena teploty sa bude počítať od tejto hodnoty. Nepoužívajte namiesto bežného zvýšenia alebo zníženia teploty.

## settings.heatingCurveCoefficient

Určuje, o koľko sa posunie krivka pri zmene hlavnej teploty. Pri hodnote 1 znamená zmena o 1 °C posun krivky o 1 °C, pri hodnote 2 posun o 2 °C. Predvolená hodnota je 1, krok nastavenia 0,1.

## settings.saveHeatingCoefficient

Uloží iba koeficient pre ďalšie zmeny hlavnej teploty. Samotné uloženie neposunie krivku ani nezmení hlavnú teplotu. Neuložená hodnota koeficientu sa nepoužije.

# Vnútorná teplota

## settings.minIndoorCool

Spodný limit vnútornej teploty pre režim chladenia. Ide o teplotu miestnosti, nie o teplotu vody v chladiacom okruhu.

## settings.maxIndoorHeat

Horný limit vnútornej teploty pre režim kúrenia. Tento limit nie je nastavením teploty vykurovacej vody ani posunu krivky.

# Ohrev vody – TÚV

## settings.minWaterTemp

Dolná teplotná hranica zásobníka pre riadenie ohrevu TÚV. Nastavte ju nižšie než hornú hranicu.

## settings.maxWaterTemp

Horná teplotná hranica zásobníka pri ohreve TÚV. Nie je to nastavenie teploty vody na kohútiku.

# Vykurovacia krivka

## settings.heatCurve

Krivka určuje požadovanú teplotu vykurovacej vody podľa vonkajšej teploty. Jednotlivé body upravujú jej priebeh; hlavná karta Teplota posúva všetky body naraz.

## settings.heatCurve.minus20

Požadovaná teplota vykurovacej vody pri vonkajšej teplote −20 °C. Nejde o teplotu miestnosti.

## settings.heatCurve.minus12

Požadovaná teplota vykurovacej vody pri vonkajšej teplote −12 °C. Nejde o teplotu miestnosti.

## settings.heatCurve.minus4

Požadovaná teplota vykurovacej vody pri vonkajšej teplote −4 °C. Nejde o teplotu miestnosti.

## settings.heatCurve.plus4

Požadovaná teplota vykurovacej vody pri vonkajšej teplote +4 °C. Nejde o teplotu miestnosti.

## settings.heatCurve.plus12

Požadovaná teplota vykurovacej vody pri vonkajšej teplote +12 °C. Nejde o teplotu miestnosti.

## settings.heatCurve.plus20

Požadovaná teplota vykurovacej vody pri vonkajšej teplote +20 °C. Nejde o teplotu miestnosti.

# Iné – technické nastavenia

## settings.limitWater

Percentuálny limit výkonu pri ohreve TÚV. Nie je to údaj o aktuálnom výkone ani príkone v kW. Význam hraničných hodnôt sa riadi konkrétnym regulátorom.

## settings.limitHeat

Percentuálny limit výkonu pri kúrení. Nie je to údaj o aktuálnom výkone ani príkone v kW. Význam hraničných hodnôt sa riadi konkrétnym regulátorom.

## settings.limitCool

Percentuálny limit výkonu pri chladení. Nie je to údaj o aktuálnom výkone ani príkone v kW. Význam hraničných hodnôt sa riadi konkrétnym regulátorom.

## settings.coolerTemp

Teplotný parameter vody pre režim chladenia. Ide o chladiacu vodu, nie o požadovanú teplotu miestnosti. Vhodnú hodnotu nastavte podľa použitej chladiacej sústavy.

## settings.bivalentTemp

Teplotný parameter bivalentného režimu regulátora. Presné podmienky zapojenia doplnkového zdroja závisia od konkrétneho čerpadla a jeho konfigurácie.

## settings.timeLimitWater

Časový limit ohrevu TÚV v minútach. Je to maximálny čas počas ktorého sa čerpadlo pokúša ohriať TUV na požadovanú teplotu.

## settings.constant

Parameter regulácie čerpadla. Vhodná hodnota a jej vplyv na reguláciu závisia od konkrétneho regulátora a vykurovacej sústavy. Meňte podľa odporúčania technika.

# Nastavenia siete

## settings.deviceIp

IP adresa regulátora čerpadla, s ktorým SEMA komunikuje. Nesprávna adresa preruší komunikáciu s čerpadlom.

# Uloženie

## settings.saveSettings

Odošle upravené limity a parametre do čerpadla. Hlavná teplota, referencia a koeficient majú vlastné tlačidlá na uloženie.

# Poznámky pre správcu textov

Tieto poznámky nie sú súčasťou tooltipov:

- Významy vychádzajú z aktuálnych polí dashboardu, mapovania API a používateľského
  manuálu v projekte. Nie sú doplnené odhadované pravidlá regulátora.
- Pred podrobnejším vysvetlením potvrdiť podľa dokumentácie konkrétneho čerpadla:
  presné správanie vnútorných limitov, štart/ukončenie TÚV, význam 0 % a 0 min,
  bivalentné spínanie a účinok regulačnej konštanty. Tooltipy sú zatiaľ zámerne
  všeobecné tam, kde tieto podrobnosti nemáme doložené.
- Rozsahy a kroky zostávajú v ovládacích prvkoch; texty ich zbytočne neopakujú.
  Nulový limit sa neoznačuje za vypnutie funkcie bez potvrdenia výrobcu.
- Tooltipy rešpektujú existujúce oprávnenia. Pri zmene komponentov zachovať
  skrytie technického parametra pred používateľom, ktorý ho nevidí.
- Zdrojový súbor spravovať v projekte. Ručná úprava iba na zariadení nemusí
  prežiť aktualizáciu. Pre distribúciu zmenených textov treba zostaviť frontend
  a vydať nový release. Identifikátory sekcií musia byť jedinečné.
