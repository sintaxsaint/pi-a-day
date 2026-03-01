# Raspberry Pi 400 (BCM2711) -- Bootloader & Boot Process

*Generated 2026-03-01*

## Sources

- [BCM2711 Boot EEPROM - Official Docs](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-4-boot-eeprom)
- [raspberrypi/rpi-eeprom - GitHub](https://github.com/raspberrypi/rpi-eeprom)
- [Pi 4 Bootloader Configuration - Official Docs](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-4-bootloader-configuration)
- [Pi 4 EEPROM boot deep dive - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=243087)

---

# Raspberry Pi 400 (BCM2711) — Bootloader & Boot Process: Community Documentation

**Document Type:** Community Technical Report  
**Target Hardware:** Raspberry Pi 400 (BCM2711)  
**Last Updated:** 2025

---

## 1. Overview of the BCM2711 Boot Sequence

The Raspberry Pi 400 shares the same BCM2711 system-on-chip (SoC) as the Raspberry Pi 4 Model B, and therefore inherits an identical boot architecture built around a mutable bootloader EEPROM. The boot sequence proceeds from silicon reset through firmware execution to operating system handoff.

### Step-by-Step Boot Flow

1. **Silicon Reset & ROM Boot (First-Stage)**
   - On power-on, the BCM2711 ARM cores begin execution from an internal Read-Only Memory (ROM) embedded in the SoC silicon.
   - This ROM contains the **primary bootloader** — a fixed-purpose firmware blob that cannot be modified. It is responsible for initial hardware initialization (clock, DDR memory training) and for loading the next-stage bootloader from external non-volatile storage.
   - The ROM bootloader does not support USB or network boot directly; it operates solely from attached SPI flash (EEPROM) or SD card.

2. **EEPROM Bootloader Execution (Second-Stage)**
   - The ROM bootloader reads the SPI EEPROM mounted on the board (adjacent to the SoC). If a valid bootloader image is present, it copies it into SRAM and transfers control.
   - This **second-stage bootloader** resides in the on-board EEPROM and is field-updatable. It implements the configurable boot order, boot mode selection, and firmware loading logic.
   - On Raspberry Pi 400, the EEPROM is a 512-Kbit (64 KB) serial flash device (Winbond W25X40CL or equivalent), pre-programmed at the factory with the default Raspberry Pi bootloader.
   - *Source: BCM2711 Boot EEPROM - Official Docs*

3. **Firmware Loading (Third-Stage)**
   - Once the EEPROM bootloader completes initial setup, it reads the **start.elf** (or **start4.elf** for BCM2711) firmware file from the boot partition.
   - The firmware file is not an operating system kernel — it is a GPU firmware blob that runs on the VideoCore VI GPU. It configures the ARM cores, sets up memory, and prepares the GPU to load the Linux kernel.
   - The firmware also loads **fixup.dat** (or **fixup4.dat**) — a companion file that resolves symbol addresses between the GPU and ARM memory spaces.

4. **Device Tree & Kernel Command Line**
   - The firmware reads **config.txt** to obtain platform configuration (device tree overlays, memory split, boot options).
   - It then loads the Linux kernel (typically **kernel8.img** for 64-bit ARM) and the associated Device Tree Blob (**\*.dtb**).
   - The kernel command line is assembled from **cmdline.txt** and any built-in defaults.

5. **Kernel Handoff**
   - Control transfers to the ARM kernel entry point. From this moment, the boot process follows standard Linux ARM64 boot protocols.
   - The GPU firmware remains active in the background, handling display output and certain hardware acceleration tasks, but no longer controls boot flow.

### Summary Table

| Stage | Location | Updatable | Primary Function |
|-------|----------|-----------|------------------|
| ROM | SoC internal | No | Initial silicon init, memory training |
| EEPROM bootloader | SPI flash (64 KB) | Yes | Boot order, mode selection, firmware loading |
| start.elf / start4.elf | Boot partition (SD/USB) | Yes (via firmware package) | GPU firmware, ARM setup, kernel load |
| Linux kernel | Boot partition | Yes | Operating system handoff |

---

## 2. Boot Firmware & Storage

### EEPROM (On-Board SPI Flash)

The Raspberry Pi 400 incorporates a soldered SPI EEPROM chip that holds the primary mutable bootloader. This is a key architectural difference from earlier Raspberry Pi models (BCM2835/BCM2837) that relied entirely on boot files on the SD card.

- **Capacity:** 512 Kbit (64 KB) serial flash
- **Location:** On the main PCB, adjacent to the SoC
- **Contents:** The bootloader binary image, including boot order table, default configuration, and recovery image
- **Update mechanism:** Can be updated via the `rpi-eeprom-update` tool under Raspberry Pi OS, or by writing an EEPROM recovery image to an SD card

*Source: rpi-eeprom - GitHub*

The EEPROM holds two bootloader images:

- **Production image:** The actively-used bootloader
- **Recovery image:** A fallback image used during EEPROM updates or when the production image is corrupted

### Boot Firmware Files (SD Card / USB)

Once the EEPROM bootloader executes, it searches the boot partition (on SD card or USB mass storage) for:

- **`start4.elf`** — The main VideoCore VI firmware blob for BCM2711. This is specific to the Pi 4/Pi 400 generation and differs from the `start.elf` used on earlier BCM283x devices.
- **`fixup4.dat`** — The linker fixup file for the VideoCore firmware.
- **`config.txt`** — Configuration file read by the firmware (not by the EEPROM bootloader directly).
- **`bootcode.bin`** — Not required on BCM2711. This file was used on earlier models; the Pi 4/400 perform all pre-firmware loading via the EEPROM.

### Updating Firmware

Firmware updates are delivered through the `rpi-eeprom` package in Raspberry Pi OS:

```bash
sudo apt update
sudo apt install rpi-eeprom
sudo rpi-eeprom-update
sudo reboot
```

The update process writes a new bootloader image to the SPI EEPROM. The Raspberry Pi 400 uses the same EEPROM layout and update mechanism as the Raspberry Pi 4 Model B.

*Source: rpi-eeprom - GitHub*

---

## 3. Boot Modes Supported

The BCM2711 bootloader in the EEPROM supports multiple boot modes, configurable via the `BOOT_ORDER` field in the EEPROM configuration. The default boot order on Raspberry Pi 400 prioritizes SD card, then USB.

### Supported Boot Modes

| Boot Mode | Description | Availability on Pi 400 |
|-----------|-------------|------------------------|
| **SD Card (JEDEC MMC)** | Boot from the microSD card slot | Supported (primary) |
| **USB Mass Storage** | Boot from USB flash drive, HDD, or SSD via USB 2.0/3.0 | Supported (requires bootloader configuration) |
| **Network Boot (PXE)** | Boot over Ethernet using DHCP + TFTP | Supported; requires Ethernet adapter and network infrastructure |
| **HTTP Boot** | Boot via HTTP/HTTPS (fetching boot files from a web server) | Supported in newer EEPROM versions |
| **GPIO Boot Mode** | Boot from a device attached to GPIO pins (e.g., SPI flash) | Available via OTP configuration; not commonly used on Pi 400 |
| **NVMe Boot** | Direct boot from NVMe SSD via PCIe | Not directly supported on Pi 400 — requires Pi 4 with custom bootloader or Pi 5 |

### Boot Order Configuration

The `BOOT_ORDER` EEPROM parameter defines a prioritized sequence of boot attempts. The default value is `0xf461` (SD → USB → Network), meaning:

- Try SD card first
- Fall back to USB mass storage
- Fall back to network boot

Users can modify the boot order using the `rpi-eeprom-config` tool or by editing `/boot/firmware/config.txt` with the `BOOT_ORDER` directive (on EEPROM versions that support it).

### USB Boot Requirements

Booting from USB on the Raspberry Pi 400 requires:

- USB mass storage device with a valid boot partition (FAT32 or ext4)
- Firmware files (`start4.elf`, `fixup4.dat`, `kernel8.img`, `boot.scr`, `config.txt`, `cmdline.txt`) on the USB device
- EEPROM bootloader configured to attempt USB boot (default enables this)
- For USB 3.0 devices, ensure the device provides sufficient power or use a powered hub

### Network Boot (PXE)

Network boot is supported but requires:

- A DHCP server on the local network to provide IP address and TFTP server details
- A TFTP server hosting the boot files (`start4.elf`, `fixup4.dat`, `kernel8.img`, `*.dtb`, `config.txt`, `cmdline.txt`)
- Ethernet connectivity — the Pi 400 has a built-in Gigabit Ethernet port (via the USB hub chip)

The bootloader broadcasts a DHCP request; upon receipt of a DHCP offer containing the `tftp-server` option, it downloads the boot files via TFTP.

*Source: BCM2711 Boot EEPROM - Official Docs*

---

## 4. UART / Serial Console

The Raspberry Pi 400 provides access to a serial console via the 40-pin GPIO header (pins 8, 10, and 14/Ground). However, there are hardware and configuration quirks specific to the Pi 400 that users should be aware of.

### Pinout

| Pin Number | Function | Notes |
|------------|----------|-------|
| 6, 9, 14, 20, 25 | Ground | Any Ground pin can be used |
| 8 | UART TX (GPIO 14) | Transmit from Pi |
| 10 | UART RX (GPIO 15) | Receive to Pi |

- **Baud rate:** Default 115200 baud, 8N1
- **Voltage level:** 3.3V TTL (not RS-232). Do not connect directly to a PC's DB-9 RS-232 port without a level shifter.

### Enabling Serial Console

The serial console is controlled via two mechanisms:

1. **`config.txt`** — Add or modify the following:
   ```
   enable_uart=1
   dtoverlay=disable-bt   # Optional: disables Bluetooth to free up UART0
   ```
2. **`cmdline.txt`** — Must contain the console directive:
   ```
   console=serial0,115200 console=tty1 root=/dev/mmcblk0p2 fsckfix=true
   ```

With these settings, the Linux kernel logs boot messages to the serial port and presents a login shell on `/dev/serial0` (which maps to UART0).

### Quirk: UART on Raspberry Pi 400

On the Raspberry Pi 400, the primary UART (UART0) is routed to the Bluetooth module by default, not to the GPIO header. This is a key difference from the Raspberry Pi 4 Model B.

- To use the GPIO header for serial console, **Bluetooth must be disabled** using `dtoverlay=disable-bt` in `config.txt`.
- When Bluetooth is disabled, UART0 is remapped to GPIO pins 14 and 15.
- Alternatively, the **mini UART (UART1)** can be used on GPIO 14/15, but it has limited baud rate accuracy and lacks flow control — not recommended for reliable serial console.

### Serial Console via USB-C (Console Cable)

The Raspberry Pi 400 has a USB-C power port. Some community reports (not officially documented) suggest that certain USB-C debug cables may present a serial adapter, but this is not a standard feature. The canonical method for serial console remains the GPIO header.

### Bootloader Serial Output

The EEPROM bootloader itself does **not** output debug messages to the serial port by default. Serial console output begins after the Linux kernel takes control. To observe the earlier boot phases (EEPROM → firmware),JTAG debugging would be required, which is not documented for community use.

---

## 5. Bare-Metal and Custom Firmware Bring-Up

The Raspberry Pi 400, with its BCM2711 SoC, is a popular platform for bare-metal development. However, there are specific considerations for writing custom firmware or bootloaders without relying on the VideoCore firmware stack.

### Using Custom Firmware Without start.elf

It is possible to bypass the VideoCore firmware entirely and boot custom code directly on the ARM cores. This is commonly done in bare-metal tutorials and in projects such as U-Boot, Circle, and bare-metal ARM64 code.

#### Requirements for Bare-Metal Boot

1. **Custom boot stub or bootloader:** Must be stored in a location the EEPROM bootloader can find. The supported locations are:
   - A file named `kernel8.img` on the SD card/USB boot partition
   - The file must be a valid ARM64 ELF or raw binary, loaded at the address specified in `config.txt` (default: `0x100000`)

2. **config.txt directives for bare-metal:**
   ```
   kernel_address=0x100000
   arm_64bit=1
   enable_uart=1
   ```
   - Setting `kernel8.img` as the boot target bypasses the VideoCore firmware loading entirely.
   - However, **the VideoCore is still powered on** and manages certain hardware (e.g., clocks, power management). Some peripherals (e.g., USB, Ethernet) may require interaction with the VideoCore or the secondary firmware `start4.elf`.

3. **Disabling the VideoCore:** It is possible to power down the VideoCore to reduce power consumption in pure bare-metal applications, but this disables hardware that depends on it (USB controller, network adapter, hardware video codecs).

### U-Boot on Raspberry Pi 400

U-Boot (Das U-Boot) supports the BCM2711 and can be used as a second-stage bootloader to load operating systems from network, USB, or SD card. The typical workflow:

1. Flash a recent U-Boot binary (`u-boot.bin` or `u-boot.elf`) to the boot partition as `kernel8.img`.
2. Configure `config.txt` to point to the U-Boot image.
3. U-Boot then loads the target OS (Linux, bare-metal application) from storage or network.

Community documentation for U-Boot on Pi 4/Pi 400 is extensive; the Raspberry Pi GitHub organization maintains a fork of U-Boot with Pi 4/400 support.

### Circle — A C++ Bare-Metal Framework

Circle is a C++ bare-metal framework for Raspberry Pi (including BCM2711). It provides a lightweight alternative to the VideoCore firmware stack, handling ARM core initialization, memory management, and basic peripheral access without relying on `start.elf`.

- Circle runs entirely on the ARM cores.
- It does not require the VideoCore, making it suitable for low-power or educational bare-metal projects.
- Supported peripherals include USB host, Ethernet, SD card, and GPIO.

### Custom Firmware via USB Boot

For custom firmware deployment, the USB boot mode can be used:

1. Configure the Pi 400 to boot from USB in the EEPROM (`BOOT_ORDER` set to prioritize USB).
2. Place the custom firmware binary as `kernel8.img` on a USB mass storage device.
3. On power-on, the EEPROM bootloader reads the USB device and loads the custom firmware.

This approach is commonly used in embedded development workflows where firmware is tested on removable media.

### JTAG Debugging

The BCM2711 supports ARM CoreSight JTAG debugging. However, the Raspberry Pi 400 does not expose a standard JTAG header on the board. Users interested in JTAG debugging must solder a connection to the SoC's JTAG pins — a non-trivial modification not covered in official documentation.

*Source: BCM2711 Boot EEPROM - Official Docs; community bare-metal forums*

---

## 6. Key Differences from Neighbouring Pi Generations

The Raspberry Pi 400 uses the BCM2711 SoC, placing it between the Raspberry Pi 4 Model B (identical SoC) and the Raspberry Pi 5 (BCM2712). Below are the key boot-related differences compared to other models.

### vs. Raspberry Pi 4 Model B

- **No functional differences.** The Pi 400 and Pi 4 Model B share the identical BCM2711 SoC and boot architecture. The only difference is form factor and integrated keyboard.
- Both support the same EEPROM bootloader, boot modes, and firmware files.

### vs. Raspberry Pi 3B+ / 3B (BCM2837B0)

| Feature | Pi 400 (BCM2711) | Pi 3B+ (BCM2837B0) |
|---------|------------------|--------------------|
| Bootloader storage | SPI EEPROM (64 KB) mutable | SD card only (`bootcode.bin` required) |
| Boot ROM | Yes (immutable) | Yes (immutable) |
| USB boot | Yes (native) | Yes (via `bootcode.bin` on SD card) |
| Network boot | Yes (PXE, HTTP) | Yes (PXE) |
| PCIe support | Yes (via USB hub) | No |
| 64-bit boot | Native (`kernel8.img`) | Requires `arm_64bit=1` in `config.txt` |
| VideoCore version | VideoCore VI | VideoCore IV |

- The Pi 3B+ does not have on-board EEPROM for the bootloader; it relies entirely on `bootcode.bin` on the SD card as the second-stage bootloader.
- The Pi 400's EEPROM bootloader allows boot order configuration without modifying the SD card.

### vs. Raspberry Pi 5 (BCM2712)

| Feature | Pi 400 (BCM2711) | Pi 5 (BCM2712) |
|---------|------------------|----------------|
| Bootloader storage | SPI EEPROM (64 KB) | SPI EEPROM (512 KB) — larger |
| Boot modes | SD, USB, PXE, HTTP | Same + enhanced NVMe boot support |
| PCIe support | Via USB hub (limited) | Native PCIe Gen 3 x1 (M.2 slot) |
| Firmware file | `start4.elf` | `start5.elf` |
| Default kernel | `kernel8.img` | `kernel8.img` (identical naming) |
| Boot time | Slightly slower (DDR4) | Faster (LPDDR4X, improved bootloader) |

-
