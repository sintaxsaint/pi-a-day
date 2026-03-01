# Compute Module 5 (BCM2712) -- Bootloader & Boot Process

*Generated 2026-03-01*

## Sources

- [Pi 5 Boot Process - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=373222)
- [kernel_2712.img - DeepWiki](https://deepwiki.com/raspberrypi/firmware/2.1.5-raspberry-pi-5-kernel-(kernel_2712.img))
- [Supporting Pi 5 - Circle Discussion #413](https://github.com/rsta2/circle/discussions/413)
- [UART on Pi 5 GPIO 14/15 - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=378931)

---

# Compute Module 5 (BCM2712) — Bootloader & Boot Process: Community Documentation

**Target Hardware:** Compute Module 5 (CM5) — BCM2712 SoC  
**Scope:** Bootloader architecture, firmware storage, boot modes, serial console, and bare-metal bring-up  
**Audience:** Embedded developers, system integrators, and hobbyists working with CM5 hardware  

---

> **Note:** This document synthesizes community-contributed information from forums, GitHub discussions, and experimental documentation. Where details are unconfirmed or derived from inference, they are marked as *community-sourced* or *unverified*. Official Raspberry Pi documentation should be consulted for definitive specifications.

---

## 1. Overview of the BCM2712 Boot Sequence

The boot process on BCM2712 (Raspberry Pi 5 and Compute Module 5) differs substantially from earlier generations. Unlike the Pi 4, which relied on `bootcode.bin` loaded from an SD card or SPI flash, the CM5 implements a **multi-stage internal ROM + SPI flash** bootloader with no external `bootcode.bin` requirement on boot media.

### Step-by-Step Boot Flow

1. **Power-On / Reset**
   - The BCM2712 SoC begins execution from an **on-chip boot ROM** located on the VideoCore (VPU) processor.
   - This ROM is mask-programmed and cannot be modified.

2. **SPI Flash Loader (Stage 1)**
   - The boot ROM reads a **tagged binary blob** from the external SPI flash chip (mounted on the Compute Module board).
   - This blob contains initialization code that brings the **LPDDR4 memory controller** online.

3. **bootmain.elf Execution (Stage 2)**
   - After memory initialization, the blob loads `bootmain.elf` from SPI flash and transfers control to it.
   - This stage is analogous to the legacy `bootcode.bin` on earlier Pi models but resides in SPI flash rather than on removable media.

4. **Boot Configuration Reading**
   - `bootmain.elf` reads `bootconf.txt` stored in SPI flash.
   - This configuration file contains the **BOOT_ORDER** parameter, which defines the boot device priority (e.g., SD → USB → network).

5. **Boot Device Selection & Kernel Load**
   - Based on BOOT_ORDER, the bootloader attempts to boot from the selected media (SD card, USB, or network).
   - The bootloader reads `config.txt` and the kernel image from the boot media.
   - Control is handed to the kernel (or bare-metal application) at the configured load address.

> **Source:** "Pi5 Boot Process" — Raspberry Pi Forums (cleverca22, Jul 2024)

---

## 2. Boot Firmware & Storage

### SPI Flash Organization

The Compute Module 5 includes an **SPI flash chip** (typically 512KB to 2MB, board-dependent) that stores the bootloader components:

| Component | Location | Description |
|-----------|----------|-------------|
| Boot ROM | BCM2712 internal | Mask-Programmed; cannot be modified |
| Tagged blob | SPI flash | Initializes LPDDR4 memory controller |
| bootmain.elf | SPI flash | Main bootloader; reads bootconf.txt |
| bootconf.txt | SPI flash | Contains BOOT_ORDER and flash-level config |

### Firmware Equivalents — No External ELF/DAT Files

Unlike earlier Raspberry Pi models:

- **CM5 does NOT require `bootcode.bin`** — this file is not used and cannot be executed by the VPU.
- **CM5 does NOT require `start.elf` or `fixup.dat`** — these were used on Pi 0–3.
- **CM5 does NOT require `start4.elf` or `fixup4.dat`** — these were used on Pi 4.
- The **functionality previously provided by these files is now stored in SPI flash** and loaded by `bootmain.elf`.

> "start.elf and fixup.dat are only valid on the pi0-pi3. start4.elf and fixup4.dat are only valid on the pi4 family. and pi5 just doesnt need any elf or dat, its all in SPI flash."
> — *procount, "Pi5 Boot Process" — Raspberry Pi Forums*

### Boot Media File Requirements

For bootable SD cards or USB drives, the following minimal file set is required:

- `config.txt` — Boot configuration (kernel name, device tree, memory settings)
- Kernel image — Typically `kernel8.img` (64-bit bare-metal or Linux kernel)
- Device Tree Blob (optional in some bare-metal scenarios) — `bcm2712-rpi-5-b.dtb`

> **Community observation:** "It's true that only bcm2712-rpi-5-b.dtb and config.txt are needed on the SD card."
> — *satyria, "Pi5 Boot Process" — Raspberry Pi Forums*

---

## 3. Boot Modes Supported

The BCM2712 bootloader supports multiple boot modes, configurable via the **BOOT_ORDER** setting in SPI flash (`bootconf.txt`).

| Boot Mode | Description | Availability on CM5 |
|-----------|-------------|---------------------|
| **SD Card (eMMC/SDIO)** | Boot from on-board eMMC or external SD card slot | ✅ Supported |
| **USB Mass Storage** | Boot from USB drive (HDD, SSD, flash drive) | ✅ Supported |
| **Network / PXE** | Boot over Ethernet via DHCP + TFTP | ✅ Supported (community-confirmed) |
| **SPI Flash** | Fallback; primary firmware storage | ✅ Always used |

### BOOT_ORDER Configuration

The BOOT_ORDER parameter in `bootconf.txt` specifies a sequence of boot attempts. A typical order for general-purpose use is:

```
BOOT_ORDER=0xf46148d
```

Which typically translates to: SD → USB → Network → SPI flash (in order of priority).

### Network Boot

Community discussion confirms that **network boot (PXE) is functional** on Pi 5 / CM5:

> "PS: btw, I'm booting over the network - easier workflow for me!"
> — *pottendo, Circle GitHub Discussion #413*

Network boot requires:

- A DHCP server on the network
- A TFTP server serving `config.txt`, kernel image, and device tree blob
- Ethernet connectivity on the CM5 (via on-board PHY or USB Ethernet adapter, depending on CM5 variant)

---

## 4. UART / Serial Console — Configuration and Quirks

### Default Serial Output: ttyS11

On the Compute Module 5 (BCM2712), the **default serial console is on the dedicated UART connector** (ttyS11), not the legacy GPIO pins 14/15 (ttyS1). This is a departure from earlier Pi models.

> "On the RPi 5 the serial console is by default the dedicated UART connector ('ttyS11')."
> — *rsta2, Circle GitHub Discussion #413*

### Using Legacy GPIO UART (ttyS1)

To redirect the serial console to GPIO pins 14/15 (the traditional UART pins), the following configuration is required:

**For bare-metal Circle framework:**
```makefile
DEFINE += -DSERIAL_DEVICE_DEFAULT=0
```

> *Source: Circle GitHub Discussion #413 (rsta2, Feb 2024)*

### Bare-Metal Serial Configuration Notes

For bare-metal development:

- The default console on GPIO 14/15 is **ttyS1** (baud rate 115200, 8N1).
- If using the dedicated mini-UART connector on the CM5 IO board, it appears as **ttyS11**.
- Ensure your `config.txt` specifies the correct `kernel_address` to avoid loading issues.

### UART Availability on Compute Module 5

The CM5 has two UARTs available:

- **Mini UART (ttyS1)** — mapped to GPIO 14/15; requires configuration
- **PL011 UART (ttyS11)** — dedicated UART connector on CM5 IO board; default console

---

## 5. Bare-Metal and OS Bring-Up Notes

### Minimal config.txt for Bare-Metal

The following is the **minimum viable `config.txt`** for bare-metal bring-up on CM5:

```ini
kernel_address=0x80000
kernel=kernel_2712.img
os_check=0
```

- **`kernel_address=0x80000`**: Loads the kernel at the standard ARM64 load address. Without this, the firmware may load the image at `0x200000` and attempt Linux-specific behavior.
- **`os_check=0`**: Disables OS validation checks. Without this, the firmware assumes a Linux kernel and may load at the wrong address or attempt to load a device tree automatically.
- **`kernel=kernel_2712.img`**: Specifies the kernel filename (default is `kernel8.img`).

> "Actually you only need config.txt to boot a Pi 5, in addition to your kernel / bare metal application which should be named kernel8.img by default, but you'll have to add os_check=0 to config.txt, as otherwise it assumes that you're booting Linux, so it will run your code from 0x200000 instead of 0x80000, and will try loading the device tree blob."
> — *Fridux, "Pi5 Boot Process" — Raspberry Pi Forums*

### Device Tree Blob (DTB)

For bare-metal use, the device tree blob (`bcm2712-rpi-5-b.dtb`) may or may not be required:

- If using `os_check=0`, the bootloader does not mandate DTB loading.
- For full hardware initialization (e.g., to access board-specific peripherals), the DTB is recommended.
- Community testing shows bare-metal images can boot with only `config.txt` and the kernel image.

### Bare-Metal Framework Support

**Circle** (a popular bare-metal C++ framework for Raspberry Pi) supports CM5 on the `rpi5` branch:

- Requires `kernel_address=0x80000` in `config.txt`
- For headless operation, add `DEFINE += -DSCREEN_HEADLESS` in `Config.mk`
- Network boot is confirmed working with Circle on CM5

> "Serial works also again - on pins 14/15. I managed to merge this into circle-stdlib and even my app starts doing something..."
> — *pottendo, Circle GitHub Discussion #413*

### Known Bare-Metal Quirks

- **HDMI/Display output**: Many configuration options available on earlier Pis are not honored by the CM5 firmware. The Linux kernel now handles display output; bare-metal frameworks relying on firmware-provided graphics may have limited display compatibility.
- **USB/Ethernet**: Some bare-metal frameworks (including Circle) require code adoption for CM5's USB and Ethernet drivers (`#if RASPPI <= 4` guards may need removal).
- **Dynamic frequency scaling**: The CM5 may change ARM core frequency dynamically; bare-metal code should account for variable clock speeds or disable DVFS if timing-critical.

---

## 6. Key Differences from Neighbouring Pi Generations

| Feature | Pi 4 (BCM2711) | CM5 / Pi 5 (BCM2712) |
|---------|----------------|----------------------|
| Boot ROM | On-chip VPU | On-chip VPU (updated) |
| Boot firmware location | SPI flash + SD card | **SPI flash only** (no `bootcode.bin` on SD) |
| Required boot files | `bootcode.bin`, `config.txt`, `start4.elf`, `fixup4.dat` | **`config.txt` + kernel only** |
| Memory controller | LPDDR4 | LPDDR4 (initialized by SPI blob) |
| Default kernel load address | `0x80000` (or `0x200000` for 64-bit) | **`0x80000` (requires explicit config)** |
| Serial console default | ttyS1 (GPIO 14/15) | **ttyS11** (dedicated connector) |
| Boot modes | SD, USB, network, SPI | SD, USB, network, SPI |
| OS validation (`os_check`) | Optional | **Recommended `os_check=0` for bare-metal** |
| Display firmware support | Full (start4.elf) | Limited (handled in Linux kernel) |

### Summary of Key Changes

1. **No external bootloader files on boot media** — All firmware resides in SPI flash; no `bootcode.bin` or `start*.elf` needed.
2. **SPI flash is mandatory** — Even for SD boot, the primary firmware chain runs from SPI flash first.
3. **Default kernel address changed** — Without `kernel_address=0x80000`, bare-metal images may be loaded incorrectly.
4. **Serial console moved** — Default is now ttyS11, not the legacy GPIO UART.
5. **Network boot functional** — Unlike early Pi 4 revisions, network boot works reliably on CM5.

---

## 7. Open Questions / Areas Without Official Documentation

The following topics remain **unconfirmed or poorly documented** in official Raspberry Pi materials. Community experimentation has provided partial answers, but definitive specifications are not available.

| Area | Status | Notes |
|------|--------|-------|
| **SPI flash layout specification** | ⚠️ Unverified | No public document describes exact offsets or structure of bootconf.txt or boot blob format. |
| **BOOT_ORDER bitfield encoding** | ⚠️ Community-sourced | Known to control boot priority; exact bitfield values are inferred, not officially documented. |
| **bootconf.txt full options** | ⚠️ Unverified | Only BOOT_ORDER is widely discussed. Other options (if any) are unknown. |
| **eMMC boot vs SD card boot differences** | ⚠️ Unknown | Unclear if there are separate boot paths for on-board eMMC vs external SD. |
| **Secure boot / signed firmware** | ❓ No information | No public info on secure boot implementation for BCM2712. |
| **Recovery mode procedures** | ⚠️ Partial | Holding `FIT` or `RUN` pins during boot can trigger recovery; exact procedure for CM5 not widely published. |
| **GPU/VPU firmware source** | ❓ Not available | The tagged blob and bootmain.elf are not open-source; no public disassembly or documentation. |
| **USB device boot (not host)** | ❓ Unknown | It is unclear if CM5 can boot as a USB peripheral (device mode). |
| **PCIe boot** | ❓ Not applicable | CM5 does not have PCIe; this is not a boot mode. |
| **JTAG debug availability** | ⚠️ Unverified | No clear documentation on ARM CoreSight/JTAG debug access on CM5. |

### Recommendations for Developers

- **Experiment cautiously**: Many bootloader behaviors are discovered through community trial-and-error.
- **Use official Raspberry Pi imager** for flashing CM5 bootloader EEPROM updates when available.
- **Monitor the Raspberry Pi forums** for new discoveries; the community is the primary source of CM5 bootloader insight.
- **Reference Pi 5 documentation** — While not identical, Pi 5 (standard form factor) shares the same BCM2712 SoC and bootloader architecture; many findings apply to CM5.

---

## Appendix: Minimal config.txt Example for Bare-Metal CM5

```ini
# Minimal config.txt for bare-metal on Compute Module 5 (BCM2712)
kernel_address=0x80000
kernel=kernel_2712.img
os_check=0
# Optional: specify device tree explicitly
# device_tree=bcm2712-rpi-5-b.dtb
```

---

*This document is community-maintained. Last updated: based on source material collected November 2025.*
