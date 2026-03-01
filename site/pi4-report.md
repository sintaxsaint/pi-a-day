# Raspberry Pi 4 Model B (BCM2711) -- Bootloader & Boot Process

*Generated 2026-03-01*

## Sources

- [BCM2711 Boot EEPROM - Official Docs](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-4-boot-eeprom)
- [raspberrypi/rpi-eeprom - GitHub](https://github.com/raspberrypi/rpi-eeprom)
- [Pi 4 Bootloader Configuration - Official Docs](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-4-bootloader-configuration)
- [Pi 4 EEPROM boot deep dive - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=243087)

---

# Raspberry Pi 4 Model B (BCM2711) — Bootloader & Boot Process: Community Documentation

**Document Scope:** Raspberry Pi 4 Model B (1GB, 2GB, 4GB, 8GB variants)  
**System-on-Chip:** BCM2711  
**Document Type:** Community Technical Report

---

## 1. Overview of the BCM2711 Boot Sequence

The Raspberry Pi 4 Model B introduced a fundamentally different boot architecture compared to its predecessors. The BCM2711 SoC implements a multi-stage boot process that begins in silicon-level ROM and culminates in Linux kernel handoff.

### Step-by-Step Boot Flow

1. **Silicon ROM (First Stage)**
   - On power-on, the BCM2711 executes boot code stored in the on-chip read-only memory (ROM)
   - This ROM is mask-programmed during chip manufacture and cannot be modified
   - The ROM code performs initial silicon bring-up: PLL configuration, DDR memory training, and pin multiplexing
   - The ROM then scans for a valid bootloader in the following order (configurable via OTP and EEPROM configuration):
     - RPIBOOT USB device mode (if enabled)
     - SD card (JEDEC MMC/eMMC interface)
     - USB mass storage device
     - Network (via USB Ethernet or integrated gigabit MAC)

2. **Bootloader EEPROM (Second Stage)**
   - The ROM loads the bootloader from the dedicated SPI flash EEPROM (located on the board near the USB-C power connector)
   - This EEPROM is 512KB (or larger on later revisions) and stores the Raspberry Pi bootloader firmware
   - The bootloader in EEPROM is updatable via software (see `rpi-eeprom` package)
   - This stage performs:
     - Initialization of USB host controller
     - Loading of device tree blobs (`.dtb`) and firmware files
     - Boot mode selection based on configuration
     - Loading of `start.elf` or `start4.elf` (the VideoCore GPU firmware)

3. **VideoCore Firmware (Third Stage)**
   - The bootloader hands control to the VideoCore GPU, which executes `start.elf` (or variant)
   - On BCM2711, `start4.elf` is the primary bootloader for the Raspberry Pi 4 architecture
   - This firmware:
     - Reads `config.txt` to configure boot parameters
     - Loads the Linux kernel (or other operating system) from the boot device
     - Sets up ATAGS or device tree for kernel handoff
     - Transfers execution to the kernel

4. **Kernel Handoff**
   - The GPU boots the ARM cores from a halted state
   - Linux kernel is decompressed (if using `zImage`) and execution begins on CPU 0
   - Boot arguments are passed via ATAGS or device tree

**Note:** Unlike earlier Raspberry Pi models, `bootcode.bin` is **not used** on the Raspberry Pi 4. The SD card slot is still present but does not require a separate bootcode binary.

---

## 2. Boot Firmware & Storage

### EEPROM Bootloader

The Raspberry Pi 4 uses a dedicated SPI flash EEPROM to store the primary bootloader. Key characteristics:

| Parameter | Specification |
|-----------|----------------|
| Capacity | 512KB (standard), 1MB+ on later revisions |
| Interface | SPI (via BCM2711's SPI0 peripheral) |
| Location | On-board, near USB-C power connector |
| Update mechanism | `rpi-eeprom` package, Raspberry Pi Imager |
| Default boot order | Configurable via EEPROM configuration |

**Source:** Official Raspberry Pi Documentation — "Raspberry Pi boot EEPROM" (raspberrypi.com)

The EEPROM contains the `pieeprom.bin` image, which includes:

- Bootloader firmware
- Default configuration
- Recovery image for failsafe boot

### Firmware Files on Boot Media

When the bootloader searches for boot media, it expects the following files in the root of the boot partition (SD card or USB):

- `start4.elf` — Primary VideoCore firmware for BCM2711
- `fixup4.dat` — Memory fixup data for GPU
- `config.txt` — Boot configuration (text file)
- `bcm2711-rpi-4-b.dtb` — Device tree blob for Pi 4 Model B
- `boot.scr` (optional) — U-Boot script if using U-Boot
- `vmlinuz` or `zImage` — Linux kernel

**Note:** The filename `start.elf` from earlier Pi generations is not used on BCM2711. The Pi 4 uses `start4.elf` specifically.

### Recovery Boot

The EEPROM includes a recovery mode triggered by:

1. Holding the `RUN` pin low during power-on (or using the factory recovery button on Compute Module boards)
2. Writing a special `recovery.bin` to a FAT-formatted SD card inserted in the board

This allows reflashing the EEPROM even if the primary bootloader is corrupted.

---

## 3. Boot Modes Supported

The BCM2711 supports multiple boot modes, configured via EEPROM settings or OTP bits.

### SD Card Boot

- **Interface:** JEDEC-compliant MMC (eMMC) interface supporting SD cards
- **Requirements:** 
  - MBR-partitioned SD card with FAT32 boot partition
  - Valid firmware files (`start4.elf`, etc.)
  - EEPROM must be configured for SD boot priority
- **Notes:** The SD card slot on Pi 4 uses a different controller than Pi 3; the card must contain complete boot firmware files (no `bootcode.bin` required)

### USB Mass Storage Boot

- **Supported devices:**
  - USB flash drives
  - USB hard drives / SSDs (via USB enclosure)
  - USB card readers
- **Requirements:**
  - USB boot must be enabled in EEPROM configuration
  - Device must comply with USB Mass Storage class
  - Boot files must be on the first partition (FAT32 for simplicity)
- **Known quirks:**
  - Some USB devices may not initialize quickly enough; boot delay can be configured in `config.txt`
  - USB hub enumeration order may vary; boot order in EEPROM can specify preferred devices by VID/PID
- **Source:** Official Raspberry Pi Documentation — "USB boot modes" (raspberrypi.com)

### Network Boot (PXE / HTTP)

- **PXE (Preboot Execution Environment):**
  - BCM2711 includes an integrated gigabit Ethernet MAC
  - Requires DHCP server and TFTP server on the network
  - Must be enabled in EEPROM configuration
  - Boot files fetched via TFTP include `bootcode.bin` (not used for other modes but required for network boot compatibility), `start4.elf`, etc.
  
- **HTTP Boot:**
  - Pi 4 bootloader supports HTTP/HTTPS boot (added in later firmware versions)
  - Allows booting from a web server
  - Configured via `boot.conf` or EEPROM settings
  
- **Notes:**
  - Network boot requires OTP bits to be set or EEPROM configuration to enable
  - The bootloader requests DHCP and then TFTP for `bootcode.bin` (for network boot compatibility)
  - IPv6 network boot is also supported

### GPIO Boot Mode

The BCM2711 supports boot mode selection via GPIO pins (often used with Compute Modules). This allows selecting between SD card, USB, and network boot based on GPIO states during power-on.

### NVMe Boot (via PCIe)

- **Note:** Direct NVMe boot on standard Raspberry Pi 4 Model B requires a PCIe HAT or the Pi 4's limited PCIe interface (exposed on later board revisions as a Gen 2 lane). However, native NVMe boot support was significantly expanded on Raspberry Pi 5. On Pi 4, NVMe boot typically requires the official M.2 HAT or third-party PCIe adapters.

---

## 4. UART / Serial Console

### Default State

On the Raspberry Pi 4 Model B, the primary UART (UART0 on GPIO 14/15) is **disabled by default** in the EEPROM bootloader. This differs from earlier models where the UART was typically available without configuration.

### Enabling Serial Console

**Method 1: EEPROM Configuration**
The bootloader can be configured to enable the UART by setting the `BOOT_UART` option in the EEPROM configuration:

```
BOOT_UART=1
```

This can be set using the `rpi-eeprom-config` tool:

```bash
rpi-eeprom-config --edit
```

**Method 2: config.txt**
Serial output can also be enabled via `config.txt` on the boot media:

```
enable_uart=1
```

Note: On Pi 4, `enable_uart=1` in config.txt also enables the Bluetooth UART (mini-UART) and may affect performance. For full UART control on GPIO 14/15, both EEPROM and config.txt settings may be required.

### Pinout

| GPIO | Function | Pin Number |
|------|----------|------------|
| 14   | UART0 TXD | 8  |
| 15   | UART0 RXD | 10 |

### Baud Rate

- Default: 115200 baud, 8N1
- Can be changed via kernel command line parameters

### Quirks and Known Issues

1. **Mini-UART vs. PL011:** The Pi 4 has two UARTs:
   - **PL011 UART0** — Full-featured, connected to GPIO 14/15 by default
   - **Mini-UART** — Simpler, shares pins with Bluetooth on default configuration
   
2. **Bluetooth interference:** When Bluetooth is enabled, it uses the mini-UART. You must disable Bluetooth to use GPIO 14/15 for the PL011 UART.

3. **EEPROM boot output:** The bootloader itself may output early debug messages to UART before the Linux kernel loads. This requires `BOOT_UART=1` in EEPROM.

4. **JTAG conflicts:** GPIO 22-27 can be configured for JTAG debugging; if enabled, they may conflict with certain UART configurations.

**Source:** Official Raspberry Pi Documentation — "Configure UARTs" (raspberrypi.com)

---

## 5. Bare-Metal and OS Bring-Up Notes

### U-Boot

U-Boot can be used as a second-stage bootloader on the Raspberry Pi 4, providing:

- Flexible boot menu
- Chain-loading other bootloaders
- Network boot support
- Scriptable boot sequences

**Installation:**

1. Place `u-boot.bin` (or `u-boot.elf`) in the boot partition
2. Configure `config.txt` to load U-Boot before the kernel:

```
arm_64bit=1
kernel=u-boot.bin
```

Or use `boot.scr` (U-Boot script):

1. Create a boot script using `mkimage`
2. Place as `boot.scr` in boot partition

**Notes:**
- U-Boot support for BCM2711 is community-maintained
- Some features (USB, network) may require specific builds
- The official Raspberry Pi U-Boot build is available in Raspberry Pi OS

### Circle

Circle is a bare-metal C++ framework for Raspberry Pi (all models including Pi 4). It provides:

- Direct hardware access without an OS
- Simple memory management
- Support for GPU initialization
- USB host support (in development for Pi 4)

**Notes for Pi 4:**
- Circle supports BCM2711 with limitations
- USB support is still maturing
- Requires cross-compilation toolchain (ARM GCC)

### Custom Firmware / Bare-Metal Development

**Requirements:**

1. **Cross-compiler:** ARM GCC or Clang for AArch64 (Pi 4 boots in 64-bit mode by default)
2. **Linker script:** Must place code appropriately for ARM64 execution
3. **Boot method:** Custom firmware can replace the Linux kernel in `config.txt` using `kernel=` directive

**Minimum Bare-Metal Checklist:**

```
# config.txt minimum for custom kernel
arm_64bit=1
kernel=myfirmware.elf
```

**GPU Initialization:**
- The Pi 4's VideoCore must be initialized for any video output
- Circle and other frameworks handle this internally
- For raw bare-metal, refer to the official VideoCore documentation (available from Raspberry Pi GitHub)

**Resources:**
- Raspberry Pi bare-metal examples: `https://github.com/rust-embedded/rust-raspberrypi-OS-tutorials`
- VideoCore documentation: `https://github.com/raspberrypi/documentation/tree/master/hardware/raspberrypi/bcm2711`

---

## 6. Key Differences from Neighbouring Pi Generations

### Comparison with Raspberry Pi 3 (BCM2837)

| Feature | Pi 3 (BCM2837) | Pi 4 (BCM2711) |
|---------|----------------|----------------|
| Boot ROM | Fixed in mask ROM | Fixed in mask ROM |
| Boot firmware location | SD card (`bootcode.bin`) | SPI EEPROM |
| Boot media requirement | `bootcode.bin` on SD required | No external bootcode; EEPROM sufficient |
| GPU firmware | `start.elf` | `start4.elf` |
| Architecture | ARMv8-A (64-bit optional) | ARMv8-A (64-bit default) |
| USB boot | Supported (via `bootcode.bin`) | Native USB (no bootcode needed) |
| Network boot | Broadcom Ethernet (no built-in) | Built-in Gigabit Ethernet MAC |
| UART default | Enabled by default | Disabled by default (requires config) |
| PCIe support | None | Gen 2 x1 (limited) |
| Firmware update | N/A | Via `rpi-eeprom` |

### Comparison with Raspberry Pi 5 (BCM2712)

| Feature | Pi 4 (BCM2711) | Pi 5 (BCM2712) |
|---------|----------------|----------------|
| Boot architecture | EEPROM + VideoCore | EEPROM + RP1 co-processor |
| EEPROM updates | Manual via `rpi-eeprom` | More streamlined, embedded bootloader |
| Boot modes | SD, USB, Network, GPIO | Additional NVMe native support |
| Default bootloader | Legacy Pi 4 bootloader | Newer bootloader with enhanced features |
| PCIe | Gen 2 x1 (limited) | Gen 2 x4 (full) |
| Network boot | IPv4/IPv6 TFTP | Enhanced network boot (PXE2) |
| Secure boot | Not implemented | Supported (signed bootloader) |

**Key distinction:** The Pi 5 introduced a completely rewritten bootloader architecture with the RP1 chip handling many boot-related functions. The Pi 4's bootloader remains largely unchanged in design from the original 2019 release.

---

## 7. Open Questions / Areas Without Official Documentation

The following areas either lack comprehensive official documentation or remain community-discovered:

### A. Detailed EEPROM Configuration Options

- Full documentation of all EEPROM configuration parameters is limited
- Community members have reverse-engineered options like `BOOT_ORDER`, `PCIE_PROBE`, `ETH_MAC`, and `WATCHDOG`
- Some advanced EEPROM settings are documented only in source code (`rpi-eeprom` GitHub repository)

### B. VideoCore Boot Stub Behavior

- The exact mechanism by which `start4.elf` initializes the ARM cores and performs handoff is not publicly documented
- Community bare-metal developers have reverse-engineered this process
- The boundary between GPU and CPU initialization is not officially described

### C. DDR Memory Training Details

- The ROM boot code performs DDR memory training, but the specific algorithms and timing parameters are proprietary
- No official documentation exists on how the ROM configures LPDDR4 on the Pi 4
- This is a significant barrier to full bare-metal development without using the provided bootloader

### D. USB Boot Enumeration Quirks

- While USB boot is documented, specific device compatibility issues are not
- Community forums contain device-specific workarounds
- The exact timeout values and retry logic for USB enumeration are not specified

### E. Secure Boot Status

- As of the latest firmware, the Raspberry Pi 4 does not implement secure boot in the public release
- Whether secure boot will be enabled in the future is unclear
- The Pi 5 has introduced signed bootloader support, but the Pi 4's status remains uncertain

### F.JTAG Debugging

- JTAG debugging for the Pi 4 is possible but not officially documented
- Community resources indicate GPIO 22-27 can be configured for JTAG, but the exact enable method is not in official docs

---

## Appendix: Useful Commands

```bash
# Check EEPROM version
vcgencmd bootloader_version

# Update EEPROM (requires reboot)
sudo rpi-eeprom-update -a
sudo reboot

# Configure EEPROM
sudo rpi-eeprom-config --edit

# Check boot order
vcgencmd bootloader_config

# Read current boot order
rpi-eeprom-dump
```

---

*This document is community-maintained. Information is sourced from official Raspberry Pi documentation and community contributions. For the latest official documentation, refer to raspberrypi.com/documentation.*
