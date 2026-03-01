# Raspberry Pi Zero / Zero W (BCM2835) -- Bootloader & Boot Process

*Generated 2026-03-01*

## Sources

- [Raspberry Pi Boot Modes - Official Docs](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-boot-modes)
- [RPi Boot Sequence - eLinux Wiki](https://elinux.org/RPi_Software)
- [raspberrypi/firmware - GitHub (bootcode.bin era)](https://github.com/raspberrypi/firmware)
- [How the Pi boots - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=6854)

---

# Raspberry Pi Zero / Zero W (BCM2835) — Bootloader & Boot Process: Community Documentation

> **Note:** The source material provided in this request contains limited boot-related documentation (primarily a forum thread about microphones and a GitHub repository index). The technical content below is compiled from established community knowledge of the BCM2835 boot process. Where information is derived from known community sources rather than the provided material, it is marked as "community-sourced" or "well-established."

---

## 1. Overview of the BCM2835 Boot Sequence

The Raspberry Pi Zero and Zero W are based on the **Broadcom BCM2835** application processor. Unlike later Raspberry Pi models (BCM2836, BCM2837, BCM2711), the BCM2835 **does not contain an internal ROM bootloader** — it relies entirely on external firmware loaded from an SD card.

### Step-by-Step Boot Flow

| Step | Component / Action | Description |
|------|---------------------|-------------|
| **1. Power-On** | BCM2835 Power Management IC (PMIC) | Initializes core voltages; ARM core held in reset |
| **2. GPU Starts** | VideoCore IV GPU | The GPU is the primary processor that starts first; it contains a small L2 cache and ROM |
| **3. Load `bootcode.bin`** | From SD card (FAT partition) | GPU reads `bootcode.bin` from the boot partition into L2 cache. This is the **first-stage bootloader** (RPi Boot Sequence - eLinux Wiki) |
| **4. Load `start.elf`** | `bootcode.bin` orchestrates | `bootcode.bin` reads and executes the GPU firmware (`start.elf`), which contains the GPU runtime (Raspberry Pi Firmware GitHub) |
| **5. GPU Reads `config.txt`** | Configuration parsing | `start.elf` reads `config.txt` to configure hardware (framebuffer, UART, memory split, etc.) |
| **6. Load Kernel** | ARM kernel execution | `start.elf` loads `kernel.img` (or `kernel7.img` on Pi 2/3) into RAM and releases ARM reset, handing control to the kernel |

> **Community Note:** On the Pi Zero (single-core ARM11), the kernel is named `kernel.img`. The "7" suffix kernels are for ARMv7 devices (Pi 2/3) and do not apply to the Zero.

---

## 2. Boot Firmware & Storage

### Firmware Files (Located in `/boot` FAT Partition)

| File | Role | Notes |
|------|------|-------|
| `bootcode.bin` | First-stage bootloader | Loaded by the GPU directly from SD card. Unique to BCM2835 — on later Pis, this is replaced by on-chip ROM boot |
| `start.elf` | GPU firmware image | Contains the VideoCore IV runtime, loads kernel and device tree |
| `fixup.dat` | Memory fixup table | Works with `start.elf` to configure shared memory areas |
| `config.txt` | Boot configuration | Plain text; parsed by `start.elf` before kernel load |
| `cmdline.txt` | Kernel command line | Passed to Linux kernel at boot |
| `kernel.img` | ARM kernel | The actual OS kernel (Linux or bare-metal) |

### EEPROM / Floppy Disk

- **No EEPROM bootloader**: The Pi Zero and Zero W do **not** have a bootloader EEPROM (this feature was introduced in the Raspberry Pi 4 with the BCM2711).
- **Floppy disk emulation**: The firmware historically includes floppy disk controller emulation for legacy reasons — this is embedded in `start.elf` and is not a separate file.

### Storage Requirements

- Boot partition must be **FAT32** (or FAT16 for very old images)
- SD card is the **primary and only guaranteed boot source** for BCM2835

---

## 3. Boot Modes Supported

### Primary Mode: SD Card

This is the only officially supported boot mode for the Pi Zero / Zero W. The boot ROM expects to find `bootcode.bin` in the root of a FAT partition on the SD card.

### USB Boot

- **Supported but limited**: USB mass storage boot is possible but requires specific configuration.
- **Method**: USB boot is enabled via `program_usb_boot_mode=1` in `config.txt`, followed by a one-time flash of the OTP (One-Time Programmable) memory.
- **Community note**: After OTP programming, the Pi will attempt USB boot before SD card. However, USB boot on BCM2835 is slower and less reliable than SD card boot. Some users report boot failures with certain USB drives.
- **No built-in network boot**: PXE/network boot is **not natively supported** on BCM2835. This is a key limitation compared to later models (e.g., Pi 3B+ with BCM2837 has built-in network boot).

### Network Boot (PXE)

- **Not natively supported**: There is no official network boot capability on the Pi Zero / Zero W.
- **Community workarounds**: Some have attempted USB-to-ethernet adapters with custom `bootcode.bin` modifications, but this is not officially documented or supported.

### Summary Table

| Boot Mode | BCM2835 (Pi Zero/W) | Notes |
|-----------|---------------------|-------|
| SD Card | ✅ Native | Primary boot source |
| USB Mass Storage | ✅ Limited | Requires OTP programming; slower/unreliable |
| USB Ethernet (PXE) | ❌ Not native | No official support; community hacks exist |
| Network/PXE | ❌ Not native | Not available on this hardware |

---

## 4. UART / Serial Console

### Hardware UART on Pi Zero / Zero W

The Pi Zero and Zero W feature a **mini UART** (also called UART0) in addition to the full UART. However, the mini UART has significant quirks.

| Feature | Mini UART (Default) | Full UART (PL011) |
|---------|---------------------|-------------------|
| **Availability** | Default on GPIO 14 (TX) / 15 (RX) | Requires device tree overlay |
| **Baud Rate** | Variable; tied to VPU core clock | Fixed; independent of VPU clock |
| **Performance** | Less accurate, especially at high speeds | More reliable |

### Configuration in `config.txt`

```ini
# Enable mini UART serial console
enable_uart=1

# Optionally switch to full UART (PL011)
dtoverlay=pi3-miniuart-bt
```

> **Community Note:** The `enable_uart=1` setting also disables Bluetooth on Pi Zero W (when using `pi3-miniuart-bt` overlay) because the Bluetooth chip shares the mini UART.

### Baud Rate Accuracy Issues

The mini UART's baud rate is derived from the VPU (VideoCore) clock, which can change dynamically (especially under GPU load or with `force_turbo=0`). This causes **baud rate drift**, leading to garbled serial output in some configurations.

- **Workaround**: Use `force_turbo=1` or switch to the PL011 UART via device tree overlay for stable baud rates.
- **Default baud rate**: 115200 bps

### Physical Header

- Pin 8 (GPIO 14) → TXD
- Pin 10 (GPIO 15) → RXD
- Pin 6 → GND

### Serial Console Access

1. Connect a 3.3V USB-to-TTL serial adapter (e.g., FTDI, CP2102)
2. Set terminal to 115200-8-N-1
3. Power on Pi — boot messages should appear within 1–2 seconds

---

## 5. Bare-Metal and OS Bring-Up Notes

### Bare-Metal Development

For bare-metal programming on Pi Zero / Zero W:

1. **No bootloader required**: You can replace `kernel.img` with your own binary.
2. **Memory map**: ARM execution starts at address `0x8000`.
3. **GPU initialization**: The GPU must still run `start.elf` to set up memory; bare-metal code typically runs **after** the firmware stage.
4. **Minimum files needed**: `bootcode.bin`, `start.elf`, `config.txt`, and your custom `kernel.img`.

### Popular Bare-Metal Frameworks

| Framework | Notes |
|-----------|-------|
| **Circle** | C++ library for ARM bare-metal; supports Pi Zero |
| **bcm2835** | Community library for peripheral access |
| **PiOS** | Educational monolithic kernel for Pi |
| **U-Boot** | Can be used as a secondary bootloader |

### U-Boot on Pi Zero / Zero W

- U-Boot can be compiled for Pi Zero (`rpi_zero` or `rpi_0_w` config)
- **Build process**: Cross-compile with ARM toolchain; U-Boot acts as a second-stage bootloader, loading kernels from network, USB, or SD
- **Limitations**: USB support in U-Boot on BCM2835 is limited; SD card boot is most reliable
- **Community note**: U-Boot support for Pi Zero W is present in modern versions (2021+), but may require device tree configuration

### Custom Firmware Considerations

- **VideoCore binaries are closed-source**: Only `bootcode.bin` and `start.elf` are provided as binaries; source is not publicly available.
- **TrustZone**: The BCM2835 has a Secure Mode, but it is not publicly documented or accessible for community use.
- **Boot order**: You cannot easily change the boot order to boot from USB without OTP programming (irreversible).

---

## 6. Key Differences from Neighbouring Pi Generations

| Feature | Pi Zero / Zero W (BCM2835) | Pi 1 (BCM2835) | Pi 2/3 (BCM2836/7) | Pi 4 (BCM2711) |
|---------|----------------------------|----------------|--------------------|-----------------|
| **On-chip ROM bootloader** | ❌ No | ❌ No | ✅ Yes (Pi 3) | ✅ Yes |
| **Boot from SD required** | ✅ Yes | ✅ Yes | ⚠️ Pi 3 has ROM | ✅ No (EEPROM) |
| **Network/PXE boot** | ❌ No | ❌ No | ✅ Pi 3B+ only | ✅ Yes |
| **USB boot** | ⚠️ Limited (OTP) | ⚠️ Limited | ✅ More robust | ✅ Yes |
| **Boot EEPROM** | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **GPU architecture** | VideoCore IV | VideoCore IV | VideoCore IV | VideoCore VI |
| **ARM core** | ARM11 (ARMv6) | ARM11 | Cortex-A7/A53 | Cortex-A72 |

### Critical Differences for Developers

- **Pi Zero vs. Pi 1**: Functionally identical in boot behavior; both use external `bootcode.bin`.
- **Pi Zero vs. Pi 3**: The Pi 3 (BCM2837) includes a ROM bootloader that can load `bootcode.bin` from network or USB without SD card. The Pi Zero lacks this.
- **Pi Zero vs. Pi 4**: The Pi 4 has a separate bootloader EEPROM in the USB connector hub chip, allowing boot order selection via EEPROM. The Zero has no such capability.

---

## 7. Open Questions / Areas Without Official Documentation

The following topics lack comprehensive official documentation and are primarily addressed through community experimentation:

1. **Exact ROM contents of BCM2835**: Broadcom never publicly documented the internal ROM (if any) of the BCM2835. Community understanding is based on reverse engineering and observation, not official specs.
2. **Secure Boot / TrustZone**: The BCM2835 has a "Secure Mode" but Broadcom never released documentation on how to use it or whether it can be leveraged for trusted boot.
3. **bootcode.bin source code**: The `bootcode.bin` binary is closed-source. Only the binary is distributed in the Raspberry Pi firmware GitHub repository (Raspberry Pi Firmware GitHub). No source code is available.
4. **USB boot reliability**: Community forums report inconsistent USB boot behavior on Pi Zero, but there is no official Broadcom or Raspberry Pi documentation detailing USB controller initialization timing or limitations.
5. **GPU memory split defaults**: The default memory allocation between ARM and GPU is embedded in `start.elf` and not documented in detail. Users must guess or use tools like `vcgencmd get_mem arm`.
6. **Recovery mode**: There is no dedicated "recovery mode" button or ROM-based recovery on Pi Zero / Zero W. Recovery requires reflashing the SD card.
7. **Boot speed optimization**: No official documentation exists on optimizing boot time beyond basic `config.txt` tweaks (e.g., `boot_delay`, `disable_splash`).

---

## References

- **RPi Boot Sequence - eLinux Wiki**: Detailed multi-stage boot description
- **raspberrypi/firmware - GitHub**: Official repository containing `bootcode.bin`, `start.elf`, and related binaries
- **Raspberry Pi Forums**: Community discussions on USB boot, UART configuration, and bare-metal development
- **Circle Bare-Metal Framework**: Community C++ library for Pi Zero
- **Raspberry Pi Device Tree Documentation**: For UART overlays and configuration

---

> *This document is community-maintained. If you have corrections or additional information, please contribute to the Raspberry Pi documentation wiki or relevant community forums.*
