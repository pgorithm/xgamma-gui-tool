"""Display environment probes (VM, HDR) shared by init worker and UI layer.

Single source for PRD 3.1 / 3.8 warnings; avoid duplicating logic in gui stubs.
"""

import subprocess

from .command_resolution import resolve_command

VM_WARNING = 'VM environment may limit gamma adjustment.'
HDR_WARNING = 'HDR or 10-bit mode may disable manual gamma adjustment.'


def _read_system_hint(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.readline().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return ''


class EnvironmentProbe:
    """Cached checks for virtualization and HDR-style pipelines (Linux/X11)."""

    def __init__(self):
        self._is_vm_cached = None
        self._is_hdr_cached = None

    def is_virtual_machine(self):
        if self._is_vm_cached is not None:
            return self._is_vm_cached

        keywords = ['virtualbox', 'vmware', 'kvm', 'qemu', 'hyper-v', 'parallels']
        hints = [
            _read_system_hint('/sys/class/dmi/id/product_name'),
            _read_system_hint('/sys/class/dmi/id/sys_vendor'),
        ]
        for hint in hints:
            lowered = hint.lower()
            if lowered and any(word in lowered for word in keywords):
                self._is_vm_cached = True
                return True
        virt = resolve_command('systemd-detect-virt')
        if not virt:
            self._is_vm_cached = False
            return False
        try:
            result = subprocess.run(
                [virt],
                capture_output=True,
                text=True,
                timeout=2,
            )
            vm_result = result.returncode == 0 and result.stdout.strip() not in ('none', '')
            self._is_vm_cached = vm_result
            return vm_result
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            self._is_vm_cached = False
            return False

    def is_hdr_pipeline_active(self):
        if self._is_hdr_cached is not None:
            return self._is_hdr_cached

        xrandr_path = resolve_command('xrandr')
        if not xrandr_path:
            self._is_hdr_cached = False
            return False
        try:
            result = subprocess.run(
                [xrandr_path, '--verbose'],
                capture_output=True,
                text=True,
                timeout=3,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            self._is_hdr_cached = False
            return False
        text = result.stdout.lower()
        hdr_tokens = ['hdr', '10 bpc', '10-bit', 'deep color']
        hdr_result = any(token in text for token in hdr_tokens)
        self._is_hdr_cached = hdr_result
        return hdr_result

    def collect_warnings(self):
        messages = []
        if self.is_virtual_machine():
            messages.append(VM_WARNING)
        if self.is_hdr_pipeline_active():
            messages.append(HDR_WARNING)
        return messages


def collect_environment_warnings():
    """Run a fresh probe and return user-facing warning strings (init worker, tests)."""
    return EnvironmentProbe().collect_warnings()
