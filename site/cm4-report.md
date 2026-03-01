# Compute Module 4 / 4S (BCM2711) -- Bootloader & Boot Process

*Generated 2026-03-01*

## Sources

- [BCM2711 Boot EEPROM - Official Docs](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-4-boot-eeprom)
- [raspberrypi/rpi-eeprom - GitHub](https://github.com/raspberrypi/rpi-eeprom)
- [Pi 4 Bootloader Configuration - Official Docs](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-4-bootloader-configuration)
- [Pi 4 EEPROM boot deep dive - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=243087)

---

# Compute Module 4 / 4S (BCM2711) — Bootloader & Boot Process: Community Documentation

This report documents the boot process for the Raspberry Pi Compute Module 4 (CM4) and Compute Module 4S (CM4S), focusing on the BCM2711 processor. It consolidates information from official Raspberry Pi documentation and the `rpi-eeprom` GitHub repository to provide a technical reference for developers and system integrators.

> **Disclaimer**: This document summarizes publicly available information. Where details are inferred from community testing rather than official white papers, they are marked as "Community knowledge."

---

## 1. Overview of the BCM2711 Boot Sequence

The boot process on the Compute Module 4 (BCM2711) differs significantly from earlier generations (e.g., BCM2835, BCM2837). The transition from the legacy `bootcode.bin` method to a dedicated on-module **EEPROM** marks the most significant architectural change.

### Step-by-Step Flow

1.  **Power-On & PM_RST**:
    Upon applying power, the PM_RST (Power Management Reset) line is released. The system enters a reset state, and the VideoCore (VC4) subsystem begins execution.

2.  **VideoCore (VC4) ROM Execution**:
    The BCM2711 contains a small, read-only bootloader embedded in the GPU silicon (L2 cache). This **ROM code** is the first executable code. Its primary task is to locate and load the next stage bootloader.
    *   *Source: "Boot sequence" (Raspberry Pi Documentation)*

3.  **EEPROM Bootloader**:
    The ROM code reads the **SPI Flash EEPROM** located on the Compute Module. This EEPROM (typically 8Mbit/1MB) contains the primary bootloader firmware (`pieeprom.bin`).
    *   The bootloader performs basic SDRAM initialization (essential for further loading).
    *   It reads its configuration (BOOT_ORDER, PCIE_PROBE, etc.) from a specific region in the EEPROM.

4.  **Boot Device Selection**:
    Based on the `BOOT_ORDER` configuration in the EEPROM, the bootloader attempts to load the next stage from one of the supported boot media (SD, USB, Network). It may try them sequentially (e.g., try SD, then USB, then Network) depending on the configuration.

5.  **Loading the GPU Firmware (`start.elf`)**:
    Once a boot device is found, the bootloader loads the second-stage firmware (`start.elf` and associated files like `fixup.dat`, `vlls/`) into SDRAM. This firmware runs on the VideoCore and manages the arm64 CPUs, memory, and peripherals.
    *   *Source: "Raspberry Pi boot EEPROM" (Raspberry Pi Documentation)*

6.  **Boot Configuration & Kernel Handoff**:
    The `start.elf` firmware parses `config.txt` and `cmdline.txt`. It allocates memory, loads the Linux kernel (or bare-metal payload) and the Device Tree Blob (DTB), then releases the ARM cores from reset to begin execution.
    *   *Source: "Boot sequence" (Raspberry Pi Documentation)*

---

## 2. Boot Firmware & Storage

Unlike the Raspberry Pi 3B+, the CM4 does **not** rely on `bootcode.bin` located on the SD card for the primary boot process.

### Boot EEPROM
*   **Location**: On the CM4 module itself, there is a dedicated SPI Flash IC (or eMMC variant sharing the same bus logic).
*   **Content**: Contains the "Pie" bootloader (`pieeprom.bin`).
*   **Recovery**: The bootloader can be updated via the `rpi-eeprom` package.
*   **Source**: The `rpi-eeprom` GitHub repository contains the `firmware-2711` branch, which holds the binary images for the CM4/Pi 4 bootloader.

### Firmware Files (on Boot Media)
Once the bootloader selects the boot device (e.g., eMMC), it looks for the following in the `/boot` (or `/boot/firmware`) partition:
*   `start.elf`: The primary GPU firmware.
*   `fixup.dat`: Memory fixup data for the ARM cores.
*   `vlls/`: Directory containing additionalVideoCore binaries.
*   `bootcode.bin`: **Note**: While `bootcode.bin` is *not* used for normal EEPROM booting, it is used in specific recovery scenarios (e.g., USB Boot MSD recovery mode). It is typically placed on the root of the recovery SD/USB drive.

### Compute Module 4 vs 4S Storage
*   **CM4**: Features onboard **eMMC** storage (8GB, 16GB, or 32GB). The SD card interface is disabled or absent.
*   **CM4S**: Features an **SD card** interface instead of eMMC. It functions similarly to a "Lite" version of the CM4.
    *   *Community knowledge*: The CM4S is electrically similar to the CM4 but uses the SD card pins instead of the eMMC NAND interface.

---

## 3. Boot Modes Supported

The BCM2711 bootloader in the CM4 supports a rich set of boot modes, configured via the `BOOT_ORDER` parameter in the EEPROM.

1.  **SD Card / eMMC Boot**:
    *   The default boot mode for CM4.
    *   The bootloader scans the eMMC (or SD card on CM4S) for a partition table and looks for the `boot` partition.
2.  **USB Mass Storage Boot**:
    *   Supports booting from USB drives (flash drives, SSDs).
    *   Requires USB boot mode
