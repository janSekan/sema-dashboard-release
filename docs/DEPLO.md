> Historický prevádzkový návod. Pre aktuálne spustenie vývoja začni v [hlavnom README](../README.md). Publikovanie release a kanály `testing`/`main` sa riadia [RELEASE_WORKFLOW.md](RELEASE_WORKFLOW.md); staršie update postupy nižšie nie sú aktuálnym publikačným workflow.

# SEMA Dashboard Deployment Guide v1.1

Autor: Jan Sekan

Posledná aktualizácia: 2026-07

---

# 1. Prehľad

SEMA Dashboard je riadiaci a diagnostický systém určený pre tepelné čerpadlá.

Beží na:

- Raspberry Pi Zero 2W
- Raspberry Pi 3 Model A+
- Raspberry Pi OS Lite
- FastAPI backend
- React frontend (buildnutý do `dist`)
- SQLite databáza
- Tailscale vzdialený prístup
- Ethernet komunikácia s tepelným čerpadlom
- WiFi Provisioning (AP mód)
- Nginx Reverse Proxy

Architektúra:

```
Internet
│
Tailscale
│
RPi Zero 2W
├── wlan0 → Domáca WiFi
└── eth0 → Tepelné čerpadlo

```

SEMA Dashboard komunikuje:

- lokálne s tepelným čerpadlom cez Ethernet
- so servisným technikom cez Tailscale
- so zákazníkom cez webové dashboard.semaeco.sk

---

# 2. Požiadavky

## Hardware

- Raspberry Pi Zero 2W / Raspberry Pi 3 Model A+
- SD karta (odporúčané 16 GB alebo viac)
- USB Ethernet adaptér
- napájanie 5 V

## Software

- Raspberry Pi OS Lite
- GitHub Release Repository
- Tailscale účet
- Raspberry Pi Imager

---

# 3. Flash Raspberry Pi OS Lite

Flash vykonať pomocou:

**Raspberry Pi Imager**

Odporúčané nastavenia:

- hostname
- username
- password
- Enable SSH
- Configure WiFi
- Locale
- Timezone

Odporúčaná verzia systému:

```

Raspberry Pi OS Lite (64-bit)

```

---

## Dôležitá poznámka

Počas vývoja sa niekoľkokrát stalo, že Raspberry Pi Imager neaplikoval:

- hostname
- username
- password
- WiFi konfiguráciu

Po prvom boote preto vždy overiť lokálne cez monitor.

---

# 4. Prvé spustenie

Prihlásenie lokálne.

Overenie hostname:

```bash
hostname
```

Overenie siete:

```bash
nmcli device
```

Overenie IP:

```bash
hostname -I
```

Odporúča sa overiť aj čas:

```bash
timedatectl
```

---

# 5. Oprava WiFi ak nefunguje

Typické príznaky:

```
wlan0 unavailable
```

alebo

```
Soft blocked: yes
```

Kontrola:

```bash
rfkill list
```

Oprava:

```bash
sudo rfkill unblock wifi
```

Zapnutie WiFi:

```bash
sudo nmcli radio wifi on
```

Kontrola:

```bash
nmcli radio wifi
```

Očakávaný výsledok:

```
enabled
```

---

# 6. Pripojenie na WiFi

Pripojenie vykonať cez:

- raspi-config
- alebo
- nmcli

Kontrola:

```bash
nmcli device
```

Očakávaný výsledok:

```
wlan0 connected
```

Overenie internetu:

```bash
ping -c 4 google.com
```

---

# 7. SSH

Zistenie IP adresy:

```bash
hostname -I
```

Pripojenie:

```bash
ssh jan@IP_ADRESA
```

Po úspešnom SSH už nie je potrebný monitor.

---

## Poznámka

Pri Golden Image budú SSH host keys odstránené.

Po prvom boote ich automaticky vytvorí:

```
sema-firstboot.service
```

Nie je potrebný manuálny zásah.

---

# 8. Aktualizácia systému

Aktualizácia balíkov:

```bash
sudo apt update
sudo apt full-upgrade -y
```

Reboot:

```bash
sudo reboot
```

Po reboote overiť:

```bash
uname -a
```

---

# 9. Tailscale

Inštalácia:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

Prihlásenie:

```bash
sudo tailscale up
```

Kontrola:

```bash
tailscale status
```

Tailscale IP:

```bash
tailscale ip -4
```

SSH test:

```bash
ssh jan@TAILSCALE_IP
```

---

## Poznámka

Pred vytvorením Golden Image musí byť zariadenie z Tailscale odhlásené.

---

# 10. Inštalácia potrebných balíkov

```bash
sudo apt install \
git \
python3-pip \
python3-venv \
nginx \
hostapd \
dnsmasq \
avahi-daemon \
curl \
-y
```

Kontrola:

```bash
git --version
python3 --version
nginx -v
```

Od tohto bodu pokračuje inštalácia samotného SEMA Dashboardu.

# 11. Release Repository

Vytvorenie pracovného adresára:

```bash
mkdir -p ~/sema
cd ~/sema
```

Clone release repozitára:

```bash
git clone https://github.com/USERNAME/sema-dashboard-release.git .
```

Kontrola:

```bash
git status
```

Očakávaný výsledok:

```text
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

---

# 12. Python prostredie

Vytvorenie virtuálneho prostredia:

```bash
python3 -m venv .venv
```

Aktivácia:

```bash
source .venv/bin/activate
```

Inštalácia závislostí:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Kontrola:

```bash
pip list
```

Po skončení práce:

```bash
deactivate
```

---

# 13. Environment

Súbor:

```text
/home/jan/sema/.env
```

Nie je súčasťou Release repozitára.

Musí existovať lokálne.

Obsahuje napríklad:

- SECRET_KEY
- DEVICE_ID
- prihlasovacie údaje
- ďalšie lokálne nastavenia

Kontrola:

```bash
cat /home/jan/sema/.env
```

---

# 14. Backend test

Prechod do backendu:

```bash
cd ~/sema/backend
```

Aktivácia prostredia:

```bash
source ../.venv/bin/activate
```

Spustenie:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Test:

```bash
curl http://localhost:8000/api/health
```

Očakávaný výsledok:

```json
{ "status": "ok" }
```

Backend ukončiť:

```text
CTRL + C
```

---

# 15. Systemd

Vytvoriť:

```bash
sudo nano /etc/systemd/system/sema.service
```

Obsah:

```ini
[Unit]
Description=SEMA Dashboard FastAPI
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
User=jan
WorkingDirectory=/home/jan/sema/backend
EnvironmentFile=/home/jan/sema/.env
ExecStart=/home/jan/sema/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Aktivácia:

```bash
sudo systemctl daemon-reload

sudo systemctl enable sema

sudo systemctl start sema
```

Kontrola:

```bash
sudo systemctl status sema --no-pager
```

Očakávaný výsledok:

```text
active (running)
```

---

# 16. Automatický denný reboot

Dočasný watchdog.

Úprava cronu:

```bash
sudo crontab -e
```

Pridať:

```cron
0 2 * * * /sbin/reboot
```

Výsledok:

Každý deň o:

```text
02:00
```

prebehne automatický reboot systému.

Poznámka:

V budúcnosti bude nahradený vlastným watchdog mechanizmom.

---

# 17. Ethernet pripojenie čerpadla

### Nastavenie čerpadla:

IP:

```text
192.168.69.2
```

Maska:

```text
255.255.255.0
```

DHCP:

```text
OFF
```

---

### Nastavenie Raspberry Pi:

IP:

```text
192.168.69.10
```

Maska:

```text
255.255.255.0
```

Gateway:

```text
nechať prázdnu
```

DNS:

```text
nechať prázdne
```

Zistenie názvu profilu:

```bash
nmcli connection show
```

Nastavenie:

```bash
sudo nmcli connection modify "LAN" \
ipv4.method manual \
ipv4.addresses 192.168.69.10/24
```

Aktivácia:

```bash
sudo nmcli connection up "LAN"
```

Kontrola:

```bash
ip -4 addr show dev eth0
```

---

# 18. Test komunikácie s čerpadlom

Ping:

```bash
ping -c 4 192.168.69.2
```

Status XML:

```bash
curl --user "$DEVICE_USER" http://192.168.69.2/status.xml
```

Očakávaný výsledok:

XML odpoveď tepelného čerpadla.

Ak komunikácia nefunguje:

Overiť:

```bash
nmcli device
```

a

```bash
lsusb
```

USB Ethernet adaptér musí byť rozpoznaný.

---

# 19. WiFi Provisioning

Potrebné balíky:

```bash
sudo apt install hostapd dnsmasq -y
```

SEMA používa AP mód pre prvotné nastavenie WiFi.

SSID:

```text
SEMA-Setup
```

Po úspešnom pripojení zariadenia do domácej siete sa AP automaticky vypne.

Ak dôjde k strate WiFi, AP sa automaticky znovu aktivuje.

---

# 20. AP profil

Súbor:

```text
/etc/NetworkManager/system-connections/sema-ap.nmconnection
```

Obsah:

```ini
[connection]
id=sema-ap
type=wifi
interface-name=wlan0
autoconnect=false

[wifi]
mode=ap
ssid=SEMA-Setup

[wifi-security]
key-mgmt=wpa-psk
psk=sema1234

[ipv4]
method=shared
address1=192.168.4.1/24

[ipv6]
method=disabled
```

Nastavenie práv:

```bash
sudo chmod 600 /etc/NetworkManager/system-connections/sema-ap.nmconnection
```

Reload konfigurácie:

```bash
sudo nmcli connection reload
```

Kontrola:

```bash
nmcli connection show
```

Musí sa zobrazovať profil:

```text
sema-ap
```

# 21. AP Fallback Watcher

Skript:

```text
/home/jan/sema/scripts/wifi-watch.sh
```

Úloha skriptu:

- pravidelne kontrolovať stav WiFi pripojenia,
- automaticky zapnúť AP mód pri strate WiFi,
- automaticky sa pokúšať znovu pripojiť na poslednú uloženú WiFi,
- po úspešnom pripojení AP automaticky vypnúť.

---

## Setup Lock

Počas nastavovania WiFi cez stránku **WifiSetup** je vytvorený lock súbor.

Účel:

Zabrániť tomu, aby watcher počas zadávania prihlasovacích údajov vypol AP a pokúsil sa pripojiť na WiFi.

Po dokončení konfigurácie je lock automaticky odstránený.

---

# 22. Povolenie nmcli bez hesla

Nutné pre WiFi Provisioning.

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

---

# 23. WiFi Watch Service

Súbor:

```text
/etc/systemd/system/sema-wifi-watch.service
```

Obsah:

```ini
[Unit]
Description=SEMA WiFi AP fallback watcher
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/home/jan/sema/scripts/wifi-watch.sh
```

---

# 24. WiFi Watch Timer

Súbor:

```text
/etc/systemd/system/sema-wifi-watch.timer
```

Obsah:

```ini
[Unit]
Description=Run SEMA WiFi watcher periodically

[Timer]
OnBootSec=30
OnUnitActiveSec=30
Unit=sema-wifi-watch.service

[Install]
WantedBy=timers.target
```

Aktivácia:

```bash
sudo systemctl daemon-reload

sudo systemctl enable sema-wifi-watch.timer

sudo systemctl start sema-wifi-watch.timer
```

Kontrola:

```bash
systemctl list-timers | grep sema
```

---

## Správanie

Každých 30 sekúnd:

- ak je WiFi pripojená → nič nerobí,
- ak je aktívny AP mód → skúsi sa pripojiť na poslednú uloženú WiFi,
- ak WiFi nie je dostupná → ponechá AP zapnuté.

---

# 25. Nginx Reverse Proxy

Cieľ:

Namiesto:

```text
http://IP:8000
```

používať:

```text
http://IP
```

Zároveň umožniť prístup k pôvodnému webovému rozhraniu tepelného čerpadla cez:

```text
http://IP:8081
```

---

## Inštalácia

```bash
sudo apt update
sudo apt install nginx -y
```

---

## Kontrola

```bash
systemctl status nginx --no-pager
```

Očakávaný výsledok:

```text
active (running)
```

---

## Odstránenie default konfigurácie

```bash
sudo rm /etc/nginx/sites-enabled/default
```

---

## Vytvorenie konfigurácie

```bash
sudo nano /etc/nginx/sites-available/sema
```

Obsah:

```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 8081;
    server_name _;

    location / {
        proxy_pass http://192.168.69.2/;

        proxy_set_header Host 192.168.69.2;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Aktivácia

```bash
sudo ln -s /etc/nginx/sites-available/sema /etc/nginx/sites-enabled/sema
```

---

## Test konfigurácie

```bash
sudo nginx -t
```

Očakávaný výsledok:

```text
syntax is ok
test is successful
```

---

## Reload konfigurácie

```bash
sudo systemctl reload nginx
```

---

## Test Dashboardu

```bash
curl http://localhost/api/health
```

---

## Test webového rozhrania čerpadla

```bash
curl -I http://localhost:8081
```

Očakávaný výsledok:

```text
HTTP/1.1 200 OK
```

(alebo odpoveď webového servera čerpadla)

---

## Výsledok

SEMA Dashboard je dostupný na:

```text
http://IP
```

bez portu 8000.

Pôvodné webové rozhranie tepelného čerpadla je dostupné na:

```text
http://IP:8081
```

---

## Poznámka

Prístup k čerpadlu cez samostatný port 8081 bol zvolený zámerne.

Pokus o sprístupnenie čerpadla cez:

```text
http://IP/pump/
```

spôsoboval problémy s JavaScriptom a AJAX komunikáciou (`gweth.js`, `status.xml`, `parameters.htm`, `timer.htm`).

Samostatný port 8081 zabezpečuje plnú kompatibilitu s pôvodným webovým rozhraním čerpadla.

Výhodou je tiež možnosť ponechať na všetkých inštaláciách rovnakú IP adresu čerpadla:

```text
192.168.69.2
```

bez potreby individuálneho adresovania jednotlivých zariadení.

Poznámka:

SEMA Dashboard:

```
http://IP
```

Webové rozhranie tepelného čerpadla:

```
http://IP:8081
```

Port **8081** bol zvolený zámerne kvôli kompatibilite pôvodného webového rozhrania Panasonic.

---

# 26. Automatická aktualizácia po boote

Cieľ:

Po každom štarte zariadenia automaticky skontrolovať dostupnosť novej verzie Dashboardu.

Dôvod:

SEMA zariadenia môžu byť nainštalované aj niekoľko mesiacov po vytvorení Golden Image.

Automatická aktualizácia zabezpečí, že po prvom pripojení do internetu sa zariadenie aktualizuje na najnovšiu verziu.

---

## Systemd služba

Vytvorenie:

```bash
sudo nano /etc/systemd/system/sema-update.service
```

Obsah:

```ini
[Unit]
Description=SEMA Auto Update
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/home/jan/sema/scripts/update.sh
```

---

## Systemd timer

Vytvorenie:

```bash
sudo nano /etc/systemd/system/sema-update.timer
```

Obsah:

```ini
[Unit]
Description=Run SEMA update after boot

[Timer]
OnBootSec=15min
Unit=sema-update.service

[Install]
WantedBy=timers.target
```

---

## Aktivácia

```bash
sudo systemctl daemon-reload

sudo systemctl enable sema-update.timer
sudo systemctl start sema-update.timer
```

---

## Kontrola

```bash
systemctl list-timers | grep sema-update
```

Očakávaný výsledok:

```text
sema-update.timer
```

---

## Správanie

Po štarte zariadenia:

```text
Boot
↓
SEMA Dashboard sa spustí
↓
Po 15 minútach
↓
Kontrola aktualizácie
↓
GitHub release repo
↓
Aktualizácia
↓
Reštart služby SEMA
```

---

## Poznámka

Zariadenie sa aktualizuje po každom boote.

Keďže systém má dočasný denný reboot o 02:00, kontrola aktualizácie prebehne približne:

```text
02:15
```

# 27. Aktualizácia aplikácie

Manuálne:

```bash
./scripts/update.sh
```

Obsah skriptu:

```bash
#!/bin/bash
set -e

cd /home/jan/sema

echo "Fetching latest release..."
git fetch origin

echo "Resetting to origin/main..."
git reset --hard origin/main

echo "Restarting SEMA service..."
sudo systemctl restart sema

echo "Status:"
sudo systemctl status sema --no-pager
```

---

# 28. Helper Scripts

Adresár:

```
scripts/
```

Obsah:

```
update.sh
health.sh
logs.sh
wifi-watch.sh
check-usb-ethernet.sh
```

Práva:

```bash
chmod +x scripts/*.sh
```

---

# 29. Default účty

User

```
user
```

```
sema-eco
```

Admin

```
admin
```

```
KatkaMarekMatej
```

---

# 30. Diagnostika

SEMA

```bash
systemctl status sema --no-pager
```

Log

```bash
journalctl -u sema -f
```

Nginx

```bash
systemctl status nginx --no-pager
```

WiFi

```bash
nmcli device
```

Tailscale

```bash
tailscale status
```

USB

```bash
lsusb
```

USB strom

```bash
lsusb -t
```

Kernel log

```bash
dmesg | grep -iE "usb|error -71"
```

---

# 31. USB Ethernet Watchdog

## Cieľ

Detegovať zlyhanie inicializácie USB Ethernet adaptéra počas bootu.

Na Raspberry Pi Zero 2W sa môže sporadicky stať, že USB Ethernet adaptér nebude počas štartu rozpoznaný.

Typický prejav:

- neexistuje `eth0`
- adaptér sa nezobrazí v `lsusb`
- Dashboard nekomunikuje s tepelným čerpadlom

---

## Watchdog skript

Vytvoriť:

```bash
sudo nano /home/jan/sema/scripts/check-usb-ethernet.sh
```

Obsah:

```bash
#!/bin/bash

ADAPTER_ID="1a86:e396"
COUNT_FILE="/var/tmp/sema-usb-eth-reboot-count"
MAX_REBOOTS=10

sleep 20

if lsusb | grep -q "$ADAPTER_ID"; then
    logger "SEMA: USB Ethernet found"
    rm -f "$COUNT_FILE"
    exit 0
fi

count=0

if [ -f "$COUNT_FILE" ]; then
    count=$(cat "$COUNT_FILE")
fi

count=$((count + 1))
echo "$count" > "$COUNT_FILE"

logger "SEMA: USB Ethernet missing. Reboot attempt $count/$MAX_REBOOTS"

if [ "$count" -le "$MAX_REBOOTS" ]; then
    reboot
else
    logger "SEMA: USB Ethernet still missing after $MAX_REBOOTS attempts."
    exit 1
fi
```

---

## Nastavenie práv

```bash
chmod +x /home/jan/sema/scripts/check-usb-ethernet.sh
```

---

## Systemd služba

Vytvoriť:

```bash
sudo nano /etc/systemd/system/check-usb-ethernet.service
```

Obsah:

```ini
[Unit]
Description=SEMA USB Ethernet Watchdog
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/home/jan/sema/scripts/check-usb-ethernet.sh

[Install]
WantedBy=multi-user.target
```

---

## Aktivácia

```bash
sudo systemctl daemon-reload

sudo systemctl enable check-usb-ethernet.service
```

---

## Kontrola

```bash
systemctl status check-usb-ethernet.service --no-pager
```

---

## Správanie

Po každom boote:

```text
Boot
↓
20 sekúnd čakanie
↓
Kontrola USB Ethernet adaptéra
↓
Adaptér nájdený
    ↓
pokračovať

alebo

Adaptér nenájdený
    ↓
automatický reboot
    ↓
maximálne 10 pokusov
    ↓
ponechať systém bežať pre servisnú diagnostiku
```

---

## Diagnostika

Kontrola USB zariadení:

```bash
lsusb
```

Očakávaný výsledok:

```text
1a86:e396 QinHeng Electronics USB 10/100 LAN
```

Kontrola kernel logu:

```bash
dmesg | grep -iE "usb|error -71"
```

Typická chyba:

```text
device descriptor read/64, error -71
```

# 32. Automatické generovanie SSH host keys

Cieľ:

Po flashnutí Golden Image musí každé zariadenie automaticky vygenerovať vlastné unikátne SSH host keys.

SSH host keys sa pred vytvorením image zámerne odstránia:

```bash
sudo rm /etc/ssh/ssh_host_*
```

Aby SSH fungovalo bez manuálneho zásahu po prvom boote, vytvorí sa firstboot skript a systemd väzba pred štartom SSH služby.

---

## Firstboot skript

Súbor:

```bash
/usr/local/bin/sema-firstboot.sh
```

Vytvorenie:

```bash
sudo nano /usr/local/bin/sema-firstboot.sh
```

Obsah:

```bash
#!/bin/bash

set -e

if ! ls /etc/ssh/ssh_host_* >/dev/null 2>&1; then
    echo "SSH host keys not found. Generating..."
    ssh-keygen -A
fi
```

Práva:

```bash
sudo chmod +x /usr/local/bin/sema-firstboot.sh
```

---

## Firstboot systemd služba

Súbor:

```bash
/etc/systemd/system/sema-firstboot.service
```

Vytvorenie:

```bash
sudo nano /etc/systemd/system/sema-firstboot.service
```

Obsah:

```ini
[Unit]
Description=SEMA First Boot Tasks
Before=ssh.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/sema-firstboot.sh

[Install]
WantedBy=multi-user.target
```

---

## SSH override

Súbor:

```bash
/etc/systemd/system/ssh.service.d/override.conf
```

Vytvorenie:

```bash
sudo systemctl edit ssh.service
```

Obsah:

```ini
[Unit]
Requires=sema-firstboot.service
After=sema-firstboot.service
```

Pozor:

Do override súboru vložiť iba uvedený blok nad riadok:

```text
### Edits below this comment will be discarded
```

---

## Aktivácia

```bash
sudo systemctl daemon-reload
sudo systemctl enable sema-firstboot.service
```

---

## Test

```bash
sudo rm /etc/ssh/ssh_host_*
sudo reboot
```

Po reboote overiť:

```bash
ls -l /etc/ssh/ssh_host_*
systemctl status ssh --no-pager
```

Očakávaný výsledok:

```text
SSH host keys existujú
ssh.service je active (running)
```

---

## Výsledok

Po flashnutí Golden Image:

```text
Boot
↓
sema-firstboot.service
↓
ssh-keygen -A
↓
ssh.service
↓
SSH funguje bez manuálneho zásahu
```

# 33. Golden Image

Pred vytvorením image:

### Odhlásiť Tailscale

```bash
sudo tailscale logout
sudo systemctl stop tailscaled
sudo rm -rf /var/lib/tailscale
```

### Odstrániť zákaznícke WiFi

```bash
sudo nmcli connection delete NAZOV_WIFI
```

### Vymazať SSH host keys

```bash
sudo rm /etc/ssh/ssh_host_*
```

### Vyčistiť databázu

```bash
rm ~/sema/backend/data.db
```

### Vypnúť Raspberry Pi

```bash
sudo shutdown now
```

---

## Kompletný cleanup

```bash
sudo tailscale logout

sudo systemctl stop tailscaled

sudo rm -rf /var/lib/tailscale

sudo nmcli connection delete SEKAN

sudo rm /etc/ssh/ssh_host_*

rm ~/sema/backend/data.db

sudo shutdown now
```

---

## Po prvom boote novej jednotky

```
Boot
↓

SEMA Firstboot

↓

SSH Host Keys

↓

SEMA Dashboard

↓

SEMA Auto Update (3 min)

↓

SEMA-Setup

↓

WifiSetup

↓

Pripojenie do WiFi

↓

Tailscale

↓

Hotovo
```

---

## Overenie úspešného nasadenia

Musí fungovať:

- Dashboard
- Login
- Grafy
- Settings
- Ethernet komunikácia
- AP Fallback
- Automatické opätovné pripojenie WiFi
- WifiSetup
- Tailscale
- Auto Update
- USB Ethernet Watchdog
- SSH Firstboot
- Git Update Workflow
- Nginx Reverse Proxy

Ak všetky body fungujú, Golden Image je pripravený na distribúciu.
