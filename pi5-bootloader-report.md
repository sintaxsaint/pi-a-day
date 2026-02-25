# Raspberry Pi 5 Bootloader & Boot Process

*Generated 2026-02-25*

## Sources

- [Pi5 Boot Process — Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=373222)
- [kernel_2712.img — DeepWiki](https://deepwiki.com/raspberrypi/firmware/2.1.5-raspberry-pi-5-kernel-(kernel_2712.img))
- [Supporting Pi 5 — Circle Discussion #413](https://github.com/rsta2/circle/discussions/413)
- [UART on Pi 5 GPIO 14/15 — Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=378931)

---

# Raspberry Pi 5 Bootloader & Boot Process: Community Documentation

> **Disclaimer**: This document is community-sourced documentation compiled from official Raspberry Pi forums, GitHub discussions, and wiki pages. Information marked as "community-sourced" reflects the experience of developers in the community and may not be officially documented by the Raspberry Pi Foundation. Readers should verify critical details against official Raspberry Pi documentation where possible.

---

## 1. Overview of the Raspberry Pi 5 Boot Sequence (Step-by-Step from Power-On to Kernel)

The Raspberry Pi 5 introduces a boot architecture that differs in several key respects from its predecessors. While the fundamental stages remain similar — power-on, ROM boot, bootloader execution, then OS loading — the specifics have changed substantially.

### 1.1 High-Level Boot Flow

Based on community-sourced information, the boot sequence proceeds as follows:

1. **Power-On / Reset**: The SoC begins execution from the internal ROM.
2. **ROM Bootloader (First Stage)**: The built-in ROM code performs initial hardware initialization. This stage is fixed and cannot be modified.
3. **Bootloader (EEPROM)**: The second-stage bootloader resides in the SPI-connected EEPROM. This is upgradeable via `rpi-eeprom`. This stage handles:
   - Loading the third-stage bootloader or directly loading `kernel_2712.img`
   - Reading `config.txt` and `boot.scr` (if present)
   - Selecting the boot device (SD card, USB, network)
4. **Boot Partition Files**: The bootloader reads configuration from:
   - `config.txt` — primary boot configuration
   - `boot.scr` — optional boot script (script.bin replacement)
   - `cmdline.txt` — kernel command line
5. **Kernel Loading**: The bootloader loads the kernel image into memory and transfers control.

### 1.2 Boot Devices

The Raspberry Pi 5 supports boot from:

- **microSD card** (primary for most users)
- **USB mass storage** (via bootloader selection)
- **Network boot** (PXE) — community testing indicates this works, though full support varies

> **Note**: The bootloader automatically attempts boot devices in a configurable order. The default order can be changed via `rpi-eeprom` configuration.

---

## 2. The Bootloader (EEPROM / rpi-eeprom) and Its Role

### 2.1 EEPROM Overview

The Raspberry Pi 5 uses a separate SPI-connected EEPROM chip to store the bootloader, separate from the SoC's internal ROM. This is a key difference from earlier models (especially Pi 3 and earlier) which used NOOBS or relied more heavily on the bootloader embedded in the GPU partition.

> **Source**: Community knowledge — the EEPROM is visible via `rpi-eeprom` utility.

### 2.2 rpi-eeprom Utility

The `rpi-eeprom` package provides tools to:

- **Update the bootloader firmware**: `sudo rpi-eeprom-update -a`
- **View current version**: `vcgencmd bootloader_version`
- **Configure boot order and options**: Edit `/etc/default/rpi-eeprom-update` and related configuration files

### 2.3 Configuration Files Read by Bootloader

| File | Purpose |
|------|---------|
| `config.txt` | Boot-time hardware configuration (device tree overlays, kernel address, firmware options) |
| `boot.scr` | Optional boot script processed by the bootloader |
| `cmdline.txt` | Kernel command-line arguments |
| `bootcode.bin` | Not used on Pi 5 — this file is for earlier Pi models |

### 2.4 Key config.txt Options for Pi 5

Based on community experience with bare-metal development:

- **`kernel_address=0x80000`** — **Critical** for bare-metal kernels. Without this, the Pi 5 bootloader may load the kernel image to the wrong memory address, causing boot failure. This is documented in the Circle bare-metal framework discussions. (Source: Circle Discussion #413)
- **`arm_64bit=1`** — Required for 64-bit ARM (AArch64) operation.
- **`device_tree_address`**, **`initramfs`** — Standard options, similar to Pi 4.

### 2.5 Bootloader Behavior Differences from Pi 4

Community members have noted that the Pi 5 bootloader is more restrictive about certain configuration options. In particular:

- The bootloader performs stricter validation of kernel images.
- Some `config.txt` options that worked on Pi 4 are ignored or behave differently on Pi 5.

> **Community-sourced**: These observations come from developers migrating bare-metal code from Pi 4 to Pi 5.

---

## 3. kernel_2712.img — What It Is, Why It Exists, How It Differs from kernel8.img

### 3.1 What is kernel_2712.img?

`kernel_2712.img` is the primary kernel image filename used by the Raspberry Pi 5 bootloader. The number **2712** refers to the **Broadcom BCM2712** SoC used in the Raspberry Pi 5.

This naming convention follows the pattern established for earlier Raspberry Pi models:

| Model | SoC | Default Kernel Filename |
|-------|-----|-------------------------|
| Pi 3 | BCM2837 | `kernel8.img` (64-bit) |
| Pi 4 | BCM2711 | `kernel8.img` (64-bit) |
| **Pi 5** | **BCM2712** | **`kernel_2712.img`** |

### 3.2 Why a New Filename?

The bootloader looks for a kernel image matching the SoC identifier. This allows the bootloader to distinguish between kernels for different hardware revisions and avoids accidentally loading a kernel compiled for the wrong SoC (which could cause hardware damage or undefined behavior).

### 3.3 How It Differs from kernel8.img

| Aspect | kernel8.img | kernel_2712.img |
|--------|-------------|------------------|
| **Target SoC** | BCM2837 (Pi 3), BCM2711 (Pi 4) | BCM2712 (Pi 5) |
| **Architecture** | ARMv8-A (AArch64) | ARMv8-A (AArch64) |
| **Device Tree** | `bcm2711.dtb` (Pi 4) | `bcm2712.dtb` |
| **Bootloader detection** | Default fallback if SoC-specific image not found | SoC-specific name for BCM2712 |
| **Loaded address** | Typically `0x80000` | Typically `0x80000` (but see `kernel_address` below) |

### 3.4 Using Alternative Kernel Names

The bootloader can be configured to load an alternative kernel filename via `config.txt`:

```
kernel=my_custom_kernel.img
```

However, the SoC-specific naming (`kernel_2712.img`) is the default and recommended approach.

> **Community note**: Some bare-metal developers on the Pi 5 have reported that the bootloader does not automatically fall back to `kernel8.img` if `kernel_2712.img` is missing. This differs from Pi 4 behavior where `kernel8.img` served as a universal 64-bit fallback.

---

## 4. UART / Serial Console on GPIO 14/15 — Configuration, Quirks, Differences from Pi 4

### 4.1 Critical Change: Default Serial Console Location

**The most significant change in the Raspberry Pi 5 boot process related to UART is that the default console is no longer on GPIO pins 14/15.**

According to community discussion (Circle Discussion #413):

- **Raspberry Pi 5**: Default serial console is on the **dedicated UART connector** (referred to as `ttyS11` in Linux). This is a separate 3-pin JST connector near the GPIO header, intended for the official Raspberry Pi debug cable.
- **GPIO pins 14/15** (the traditional UART pins): These are now accessed as `ttyS1` in Linux, not `ttyS0` as on earlier models.

> **Source**: Circle Discussion #413 — "On the RPi 5 the serial console is by default the dedicated UART connector ('ttyS11')."

### 4.2 Enabling UART on GPIO 14/15 (ttyS1)

For users who need to use the traditional GPIO 14/15 UART pins (common in breadboard setups, HATs, and debug configurations), additional configuration is required.

#### For Bare-Metal / Circle Framework

From the Circle bare-metal framework documentation:

```makefile
# In Config.mk
DEFINE += -DSERIAL_DEVICE_DEFAULT=0
```

This tells the firmware to use `ttyS1` (GPIO 14/15) instead of the default `ttyS11`.

#### For Linux / Raspberry Pi OS

In `config.txt`, add:

```
enable_uart=1
dtoverlay=disable-bt
```

However, note that the device node may now be `/dev/ttyS1` instead of `/dev/ttyS0`.

### 4.3 Screen Headless Mode

An important quirk discovered by the community:

> **Community-sourced**: On the Raspberry Pi 5 (and also Pi 4), if you want to run without an HDMI screen attached, you need to add the following to your `Config.mk` (for bare-metal frameworks like Circle):

```
DEFINE += -DSCREEN_HEADLESS
```

Otherwise, the `CScreenDevice` instance fails to initialize and the program does not run. This is because the Pi 5 firmware performs stricter HDMI presence detection than earlier models. (Source: Circle Discussion #413)

### 4.4 Summary of UART Changes

| Aspect | Pi 4 and Earlier | Pi 5 |
|--------|------------------|------|
| Default console | `/dev/ttyS0` (GPIO 14/15) | `/dev/ttyS11` (dedicated connector) |
| GPIO UART device | `/dev/ttyS0` | `/dev/ttyS1` |
| Configuration | `enable_uart=1` | `enable_uart=1` + disable BT overlay |
| Bare-metal default | UART on GPIO 14/15 | UART on dedicated debug connector |

---

## 5. Bare-Metal and OS Bring-Up Notes (Relevant for Circle, U-Boot, Custom Firmware)

This section compiles community experience with bare-metal development on the Raspberry Pi 5.

### 5.1 Circle Framework Support

The Circle bare-metal C++ framework has official support for Raspberry Pi 5 on the **`rpi5` branch**. Key points:

- **Documentation**: See `doc/rpi5.txt` in the Circle repository.
- **Kernel address**: Must set `kernel_address=0x80000` in `config.txt`. Without this, the kernel loads to the wrong address. (Source: Circle Discussion #413)
- **Serial configuration**: Use `DEFINE += -DSERIAL_DEVICE_DEFAULT=0` to enable GPIO 14/15 UART.
- **Screen headless**: Use `DEFINE += -DSCREEN_HEADLESS` when no HDMI display is attached.
- **Status**: As of early 2024, EMMC/SD card, timer, I2C, and basic serial work. Network and USB require further adoption of the codebase.

### 5.2 Observed #if RASPPI <= 4 Code

Community developers have noted that many existing bare-metal libraries and frameworks contain conditional compilation guards like:

```c
#if RASPPI <= 4
// Pi 4 and earlier only
#endif
```

These sections require modification to support the Raspberry Pi 5 (RASPPI = 5). This affects:

- USB stack initialization
- Ethernet/PHY drivers
- Clock and power management
- GPIO pin multiplexing

> **Community note**: Some functionality (particularly USB and Ethernet) requires updating drivers to work with the BCM2712's different peripheral configuration.

### 5.3 Network Boot

Network boot (PXE) is reported to work on the Raspberry Pi 5, though official documentation is limited. From the Circle discussion:

> "PS: btw, I'm booting over the network - easier workflow for me!" (Source: Circle Discussion #413)

This suggests that network boot is functional, but detailed configuration may vary from Pi 4.

### 5.4 Video / HDMI Support

A significant change in the Pi 5 affects bare-metal developers who rely on the firmware for video output:

> "The HDMI screen support in the RPi 5 firmware is not like the support for the earlier models. Many configuration options are missing. Raspberry Pi OS is generating the display output in the Linux kernel now, but Circle still relies on the firmware." (Source: Circle Discussion #413)

This means:

- The firmware no longer provides the same level of display configuration as on Pi 4.
- Some displays that worked on Pi 4 do not work on Pi 5 with bare-metal code.
- Linux-based OSes handle display in-kernel; bare-metal frameworks must work within firmware limitations.

---

## 6. Key Differences from Raspberry Pi 4 Boot Process

The following table summarizes the major differences between the Pi 4 and Pi 5 boot processes:

| Feature | Raspberry Pi 4 | Raspberry Pi 5 |
|---------|----------------|----------------|
| **SoC** | Broadcom BCM2711 | Broadcom BCM2712 |
| **Default kernel** | `kernel8.img` | `kernel_2712.img` |
| **Bootloader storage** | SPI EEPROM | SPI EEPROM |
| **Default serial console** | `/dev/ttyS0` (GPIO 14/15) | `/dev/ttyS11` (dedicated connector) |
| **GPIO UART device** | `/dev/ttyS0` | `/dev/ttyS1` |
| **kernel_address config** | Optional, rarely needed | **Required** for bare-metal (`0x80000`) |
| **Screen headless mode** | Not typically required | Required for headless operation |
| **Firmware video support** | Full configuration via `config.txt` | Reduced; display handled in kernel (Linux) |
| **Boot device priority** | SD → USB → Network (configurable) | Same, but EEPROM config changed |
| **ARM architecture** | ARMv8-A (Cortex-A72) | ARMv8-A (Cortex-A76*) |

> *The BCM2712 uses ARM Cortex-A76 cores, a newer microarchitecture than the Cortex-A72 used in Pi 4.

### 6.1 Memory Map Changes

The BCM2712 introduces changes to the peripheral base address and memory layout. Bare-metal developers must use the correct peripheral base address for the new SoC.

### 6.2 PCIe Support

The Raspberry Pi 5 introduces PCIe connectivity (via the RP1 southbridge). This affects boot in that PCIe devices (NVMe, etc.) can be used as boot devices, but this is handled by the bootloader and may require updated firmware.

---

## 7. Open Questions / Areas Without Official Documentation

The following areas lack comprehensive official documentation and remain community-sourced or partially understood:

### 7.1 Bootloader Configuration Details

- **Detailed EEPROM configuration options**: The full range of `rpi-eeprom` configuration parameters is not fully documented publicly.
- **Boot order precedence**: Exact boot priority and fallback behavior for different boot devices.

### 7.2 PCIe / RP1 Boot

- **PCIe boot support**: While PCIe boot is available, the exact requirements and limitations (e.g., which NVMe drives are supported) are not fully documented.
- **RP1 southbridge**: How the RP1 chip's role in I/O affects boot is not fully explained in public docs.

### 7.3 Firmware Video Limitations

- **HDMI firmware capabilities**: The community notes that "many configuration options are missing" but the exact list of supported/unsupported options is not enumerated.
- **Display detection behavior**: Why some displays work on Pi 4 but not Pi 5 with bare-metal code is not clearly documented.

### 7.4 UART Connector Pinout

- The location and pinout of the dedicated UART connector (ttyS11) is mentioned in official docs but detailed usage (voltage levels, TTL vs RS232) is not well-covered.

### 7.5 Network Boot Details

- **PXE/DHCP configuration**: Specific DHCP vendor class identifiers or boot filenames for Pi 5 network boot.
- **Network boot security**: Whether network boot can be disabled or protected (like TPM binding).

### 7.6 Bare-Metal Development

- **Correct peripheral base addresses**: Official documentation for BCM2712 memory-mapped I/O is limited.
- **USB/ethernet initialization**: Community developers report having to reverse-engineer or adapt code from Pi 4.
- **Clock and power management**: The PMU (Power Management Unit
