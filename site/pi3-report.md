# Raspberry Pi 3 (BCM2837) -- Bootloader & Boot Process

*Generated 2026-03-01*

## Sources

- [Pi 3 USB / Network Boot - Official Docs](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#pi-3-only-bootcode-bin-usb-boot)
- [raspberrypi/usbboot - GitHub (BCM2837 USB boot ROM)](https://github.com/raspberrypi/usbboot)
- [RPiconfig boot options - eLinux Wiki](https://elinux.org/RPiconfig)
- [BCM2837 64-bit boot thread - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=174648)

---

# Raspberry Pi 3 (BCM2837) — Bootloader & Boot Process: Community Documentation

> **Important Note**: This document covers the Raspberry Pi 3 family using the BCM2837 SoC: Pi 3 Model B, Pi 3 Model B+, Pi 3 Model A+, and Pi 2 Model B v1.2. It does not cover BCM2835, BCM2836, or later generations (BCM2711, etc.).

---

## 1. Overview of the BCM2837 Boot Sequence

The BCM2837 SoC contains an embedded boot ROM that executes immediately on power-on or reset. This ROM is hardcoded into the silicon and cannot be modified. The boot process proceeds through multiple stages, involving both the ARM cores and the VideoCore IV GPU.

### Step-by-Step Boot Flow

1. **Power-On / Reset**
   - The BCM2837 begins execution from a fixed address in the internal boot ROM (0x00000000).
   - The boot ROM performs initial hardware initialization (PLLs, SDRAM controller calibration).

2. **Boot Mode Selection**
   - The ROM checks boot mode selection pins (or OTP bits) to determine the boot source.
   - Supported boot sources are tried in a defined order (see Section 3).

3. **First Stage: Loading `bootcode.bin`**
   - On Pi 3 devices, the ROM reads the first FAT-formatted partition on the SD card (or equivalent boot device).
   - It loads `bootcode.bin` into the L2 cache (or SRAM on some variants).
   - *Note*: On Pi 3B+ and Pi 3A+, `bootcode.bin` may be replaced by OTP-enabled EEPROM boot behavior (see Section 2).

4. **Second Stage: GPU Firmware (`start.elf` and variants)**
   - `bootcode.bin` enables the SDRAM and loads the VideoCore firmware (`start.elf`) from the boot partition.
   - The GPU begins execution and configures the ARM cores' memory layout.
   - Additional firmware files are loaded:
     - `fixup.dat` — memory split configuration
     - `config.txt` — parsed for hardware configuration
     - `cmdline.txt` — kernel command line passed to the ARM core

5. **Third Stage: Loading the Kernel**
   - The GPU loads the kernel image (typically `kernel8.img` for 64-bit, `kernel7.img` for 32-bit) into SDRAM.
   - Device tree blobs (`.dtb`) or device tree overlays may also be loaded.
   - The GPU then releases the ARM cores from reset, passing control to the loaded kernel.

6. **Kernel Handoff**
   - The ARM core(s) begin execution at the kernel entry point.
   - The Linux kernel (or bare-metal payload) takes over all further control.

> **Source**: Raspberry Pi Documentation — "Boot sequence" and "Raspberry Pi boot EEPROM" (Raspberry Pi Ltd.)

---

## 2. Boot Firmware & Storage

### SD Card — The Primary Boot Medium

On the Raspberry Pi 3 family, the SD card remains the primary and most well-documented boot medium. The boot partition must be:

- **FAT32** formatted (typically the first partition, flagged as bootable)
- Located in the first portion of the SD card
- Containing the required firmware files

### Required Boot Files

| File | Purpose |
|------|---------|
| `bootcode.bin` | First-stage bootloader — initializes SDRAM, loads start.elf |
| `start.elf` | VideoCore firmware — main GPU bootloader |
| `fixup.dat` | Memory split configuration between GPU and ARM |
| `config.txt` | Hardware configuration (video, UART, overclock, boot options) |
| `cmdline.txt` | Kernel command line (single line, no line breaks) |
| `kernel8.img` | 64-bit ARM kernel (Pi 3 64-bit mode) |
| `kernel7.img` | 32-bit ARM kernel (default) |
| `*.dtb` | Device tree blobs for hardware description |

> **Source**: Raspberry Pi Documentation — "boot folder contents" (Raspberry Pi Ltd.)

### EEPROM Boot — Pi 3B+ and Pi 3A+

The **Pi 3 Model B+** and **Pi 3 Model A+** introduced bootloader EEPROM support, though it functions differently than on Pi 4:

- **Pi 3B+** has a bootloader stored in OTP (One-Time Programmable) memory that can load `bootcode.bin` from SD card, or — if boot from network/USB is OTP-enabled — from those sources.
- **Pi 3A+** similarly supports EEPROM-based boot modes, but the mechanism is more constrained than on Pi 4.
- **Pi 2 Model B v1.2** uses the same BCM2837 SoC as Pi 3 and behaves identically to Pi 3B for boot purposes.

> **Note**: The Raspberry Pi 3 family does **not** have a user-updateable SPI flash EEPROM like Pi 4. The bootloader is burned into OTP bits during manufacturing or via the `raspberrypi-utils` tools.

> **Source**: Raspberry Pi Documentation — "Raspberry Pi boot EEPROM" (Raspberry Pi Ltd.)

### Firmware Variants

The `start.elf` has several variants controlling GPU memory split:

- `start.elf` — default split
- `start_cd.elf` — minimal GPU (for headless/compute use)
- `start_x.elf` — includes camera and codec support
- `start_db.elf` — debug variant with verbose output

> **Source**: Raspberry Pi Documentation — "config.txt" (Raspberry Pi Ltd.)

---

## 3. Boot Modes Supported

The BCM2837 supports multiple boot modes, though availability varies by model and firmware version.

### SD Card Boot

- **Supported on**: All Pi 3 variants (B, B+, A+, Pi 2 v1.2)
- **Mechanism**: Boot ROM reads the first FAT partition on the SD card
- **Default behavior** for all models

### USB Boot

- **Supported on**: Pi 3B, Pi 3B+, Pi 3A+, Pi 2 v1.2
- **Requirements**:
  - OTP bit must be set to enable USB boot (`program_usb_boot_mode=1` in `config.txt` + reboot)
  - A suitable USB device (mass storage device) must be present
- **Behavior**: After the OTP bit is set, the boot ROM will attempt USB mass storage before falling back to SD card
- **Limitation**: USB boot on Pi 3 relies on the USB 2.0 controller, which must be initialized by the GPU firmware. Early-stage USB boot is slower than SD card boot.
- **Compatibility**: The `raspberrypi/usbboot` repository provides a host-side tool (`rpiboot`) for provisioning. However, note that the mass-storage-gadget firmware in the usbboot repo explicitly supports **Pi 3A+**, not Pi 3B/3B+ (which use the legacy msd firmware).

> **Source**: Raspberry Pi Documentation — "USB boot modes" and "Raspberry Pi boot modes" (Raspberry Pi Ltd.)  
> **Source**: GitHub — `raspberrypi/usbboot` README (noting compatible device list)

### Network Boot (PXE)

- **Supported on**: Pi 3B, Pi 3B+, Pi 3A+, Pi 2 v1.2
- **Requirements**:
  - OTP bit must be set for network boot
  - DHCP server and TFTP server on the network
  - Ethernet adapter (built-in on all Pi 3 models)
- **Mechanism**: The boot ROM broadcasts a DHCP request, receives an IP address and TFTP server details, then downloads `bootcode.bin` (or equivalent) over HTTP/TFTP
- **Implementation**: The Pi 3 uses the **network boot mode** which can operate over IPv4 (more common) or IPv6
- **Performance**: Network boot is generally slower than SD card boot but useful for diskless deployments

> **Source**: Raspberry Pi Documentation — "Network boot your Raspberry Pi" (Raspberry Pi Ltd.)

### Boot Order

The boot ROM attempts sources in a fixed priority order. The exact order on BCM2837:

1. **SD card** (primary, always attempted first)
2. **USB** (if OTP bit set)
3. **Network** (if OTP bit set; may be attempted in parallel or after USB failure)

The OTP bits control whether USB and network modes are even attempted. Once a valid bootable device is found, the process proceeds.

> **Source**: Raspberry Pi Documentation — "Raspberry Pi boot modes" (Raspberry Pi Ltd.)

---

## 4. UART / Serial Console — Configuration and Quirks

The Raspberry Pi 3 has specific UART configurations that differ from earlier models due to the integration of Bluetooth.

### Hardware UARTs on Pi 3

| UART | Device Node | Purpose |
|------|-------------|---------|
| **PL011** (primary) | `/dev/ttyS0` | Primary UART, pins 14/15 (GPIO 14/15) |
| **mini UART** | `/dev/ttyS0` (or `/dev/ttyAMA0` on earlier Pi) | Secondary UART, lower performance |

**Critical change on Pi 3**: The **mini UART** became the default for GPIO pins 14/15 (the familiar TXD/RXD pins). The **PL011** is now internally routed to Bluetooth. This is a significant difference from Pi 2.

### Enabling the Serial Console

1. Add to `config.txt`:
   ```
   enable_uart=1
   ```
   - On Pi 3, this enables the mini UART on GPIO 14/15
   - Disables Bluetooth if `dtoverlay=pi3-disable-bt` is also set

2. Add to `cmdline.txt` (kernel command line):
   ```
   console=serial0,115200
   ```

3. (Optional) Disable Bluetooth to free the PL011:
   ```
   dtoverlay=pi3-disable-bt
   ```
   This makes `/dev/ttyAMA0` available on the GPIO pins.

### Baud Rate and Timing Quirks

- The **mini UART** baud rate is derived from the core clock and can vary with overclocking settings, potentially causing baud rate mismatch.
- The PL011 (when available) is a more reliable full-featured UART with proper FIFO and baud rate control.
- **Flow control** (CTS/RTS) is not available on the GPIO header UARTs — only TX/RX (and ground) are exposed on pins.

### Boot Serial Output

The firmware (`bootcode.bin`, `start.elf`) outputs early boot messages to the primary UART (the one mapped to GPIO 14/15 at boot time). This output is useful for debugging boot failures:

- **Pi 3 default**: mini UART outputs at 115200 baud
- Messages include: firmware version, SDRAM initialization, partition detection, kernel load progress

### Known Issues

- **Bluetooth interference**: By default, Bluetooth uses the PL011, which shares the same pins as the GPIO UART. Without configuration, serial console on the header may not work or may output garbage if Bluetooth is active.
- **Pi 3B+ UART mapping**: Some community reports indicate that the UART mapping changed slightly between Pi 3B and Pi 3B+ firmware versions; always verify with `vcgencmd get_config str` .
- **Mini UART instability**: Under heavy system load or with certain `config.txt` settings (e.g., `core_freq` changes), the mini UART baud rate can drift.

> **Source**: Raspberry Pi Documentation — "Configure UARTs" (Raspberry Pi Ltd.)  
> **Source**: Community reports — Raspberry Pi Forums

---

## 5. Bare-Metal and OS Bring-up Notes

### Bare-Metal Development on BCM2837

Developing bare-metal code for the Pi 3 requires understanding the split between ARM and GPU responsibilities.

#### Option 1: Bypassing the GPU (ARM-only Boot)

- The Pi 3 can boot directly into ARM-only code by placing a specially crafted `kernel8.img` (64-bit) or `kernel7.img` (32-bit) in the boot partition, but **the GPU still executes `start.elf`** to initialize SDRAM.
- It is not possible to completely bypass the GPU firmware — the SDRAM initialization is only performed by the VideoCore.
- Bare-metal tutorials typically use a minimal `bootcode.bin` + `start.elf` + `kernel8.img` flow.

#### Option 2: Using Existing Frameworks

- **Circle** — A C++ bare-metal framework for Raspberry Pi (supports Pi 3 / BCM2837). Provides a clean API for GPIO, UART, USB, and other peripherals.
- **U-Boot** — The Universal Boot Loader can be compiled for Pi 3, providing a flexible second-stage bootloader. U-Boot supports network boot, SATA, USB, and can load kernels from various sources.
  - Build with: `make CROSS_COMPILE=aarch64-raspberrypi-linux-gnu- rpi_3_defconfig`
  - U-Boot can be loaded as `boot.img` by the Pi 3 firmware
- **Bare-metal examples** — The `raspberrypi/firmware` GitHub repository contains minimal example code.

#### Boot Configuration via `config.txt`

Key `config.txt` options for bare-metal development:

| Option | Description |
|--------|-------------|
| `kernel8.img` / `kernel7.img` | Specifies which kernel to load (8 = 64-bit, 7 = 32-bit) |
| `arm_64bit=1` | Forces 64-bit kernel load mode |
| `disable_commandline_tags=1` | Prevents firmware from passing ATAGS/DTB to kernel |
| `device_tree_address=0x100` | Sets location for device tree blob |
| `enable_uart=1` | Enables UART output |
| `gpio` | Can be used to configure pin states before kernel boot |

> **Source**: Raspberry Pi Documentation — "config.txt" (Raspberry Pi Ltd.)

### Device Tree and Overlays

- The Pi 3 uses **device tree** to describe hardware.
- Custom hardware can be described using device tree overlays (`.dtbo` files compiled from `.dts`).
- Overlays are loaded from `/boot/overlays/` and referenced in `config.txt` using `dtoverlay=`
- The device tree blob (`.dtb`) is typically `bcm2837-rpi-3-b.dtb` or `bcm2837-rpi-3-b-plus.dtb`

> **Source**: Raspberry Pi Documentation — "Device Trees, overlays, and parameters" (Raspberry Pi Ltd.)

### Boot Debugging Tips

- **Boot delay**: Add `boot_delay=1` to `config.txt` to give time for UART connection
- **Boot log level**: Not directly controllable from firmware, but Linux kernel `earlyprintk` can be enabled
- **LED codes**: The Pi 3 has a single green Activity LED (ACT). Patterns indicate boot failures (e.g., 3 flashes = `bootcode.bin` not found, 4 flashes = `start.elf` not found, 7 flashes = kernel not found)

> **Source**: Raspberry Pi Documentation — "LED warning flash codes" (Raspberry Pi Ltd.)

---

## 6. Key Differences from Neighbouring Pi Generations

| Feature | Pi 2 (BCM2836) | Pi 3 (BCM2837) | Pi 3B+ (BCM2837B0) | Pi 4 (BCM2711) |
|---------|----------------|----------------|---------------------|----------------|
| **SoC architecture** | ARM Cortex-A7 (32-bit) | ARM Cortex-A53 (64-bit) | ARM Cortex-A53 (64-bit) | ARM Cortex-A72 (64-bit) |
| **Boot ROM** | Limited boot modes | Extended boot modes (USB/PXE) | EEPROM bootloader (limited) | Full SPI EEPROM bootloader |
| **Boot firmware storage** | SD card only | SD + OTP (USB/PXE) | OTP + EEPROM | User-updateable SPI flash |
| **USB boot** | No (without bootloader EEPROM) | Yes (OTP-enabled) | Yes (OTP-enabled) | Yes (default) |
| **Network boot** | Limited | Yes (OTP-enabled) | Yes (OTP-enabled) | Yes (default) |
| **GPU firmware** | VideoCore IV | VideoCore IV | VideoCore IV | VideoCore VI (newer) |
| **UART routing** | PL011 on GPIO 14/15 |
