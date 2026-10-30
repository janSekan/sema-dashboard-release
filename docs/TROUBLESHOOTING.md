# SEMA Dashboard Troubleshooting Guide v1.0

Autor: Jan Sekan

Posledná aktualizácia: 2026-06

---

# Prehľad

Tento dokument obsahuje všetky problémy, ktoré sa objavili počas prvého reálneho nasadenia SEMA Dashboard na Raspberry Pi Zero 2W a ich riešenia.

---

# WIFI-001

## Problém

Po flashnutí Raspberry Pi OS Lite:

- hostname sa nenastavil
- používateľ sa nevytvoril
- heslo sa nenastavilo
- WiFi sa nenastavila

RPi sa neobjavilo v sieti.

## Diagnostika

Po pripojení monitora sa zobrazil prvotný setup wizard.

## Riešenie

Dokončiť prvotný setup lokálne.

Nespoliehať sa na nastavenia z Raspberry Pi Imager.

Pri každom novom nasadení overiť:

```bash
hostname
nmcli device
```

---

# WIFI-002

## Problém

WiFi zariadenie bolo:

```text
unavailable
```

## Diagnostika

```bash
rfkill list
```

Výsledok:

```text
Soft blocked: yes
```

## Riešenie

```bash
sudo rfkill unblock wifi
```

Kontrola:

```bash
rfkill list
```

Výsledok:

```text
Soft blocked: no
```

---

# WIFI-003

## Problém

Aj po odblokovaní WiFi:

```text
nmcli device
```

zobrazovalo:

```text
wlan0 unavailable
```

## Diagnostika

```bash
nmcli radio wifi
```

Výsledok:

```text
disabled
```

## Riešenie

```bash
sudo nmcli radio wifi on
```

Kontrola:

```bash
nmcli radio wifi
```

Výsledok:

```text
enabled
```

---

# DEPLOY-001

## Problém

Backend sa nespustil.

Chyba:

```text
pwdlib.exceptions.HasherNotAvailable
```

alebo

```text
argon2 hash algorithm is not available
```

## Príčina

V requirements.txt chýbal:

```text
argon2-cffi
```

## Riešenie

```bash
pip install argon2-cffi
```

Doplniť do requirements.txt:

```text
argon2-cffi==25.1.0
```

---

# DEPLOY-002

## Problém

Po:

```bash
git pull
```

zmizol súbor:

```text
.env
```

## Príčina

.env bol odstránený z release repa.

Git korektne zmazal aj lokálnu kópiu.

## Riešenie

Release repo:

```gitignore
.env
```

.env nesmie byť súčasťou release repa.

Musí existovať iba lokálne:

```text
/home/jan/sema/.env
```

---

# ETH-001

## Problém

eth0 nemal IP adresu.

## Diagnostika

```bash
ip addr show eth0
```

nezobrazovalo:

```text
inet
```

## Riešenie

Nastaviť statickú IP:

```bash
sudo nmcli connection modify "Wired connection 1" \
ipv4.method manual \
ipv4.addresses 192.168.69.10/24
```

Aktivovať:

```bash
sudo nmcli connection up "Wired connection 1"
```

Kontrola:

```bash
ip -4 addr show dev eth0
```

---

# AP-001

## Problém

WifiSetup sa nezobrazovala.

Endpoint:

```text
/api/system/setup-mode
```

vracal:

```json
{
  "setupMode": false
}
```

aj keď bol aktívny AP mód.

## Príčina

Detekcia AP predpokladala:

```text
sema-ap:wlan0:wifi
```

ale NetworkManager vracal:

```text
sema-ap:wlan0:802-11-wireless
```

## Nesprávne riešenie

```python
if "sema-ap:wlan0:wifi" in result.stdout:
```

## Správne riešenie

```python
for line in result.stdout.splitlines():
    parts = line.split(":")

    if len(parts) >= 2:
        name = parts[0]
        device = parts[1]

        if name == "sema-ap" and device == "wlan0":
            return True
```

---

# AP-002

## Problém

Endpoint:

```text
/api/system/setup-mode
```

vracal:

```text
Internal Server Error
```

## Chyba

```text
NameError: os is not defined
```

## Príčina

Chýbal:

```python
import os
```

vo wifi_service.py

## Riešenie

Pridať:

```python
import os
```

---

# AP-003

## Problém

Wifi scan a WiFi connect nefungovali.

V logu:

```text
pam_unix(sudo:auth)
```

a

```text
password for jan
```

## Príčina

Backend spúšťal:

```bash
sudo nmcli ...
```

ale systemd služba nemala možnosť zadať heslo.

## Riešenie

Vytvoriť:

```bash
sudo visudo -f /etc/sudoers.d/sema-nmcli
```

Obsah:

```text
jan ALL=(root) NOPASSWD: /usr/bin/nmcli
```

Práva:

```bash
sudo chmod 440 /etc/sudoers.d/sema-nmcli
```

Kontrola:

```bash
sudo -n nmcli device
```

---

# AP-004

## Problém

Po zadaní správneho SSID a hesla formulár vypísal:

```text
Pripojenie zlyhalo
```

ale RPi sa reálne pripojilo.

## Príčina

Po úspešnom pripojení:

- AP sa vypol
- mobil stratil spojenie s 192.168.4.1
- frontend už nedostal odpoveď

## Riešenie

Nepoužívať formuláciu:

```text
Pripojenie zlyhalo
```

Použiť neutrálnu hlášku:

```text
Ak boli údaje správne, zariadenie sa pripája k WiFi.
```

---

# AP-005

## Problém

Po zmazaní WiFi profilu:

```bash
sudo nmcli connection delete SEKAN
```

sa stratilo SSH spojenie.

## Správanie

WiFi watcher správne spustil:

```text
SEMA-Setup
```

## Výsledok

Provisioning flow bol úspešne otestovaný.

---

# TEST-001

## Úspešne otestované

Scenár:

```text
Router vypnutý
↓
RPi reboot
↓
SEMA-Setup sa objaví
↓
WifiSetup stránka funguje
↓
Scan funguje
↓
Connect funguje
↓
RPi sa pripojí na WiFi
↓
AP sa vypne
↓
Tailscale sa obnoví
```

Výsledok:

```text
PASS
```

---

# TEST-002

## Úspešne otestované

Scenár:

```text
Odstránenie uloženého WiFi profilu
↓
WiFi odpojená
↓
AP sa automaticky zapne
↓
WifiSetup obnoví pripojenie
```

Výsledok:

```text
PASS
```

---

# Stav systému

Pri vydaní v1.0 boli úspešne otestované:

- Raspberry Pi Zero 2W
- FastAPI
- React build
- SQLite
- Systemd
- Tailscale
- Ethernet komunikácia s čerpadlom
- AP fallback
- WiFi provisioning
- Git update workflow

Deployment bol úspešne dokončený.
