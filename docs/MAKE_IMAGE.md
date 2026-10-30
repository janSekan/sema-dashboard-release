# Vytvorenie Image z SD karty

### 1. Zistenie ako je označená karta

```bash
lsblk
```

Bude tam niečo ako **sda** alebo **sdb**

### 2. Odpojíme partície

```bash
sudo umount /dev/sda1
sudo umount /dev/sda2
```

Overíme či sú partície odpojené

```bash
lsblk
```

### 3. Vytvorenie image-u

```bash
sudo dd if=/dev/sda of=~/Images/IMAGE.img bs=4M status=progress conv=fsync
```

Kde:

- if=/dev/**sda** = zdroj (celá SD karta) (podľa bodu 1)
- of=...img = umiestenie a názov výstupného image
- bs=4M = veľkosť bloku pre rýchlejšie kopírovanie
- status=progress = priebežný progres
- conv=fsync = korektné zapísanie dát pred ukončením

### 4. Zmenšenie imagu

Pri vytvorení má image velkosť celej SD karty (16GB/32GB/64GB)

Ak nemáme nainštalujeme **PiShrink**

```bash
git clone https://github.com/Drewsif/PiShrink.git
cd PiShrink
```

Zmenšenie na minimálnu velkosť

```bash
sudo ./pishrink.sh ~/Images/IMAGE.img
```
