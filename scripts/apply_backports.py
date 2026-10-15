#!/usr/bin/env python3
"""Накладывает бэкпорты из backports/<имя>/<имя>.patch по значениям experiments.

Запуск: apply_backports.py <корень ядра>   (EXPERIMENTS берётся из окружения)

  lzorle   lzo-rle для zram (Linux 5.1): lib/lzo из 5.4, crypto/lzo-rle.c, строка lzo-rle в zcomp.c
  tcppace  TCP internal pacing (Linux 4.13): BBR и SO_MAX_PACING_RATE работают без fq (адаптация под TSQ 4.9)
  utilest  util_est (Linux 4.17): schedutil учитывает загрузку задач по прошлым активациям, sysctl kernel.sched_util_est
  swapmax  vm.swappiness до 200 (идея Linux 5.8; формула 4.9 уже допускает)
  wsprot   защита файлового кэша в reclaim, sysctl vm.file_protect_kbytes (0 = выключено)
Значения swap<N> и wsprot<МБ> (swap150, wsprot200) здесь равны swapmax и wsprot; числа использует apply_tweaks.py.

Строго: патч обязан лечь без отклонений на файлы закреплённого коммита ядра. Уже наложенный патч
(обратное наложение проходит) пропускается. При смене kernel_ref патчи могут перестать ложиться: тогда сборка упадёт здесь, а не позже.
"""
import os
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
BACKPORTS = {
    "lzorle": "backports/lzorle/lzorle.patch",
    "tcppace": "backports/tcppace/tcppace.patch",
    "utilest": "backports/utilest/utilest.patch",
    "swapmax": "backports/swapmax/swapmax.patch",
    "wsprot": "backports/wsprot/wsprot.patch",
}


def die(msg):
    print(f"[ОШИБКА] {msg}", file=sys.stderr)
    sys.exit(1)


def run_patch(args, patch):
    with open(patch, "rb") as f:
        return subprocess.run(["patch", "-p1", "--no-backup-if-mismatch", *args], cwd=ROOT, stdin=f,
                              capture_output=True, text=True)


def main():
    toks = [t.strip().lower() for t in os.environ.get("EXPERIMENTS", "").replace(";", ",").replace(" ", ",").split(",")]
    # swap<N> и wsprot<МБ> несут число для apply_tweaks.py, патч у них общий
    toks = ["swapmax" if re.fullmatch(r"swap[=:_-]?[0-9]{1,3}", t) else "wsprot" if re.fullmatch(r"wsprot[=:_-]?[0-9]{1,4}", t) else t
            for t in toks]
    todo = [t for t in BACKPORTS if t in toks]
    if not todo:
        print("[backports] нечего накладывать")
        return
    if not (ROOT / "Makefile").exists() or not (ROOT / "net").is_dir():
        die(f"{ROOT}: не корень ядра")
    for name in todo:
        patch = REPO / BACKPORTS[name]
        if not patch.exists():
            die(f"нет файла {patch}")
        if run_patch(["--dry-run", "-R", "-s"], patch).returncode == 0:
            print(f"[backports] {name}: уже наложен")
            continue
        r = run_patch(["--dry-run", "-s"], patch)
        if r.returncode != 0:
            die(f"{name}: патч не ложится на это дерево (сменился kernel_ref?)\n{r.stdout}{r.stderr}")
        r = run_patch(["-s"], patch)
        if r.returncode != 0:
            die(f"{name}: ошибка наложения\n{r.stdout}{r.stderr}")
        files = [l.split(" b/", 1)[1] for l in patch.read_text(encoding="utf-8", errors="replace").splitlines()
                 if l.startswith("diff --git ")]
        print(f"[backports] {name}: наложен, файлов {len(files)}")


if __name__ == "__main__":
    main()
