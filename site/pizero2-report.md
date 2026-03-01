# Raspberry Pi Zero 2 W (BCM2837B0) -- Bootloader & Boot Process

*Generated 2026-03-01*

## Sources

- [Pi 3 USB / Network Boot - Official Docs](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#pi-3-only-bootcode-bin-usb-boot)
- [raspberrypi/usbboot - GitHub (BCM2837 USB boot ROM)](https://github.com/raspberrypi/usbboot)
- [RPiconfig boot options - eLinux Wiki](https://elinux.org/RPiconfig)
- [BCM2837 64-bit boot thread - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=174648)

---

# Raspberry Pi Zero 2 W (BCM2837B0) — Bootloader & Boot Process: Community Documentation

**Version 1.0 | Community-Maintained Technical Report**

---

## 1. Overview of the BCM2837B0 Boot Sequence

The Raspberry Pi Zero 2 W uses the **BCM2837B0** SoC, which is a variant of the BCM2837 (originally introduced in the Raspberry Pi 3B). This processor contains a **boot ROM** embedded in the silicon — this is the first code that executes when power is applied, and it cannot be modified.

### Step-by-Step Boot Flow

1. **Power-On / Reset**
   - The VideoCore IV GPU core powers on first (this is a characteristic of all BCM283x-family SoCs)
   - The ARM CPU remains held in reset while the GPU executes its boot ROM

2. **ROM Boot Loader (Stage 1)**
   - The GPU boot ROM scans for a valid boot medium
   - Boot order is fixed in ROM: **SD card (first) → USB (second)**
   - The ROM looks for a FAT filesystem on the SD card (or USB mass storage device)
   - If no bootable device is found, the boot ROM enters USB device mode (waiting for `rpiboot`)

3. **Bootloader Firmware Loading (Stage 2)**
   - Once a FAT partition is found, the ROM loads `bootcode.bin` into L2 cache
   - `bootcode.bin` is the **secondary bootloader** — it initializes SDRAM and loads the main firmware
   - On the Zero 2 W, `bootcode.bin` is required on the SD card (unlike Pi 4 which has internal EEPROM)

4. **VideoCore Firmware (Stage 3)**
   - `start.elf` (or `start4.elf` for newer firmware) is loaded — this is the VideoCore firmware
   - This firmware reads `config.txt`, `cmdline.txt`, and any device tree overlays
   - The firmware also handles GPU-side initialization (clock speeds, memory split)

5. **Kernel Handoff**
   - For Linux: the ARM CPU is released from reset; the kernel (`kernel.img` or `kernel8.img` for 64-bit) is loaded to the specified memory address
   - The kernel command line from `cmdline.txt` is passed to the kernel
   - Device tree blobs (`.dtb`) or device tree overlays (`.dtbo`) are passed for hardware description

> **Note:** The Zero 2 W does **not** have a bootloader EEPROM (unlike the Pi 4, Pi 400, Compute Module 4/5). All firmware files must reside on the bootable SD card or USB drive.

---

## 2. Boot Firmware & Storage

### Firmware Files Required on Boot Media

For the Zero 2 W to boot, the following files must be present on a FAT-formatted partition (typically the first partition on the SD card):

| File | Purpose |
|------|---------|
| `bootcode.bin` | Secondary bootloader — initializes SDRAM, loads `start.elf` |
| `start.elf` | VideoCore firmware — boots the ARM CPU, reads `config.txt` |
| `config.txt` | Configuration file for GPU and boot settings |
| `cmdline.txt` | Kernel command line arguments |
| `kernel.img` | 32-bit ARM kernel (ARMv7) |
| `kernel8.img` | 64-bit ARM kernel (ARMv8, if using 64-bit OS) |
| `*.dtb` | Device tree blobs for board configuration |
| `*.dtbo` | Device tree overlays |

> **Source:** Raspberry Pi Documentation — *boot folder contents*

### EEPROM Status

The Zero 2 W does **not** have a bootloader EEPROM. This distinguishes it from the Raspberry Pi 4 series and Compute Module 4/5, which store the bootloader in SPI flash. All boot firmware must be provided externally via SD card or USB.

### Firmware Source

The official firmware is maintained in the Raspberry Pi GitHub repository:

- **Repository:** `raspberrypi/firmware` (boot folder)
- **URL:** https://github.com/raspberrypi/firmware/tree/master/boot

Community members typically copy these files from a Raspberry Pi OS image or the official firmware repository.

---

## 3. Boot Modes Supported

The BCM2837B0 supports multiple boot modes. The primary mode is determined by the contents of the boot media and the OTP (One-Time Programmable) memory configuration.

### 3.1 SD Card Boot (Default)

- **Primary boot device** — the ROM always attempts SD card boot first
- Requires a FAT-formatted partition with the firmware files listed above
- Supports both **SDIO** and **SPI-mode** SD card interfaces (the Zero 2 W uses the standard SD interface)

### 3.2 USB Boot

The Zero 2 W supports booting from **USB mass storage devices** (flash drives, hard drives, SSDs). This requires:

1. **USB boot mode must be enabled** — the OTP bit for USB boot must be set
2. On a new Zero 2 W, USB boot is **not enabled by default** — you must enable it via `program_usb_boot_mode=1` in `config.txt` and reboot once

> **Note:** The official documentation states that on Raspberry Pi 3-series devices, you must enable USB boot mode via the OTP. The Zero 2 W (which uses the same SoC family) likely inherits this behavior, though community testing confirms USB boot works on most units.

**Procedure to enable USB boot:**

```bash
# Add to config.txt on an SD card, boot once, then remove the line
program_usb_boot_mode=1
```

After enabling, the boot order becomes:

1. SD card (if bootable)
2. USB device (if no SD card boot)

### 3.3 USB Device Boot (rpiboot)

The Zero 2 W supports being booted via **USB device mode** using the `rpiboot` tool. This is the method used for flashing eMMC on Compute Modules, but it also works on the Zero 2 W.

- The device enumerates as a **USB mass storage device** (or in newer firmware, as a composite device with serial console)
- The host computer runs `rpiboot` which serves a boot image over USB
- This allows provisioning without an SD card

> **Source:** GitHub — *raspberrypi/usbboot* lists Zero 2 W as compatible with the **mass-storage-gadget** firmware, which runs a Linux initramfs enabling USB device boot

### 3.4 Network / PXE Boot

**Network boot is not natively supported** on the Zero 2 W in the same way it is on Pi 3B+ and Pi 4. The BCM2837B0 ROM does not include a built-in PXE client. However:

- Network boot can be achieved by booting via USB and then loading network drivers from the initramfs
- Some community projects have demonstrated network boot by using the USB gadget interface with DHCP/TFTP
- The official network boot documentation focuses on Pi 3B+ and newer — the Zero 2 W is not listed

> **Community Note:** Network boot on the Zero 2 W requires additional software and is not a plug-and-play feature.

### 3.5 Boot Mode Summary Table

| Boot Mode | Supported? | Notes |
|-----------|------------|-------|
| SD Card | ✅ Yes (default) | Requires FAT partition with firmware files |
| USB Mass Storage | ✅ Yes (with OTP enable) | Must set `program_usb_boot_mode=1` |
| USB Device (rpiboot) | ✅ Yes | Uses mass-storage-gadget firmware |
| Network / PXE | ⚠️ Limited | Requires custom initramfs; not native |
| GPIO Boot | ❌ No | Not available on Zero 2 W |
| NVMe Boot | ❌ No | No PCIe on Zero 2 W |

---

## 4. UART / Serial Console

The Zero 2 W provides access to the **primary UART** (UART0) on the 40-pin GPIO header. This is the default console for boot messages and Linux serial console.

### Pinout

| Pin | Function |
|-----|----------|
| GPIO 14 | UART0 TX (Alt 0) |
| GPIO 15 | UART0 RX (Alt 0) |
| Pin 6 | GND |

- **Voltage:** 3.3V (TTL level) — do not connect directly to RS-232 without a level shifter
- **Default baud rate:** 115200 baud, 8N1

### Enabling Serial Console

1. **In `cmdline.txt`:**
   ```
   console=serial0,115200 console=tty1 root=/dev/mmcblk0p2 rootfs=ext4 fsck.repair=yes rootwait
   ```

2. **In `config.txt`:**
   - No special configuration needed for default UART
   - To disable serial console: `enable_uart=0`

3. **Device name:** On Raspberry Pi OS, the primary UART is mapped to `serial0`, which typically points to `/dev/ttyS0` (or `/dev/ttyAMA0` on older images)

### Boot Messages via UART

The GPU firmware (`start.elf`) outputs boot debug messages to the UART **before** the ARM kernel starts. This includes:

- Memory initialization messages
- Loading of firmware files
- Device tree information

If no output is seen on the UART, common causes include:

- Incorrect baud rate
- Missing ground connection
- `enable_uart=0` set in `config.txt`
- USB-to-TTL adapter issues (particularly with cheap clones)

### quirks and Community Observations

- **No mini-UART vs PL011:** The Zero 2 W uses the **PL011** UART (not the mini-UART found on Zero and Zero W). This is important because the mini-UART has a divided clock that makes baud rate generation less accurate. The PL011 on Zero 2 W is more reliable for high-speed serial communication.

- **Serial console on USB:** When using the `mass-storage-gadget` USB boot mode (via `rpiboot`), the device also creates a **USB CDC-ACM serial interface**. This provides a second serial console over USB in addition to the hardware UART. Both are available in the Linux initramfs environment.

> **Source:** GitHub — *raspberrypi/usbboot* — "Because it runs Linux, it also provides a console login via both the hardware UART and the USB CDC-UART interfaces."

---

## 5. Bare-Metal and OS Bring-Up Notes

### 5.1 Bare-Metal Development

For bare-metal programming on the Zero 2 W (BCM2837B0), developers interact with:

- **VideoCore mailbox interface** — for communication between ARM and GPU
- **ARM local peripherals** — timer, interrupt controller
- **GPU memory** — firmware loads at address `0x00000000` (ARM's view of GPU memory)
- **SDRAM** — initialized by `bootcode.bin` and `start.elf`

Popular bare-metal frameworks and tutorials:

- **Circle** — C++ bare-metal framework supporting Raspberry Pi 1 through 3 (including BCM2837)
  - https://github.com/rsta2/circle
- **bcm2837** — community bare-metal examples for the Raspberry Pi 3 series (BCM2837)
- **Raspberry Pi bare metal forum** — active community discussions

> **Community Note:** While Circle supports the Pi 3 family, specific Zero 2 W (BCM2837B0) compatibility should be verified. The B0 variant is a die shrink of the original BCM2837 with improved power management, but the peripheral map is largely identical.

### 5.2 U-Boot

U-Boot can be used as a first-stage bootloader on the Zero 2 W. This is useful for:

- Network boot via TFTP
- Loading kernels from ext4 filesystems
- More flexible boot scripts

To use U-Boot:

1. Compile U-Boot for `rpi_3` or `bcm2837` (the Zero 2 W uses the same device tree as Pi 3)
2. Rename to `boot.scr.uimg` or load via `bootcmd`
3. Place on SD card alongside firmware files

> **Community Note:** Official U-Boot support for BCM2837 is included in mainline U-Boot. The Zero 2 W should work with the `rpi_3_defconfig`, but this is community-verified, not officially documented.

### 5.3 64-bit OS Support

The BCM2837B0 is a **64-bit capable** ARMv8 processor (Cortex-A53). The Zero 2 W can boot:

- **32-bit kernels** — `kernel.img` (ARMv7)
- **64-bit kernels** — `kernel8.img` (ARMv8, ARM64)

To boot a 64-bit OS (e.g., 64-bit Raspberry Pi OS):

- Ensure `kernel8.img` is present on the boot partition
- The firmware automatically detects and loads the 64-bit kernel if present

> **Community Note:** Raspberry Pi OS 64-bit is officially supported on Zero 2 W. Some community reports indicate that 64-bit images may have slightly different boot behavior, but firmware files are identical.

### 5.4 Boot Speed and Optimization

- **SD card class:** Use Class 10 or UHS-I cards for optimal boot times
- **USB boot:** USB 2.0 is the limiting factor; USB 3.0 devices work but are limited to USB 2.0 speeds
- **Boot delay:** The `boot_delay` option in `config.txt` adds a wait period before loading the kernel (useful for recovery)

---

## 6. Key Differences from Neighbouring Pi Generations

The Zero 2 W sits in the product line between the original Zero/W and the Raspberry Pi 4 series. Below are the most relevant distinctions:

| Feature | Pi Zero / Zero W (BCM2835) | **Zero 2 W (BCM2837B0)** | Pi 3B (BCM2837) | Pi 4 (BCM2711) |
|---------|---------------------------|--------------------------|-----------------|----------------|
| **Architecture** | ARMv6 (ARM11) | ARMv8 (Cortex-A53) | ARMv8 (Cortex-A53) | ARMv8 (Cortex-A72) |
| **CPU Cores** | 1 | 4 | 4 | 4 (Pi 4B) |
| **Clock Speed** | 1 GHz | 1 GHz | 1.2 GHz | 1.5 GHz (Pi 4) |
| **Boot EEPROM** | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **Boot Firmware Location** | SD card / USB | SD card / USB | SD card / USB | EEPROM + SD card |
| **Default Boot Device** | SD card | SD card | SD card | EEPROM |
| **USB Boot** | ⚠️ Limited (requires special firmware) | ✅ Yes (with OTP) | ✅ Yes | ✅ Yes |
| **Network Boot** | ❌ No | ⚠️ Limited | ✅ Yes (Pi 3B+) | ✅ Yes |
| **PCIe** | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **GPIO Boot Mode** | ❌ No | ❌ No | ❌ No | ✅ Yes (Pi 4) |
| **Mini-UART** | Yes | No (PL011) | No (PL011) | No (PL011) |
| **RAM** | 512 MB | 512 MB LPDDR2 | 1 GB LPDDR2 | 1–8 GB LPDDR4 |
| **Official 64-bit OS** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |

### Key Takeaways for Zero 2 W

1. **Like Pi 3:** Uses the same ARM architecture (BCM2837 family) and supports 64-bit; shares the PL011 UART
2. **Like original Zero:** Lacks EEPROM, requires SD card or USB for firmware; compact form factor
3. **Unlike Pi 4:** Does not support network boot natively, no GPIO boot mode, no PCIe

---

## 7. Open Questions / Areas Without Official Documentation

The following areas lack official Raspberry Pi documentation or have conflicting/incomplete community information:

### 7.1 USB Boot OTP Status

**Question:** Is the USB boot mode OTP bit pre-programmed on the Zero 2 W, or must users explicitly enable it?

- The Pi 3 series requires explicit OTP programming via `program_usb_boot_mode=1`
- Community reports suggest most Zero 2 W units boot USB devices without this step, but this is not officially confirmed
- **Community behavior:** Most Zero 2 W units appear to boot USB devices out of the box, but
