# Raspberry Pi 500 (BCM2712) -- Bootloader & Boot Process

*Generated 2026-03-01*

## Sources

- [Pi 5 Boot Process - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=373222)
- [kernel_2712.img - DeepWiki](https://deepwiki.com/raspberrypi/firmware/2.1.5-raspberry-pi-5-kernel-(kernel_2712.img))
- [Supporting Pi 5 - Circle Discussion #413](https://github.com/rsta2/circle/discussions/413)
- [UART on Pi 5 GPIO 14/15 - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=378931)

---

# Raspberry Pi 500 (BCM2712) -- Bootloader & Boot Process: Community Documentation

**Report Type:** Community Documentation  
**Target Hardware:** Raspberry Pi 500 (BCM2712)  
**Last Updated:** 2025

---

> **Note on Scope:** The Raspberry Pi 500 uses the same BCM2712 processor as the Raspberry Pi 5, in a keyboard-integrated form factor. This document covers the boot process as it applies to the Pi 500; where behavior is identical to the Pi 5, it is noted as such.

---

## 1. Overview of the BCM2712 Boot Sequence

The BCM2712 boot sequence on the Raspberry Pi 500 proceeds through several distinct stages, from power-on to kernel handoff. Unlike earlier Raspberry Pi models, the Pi 500 does not rely on bootcode.bin on the SD card; all firmware resides in SPI flash.

### Step-by-Step Boot Flow

1. **Power-On / POR Reset**
   - The system emerges from power-on reset. Execution begins on the VideoCore VI (VPU) processor, which contains a mask ROM that cannot be modified.

2. **VPU Boot ROM Execution**
   - The VPU executes the built-in mask ROM, which contains the first-stage bootloader.
   - *Source: Raspberry Pi Forums – "Pi5 Boot Process" (cleverca22)*

3. **SPI Flash Loader**
   - The boot ROM reads a **tagged binary blob** from the SPI flash memory chip.
   - This blob is stored in EEPROM on the board and is not user-editable without specialized tools.

4. **LPDDR4 Memory Initialization**
   - The loaded blob initializes the LPDDR4 memory controller, bringing the system RAM online.
   - *Source: Raspberry Pi Forums – "Pi5 Boot Process" (cleverca22)*

5. **bootmain.elf Loading**
   - The blob loads `bootmain.elf` from SPI flash and transfers execution to it.
   - *Source: Raspberry Pi Forums – "Pi5 Boot Process" (cleverca22)*

6. **Boot Configuration Reading**
   - `bootmain.elf` reads `bootconf.txt` (also held in SPI flash), which contains the **BOOT_ORDER** directive and other boot-time parameters.
   - *Source: Raspberry Pi Forums – "Pi5 Boot Process" (cleverca22)*

7. **Boot Device Selection (BOOT_ORDER)**
   - Based on the `BOOT_ORDER` setting, the firmware attempts to boot from configured media (SD card, USB, network).
   - *Source: Raspberry Pi Forums – "Pi5 Boot Process" (cleverca22)*

8. **Kernel Handoff**
   - For Linux: The firmware loads `kernel8.img`, the device tree blob (e.g., `bcm2712-rpi-500-b.dtb`), and any initramfs.
   - For bare-metal: The firmware loads the user-specified kernel image to the address defined in `config.txt` and transfers control.
   - *Source: Community experimentation (satyria, Fridux)*

---

## 2. Boot Firmware & Storage

Unlike earlier Raspberry Pi models, the Pi 500 stores all boot firmware in **SPI flash EEPROM** on the board. No boot files are required on the SD card for basic operation, though configuration files are needed.

### Firmware Components

| Component | Location | Notes |
|-----------|----------|-------|
| Boot ROM (first stage) | VPU mask ROM | Cannot be modified |
| Tagged blob | SPI flash EEPROM | Contains memory init and second-stage loader |
| bootmain.elf | SPI flash EEPROM | Second-stage bootloader |
| bootconf.txt | SPI flash EEPROM | Contains BOOT_ORDER and related settings |
| start.elf / fixup.dat | **Not used** | These files are only for Pi 0–4; Pi 5/500 does not use them |
| start4.elf / fixup4.dat | **Not used** | Pi 4-specific; replaced by SPI flash firmware |

> *"start.elf and fixup.dat are only valid on the pi0-pi3... and pi5 just doesnt need any elf or dat, its all in SPI flash."*  
> — cleverca22, Raspberry Pi Forums

### SD Card Requirements

For a minimal boot, the SD card must contain:

1. **`config.txt`** – Required. Specifies kernel location and other boot options.
2. **Device Tree Blob** – Required for Linux. Typically `bcm2712-rpi-500-b.dtb` (or `bcm2712-rpi-5-b.dtb` as a substitute).
3. **Kernel image** – `kernel8.img` is the default; custom names can be specified in `config.txt`.

> *"It's true that only bcm2712-rpi-5-b.dtb and config.txt are needed on the SD card."*  
> — satyria, Raspberry Pi Forums

> *"Actually you only need config.txt to boot a Pi 5, in addition to your kernel / bare metal application which should be named kernel8.img by default."*  
> — Fridux, Raspberry Pi Forums

### Minimal config.txt for Bare-Metal

```ini
kernel_address=0x80000
kernel=mykernel.img
os_check=0
```

- `kernel_address=0x80000` — Specifies the load address. Without this, the firmware may load the image to `0x200000` and attempt Linux-specific setup.
- `os_check=0` — Disables OS validation, allowing bare-metal programs to execute correctly.
- *Source: Community experimentation (Fridux, rsta2)*

---

## 3. Boot Modes Supported

The BCM2712 on the Pi 500 supports multiple boot modes, configured via the `BOOT_ORDER` setting in SPI flash. The default boot order can be modified using the `raspi-config` tool or by editing the SPI flash boot configuration.

### Supported Boot Modes

| Boot Mode | Description | Availability |
|-----------|-------------|--------------|
| **SD Card** | Boot from microSD card inserted in the onboard slot | Default primary |
| **USB** | Boot from USB mass storage device (USB flash drive, SSD, HDD) | Supported |
| **Network / PXE** | Boot over Ethernet using PXE | Supported (confirmed by Circle community) |
| **SPI Flash** | Fallback; contains bootloader itself | Always available as source of firmware |

> *"I managed to merge this into circle-stdlib... PS: btw, I'm booting over the network - easier workflow for me!"*  
> — pottendo, GitHub Circle Discussion #413

### BOOT_ORDER Configuration

The `BOOT_ORDER` setting in `bootconf.txt` (stored in SPI flash) determines the boot priority. Common values include:

- `0xf461` — SD → USB → Network (example)
- `0x1` — SD card only
- Full documentation is maintained by the Raspberry Pi community; official documentation is limited.

### Notes on Boot Mode Quirks

- **SD card must be present** for the firmware to consider the SD boot mode, even if booting from USB.
- **USB boot** requires the USB mass storage device to contain a valid FAT filesystem with `config.txt`, device tree blob, and kernel image.
- **Network boot** requires a DHCP server and TFTP server; the Pi 500 must have network boot enabled in the EEPROM configuration.

---

## 4. UART / Serial Console

The Raspberry Pi 500 has a dedicated UART connector that differs from previous models. There are important quirks for bare-metal and serial console access.

### Default Serial Console

- The default serial console on Pi 5/500 is on a **dedicated UART connector** (labeled on the board), not the GPIO pins.
- This serial device is **`ttyS11`** by default.
- *Source: GitHub Circle Discussion #413 (rsta2)*

### Using GPIO UART (ttyS1)

To use the standard UART on GPIO pins 14/15 (the legacy behavior used on Pi 0–4), add the following to your `config.txt`:

```ini
enable_uart=1
```

Or, for bare-metal development with Circle:

```ini
DEFINE += -DSERIAL_DEVICE_DEFAULT=0
```

> *"On the RPi 5 the serial console is by default the dedicated UART connector ('ttyS11'). If you want to use the UART at GPIO pins 14/15 ('ttyS1') you have to add the following option to Config.mk: DEFINE += -DSERIAL_DEVICE_DEFAULT=0"*  
> — rsta2, GitHub Circle Discussion #413

### Physical Connector Notes

- The dedicated UART connector is located near the GPIO header on the Pi 500 board.
- Some passive cooling solutions may obscure access to this connector.
- *Source: GitHub Circle Discussion #413 (pottendo)*

### Baud Rate and Settings

- Default baud rate: **115200**
- 8N1 (8 data bits, no parity, 1 stop bit)

---

## 5. Bare-Metal and OS Bring-Up Notes

### Development Considerations

The Pi 500 supports bare-metal development, but there are specific requirements and tooling considerations.

### Required Files for Bare-Metal Boot

As confirmed by community experimentation:

1. **`config.txt`** — with at minimum:
   ```ini
   kernel_address=0x80000
   kernel=mykernel.img
   os_check=0
   ```

2. **Device tree blob** — `bcm2712-rpi-5-b.dtb` (or a compatible variant) is required for Linux; for pure bare-metal with no device tree, this may be omitted but behavior varies.

3. **Kernel image** — Must be a 64-bit ARM (AArch64) ELF or raw binary. The default name is `kernel8.img`.

> *"kernel8.img is the default name, but you'll have to add os_check=0 to config.txt, as otherwise it assumes that you're booting Linux, so it will run your code from 0x200000 instead of 0x80000."*  
> — Fridux, Raspberry Pi Forums

### Toolchain Recommendations

- Use **GCC 12.2.Rel1** or later for AArch64 bare-metal development.
- *Source: GitHub Circle Discussion #413 (rsta2)*

### Circle OS Support

The Circle bare-metal library provides experimental support for Raspberry Pi 5 (and by extension, Pi 500). Key notes:

- Branch: `rpi5` — available in the Circle repository.
- Requires `kernel_address=0x80000` in `config.txt`.
- For headless operation (no HDMI), add:
  ```make
  DEFINE += -DSCREEN_HEADLESS
  ```
- *Source: GitHub Circle Discussion #413 (rsta2)*

### USB and Network in Bare-Metal

- USB and Ethernet support in bare-metal environments requires additional driver development.
- The Circle library has conditional compilation (`#if RASPPI <= 4`) that excludes Pi 5 support for some peripherals; community adoption is ongoing.
- *Source: GitHub Circle Discussion #413 (pottendo)*

---

## 6. Key Differences from Neighbouring Pi Generations

The BCM2712-based Pi 500 differs significantly from both the Pi 4 (BCM2711) and earlier models.

| Feature | Pi 0–3 (BCM2835/BCM2837) | Pi 4 (BCM2711) | Pi 5 / Pi 500 (BCM2712) |
|---------|--------------------------|----------------|-------------------------|
| Boot firmware location | SD card (`bootcode.bin`) | SD card / EEPROM | SPI flash EEPROM only |
| Boot ROM | On VPU | On VPU | On VPU (updated) |
| Memory initialization | By firmware from SD | By firmware from SD/EEPROM | By blob from SPI flash |
| `start.elf` / `fixup.dat` | Required | Required | **Not used** |
| `start4.elf` / `fixup4.dat` | N/A | Required | **Not used** |
| Boot modes | SD / USB / network | SD / USB / network / EEPROM | SD / USB / network |
| Default kernel | `kernel.img` (32-bit) | `kernel7l.img` (32-bit), `kernel8.img` (64-bit) | `kernel8.img` (64-bit only) |
| Serial console | UART on GPIO 14/15 (ttyS0) | UART on GPIO 14/15 (ttyS0) | Dedicated UART (ttyS11) by default |
| Device tree | Optional for Linux | Required for Linux | Required for Linux |

### Summary of Differences

1. **No bootcode.bin or start*.elf files** — Firmware is entirely in SPI flash; the SD card is only a data partition.
2. **New boot flow** — VPU → SPI blob → bootmain.elf → bootconf.txt → media.
3. **64-bit only** — No 32-bit boot path; all kernels must be AArch64.
4. **Changed serial console** — Default is now `ttyS11` on a dedicated connector, not the legacy GPIO UART.
5. **Network boot supported** — Confirmed working in the Circle community; PXE is functional.

---

## 7. Open Questions / Areas Without Official Documentation

The following areas lack comprehensive official documentation and are either inferred from community experimentation or remain undocumented:

### Boot ROM Details

- The exact capabilities and limitations of the VPU mask ROM are not publicly documented by Raspberry Pi Ltd.
- It is unclear whether the boot ROM supports fallback to USB device mode or other exotic boot modes.

### SPI Flash Boot Configuration

- The full format and options available in `bootconf.txt` stored in SPI flash are not officially documented.
- The procedure to modify SPI flash contents (beyond using `raspi-config` or official recovery tools) is not publicly documented.

### EEPROM Update Process

- The process for updating the SPI flash firmware (EEPROM) is not fully documented for end users, though Raspberry Pi provides a recovery image mechanism.
- The exact contents and version scheme of the SPI flash firmware are not publicly documented.

### Device Tree Blob Selection

- It is unclear how the firmware selects the correct device tree blob; the mechanism (e.g., board revision reading) is not officially documented.
- The exact naming convention for device tree blobs on Pi 500 (`bcm2712-rpi-500-b.dtb` vs. `bcm2712-rpi-5-b.dtb`) is not formally documented.

### Network Boot Detailed Requirements

- While network boot is confirmed functional, the exact DHCP/TFTP requirements and limitations are not fully documented.
- Whether network boot supports VLANs, IPv6, or secure boot is unknown.

### Bare-Metal Handoff Details

- The exact register state at kernel handoff (what registers contain what values, stack setup, MMU state) is not officially documented.
- Whether a device tree is required for bare-metal handoff is not clearly documented.

### USB Boot Mass Storage Support

- Which USB mass storage classes are supported is not officially documented.
- Boot from USB hubs is not clearly documented.

### Boot Performance and Timing

- No official documentation exists on boot timing, SPI flash read speeds, or boot stage durations.

---

## Appendix: Quick Reference for Bare-Metal Development

### Minimal SD Card Contents

```
├── config.txt
├── bcm2712-rpi-5-b.dtb   # (or bcm2712-rpi-500-b.dtb if available)
└── kernel8.img           # or custom name specified in config.txt
```

### Minimal config.txt

```ini
kernel_address=0x80000
kernel=kernel8.img
os_check=0
```

### UART Selection Summary

| Desired UART | Configuration |
|--------------|---------------|
| Default (ttyS11, dedicated connector) | No extra config needed |
| GPIO pins 14/15 (ttyS1) | Add `enable_uart=1` to config.txt (Linux) or `-DSERIAL_DEVICE_DEFAULT=0` (Circle) |

---

## References

1. Raspberry Pi Forums – "Pi5 Boot Process" (thread), July 2024. https://forums.raspberrypi.com/viewtopic.php?t=373222
2. satyria – bare-metal Pi 5 tutorial (German), 2024. https://satyria.de/arm/
3. GitHub – Circle bare-metal library, Discussion #413 ("Supporting Pi 5"), November 2023 – February 2024. https://github.com/rsta2/circle/discussions/413
4. Raspberry Pi Ltd. – Raspberry Pi 5 documentation (official). https://www.raspberrypi.com/documentation/computers/raspberry-pi-5.html

---

*This document is community-generated and may contain inferences or unverified details.
