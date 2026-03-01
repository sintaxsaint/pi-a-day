# Raspberry Pi 2 Model B (BCM2836) -- Bootloader & Boot Process

*Generated 2026-03-01*

## Sources

- [Raspberry Pi Boot Modes - Official Docs](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-boot-modes)
- [How the Pi boots - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=6854)
- [RPi U-Boot - eLinux Wiki](https://elinux.org/RPi_U-Boot)
- [raspberrypi/firmware - GitHub](https://github.com/raspberrypi/firmware)

---

# Raspberry Pi 2 Model B (BCM2836) — Bootloader & Boot Process: Community Documentation

**Document Scope**: Raspberry Pi 2 Model B rev 1.0 and rev 1.1 (BCM2836)  
**Audience**: Embedded developers, firmware engineers, and community contributors  
**Status**: Community-compiled; some areas lack official documentation  

---

## 1. Overview of the BCM2836 Boot Sequence

The Raspberry Pi 2 Model B uses a unique **GPU-first boot architecture**. Unlike typical ARM SoCs where the CPU boots first, the BCM2836 (and its predecessor BCM2835) boots the VideoCore IV GPU, which then initializes and boots the ARM cores. This is a distinctive characteristic of all Raspberry Pi models prior to the Raspberry Pi 4.

### Step-by-Step Boot Flow

1. **Power-On / Reset**
   - On power-on, the BCM2836's internal boot ROM (masked into the silicon) executes first.
   - The boot ROM's primary task is to locate and load the next-stage bootloader from external storage.

2. **Boot ROM Searches for `bootcode.bin`**
   - The boot ROM scans for a FAT-formatted SD card (or other boot media) in a fixed order.
   - It reads the first partition, looking for a file named `bootcode.bin` in the root directory.
   - **Note**: If `bootcode.bin` is not found, the boot sequence halts with no video output and the ACT LED remains off.
   - Source: `raspberrypi/firmware` GitHub repository describes `bootcode.bin` as "the GPU firmwares and bootloader" (raspberrypi/firmware)

3. **`bootcode.bin` Executes on GPU**
   - Loaded into the GPU's L2 cache or small internal RAM.
   - This stage initializes the SDRAM (memory controller) and prepares the system for loading the main firmware.
   - It also performs early GPIO pin setup and basic power management.

4. **Loading of `start.elf`**
   - After SDRAM is available, `bootcode.bin` loads `start.elf` (or a variant — see Section 2) into SDRAM.
   - `start.elf` is a large binary blob containing the VideoCore firmware, which includes:
     - Graphics processing initialisation
     - Framebuffer setup
     - Hardware initialization (USB, Ethernet, etc.)
     - Device Tree blob (`.dtb`) loading
     - ARM kernel loading and handoff

5. **Device Tree and Configuration Loading**
   - The firmware reads `config.txt` for board configuration (GPU memory split, overclocking, device tree parameters, etc.).
   - It reads `cmdline.txt` to build the kernel command line.
   - It loads the appropriate `.dtb` file (e.g., `bcm2709-rpi-2-b.dtb`) for the BCM2836.

6. **Kernel Load and ARM Handoff**
   - The firmware loads `kernel.img` (or a custom kernel filename) into memory at a fixed address.
   - It configures the ARM core(s) with the device tree pointer, ATAGS (if used), and any initrd.
   - The GPU releases the ARM cores from reset, and execution begins at the kernel's entry point.
   - The GPU continues running for video/graphics services but is no longer in the boot path.

### Summary of Memory Map (BCM2836)

| Address Range       | Purpose                        |
|---------------------|--------------------------------|
| 0x0000_0000–0x0FFF_FFFF | Boot ROM (internal)          |
| 0x2000_0000–0x20FF_FFFF | SDRAM (1 GB on Pi 2 B)      |
| 0x3F00_0000–0x3FFFFFFF | Peripheral registers (BCM2836) |

---

## 2. Boot Firmware & Storage

### Firmware Files on the Boot Partition

The SD card's FAT partition must contain at minimum the following files for a successful boot:

| File               | Description |
|--------------------|-------------|
| `bootcode.bin`     | Second-stage bootloader; runs on the GPU. Initializes SDRAM. |
| `start.elf`        | Main GPU firmware blob; handles boot configuration and kernel handoff. |
| `fixup.dat`        | Memory fixup data for `start.elf`; must match the specific `start.elf` version. |
| `config.txt`       | Board configuration (GPU memory, overclock, DTB overlays, etc.). |
| `cmdline.txt`      | Kernel command line arguments. |
| `kernel.img`       | Linux kernel (or custom firmware) for the ARM cores. |
| `*.dtb`            | Device Tree Blob for the board (e.g., `bcm2709-rpi-2-b.dtb`). |

Source: `raspberrypi/firmware` GitHub repository

### Firmware Variants

The firmware directory (`/boot` on Raspberry Pi OS) contains several variants of the GPU firmware:

- **`start.elf`**: Standard firmware with all features enabled.
- **`start_x.elf`**: Includes camera support (likely unused on Pi 2 B unless a Camera Module is attached).
- **`start_db.elf`**: Debug-enabled firmware; provides additional serial output during boot.
- **`start_cd.elf`**: Cut-down firmware (reduced features, lower memory footprint).

Each variant has a matching `fixup_*.dat` file.

### Storage Medium

- **Primary boot medium**: SD card (MMC/SDIO interface)
- The BCM2836 boot ROM is hardcoded to search for `bootcode.bin` on the SD card first. There is **no on-chip EEPROM** for storing the bootloader on the Pi 2 Model B (unlike Pi 3B+ and later models).
- USB boot and network boot are supported as *secondary* boot modes, but require additional configuration (see Section 3).

### Firmware Update Mechanism

Firmware is updated by replacing the files on the SD card's boot partition with newer versions from the official `raspberrypi/firmware` GitHub repository. There is no on-board EEPROM to store firmware; all firmware is loaded from the SD card each boot.

---

## 3. Boot Modes Supported

The BCM2836 supports multiple boot modes, though not all are enabled by default.

### 3.1 SD Card Boot (Primary / Default)

- The boot ROM looks for an SD card in the microSD slot.
- The card must have a FAT-formatted partition (usually the first partition).
- The boot ROM reads `bootcode.bin` from the root of this partition.
- **Quirk**: The boot ROM does *not* support SD cards larger than 32 GB formatted as FAT32 without specific adjustments. Larger cards typically work because the boot ROM only reads the first partition, which can still be FAT16/FAT32.

### 3.2 USB Boot Mode

The BCM2836 can boot from USB mass storage devices, but this requires an enablement step:

- **Requires `bootcode.bin` with USB support**: The standard `bootcode.bin` includes USB driver code, but the boot ROM does not enumerate USB devices until after `bootcode.bin` runs.
- **Process**: The boot ROM still requires an SD card with `bootcode.bin` to initiate USB boot. Once loaded, `bootcode.bin` can enumerate USB mass storage and load `start.elf` and the kernel from a USB device.
- **Configuration**: Setting `program_usb_boot_mode=1` in `config.txt` (or an OTP bit) reprograms the SoC to attempt USB boot if no valid SD card is detected. However, on the BCM2836 this is a community-documented feature — not officially guaranteed by Broadcom.
- **Source**: Raspberry Pi boot modes documentation (Raspberry Pi Boot Modes - Official Docs)

> **Community Note**: USB boot on BCM2836 is less reliable than on later chips (BCM2837, BCM2711). Many users report that a small SD card with only `bootcode.bin` is needed as a "boot stub" to enable full USB boot.

### 3.3 Network Boot (PXE)

- The BCM2836 supports PXE (Preboot eXecution Environment) over Ethernet.
- **Requirements**:
  - A DHCP server on the network to provide IP address and TFTP server details.
  - A TFTP server hosting `bootcode.bin`, `start.elf`, `config.txt`, `cmdline.txt`, and kernel files.
- **Enablement**: Network boot is typically triggered when no SD card is present and a DHCP server is available.
- **Source**: Raspberry Pi Boot Modes - Official Docs

> **Community Note**: Network boot requires the `usb-hub` firmware to be loaded (part of `start.elf`). Ethernet is provided by the on-board LAN9514/LAN9512 USB-to-Ethernet chip, which must be initialised before network boot can proceed. This adds delay and complexity compared to SD boot.

### 3.4 Boot Mode Summary Table

| Boot Mode   | Default? | Requires SD Card? | Notes |
|-------------|-----------|-------------------|-------|
| SD Card     | Yes       | Yes (mandatory)   | Primary and most reliable boot source. |
| USB         | No        | Optional (see note) | Requires `bootcode.bin` on SD or OTP enablement. |
| PXE/Network | No        | No                | Requires Ethernet hardware and DHCP/TFTP server. |

---

## 4. UART / Serial Console — Configuration and Quirks

### UART Hardware on BCM2836

The BCM2836 features two UARTs:

- **UART0** (PL011): Full-featured UART, used by default for the serial console.
- **UART1** (mini-UART): Simpler UART with fewer features, typically used for Bluetooth on later models (not applicable to Pi 2 B).

### Pinout on the 40-Pin Header

| Pin # | Function       | GPIO Pin |
|-------|----------------|----------|
| 8     | UART0 TX       | GPIO 14  |
| 10    | UART0 RX       | GPIO 15  |
| 6     | GND            | —        |

> **Warning**: The UART runs at 3.3V logic levels. Do not connect directly to RS-232 ports without a level shifter.

### Enabling the Serial Console

1. **Add to `cmdline.txt`**:
   ```
   console=serial0,115200 console=tty1 root=/dev/mmcblk0p2 rootfs type=ext4 fsck.repair=yes rootwait
   ```
   This tells the kernel to use `serial0` (mapped to UART0) as a console at 115200 baud.

2. **Optional: Disable serial console in `config.txt`**:
   ```
   enable_uart=1
   ```
   This ensures the UART is enabled (on some OS images it may be disabled by default to save power).

### Bootloader Serial Output

- `start.elf` outputs boot messages to the UART *before* the Linux kernel takes over.
- If using `start_db.elf` (debug firmware), additional diagnostic messages are printed.
- The baud rate is fixed at 115200 by the firmware.

### Known Quirks

- **No early UART on boot ROM**: The BCM2836 boot ROM does *not* output to UART. If the board fails to boot, there is no serial output until `bootcode.bin` loads.
- **GPIO pin muxing**: By default, GPIO 14 and 15 are configured for UART0. If you need these GPIO pins for other purposes, you must disable the UART in `config.txt` (`enable_uart=0`) and/or use a device tree overlay to remap.
- **Flow control**: The serial console does not use hardware flow control (RTS/CTS) by default. This is consistent across all Pi models prior to Pi 4.
- **BLE / Bluetooth conflict**: Not applicable to Pi 2 B — Bluetooth was not integrated until Pi 3 B.

---

## 5. Bare-Metal and OS Bring-Up Notes

### 5.1 Loading Custom Firmware

Unlike platforms with a traditional BIOS or UEFI, the Raspberry Pi has no built-in firmware loader for arbitrary ARM binaries. Instead, the GPU (`start.elf`) is responsible for loading and starting the ARM code.

To run bare-metal code on the Pi 2 Model B:

1. **Use the standard boot flow** — compile your code as `kernel.img` and place it on the SD card. The GPU will load and jump to your code.
2. **Alternative**: Disable the GPU entirely (not officially supported on BCM2836; some community projects have attempted GPU-free boot but it requires replacing the boot ROM, which is not possible).

### 5.2 U-Boot

U-Boot can be used as a secondary bootloader on the Pi 2:

1. Compile U-Boot for `rpi_2` or `bcm2836`.
2. Rename the U-Boot binary to `boot.scr` or load it via `bootcmd` in `config.txt`.
3. U-Boot runs as a "kernel" loaded by `start.elf`.

> **Community Note**: The official Raspberry Pi documentation does not cover U-Boot in detail, but the eLinux Wiki (RPi U-Boot) documents build and deployment steps. The page was not accessible during source collection, but community forums confirm U-Boot support exists for the Pi 2.

### 5.3 Circle — A Bare-Metal C++ Framework

Circle is a C++ bare-metal framework for Raspberry Pi (supporting Pi 1, 2, 3, and 4). It provides:

- A standalone runtime that does not require `start.elf` (by using a custom `kernel.img` that handles all hardware init).
- Direct peripheral access without the VideoCore.
- Build system support for the BCM2836.

### 5.4 Custom Firmware Considerations

- **Memory split**: In `config.txt`, set `gpu_mem` to control how much SDRAM is allocated to the GPU. Bare-metal code typically sets `gpu_mem=16` or `gpu_mem=0` to maximise available RAM.
- **Device Tree**: Even bare-metal code can use the `.dtb` file for hardware discovery, or disable device tree with `device_tree=` in `config.txt`.
- **ATAGS vs. Device Tree**: The BCM2836 supports both ATAGS (legacy) and Device Tree. Linux uses Device Tree; bare-metal code may use either.

### 5.5 Loading an Initrd

If your bare-metal setup requires an initial ramdisk:

```
initramfs initrd.gz followkernel
```

This tells `start.elf` to load the initrd and pass its address to the kernel.

---

## 6. Key Differences from Neighbouring Pi Generations

| Feature                | Pi 1 (BCM2835)      | Pi 2 B (BCM2836)      | Pi 3 B (BCM2837)    |
|------------------------|---------------------|-----------------------|---------------------|
| CPU                    | Single-core Cortex-A7 (actually ARM1176JZF-S) | Quad-core Cortex-A7 | Quad-core Cortex-A53 (64-bit) |
| RAM                    | 256–512 MB          | 1 GB                  | 1 GB                |
| Boot ROM               | Same architecture   | Same architecture     | Same + EEPROM option |
| Boot firmware location | SD card only        | SD card only          | SD card; optional EEPROM (Pi 3B+) |
| USB boot               | Limited             | Supported (via bootcode.bin) | Supported (more reliable) |
| Network boot           | Yes (PXE)           | Yes (PXE)             | Yes (PXE)           |
| 64-bit support         | No                  | No                    | Yes (ARMv8)         |
| On-board Bluetooth    | No                  | No                    | Yes (Pi 3 B only)   |

### Differences Specific to BCM2836 vs. BCM2835

- **CPU cores**: The BCM2836 adds three additional ARM cores (total 4). The boot ROM must bring up all four cores; `start.elf` configures SMP (symmetric multiprocessing).
- **Memory**: The BCM2836 supports up to 1 GB of SDRAM, double the maximum of BCM2835.
- **Peripheral base address**: The peripheral register base changed from `0x20000000` (BCM2835) to `0x3F000000` (BCM2836). This is reflected in the Device Tree and in bare-metal code.
- **
