# Arkadiusz Grzelka

Embedded engineer and founder of [Devitwise](https://devitwise.com), an engineering
partner for firmware, backend, mobile and AI work.

Most of my time goes into firmware on Zephyr RTOS and the nRF Connect SDK:
Bluetooth LE Audio and Auracast, audio codecs, MCUboot, and bringing up new
Microchip PIC32 parts in Zephyr. When I hit a bug or a missing driver, I fix it
upstream.

## Upstream work

**Merged**
- Zephyr: [Bluetooth BAP broadcast sink fix](https://github.com/zephyrproject-rtos/zephyr/pull/119637),
  [`fs_normalize_path`](https://github.com/zephyrproject-rtos/zephyr/pull/118111),
  [mcumgr UBSan fix](https://github.com/zephyrproject-rtos/zephyr/pull/120536),
  PIC32CZ CA clock and DMA fixes
- MCUboot: serial recovery [timeout](https://github.com/mcu-tools/mcuboot/pull/2842)
  and [inactivity exit](https://github.com/mcu-tools/mcuboot/pull/2830)
- Google Bumble: ISO and BIG sync error handling, SMP key distribution ordering
  ([#958](https://github.com/google/bumble/pull/958), [#959](https://github.com/google/bumble/pull/959), [#967](https://github.com/google/bumble/pull/967))
- Zephyr Microchip HAL: SERCOM USART and SPI fixes for PIC32C / SAM

**In review**
- Zephyr: [Cirrus Logic CS47L63 codec driver](https://github.com/zephyrproject-rtos/zephyr/pull/118752),
  [PIC32CZ CA USB device driver](https://github.com/zephyrproject-rtos/zephyr/pull/120162),
  PIC32CM SG/GC ADC, CAN and comparator drivers
- nRF Connect SDK: [nrf_audio timestamp-wrap drift fix](https://github.com/nrfconnect/sdk-nrf/pull/31659)
- Renode: [STM32H5 FDCAN support](https://github.com/renode/renode-infrastructure/pull/219)

All of it: [Zephyr](https://github.com/zephyrproject-rtos/zephyr/pulls?q=is%3Apr+author%3ATheArkadiuszGrzelka)
· [nRF Connect SDK](https://github.com/nrfconnect/sdk-nrf/pulls?q=is%3Apr+author%3ATheArkadiuszGrzelka)
· [MCUboot](https://github.com/mcu-tools/mcuboot/pulls?q=is%3Apr+author%3ATheArkadiuszGrzelka)

## Stack

**Languages:** C, C++, C3, Python, Bash  
**Embedded:** Zephyr RTOS, nRF Connect SDK, Yocto / embedded Linux, FPGA, Renode  
**Wireless:** Bluetooth Low Energy, LE Audio / Auracast, Wi-Fi, Thread, LTE-M, NFC  
**Security:** secure boot, MCUboot  
**DevOps:** Docker and containerization, CI pipelines  
**AI / ML:** machine learning, edge inference, LLM tooling

## Contact

[devitwise.com](https://devitwise.com) ·
[LinkedIn](https://www.linkedin.com/in/arkadiusz-grzelka-244402114)
