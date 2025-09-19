import subprocess
import shutil
import time
import threading
from datetime import datetime
import psutil  # precisa instalar: pip install psutil

class BaseModule:
    """Interface para módulos de status"""
    def get(self):
        return ""

class ClockModule(BaseModule):
    def get(self):
        return " " + datetime.now().strftime("%H:%M")

class CpuModule(BaseModule):
    def get(self):
        return f" {psutil.cpu_percent()}%"

class MemModule(BaseModule):
    def get(self):
        mem = psutil.virtual_memory()
        return f" {mem.percent}%"

class BatteryModule(BaseModule):
    def get(self):
        batt = psutil.sensors_battery()
        if not batt:
            return " AC"
        icon = "" if batt.percent > 80 else "" if batt.percent > 30 else ""
        return f"{icon} {batt.percent}%"

class WorkspacesModule(BaseModule):
    def __init__(self, wm):
        self.wm = wm
    def get(self):
        ws_manager = getattr(self.wm, "workspaces_manager", None)
        if not ws_manager:
            return "WS:?"
        current = ws_manager.current_index + 1
        return f" {current}"

class LayoutModule(BaseModule):
    def __init__(self, wm):
        self.wm = wm
    def get(self):
        layout = "?"
        if hasattr(self.wm.layout_manager, "current_name"):
            layout = self.wm.layout_manager.current_name()
        return f" {layout}"

class FocusModule(BaseModule):
    def __init__(self, wm):
        self.wm = wm
    def get(self):
        focus = getattr(self.wm, "focus", None)
        try:
            title = focus.get_wm_name() if focus else None
        except Exception:
            title = None
        return f" {title or 'none'}"


class Notifications:
    def __init__(self, wm, config=None):
        self.wm = wm
        self.config = config or {}

        self.has_lemonbar = shutil.which("lemonbar") is not None
        self.has_notify = shutil.which("notify-send") is not None

        # Configuração de módulos
        self.modules = []
        module_names = self.config.get("modules", ["workspaces", "layout", "focus", "clock"])
        for m in module_names:
            if m == "clock": self.modules.append(ClockModule())
            elif m == "cpu": self.modules.append(CpuModule())
            elif m == "mem": self.modules.append(MemModule())
            elif m == "battery": self.modules.append(BatteryModule())
            elif m == "workspaces": self.modules.append(WorkspacesModule(wm))
            elif m == "layout": self.modules.append(LayoutModule(wm))
            elif m == "focus": self.modules.append(FocusModule(wm))

        self.update_interval = self.config.get("update_interval", 1.0)
        self.last_update = 0
        self.running = False

    # --------------------------
    # Renderiza status
    # --------------------------
    def render_status(self):
        return " | ".join(m.get() for m in self.modules)

    def update_lemonbar(self):
        if not self.has_lemonbar:
            return

        now = time.time()
        if now - self.last_update < self.update_interval:
            return
        self.last_update = now

        msg = self.render_status()
        cmd = ["lemonbar", "-p", "-g", "1920x24+0+0", "-B", "#222", "-F", "#fff"]
        try:
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
            p.communicate(input=msg)
        except Exception as e:
            print(f"[Notifications] Erro lemonbar: {e}")

    # --------------------------
    # Notificações desktop
    # --------------------------
    def notify(self, message, urgency="low"):
        if self.has_notify:
            try:
                subprocess.Popen(["notify-send", "-u", urgency, "MyWM", message])
            except Exception as e:
                print(f"[Notifications] Erro notify-send: {e}")
        else:
            print(f"[{urgency.upper()}] {message}")

    # --------------------------
    # Loop de atualização
    # --------------------------
    def start(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self.running:
            self.update_lemonbar()
            time.sleep(self.update_interval)

    def stop(self):
        self.running = False

    def window_changed(self):
        """Chamada em eventos do WM"""
        self.last_update = 0
        self.update_lemonbar()
