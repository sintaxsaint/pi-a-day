# Compute Module 3 / 3+ (BCM2837) -- Bootloader & Boot Process

*Generated 2026-03-01*

## Sources

- [Pi 3 USB / Network Boot - Official Docs](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#pi-3-only-bootcode-bin-usb-boot)
- [raspberrypi/usbboot - GitHub (BCM2837 USB boot ROM)](https://github.com/raspberrypi/usbboot)
- [RPiconfig boot options - eLinux Wiki](https://elinux.org/RPiconfig)
- [BCM2837 64-bit boot thread - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=174648)

---

# Compute Module 3 / 3+ (BCM2837) — Bootloader & Boot Process: Community Documentation

**Document Scope:** This report covers the BCM2837-based Compute Module 3 (CM3) and Compute Module 3+ (CM3+) platforms. It addresses bootloader behavior, firmware components, supported boot modes, serial console configuration, and bare-metal development considerations. Information is drawn from official Raspberry Pi documentation, the `raspberrypi/usbboot` GitHub repository, and community sources. Where documentation is sparse or contradictory, this is noted explicitly.

**Intended Audience:** Embedded systems engineers, firmware developers, and community members working with Compute Module 3 or 3+ hardware.

---

## 1. Overview of the BCM2837 Boot Sequence

The BCM2837 System-on-Chip (SoC) uses a two-stage boot architecture in which the VideoCore IV GPU executes firmware before handing control to the ARM Cortex-A53 CPUs. This is a fundamental characteristic of all Raspberry Pi silicon prior to BCM2711.

### 1.1 Step-by-Step Boot Flow

The boot process on BCM2837 proceeds as follows:

1. **Power-On and ROM Boot (Stage 0)**
   - On power-on, the SoC executes mask ROM code baked into the silicon. This ROM is immutable and contains the *first-stage* bootloader.
   - The ROM inspects the OTP (One-Time Programmable) memory bits to determine the boot device priority. It does **not** execute arbitrary code from any storage medium at this stage.

2. **Bootloader Selection (Stage 1)**
   - The ROM bootloader reads the first partition (FAT) of the selected boot device (SD card, eMMC, or USB).
   - On Compute Module 3/3+, the default boot device is the onboard eMMC (8 GB soldered flash). The module can boot from SD card if the appropriate IO board is used and the OTP is configured.
   - The ROM loads `bootcode.bin` into the L2 cache (or SRAM on some variants). This file is the *second-stage* bootloader.

3. **Loading start.elf (Stage 2)**
   - `bootcode.bin` enables the SDRAM and loads `start.elf` (or `start_cd.elf` / `start_db.elf` for debug and display-core variants) from the boot partition.
   - `start.elf` is the VideoCore firmware binary. It contains the GPU firmware, memory initialization, and the logic to load the kernel.

4. **Kernel Loading (Stage 3)**
   - The GPU reads `config.txt` to apply board-specific configuration (device tree blobs, kernel overrides, UART selection).
   - It loads the ARM kernel (`kernel8.img` for 64-bit, `kernel7.img` for 32-bit) into RAM at address `0x100000` (1 MB).
   - On BCM2837, the default is to boot in 64-bit mode if a 64-bit kernel is present.
   - The GPU then releases the ARM cores from reset, transferring execution to the loaded kernel image.

### 1.2 Boot Partition Requirements

The boot medium must contain a FAT32 (or FAT16) partition with the following minimum files:

- `bootcode.bin` — second-stage bootloader
- `start.elf` — main VideoCore firmware
- `config.txt` — configuration file parsed by the GPU
- `cmdline.txt` — kernel command line arguments
- `kernel8.img` or `kernel7.img` — ARM executable

On Compute Module 3/3+, the eMMC is the default boot medium. The module does not have a built-in SD card slot; an IO board (CMIODIO or CM3/3+ IO Board) is required to expose the eMMC as a USB mass-storage device or to add an SD card slot.

---

## 2. Boot Firmware & Storage

### 2.1 Firmware Components

| File | Purpose | Loaded By |
|------|---------|------------|
| `bootcode.bin` | Initializes SDRAM, locates and loads `start.elf` | ROM (mask ROM) |
| `start.elf` | GPU firmware; loads kernel, parses `config.txt` | `bootcode.bin` |
| `fixup.dat` | Memory fixup table paired with `start.elf` | Loaded alongside `start.elf` |
| `config.txt` | Boot configuration (text file) | Parsed by `start.elf` |
| `cmdline.txt` | Kernel command line | Passed to kernel by `start.elf` |

These firmware files are architecture-specific. For BCM2837, the firmware files must be from the `rpi-update` or Raspberry Pi GitHub `firmware` repository branch appropriate to the Pi 3 / CM3 generation. Using firmware from the Pi 4 or Pi 5 branches will not work.

### 2.2 Storage Media

- **eMMC (Compute Module 3/3+):** The primary onboard storage. The eMMC presents as a standard block device (`/dev/mmcblk0`) under Linux. The ROM bootloader accesses it via the SDHCI controller.
- **SD Card:** When the CM3/3+ is mounted on an IO board with an SD card slot, the OTP can be programmed to prefer SD card boot. The SD card operates on the same SDHCI controller as the eMMC.
- **USB Mass Storage:** BCM2837 supports USB mass storage boot, but this requires OTP configuration. The `raspberrypi/usbboot` tool can be used to flash the eMMC over USB when the module is in USB boot mode. (Source: `raspberrypi/usbboot` GitHub repository — lists CM3 and CM3+ as compatible devices.)

### 2.3 OTP and Boot Order

The boot device order is controlled by OTP memory bits. The Raspberry Pi bootloader supports programmable boot order via OTP. The default order on CM3/3+ is:

1. eMMC
2. SD card (if present on the IO board)
3. USB (if OTP is configured)

The OTP is writable only once per bit (set to 1). Community documentation on the OTP bit definitions is available from the official docs and from the `rpi-eeprom` repository. The relevant bits for boot mode selection are documented in the "Raspberry Pi OTP register and bit definitions" section of the official documentation. (Source: Raspberry Pi Documentation — "Raspberry Pi boot modes" and "OTP register and bit definitions")

---

## 3. Boot Modes Supported

### 3.1 SD Card / eMMC Boot

This is the default and most straightforward boot mode. The ROM bootloader reads the FAT partition from the eMMC (or SD card) and loads `bootcode.bin`. This mode requires no special OTP configuration.

- **CM3/3+ default:** Boots from onboard eMMC.
- **With IO board:** Can boot from microSD card if the IO board provides an SD slot.

### 3.2 USB Boot

USB mass storage boot was added to BCM2837 via firmware updates. To enable USB boot:

- OTP bit `0x6` (or equivalent, per the official docs) must be set to enable USB boot mode.
- A USB mass storage device (flash drive, HDD, SSD) must be connected to the USB port (via the IO board's USB connector).
- The boot files must reside on the USB device's first FAT partition.

The `raspberrypi/usbboot` tool provides a host-side utility (`rpiboot`) that enumerates the Compute Module as a USB mass storage device, allowing the eMMC to be flashed from a host PC. The tool supports CM3 and CM3+. (Source: `raspberrypi/usbboot` GitHub repository — "Compatible devices" list)

> **Community note:** USB boot on BCM2837 is slower than eMMC boot and may exhibit timing issues with some USB devices. Using a powered USB hub or a high-quality short cable is recommended in the official documentation.

### 3.3 Network Boot (PXE)

PXE (Preboot Execution Environment) network boot is supported on BCM2837. The requirements are:

- The OTP must have the network boot bit set.
- A DHCP server must be present on the network to provide an IP address and TFTP server address.
- A TFTP server must serve the boot files (`bootcode.bin`, `start.elf`, `config.txt`, kernel).
- The Ethernet interface must be connected to the IO board's Ethernet port (via the CM3/3+ IO board).

The boot sequence for PXE involves the ROM bootloader attempting SD/eMMC boot first, then falling back to USB, and finally to network boot if the OTP is configured accordingly. The official documentation details the exact fallback order. (Source: Raspberry Pi Documentation — "Network booting")

### 3.4 GPIO Boot Mode

GPIO boot mode (selecting a boot device via GPIO pins) is documented in the official docs for newer Pi models, but community documentation indicates it may not be available on BCM2837. This is an area of uncertainty — the official "GPIO boot mode" page does not explicitly list CM3/3+ as supported. (Source: Raspberry Pi Documentation — "GPIO boot mode")

---

## 4. UART / Serial Console

### 4.1 Default UART Configuration

BCM2837 provides two UARTs:

- **UART0 (PL011):** Full-featured UART, mapped to GPIO pins 14 (TXD) and 15 (RXD) by default.
- **UART1 (mini UART):** Simplified UART with fewer features, mapped to alternate GPIO pins.

On Compute Module 3/3+, the UART pins are exposed on the IO board's 22-pin or 40-pin header (depending on the IO board version). The default configuration in `config.txt` controls which UART is used for the serial console.

### 4.2 Enabling Serial Console

To enable the serial console on the PL011 (default):

```ini
# In config.txt
enable_uart=1
```

This maps the main console to UART0 on pins 14/15. The `cmdline.txt` must also contain the console argument:

```text
console=serial0,115200 console=tty1 root=/dev/mmcblk0p2 rootfs Type=ext4 elevator=deadline fsck.repair=yes rootwait
```

### 4.3 Compute Module Specifics

- **No on-board Ethernet/USB on bare CM3/3+:** The CM3/3+ module itself does not expose USB or Ethernet. These require an IO board (CMIODIO or CM3/3+ IO Board). The serial console is one of the few reliable bring-up interfaces when no IO board is attached.
- **Pin multiplexing:** The CM3/3+ has 200 GPIO pins, of which a subset is routed to the board edge. UART0 pins are available on these edge pins, but the exact pinout depends on the carrier board design. The IO board documentation specifies the pin assignments.
- **Baud rate:** The default baud rate is 115200 bps, 8N1.

### 4.4 Quirks

- The mini UART (UART1) has a lower bandwidth and is affected by VPU clock frequency changes. If the VPU is underclocked, the mini UART baud rate will drift. For reliable serial console, use the PL011 (UART0).
- On some early CM3 revisions, the OTP boot mode bits had to be manually configured to enable UART0 as the primary console. This was documented in community forum threads. (Source: Community forum discussions on Compute Module bring-up)
- The GPU parses `config.txt` *before* the ARM cores are started. Any UART-related settings in `config.txt` affect the GPU's console output (via the firmware's built-in serial debug), not the Linux kernel console.

---

## 5. Bare-Metal and OS Bring-up Notes

### 5.1 Bare-Metal Development

Developing bare-metal code for BCM2837 (Cortex-A53 in 64-bit mode) requires understanding the boot-time role of the VideoCore. The ARM cores are held in reset until the GPU firmware (`start.elf`) releases them. This means:

- **No direct ARM-only boot:** It is not possible to bypass the VideoCore firmware entirely on BCM2837. Even bare-metal code must be loaded by the GPU firmware.
- **Loading methods:**
  - Place `kernel8.img` (64-bit) or `kernel7.img` (32-bit) on the boot partition. The GPU loads this file to memory address `0x100000` and jumps to it.
  - Alternative: Use `uboot` as a second-stage bootloader loaded by `start.elf`, which then loads a custom kernel.

### 5.2 U-Boot

U-Boot can be used on CM3/3+ as a third-stage bootloader. The typical workflow is:

1. `start.elf` loads `uboot.bin` (or `u-boot.bin`) from the boot partition.
2. U-Boot initializes additional hardware (USB, Ethernet, storage) and loads the final OS kernel or a kernel from the network.

U-Boot support for BCM2837 is available in the mainline U-Boot tree. Community build scripts and pre-built binaries are available. The official Raspberry Pi documentation does not cover U-Boot configuration in detail, but the U-Boot project maintains board-specific defconfigs for the Pi 3 family (which share the BCM2837 SoC).

### 5.3 Circle

Circle is a bare-metal C++ framework for Raspberry Pi. It provides a minimal runtime that runs directly on the ARM CPU without requiring the VideoCore firmware. However, Circle currently requires the `kernel.img` (32-bit) loading mechanism, and support for 64-bit Pi 3 / CM3 is limited or still under development in community branches.

### 5.4 Custom Firmware Constraints

- **No direct firmware replacement:** The `bootcode.bin` and `start.elf` are binary-only proprietary blobs distributed by Raspberry Pi. There is no open-source replacement that provides full functionality.
- **EEPROM on CM3/3+:** Unlike the Compute Module 4 and 5, the CM3/3+ does not have a user-programmable bootloader EEPROM. The boot firmware resides on the boot partition of the eMMC or SD card, not in SPI flash.
- **Secure boot:** Not available on BCM2837. The secure boot chain introduced in BCM2711 (Pi 4) and later is not present on CM3/3+.

### 5.5 Linux Kernel

The official Raspberry Pi Linux kernel (` raspberrypi/kernel`) supports BCM2837. The device tree blobs for Compute Module 3 and 3+ are:

- `bcm2837-rpi-cm3.dtb` — Compute Module 3
- `bcm2837-rpi-cm3-plus.dtb` — Compute Module 3+

These device trees must be referenced in `config.txt` via the `device_tree` or `dtparam` directives.

---

## 6. Key Differences from Neighbouring Pi Generations

| Feature | Pi 2 (BCM2836) | **CM3/CM3+ (BCM2837)** | Pi 3B+ (BCM2837B0) | Pi 4 (BCM2711) |
|---------|----------------|------------------------|---------------------|-----------------|
| **CPU Architecture** | 32-bit Cortex-A7 | 64-bit Cortex-A53 | 64-bit Cortex-A53 | 64-bit Cortex-A72 |
| **Default Boot Mode** | SD card | eMMC (onboard) | SD card / USB / PXE | SPI EEPROM + SD |
| **USB Boot** | No (without OTP) | Yes (OTP-configured) | Yes (OTP-configured) | Yes (default) |
| **Network Boot (PXE)** | Limited | Yes (OTP-configured) | Yes (OTP-configured) | Yes (default) |
| **Boot EEPROM** | No | No | No | Yes (SPI flash) |
| **Secure Boot** | No | No | No | Yes |
| **Firmware Location** | SD card / FAT partition | eMMC / SD card / USB | SD card / USB | SPI flash + FAT partition |
| **GPU Firmware** | `start.elf` | `start.elf` | `start.elf` | `pieeprom.bin` + `start.elf` |

**Key takeaways for CM3/3+:**

- Unlike Pi 2, BCM2837 supports 64-bit operation.
- Unlike Pi 4, CM3/3+ lacks a programmable SPI EEPROM for the bootloader; the firmware lives on the boot partition.
- USB and network boot require OTP configuration, unlike Pi 4 where these are enabled by default.
- The CM3/3+ defaults to onboard eMMC, unlike the Pi 3B+ which defaults to SD card.

---

## 7. Open Questions / Areas Without Official Documentation

The following areas are either undocumented, ambiguously documented, or require community experimentation:

1. **GPIO Boot Mode on BCM2837:** The official "GPIO boot mode" documentation
