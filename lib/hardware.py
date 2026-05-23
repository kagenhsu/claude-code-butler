"""偵測電腦硬體規格，估算可同時執行的自動化任務數"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class HardwareSpec:
    os_name: str = ""
    os_version: str = ""
    cpu_name: str = ""
    cpu_cores: int = 0
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0
    ram_used_percent: float = 0.0
    gpu_name: str = ""
    gpu_cores: int = 0
    disk_total_gb: float = 0.0
    disk_free_gb: float = 0.0
    disk_used_percent: float = 0.0


@dataclass
class TaskCapacity:
    max_concurrent: int = 0
    ram_per_task_mb: int = 400
    bottleneck: str = ""
    recommendation: str = ""


def _run(cmd: list[str], timeout: int = 5) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def detect_hardware() -> HardwareSpec:
    spec = HardwareSpec()
    system = platform.system()
    spec.os_name = system
    spec.os_version = platform.platform()

    if system == "Darwin":
        spec.cpu_name = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        cores = _run(["sysctl", "-n", "hw.ncpu"])
        spec.cpu_cores = int(cores) if cores.isdigit() else 0

        mem = _run(["sysctl", "-n", "hw.memsize"])
        if mem.isdigit():
            spec.ram_total_gb = round(int(mem) / (1024 ** 3), 1)

        vm = _run(["vm_stat"])
        if vm:
            pages = {}
            for line in vm.split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    val = val.strip().rstrip(".")
                    if val.isdigit():
                        pages[key.strip()] = int(val)
            page_size = 16384
            free_pages = pages.get("Pages free", 0) + pages.get("Pages inactive", 0)
            spec.ram_available_gb = round(free_pages * page_size / (1024 ** 3), 1)

        if spec.ram_total_gb > 0 and spec.ram_available_gb > 0:
            used = spec.ram_total_gb - spec.ram_available_gb
            spec.ram_used_percent = round(used / spec.ram_total_gb * 100, 1)

        gpu = _run(["system_profiler", "SPDisplaysDataType"])
        for line in gpu.split("\n"):
            if "Chipset Model" in line:
                spec.gpu_name = line.split(":", 1)[1].strip()
            if "Total Number of Cores" in line:
                val = line.split(":", 1)[1].strip()
                if val.isdigit():
                    spec.gpu_cores = int(val)

        df = _run(["df", "-g", "/"])
        if df:
            parts = df.strip().split("\n")[-1].split()
            if len(parts) >= 4:
                spec.disk_total_gb = float(parts[1]) if parts[1].replace(".", "").isdigit() else 0
                spec.disk_free_gb = float(parts[3]) if parts[3].replace(".", "").isdigit() else 0
                if spec.disk_total_gb > 0:
                    spec.disk_used_percent = round((1 - spec.disk_free_gb / spec.disk_total_gb) * 100, 1)

    elif system == "Linux":
        cpu_info = _run(["lscpu"])
        for line in cpu_info.split("\n"):
            if "Model name" in line:
                spec.cpu_name = line.split(":", 1)[1].strip()
            if "CPU(s):" in line and "NUMA" not in line and "On-line" not in line:
                val = line.split(":", 1)[1].strip()
                if val.isdigit():
                    spec.cpu_cores = int(val)

        mem_info = _run(["free", "-b"])
        if mem_info:
            for line in mem_info.split("\n"):
                if line.startswith("Mem:"):
                    parts = line.split()
                    if len(parts) >= 7:
                        spec.ram_total_gb = round(int(parts[1]) / (1024 ** 3), 1)
                        spec.ram_available_gb = round(int(parts[6]) / (1024 ** 3), 1)
                        spec.ram_used_percent = round(int(parts[2]) / int(parts[1]) * 100, 1)

    elif system == "Windows":
        spec.cpu_name = platform.processor()
        spec.cpu_cores = os.cpu_count() or 0

    return spec


def estimate_task_capacity(spec: HardwareSpec) -> TaskCapacity:
    cap = TaskCapacity()

    if spec.ram_available_gb <= 0:
        cap.max_concurrent = 1
        cap.bottleneck = "無法偵測可用記憶體"
        cap.recommendation = "建議手動確認記憶體狀態"
        return cap

    ram_mb = spec.ram_available_gb * 1024
    by_ram = int(ram_mb / cap.ram_per_task_mb)

    by_cpu = max(1, spec.cpu_cores - 2)

    cap.max_concurrent = max(1, min(by_ram, by_cpu))

    if by_ram < by_cpu:
        cap.bottleneck = "記憶體"
        if spec.ram_used_percent > 80:
            cap.recommendation = f"記憶體使用率偏高（{spec.ram_used_percent}%），建議關閉不需要的應用程式"
        else:
            cap.recommendation = f"目前可用記憶體 {spec.ram_available_gb} GB，每個任務約需 {cap.ram_per_task_mb} MB"
    else:
        cap.bottleneck = "CPU 核心數"
        cap.recommendation = f"保留 2 個核心給系統，{spec.cpu_cores - 2} 個核心可分配給任務"

    return cap
