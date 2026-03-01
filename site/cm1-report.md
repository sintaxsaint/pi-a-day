# Compute Module 1 (BCM2835) -- Bootloader & Boot Process

*Generated 2026-03-01*

## Sources

- [Raspberry Pi Boot Modes - Official Docs](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-boot-modes)
- [RPi Boot Sequence - eLinux Wiki](https://elinux.org/RPi_Software)
- [raspberrypi/firmware - GitHub (bootcode.bin era)](https://github.com/raspberrypi/firmware)
- [How the Pi boots - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=6854)

---

# Compute Module 1 (BCM2835) — Bootloader & Boot Process: Community Documentation

**Document Version:** 1.0  
**Target Hardware:** Compute Module 1 (CM1), BCM2835 SoC  
**Scope:** Bootloader architecture, firmware components, boot modes, and bring-up considerations  

---

## 1. Overview of the BCM2835 Boot Sequence

The boot sequence on BCM2835 (used in the original Raspberry Pi 1, Pi Zero, and Compute Module 1) follows a well-documented but minimally officially documented path. Unlike newer SoCs, BCM2835 lacks an internal EEPROM bootloader; the entire boot firmware resides on external storage.

### Step-by-Step Boot Flow

1. **Power-On / Reset**
   - The SoC exits reset and begins executing the **first-stage bootloader** embedded in the **mask ROM** (BootROM) on the silicon.
   - This BootROM is hardcoded and cannot be modified.

2. **First-Stage: BootROM (SD Card Detection)**
   - The BootROM scans for a valid **SD card** (MMC/SD interface).
   - It looks for a properly formatted FAT filesystem (typically FAT16 or FAT32 on the boot partition).
   - Loads `bootcode.bin` from the SD card into L2 cache/ SRAM.

3. **Second-Stage: bootcode.bin**
   - Enables the SDRAM (RAM initialisation).
   - Loads `start.elf` into SDRAM.
   - At this point, GPU firmware takes over execution. The ARM CPU remains halted until the GPU prepares the environment.

4. **Third-Stage: start.elf (GPU Firmware)**
   - Parses `config.txt` and `cmdline.txt`.
   - Loads the Device Tree Blob (`.dtb`) or Device Tree Blob for B Plus (`.dtb`).
   - Loads `kernel.img` (or custom kernel specified in `config.txt`) into memory.
   - Configures ARM core clock, VPU, and hardware according to `config.txt` settings.
   - Releases the ARM CPU from reset — handoff to the operating system kernel.

5. **Kernel Handoff**
   - The ARM CPU begins executing at the entry point of `kernel.img`.
   - Boot arguments are passed via Device Tree or ATAGS (legacy).

> **Note:** This sequence is documented in community sources and inferred from the firmware binary behavior. The official Raspberry Pi documentation (Raspberry Pi Boot Modes - Official Docs) describes boot modes generically, but the specific internal BootROM behavior is not publicly disclosed by Broadcom.

---

## 2. Boot Firmware & Storage

### Firmware Components (SD Card-Based)

Unlike newer Compute Modules (CM3, CM4, CM5), the CM1 has **no on-board EEPROM**. All firmware resides on the SD card boot partition.

| File | Role |
|------|------|
| `bootcode.bin` | Second-stage bootloader; initializes SDRAM, loads `start.elf`. GPU firmware. |
| `start.elf` | Main GPU firmware; parses config, loads kernel, sets up hardware. |
| `fixup.dat` | Memory fixup table used by `start.elf` to configure SDRAM. |
| `config.txt` | Text-based configuration file for firmware and hardware settings. |
| `cmdline.txt` | Kernel command-line arguments. |
| `kernel.img` | Default ARM kernel image. |
| `*.dtb` | Device Tree Blob for hardware description. |

These files are hosted in the official GitHub firmware repository (raspberrypi/firmware).

### Storage Media

- **Primary:** MicroSD card (full-size SD adapter on CM1 IO board)
- **Boot Partition:** FAT16 or FAT32 (required for BootROM to read firmware)
- **Root Partition:** Can be ext4, F2FS, or other Linux filesystems

---

## 3. Boot Modes Supported

BCM2835 supports a limited set of boot modes compared to newer SoCs.

| Boot Mode | Support Status | Notes |
|-----------|----------------|-------|
| **SD Card** | ✅ Supported | Primary and default boot source. BootROM always attempts SD first. |
| **USB** | ⚠️ Limited | USB boot is possible but requires additional firmware (e.g., `bootcode.bin` supports USB mass storage on some Pi models). CM1 can boot from USB if the bootloader on the SD card supports it — but native USB boot (without SD card) is **not** available. |
| **Network / PXE** | ❌ Not supported natively | No built-in network boot capability in BCM2835. Requires an SD card with network boot files or custom firmware. |
| **GPIO Boot Mode** | ❌ Not available | This is a feature introduced on BCM2711 (Pi 4). Not present on BCM2835. |
| **EEPROM** | ❌ Not available | CM1 has no on-board bootloader EEPROM. |

> **Source:** Raspberry Pi Boot Modes - Official Docs confirms SD card is the primary boot mode for older hardware. Community knowledge indicates USB boot is not natively supported on BCM2835 without SD card intervention.

### Boot Order

BCM2835 BootROM default order:
1. SD card (MMC0)
2. (No internal fallback to USB or network)

---

## 4. UART / Serial Console

The Compute Module 1 exposes UART pins on the IO board, but there are specific considerations for serial console access.

### Default UART Configuration

- **Primary UART (UART0):** Exposed on GPIO pins 14 (TXD) and 15 (RXD) on the 22-pin IO header.
- **Baud Rate:** 115200 bps by default (unless overridden in `cmdline.txt` or `config.txt`).
- **No automatic console enable:** Unlike newer Pis with `enable_uart=1` in `config.txt`, CM1 may require explicit configuration.

### Serial Console Configuration

To enable serial console on CM1:

**In `config.txt`:**
```
enable_uart=1
```

**In `cmdline.txt`:**
```
console=serial0,115200 console=tty1 root=/dev/mmcblk0p2 rootfs=ext4 elevator=deadline fsck.repair=yes rootwait
```

### Quirks and Community Notes

- The CM1 IO board provides a **TTL-level serial header** (3.3V). Do not connect RS-232 directly — use a USB-to-TTL serial adapter.
- **Mini-UART vs. PL011:** On BCM2835, the primary UART is the **PL011** (full-featured UART). The mini-UART is available on the VideoCore subsystem but is not typically used for ARM console.
- **Bootloader serial output:** During early boot (before `start.elf` loads), minimal or no serial output is produced. The GPU firmware (`start.elf`) outputs to serial if configured.
- **Dual serial ports:** The Compute Module 1 has two UARTs available on GPIO, but only one is typically routed to the IO board.

> **Community Note:** Some users have reported that early boot messages from `bootcode.bin` or the BootROM are not accessible via the standard GPIO UART. This is consistent with the closed-source nature of the GPU firmware.

---

## 5. Bare-Metal and OS Bring-Up Notes

### U-Boot

- **Supported:** U-Boot can be used as a bootloader on BCM2835, replacing or supplementing the default `kernel.img` handoff.
- **Build:** Requires a BCM2835-specific defconfig (e.g., `rpi_defconfig` for original Pi, which applies to CM1).
- **Usage:** Place `u-boot.bin` or `u-boot.img` as `kernel.img` (or specify via `kernel=` in `config.txt`).
- **Limitations:** U-Boot must be built for the ARM1176 (ARM11) CPU core.

### Circle (Bare-Metal C++ Framework)

- **Supported:** Circle is a C++ bare-metal framework for Raspberry Pi (including BCM2835).
- **Use Case:** Ideal for custom firmware, RTOS-style development, or learning bare-metal programming on CM1.
- **Note:** Circle handles SDRAM initialization and provides its own startup code, bypassing `start.elf` in some configurations.

### Custom Firmware Considerations

- **Custom `bootcode.bin`:** Not feasible — binary-only and signed (community understanding).
- **Custom `start.elf`:** Not publicly documented; binaries are closed-source.
- **Custom kernel:** Fully supported; can replace `kernel.img`.
- **Device Tree:** BCM2835 supports both Device Tree and legacy ATAGs. Device Tree is the modern approach.

### SD Card Layout Requirements

For successful boot, the SD card must contain:
- A **FAT partition** (bootfs) marked as **bootable** (partition type 0x0C or 0x0E).
- Files: `bootcode.bin`, `start.elf`, `fixup.dat`, `config.txt`, `cmdline.txt`, `kernel.img`, `*.dtb`.

---

## 6. Key Differences from Neighbouring Pi Generations

| Feature | CM1 (BCM2835) | CM3 (BCM2837) | CM4 (BCM2711) |
|---------|---------------|---------------|---------------|
| **Boot EEPROM** | ❌ No | ❌ No | ✅ Yes |
| **BootROM Source** | SD card only | SD card only | SD / EEPROM / USB / Network |
| **USB Boot** | ⚠️ Via SD card | ⚠️ Via SD card | ✅ Native |
| **Network Boot** | ❌ | ❌ | ✅ (PXE) |
| **GPIO Boot Mode** | ❌ | ❌ | ✅ |
| **64-bit Support** | ❌ | ✅ (ARMv8 in 32-bit mode) | ✅ |
| **UEFI/EDK2** | ❌ | Limited | ✅ (community) |

### Why These Differences Matter

- **No EEPROM:** CM1 cannot boot without an SD card. This limits its use in embedded or headless deployments where SD card failure is a concern.
- **Limited boot media:** No native USB or network boot means deployment flexibility is reduced compared to CM4.
- **Older GPU architecture:** The VideoCore IV in BCM2835 is significantly less powerful than the VideoCore VI in BCM2711.

---

## 7. Open Questions / Areas Without Official Documentation

1. **BootROM Source Code**  
   - The BootROM in BCM2835 is closed and not publicly documented. Its exact behavior (SD card detect timing, error handling) is inferred, not specified.

2. **Bootcode.bin Internals**  
   - `bootcode.bin` is binary-only and not open source. The exact sequence of SDRAM initialization is not publicly documented.

3. **Secure Boot**  
   - BCM2835 has no documented secure boot chain. There is no OTP-based boot verification.

4. **Exact Boot Order Behavior**  
   - While SD card is known to be first, the precise fallback behavior (if SD fails, does it attempt USB?) is not officially documented for BCM2835.

5. **GPU Firmware Configuration**  
   - The full range of `config.txt` options for BCM2835 is documented in the official docs, but the underlying GPU firmware behavior is closed-source. Some undocumented options exist in community repositories.

6. **USB Boot Limitations**  
   - Whether `bootcode.bin` on BCM2835 can actually boot from USB mass storage devices (without an SD card) is unclear and likely not supported.

---

## References

- **Raspberry Pi Boot Modes - Official Docs** — https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-boot-modes
- **raspberrypi/firmware GitHub Repository** — https://github.com/raspberrypi/firmware (boot firmware binaries)
- **Raspberry Pi Forums** — Community discussions on boot behavior and hardware (note: forum content varies in technical depth)
- **Compute Module Hardware Documentation** — Official Compute Module IO board and CM1 specifications

---

*This document is community-maintained. Information is based on publicly available sources, community experimentation, and inference from firmware behavior. For official support, consult Raspberry Pi Ltd. directly.*
