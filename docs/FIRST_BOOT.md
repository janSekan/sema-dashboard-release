# FIRST_BOOT.md

Postup po flashnutí SEMA-OS-v1.0 na novú SD kartu.

## 1. Flash SD karty

Flashni image:

SEMA-OS-vxx.img

pomocou Raspberry Pi Imager.

Pri otázke "OS Customisation" zvoľ:

NO

---

## 2. Prvý boot

Vlož SD kartu do Raspberry Pi a zapni zariadenie.

Počkajte približne 1–2 minúty na dokončenie bootu.

---

## 3. Overenie AP režimu

Ak zariadenie nemá uloženú WiFi konfiguráciu, automaticky vytvorí AP:

SSID:
SEMA-Setup

Heslo:
sema1234

IP:
192.168.4.1

Pripoj sa k AP a otvor:

http://192.168.4.1

Mala by sa zobraziť Wifi Setup stránka.

---

## 4. Pripojenie na domácu WiFi

Vyber WiFi sieť.

Zadaj heslo.

Po úspešnom pripojení:

- AP sa vypne
- zariadenie sa pripojí do domácej siete

---

## 5. Kontrola služieb

```bash
systemctl status sema
systemctl status nginx
systemctl status sema-wifi-watch.timer
```

Všetky služby musia byť active.

---

## 6. Kontrola databázy

```bash
ls -l ~/sema/backend/data.db
```

Databáza sa vytvára automaticky pri prvom štarte.

---

## 7. Prihlásenie do Tailscale

Aktivácia

```bash
sudo systemctl start tailscaled
```

```bash
sudo tailscale up
```

Dokonči autorizáciu v prehliadači.

Kontrola:

```bash
tailscale status
```

---

## 8. Kontrola web aplikácie

Otvoriť:

http://IP_ADRESA_RPI

Skontrolovať:

- Login
- Dashboard
- Settings

---

## 9. Kontrola web aplikácie

Otvoriť:

http://IP_ADRESA_RPI:8081

Skontrolovať či sa pripojí na pôvodný systém čerpadla.

---

## 10. Kontrola komunikácie s čerpadlom

```bash
curl --user "$DEVICE_USER" http://192.168.69.2/status.xml
```

Musí sa vrátiť XML odpoveď.

---

## 11. Sema-Os

Po úspešnom vykonaní všetkých krokov je zariadenie pripravené na používanie.

## 12. Provision

Po pridaní zariadenia v Sema-Portal treba cez ssh na zariadení spustiť príkaz ktorý sa vygeneruje pri vytvorení zariadenia.
