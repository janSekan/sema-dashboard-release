# Roly, technické nastavenia a centrálna správa účtov

Stav 10. 11. 2026: lokálny vývoj, bez pushu alebo nasadenia na testing/produkciu.
Používateľský postup a význam nastavení: [USER_MANUAL.md](USER_MANUAL.md).

## Rozdelenie oprávnení

Portál a dashboard rozlišujú administratívny zápis od ovládania čerpadla.

- user: bežné ovládanie, hlavná teplota, štyri základné teplotné limity a útlm.
- superuser: navyše krivka, sekcia Iné, koeficient a Uložiť referenciu.
- supervisor (zobrazený ako **Supervízor**): portál ako admin iba na čítanie,
  dashboard vrátane siete/HA a pôvodného rozhrania ako admin.
- admin/superadmin: správa portálu, servisné akcie aj plné ovládanie dashboardu.
  Oživenie zostáva iba superadminovi.

Na portáli `require_admin` a `canManagePortal` zostávajú admin + superadmin.
`require_portal_view` / `canViewPortal` zahŕňajú aj supervisor. Routerová závislosť
`require_portal_access` povoľuje supervízorovi GET/HEAD/OPTIONS, ostatné metódy
vyžadujú require_admin. Výnimka POST `/api/admin/devices/{device_id}/open`
používa require_portal_view: mení iba servisný výber v session, nie evidenciu.
Supervízor nesmie zmeniť rolu (ani vlastnú), heslo, priradenie, zákazníka,
zariadenie, inštaláciu, revíziu, nastavenie, token ani ručne spustiť sync či servis.
Servisný GET iba číta DB: nesonduje jednotku ani neprepisuje výsledky požiadaviek.

Na dashboarde `isAdmin` / `require_admin` zahŕňajú supervisor + admin + superadmin.
`canConfigurePump` / `require_pump_configurator` zahŕňajú navyše superuser.
Servisný dashboardový endpoint má vlastný whitelist admin/superadmin: supervisor
ho nemôže obísť priamym proxovaným volaním. Pôvodné rozhranie čerpadla je pre
supervisor povolené ako súčasť ovládania zariadenia, nie správy portálu.

## API dashboardu

GET/POST `/device-api/settings` vyžadujú autentifikáciu aj povolený sieťový prístup.
User dostáva a smie poslať iba `minIndoorCool`, `maxIndoorHeat`, `minWaterTemp`,
`maxWaterTemp`. Prítomnosť technického poľa v jeho POST vráti 403 pred čítaním
alebo zápisom čerpadla. Pri základnom zápise sa ostatné hodnoty zachovajú
z čerstvo načítaného formulára čerpadla, nenahradia sa skrytými predvolenými hodnotami.

Koeficient a referencia vyžadujú require_pump_configurator. Konfigurácia siete
vyžaduje require_admin. Wi-Fi scan/connect pri bežnej prevádzke tiež; prvotné
oživenie v existujúcom setup režime ostáva dostupné pred prihlásením.
Všeobecné POST ovládania/hlavnej teploty/útlmu teraz tiež vyžadujú autentifikáciu.

Sekcia Účty a jej frontendové API helpery sú odstránené. `/device-api/accounts/{role}`
vracia 410 pre čítanie aj zmeny; `/device-api/account` ostáva iba informáciou
o aktuálne prihlásenom používateľovi. Existujúce DB účty/heslá sa nemažú ani nemenia.
Superuser je rozpoznávaný pri lokálnom prihlásení, ak taký účet existuje; automaticky
sa nezakladá a nemá nové predvolené heslo. Štandardné pridelenie roly prebieha
v portáli a do dashboardu sa prenáša dôveryhodnou proxy.

## Portál a kompatibilita

Admin/superadmin môže roly Superuser aj Supervízor vytvoriť a priradiť vo formulári používateľa; zoznam
obe pozná vo filtri/radení a zákaznícke počítadlo účtov zahŕňa user aj superuser.
Login user/superuser smeruje na priradený dashboard. Administrácia portálu a device-pump
proxy ostávajú pre user/superuser zakázané. Supervízor sa prihlasuje do portálu
a vyberá zariadenie cez Pripojiť sa. Do jednotky ide skutočná rola supervisor,
nikdy sa neprepisuje na admin. Staršie jednotky ju nemusia rozpoznať. Servisný výber cudzieho zariadenia zo starej admin session
sa po znížení na user/superuser ignoruje; proxy používa aktuálnu rolu z DB a vlastné priradenie.

SQLite users.role aj accounts.role prijímajú text, preto netreba meniť schému.
Validácia povolených rolí je na portálovom API aj v create_user/update_user.
Nepridáva sa synchronizácia portálových hesiel s lokálnymi záložnými účtami.

Pred budúcim vydaním otestovať dashboard na sema-001 až po výslovnom pokyne.
Superusera/Supervízora prideľovať až na dashboardoch s novými oprávneniami; staršie verzie
môžu technické sekcie skryť alebo koeficient odmietnuť. Zmenené frontendové
formuláre a backend vydať spolu: nový backend nepovolí userovi starý formulár
obsahujúci aj technické polia. Pri aktualizácii odporučiť obnovenie stránky.

Izolované testy: dashboard `tests/test_superuser.py`, portál
`backend/tests/test_superuser.py` a `backend/tests/test_supervisor.py`. Žiadne testovacie nastavenie sa neposielalo
skutočnému čerpadlu; DB aj systémové operácie sú izolované/mockované.
