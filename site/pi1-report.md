# Raspberry Pi 1 (BCM2835) -- Bootloader & Boot Process

*Generated 2026-03-01*

## Sources

- [Raspberry Pi Boot Modes - Official Docs](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-boot-modes)
- [RPi Boot Sequence - eLinux Wiki](https://elinux.org/RPi_Software)
- [raspberrypi/firmware - GitHub (bootcode.bin era)](https://github.com/raspberrypi/firmware)
- [How the Pi boots - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=6854)

---

# Raspberry Pi 1 (BCM2835) -- Bootloader & Boot Process: Community Documentation

**Target Hardware:** Raspberry Pi 1 Model A, Model B, Model A+, Model B+ (all variants using BCM2835 SoC)

---

## 1. Overview of the BCM2835 Boot Sequence

The BCM2835 employs a distinctive boot architecture in which the **VideoCore GPU** serves as the primary boot processor, with the ARM1176JZF-S CPU being activated only after the GPU has prepared the system. This is fundamentally different from most embedded platforms where the main CPU handles all boot stages.

### Step-by-Step Boot Flow

| Stage | Component | Executed On | Source |
|-------|-----------|-------------|--------|
| 1 | First-stage ROM bootloader | ARM1176 (ROM) | Internal SoC mask ROM |
| 2 | `bootcode.bin` | GPU (VideoCore) | SD card FAT partition |
| 3 | `start.elf` (or `start4.elf` for Pi 4, not applicable here) | GPU (VideoCore) | SD card FAT partition |
| 4 | Kernel / OS | ARM1176 | SD card or other media |

### Detailed Sequence

1. **Power-On Reset**
   - The BCM2835 SoC powers on with the GPU core active and the ARM core held in reset
   - The internal ROM bootloader (mask ROM, not modifiable) begins execution on the GPU

2. **SD Card Detection and Loading**
   - The ROM bootloader scans the SD card for a FAT16 or FAT32 boot partition
   - It reads the first `bootcode.bin` found (typically 64KB or less in early versions) into the GPU's L2 cache or small on-chip SRAM
   - This loader contains the SDRAM initialization code specific to the Pi 1 hardware

   *(Source: Raspberry Pi GitHub firmware repository contains bootcode.bin in the /boot directory)*

3. **SDRAM Initialization (bootcode.bin)**
   - `bootcode.bin` executes on the GPU and initializes the external SDRAM
   - This is a critical step -- without working SDRAM, the Pi cannot proceed to load larger firmware components or the Linux kernel
   - The memory controller is configured with timing parameters specific to the SDRAM chips used on the Pi 1 board

4. **Loading start.elf**
   - Once SDRAM is available, `bootcode.bin` loads `start.elf` (the main VideoCore firmware) into SDRAM
   - `start.elf` is significantly larger (several MB) and contains:
     - Graphics processing firmware
     - Audio/video codecs
     - The ARM bootloader logic
     - Device tree blob handling

5. **Configuration Reading (config.txt)**
   - `start.elf` reads `config.txt` from the boot partition to configure boot options
   - This file controls memory split (GPU vs ARM), video settings, enable_uart, overclocking, and device tree parameters

6. **Kernel Loading**
   - `start.elf` loads `kernel.img` (or a named kernel such as `kernel7.img` on later models, but Pi 1 uses `kernel.img`) into memory at address 0x00008000
   - It prepares either ATAGS (for older kernels) or a device tree blob (DTB) in memory
   - For Pi 1, the default is ATAGS at address 0x100

7. **ARM Handoff**
   - `start.elf` releases the ARM1176JZF-S from reset
   - The ARM CPU begins execution at address 0x00008000
   - Boot is complete; the Linux kernel (or bare-metal firmware) takes over

---

## 2. Boot Firmware & Storage

### Firmware Files on the SD Card Boot Partition

The Raspberry Pi 1 requires a FAT-formatted boot partition (typically the first partition, type 0x0C FAT32 or 0x0E FAT16) containing the following files:

| File | Size (approx.) | Purpose |
|------|----------------|---------|
| `bootcode.bin` | ~24KB–64KB | Second-stage bootloader; SDRAM init; loads start.elf |
| `start.elf` | ~1–4MB | Main GPU firmware; loads kernel/config; configures ARM handoff |
| `fixup.dat` | ~4KB–8KB | Memory fixup/relocation table used by start.elf |
| `config.txt` | Text | Boot configuration (user-editable) |
| `cmdline.txt` | Text | Kernel command line arguments |
| `kernel.img` | Varies | ARM executable kernel (or bare-metal program) |
| `*.dtb` | Varies | Device tree blobs (optional for Pi 1) |

*(Source: GitHub raspberrypi/firmware /boot directory structure)*

### Boot Order Priority

The ROM bootloader searches for `bootcode.bin` in the following locations (in order):

1. SD card (primary boot mode)
2. If not found, it attempts USB (with additional requirements)
3. Network boot is **not** natively supported by the BCM2835 ROM; this requires special bootloader modifications or an external SPI EEPROM (not present on Pi 1)

### EEPROM

**There is no external SPI EEPROM on the original Raspberry Pi 1 (Model A/B) or A+/B+.** The bootloader resides entirely on the SD card. This is a key distinction from later Pi models (Pi 3B+, Pi 4, Pi 5) which include an external EEPROM for storing a more flexible bootloader.

The boot firmware (`bootcode.bin`, `start.elf`, `fixup.dat`) is stored on the SD card's boot partition and must be present for each boot.

---

## 3. Boot Modes Supported

### SD Card (Primary and Only Native Mode)

- **Supported on all Pi 1 models:** Model A, Model B, Model A+, Model B+
- The BCM2835 ROM bootloader natively supports SD card boot only
- Requires a FAT-formatted partition as the first partition
- Boot files must be in the root of this partition
- The SD card must contain a valid partition table and boot sector

### USB (Limited/Community-Enabled)

- **USB boot is NOT natively supported by the BCM2835 ROM.** The original Pi 1 cannot boot directly from USB devices without significant workarounds.
- **Community workarounds exist:** Users have developed custom `bootcode.bin` variants (often called "USB boot" firmware) that allow loading from USB mass storage devices. These modified bootloaders are typically sourced from community forums or the `raspberrypi/firmware` repository's "extra" branches.
- USB boot requires the custom bootloader to first initialize USB (which the ROM cannot do), load `bootcode.bin` from a USB device, then proceed with SDRAM init and kernel load.
- **Important:** The Pi 1 Model A+ and B+ have more robust power management that may help with USB boot reliability, but the fundamental ROM limitation remains.

### Network/PXE (Not Natively Supported)

- The BCM2835 **does not** have native PXE/network boot capability in its ROM
- No Ethernet boot option is available out-of-the-box
- Community solutions exist using modified `bootcode.bin` that implement DHCP/TFTP clients, but these are not part of the official firmware and are considered experimental on Pi 1

### Summary Table

| Boot Mode | Native ROM Support | Notes |
|-----------|-------------------|-------|
| SD Card | **Yes** (primary) | Requires FAT partition with bootcode.bin |
| USB | **No** | Requires custom community bootloader |
| Network/PXE | **No** | Requires custom community bootloader |
| EEPROM | **No** | No external EEPROM on Pi 1 |

---

## 4. UART / Serial Console

### Default UART Configuration

- The BCM2835 has two UARTs:
  - **UART0 (PL011)** - Full-featured, used by default for serial console
  - **UART1 (mini UART)** - Limited features, lower performance
- On Pi 1, the **PL011 UART** is mapped to the GPIO pins 14 (TXD) and 15 (RXD) by default
- Default baud rate: **115200 bps**, 8N1 (8 data bits, no parity, 1 stop bit)

### Enabling Serial Console

- By default, the Pi 1 may or may not output to UART depending on the firmware version and `config.txt` settings
- To enable serial console output:
  ```
  enable_uart=1
  ```
  in `config.txt` (or `enable_uart=0` to disable)
- The serial console is controlled by `start.elf` firmware; earlier firmware versions had the UART enabled by default, while newer versions may require explicit enablement

### Hardware Connections

| GPIO Pin | Function | Notes |
|----------|----------|-------|
| GPIO 14 | UART0 TXD | Transmit data |
| GPIO 15 | UART0 RXD | Receive data |
| GPIO 17 | Optional: RTS/CTS | Not used by default |
| Ground | GND | Reference ground |

- A USB-to-serial TTL adapter (e.g., FTDI, CP2102) set to 3.3V logic is required
- **Warning:** Do NOT connect 5V serial adapters directly; use 3.3V logic level or level shifters to avoid damaging the BCM2835's GPIO

### Quirks on Raspberry Pi 1

1. **No automatic console on early firmware:** Early versions of `bootcode.bin`/`start.elf` did not automatically output to UART. Users reported needing specific firmware versions or `config.txt` options to see boot messages.

2. **Baud rate variation:** Some early firmware used 9600 baud by default. Modern firmware uses 115200 baud.

3. **HDMI/Composite video override:** The GPU boot process outputs to video first; serial console may be secondary. If no video output is connected, serial console may still show boot messages.

4. **GPIO pin changes on Model A+ / B+:** The header layout remains the same, but power management differences may affect UART stability (especially with certain USB hubs or power conditions).

5. **Mini UART vs PL011:** On Pi 1, the PL011 is the primary. The mini UART (UART1) is available on GPIO 14/15 if the PL011 is reconfigured, but this is rarely used.

---

## 5. Bare-Metal and OS Bring-up Notes

### U-Boot

- U-Boot can be used as a second-stage bootloader on Pi 1, loaded after `start.elf` hands off to ARM
- However, because `start.elf` already handles memory initialization and kernel loading, using U-Boot on Pi 1 is less common than on other embedded platforms
- To use U-Boot: compile `u-boot.bin` for Raspberry Pi, rename to `kernel.img`, place on SD card; U-Boot will then load the final OS
- U-Boot on Pi 1 requires a device tree blob (DTB) or ATAGS setup matching the BCM2835 hardware

### Circle (Bare-Metal C++ Framework)

- Circle is a C++ bare-metal framework for Raspberry Pi (supports Pi 1 through Pi 3)
- For Pi 1 (BCM2835), Circle provides:
  - Direct hardware access without an OS
  - SDRAM initialization (or uses the one set up by start.elf)
  - GPU initialization (optional, via circular buffer)
  - USB host/device support
  - Basic peripherals (GPIO, timer, UART, interrupt controller)
- Circle can run either:
  - **After start.elf** (using the GPU-provided memory setup), or
  - **Standalone** (by replacing kernel.img and providing minimal initialization)

### Custom Firmware / Bare-Metal Development

- The Pi 1 is an excellent platform for bare-metal development
- Custom ARM code can be loaded as `kernel.img`
- Key considerations:
  - The ARM core starts at 0x00008000
  - ATAGS are at 0x100 (if using device tree, DTB is passed in r2 or at a configured address)
  - The GPU must have already initialized SDRAM (requires running start.elf)
  - Alternative: bypass GPU entirely and write ROM-compatible code (requires different bootloader, not covered here)

### Linux Kernel

- Linux kernel for Pi 1 uses the `bcmrpi` or `bcm2709` device tree (though `bcmrpi_defconfig` is typical)
- Kernel versions up to 6.x continue to support BCM2835 (Pi 1)
- The kernel is loaded by `start.elf` at the address specified in the firmware

---

## 6. Key Differences from Neighbouring Pi Generations

| Feature | Pi 1 (BCM2835) | Pi 2 (BCM2836/2837) | Pi 3 (BCM2837) |
|---------|----------------|---------------------|----------------|
| SoC | BCM2835 (single-core ARM1176 @ 700MHz) | BCM2836/2837 (quad-core Cortex-A7/A53) | BCM2837 (quad-core Cortex-A53) |
| Boot processor | GPU (VideoCore) | GPU (VideoCore) | GPU (VideoCore) |
| Native USB boot | No (requires custom bootloader) | No | Yes (with OTP bit) |
| Network boot | No | No | Yes (with OTP bit) |
| External EEPROM | No | No | No (Pi 3B+ has it) |
| 64-bit support | No (ARMv6) | No (ARMv7) | Yes (ARMv8, optional) |
| Memory split config | `gpu_mem` in config.txt | `gpu_mem` in config.txt | `gpu_mem` in config.txt |
| Default kernel | `kernel.img` | `kernel7.img` | `kernel7.img` (or kernel8 for 64-bit) |
| Boot ROM location | Mask ROM in SoC | Mask ROM in SoC | Mask ROM in SoC |

### Pi 1 Model A+ / B+ Specific Differences

- **Reduced power consumption:** Model A+ and B+ use smaller PCB and lower-power components
- **Same boot process:** The boot sequence is identical to original Model A/B
- **No hardware differences in boot:** All Pi 1 variants share the same BCM2835 and boot behavior

---

## 7. Open Questions / Areas Without Official Documentation

### Community-Only or Undocumented Areas

1. **Exact contents of bootcode.bin:** The binary is closed-source (Broadcom proprietary). Its exact initialization sequence and SDRAM timing parameters are not publicly documented. Community knowledge is derived from reverse engineering.

2. **SD card timing and compatibility:** The ROM bootloader's SD card interface is not formally documented. Some SD cards may fail to boot due to timing issues; the community maintains lists of known-working and non-working cards.

3. **USB boot implementation details:** Since USB boot requires custom/community bootloader variants, the exact method to enable it and the limitations are not officially documented.

4. **GPU memory split internals:** While `gpu_mem` in config.txt controls the split, the exact memory layout and why certain values are required are not publicly documented.

5. **Bootloader update mechanism:** There is no official "firmware update" process for Pi 1; users manually copy newer `bootcode.bin`, `start.elf`, and `fixup.dat` from the Raspberry Pi GitHub repository.

6. **Recovery boot mode:** There is no dedicated "recovery" mode button or ROM-level recovery on Pi 1; if SD card boot fails, the device is effectively bricked until a working SD card is inserted.

7. **Device tree vs ATAGS preference:** The transition from ATAGS to device tree happened across firmware versions; exact firmware versions where device tree became default are not formally documented.

---

## References

- Raspberry Pi GitHub Firmware Repository: https://github.com/raspberrypi/firmware
- eLinux Wiki: RPi Software (boot sequence documentation)
- Raspberry Pi Forums: Community discussions on boot modes, UART, and firmware

---

*This
