# Бэкпорты: что сделано и что проверено и отброшено

Все бэкпорты включаются значением `experiments`, независимы друг от друга и сочетаются с остальными экспериментами и пресетами.
Для каждого есть свой каталог `backports/<имя>/` с патчем и README.

## Реализовано (значения `experiments`)

| Значение | Что | Источник | Статус |
|---|---|---|---|
| `lzorle` | lzo-rle для zram | Linux 5.1 / 5.4 | наложение, конфиг, компиляция, круговой тест x86 и aarch64 (qemu); на железе нет |
| `tcppace` | внутренний pacing TCP (BBR без fq) | Linux 4.13, коммит 218af599fa63 | наложение, конфиг, компиляция; на железе нет |
| `utilest` | util_est в путь выбора частоты schedutil, sysctl `kernel.sched_util_est` | Linux 4.17 | наложение, снятие, компиляция `fair/schedutil/core/sysctl`; на железе нет |
| `swapmax` / `swap<N>` | `vm.swappiness` до 200 | идея Linux 5.8 | наложение, компиляция; на железе нет |
| `wsprot` / `wsprot<МБ>` | защита файлового кэша в reclaim, `vm.file_protect_kbytes` | своё, по идее le9 | наложение, компиляция; на железе нет |
| `wbt` | blk-wbt (было раньше) | Linux 4.10 | как в предыдущих версиях |
| `lz4`, `zstd`, `iowait` | были раньше | 4.19, 6.16, 4.13 | как в предыдущих версиях |

Дополнительно проверена совместимость всего набора разом: `lab` (все бэкпорты и эксперименты вместе) накладывается на реальное дерево, `.config` проходит `check_config.py`
(все 35 строк на месте), компилируются целиком `block/`, `lib/lzo|lz4|zstd`, `crypto/`, `fs/f2fs`, `fs/pstore`, `net/ipv4|ipv6|sched`, `drivers/block/zram`, все 15 DTB.
Не собирались: полный `Image.gz-dtb` и запуск на устройстве.

## Проверено и отброшено (почему)

| Кандидат | Вывод |
|---|---|
| WireGuard (обновить до compat 1.0.20220627) | в дереве уже 1.0.20220627 и `CONFIG_WIREGUARD=y`; делать нечего |
| schedutil из 4.19 (занятые CPU, гонка в `sugov_start`, `next_freq`) | эти исправления уже в дереве (`sugov_cpu_is_busy`, двухпроходная инициализация в `sugov_start`, проверка `next_freq != UINT_MAX`); остальное завязано на WALT/CAF-правки этого файла и без них не переносится. Моя прошлая рекомендация была неверной |
| исправления BBR из 4.14 / 4.19 | `tcp_bbr.c` в дереве уже на уровне 4.9.y stable (есть `has_seen_rtt`, `full_bw_reached`); не хватало только pacing, он сделан (`tcppace`) |
| F2FS из 4.19 / ACK | в дереве F2FS уровня 4.14 (политики discard `DPOLICY_*`, `iostat`, `gc_urgent`); следующее обновление тянет fscrypt и VFS, вслепую его делать нельзя |
| BFQ | в дереве нет; mainline-BFQ работает только на blk-mq, а MMC здесь на старой очереди; BFQ-SQ для 4.9 из источника, которому можно доверять, достать не удалось (в проверенном репозитории bfq-mq ветки под blk-mq для 4.14 и новее), поэтому не включён |
| улучшения wbt (`REQ_IDLE`, blk-mq) | требуют переделки флагов запросов блочного слоя; без измерений выигрыш неясен |

### Проверено по исходникам в -14 (закреплённый коммит 124dcdc) и отброшено

| Идея | Вывод |
|---|---|
| `-mcpu=cortex-a53 -mtune=cortex-a53` в флаги | уже есть в `arch/arm64/Makefile`; `-O3` ставится глобально (`Makefile`: `KBUILD_CFLAGS += -O3`), `CC_OPTIMIZE_FOR_PERFORMANCE=y` |
| чистка отладки в `.config` (RTB, IPC_LOGGING, SCHED_DEBUG, FTRACE и т.д.) | в defconfig `DEBUG_KERNEL` и почти вся отладка уже выключены; делать нечего. Обратная сторона: из-за этого нет настраиваемых `sched_latency_ns` и др. (см. `schedtun`) |
| `PROCESS_RECLAIM` из CAF | уже `=y` (`/proc/PID/reclaim`), как и `BALANCE_ANON_FILE_RECLAIM`; в встроенном LMK есть adaptive-режим (`enable_adaptive_lmk`, по умолчанию 0) |
| мелкая блокировка binder из android-4.14 | уже есть (`binder_inner_proc_lock` используется в `drivers/android/binder.c`) |
| настройка `hispeed_freq` / `hispeed_load` у schedutil | без `SCHED_WALT` эти поля есть, но ветка с ними не работает: толку нет |
| `rcu_nocbs=0-7` из LOLZ как «лишнее» | в defconfig уже `RCU_NOCB_CPU_ALL=y`, параметр дублирует конфиг |
| отсутствие термозащиты в ядре | есть: зона `hexa-cpu-max-step` (step_wise, trip 85 °C, cpu cooling на ядра 0-7), зона GPU (95 °C) и по-ядерные зоны `apc1-cpuN-step` (105 °C); остальные зоны TSENS идут в userspace с порогом 125 °C |
| BFQ / MGLRU / WALT / EAS / ZSWAP / HZ 1000 / новый clang | не стоят цены: MMC без blk-mq, переносы на 4.9 огромные, на симметричных A53 выигрыш сомнителен |

## Не бэкпорты, но по-прежнему в списке
`SECCOMP`, `STACKPROTECTOR_STRONG`, `HARDENED_USERCOPY`: в `kuro439_defconfig` стоят `# CONFIG_SECCOMP is not set` и `# CONFIG_CC_STACKPROTECTOR is not set`.
Это настройка безопасности, а не бэкпорт; включение SECCOMP потребует убрать патч `patch_resukisu_seccomp`. Если нужно, оформляется отдельным значением `harden`.
