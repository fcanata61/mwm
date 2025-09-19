# mywm1.0/managers/notifications.py
# Sistema de status / notificações para MyWM
#
# Funcionalidades:
# - Módulos plugáveis (clock, cpu, mem, battery, workspaces, layout, focus, volume)
# - Barra persistente via lemonbar (escreve por stdin)
# - IPC JSON via UNIX socket (/tmp/mywm-status.sock)
# - Socket para eventos de clique (/tmp/mywm-click.sock) -> handle_click
# - Threaded, eficiente e com fallback se dependências faltarem

import os
import shutil
import subprocess
import threading
import time
import socket
import json
from datetime import datetime

# opcional
try:
    import psutil
except Exception:
    psutil = None

# -----------------------
# Config defaults
# -----------------------
DEFAULT_LEMON_CMD = ["lemonbar", "-p", "-g", "1920x24+0+0", "-B", "#222", "-F", "#fff"]
STATUS_SOCKET_PATH = "/tmp/mywm-status.sock"
CLICK_SOCKET_PATH = "/tmp/mywm-click.sock"

# -----------------------
# Módulos de Status
# -----------------------
class BaseModule:
    def __init__(self, wm=None, cfg=None):
        self.wm = wm
        self.cfg = cfg or {}
    def get(self):
        return ""

class ClockModule(BaseModule):
    ICON = ""
    def get(self):
        return f"{self.ICON} {datetime.now().strftime('%H:%M:%S')}"

class CpuModule(BaseModule):
    ICON = ""
    def get(self):
        if psutil:
            try:
                return f"{self.ICON} {psutil.cpu_percent(interval=None)}%"
            except Exception:
                return f"{self.ICON} ?%"
        return f"{self.ICON} n/a"

class MemModule(BaseModule):
    ICON = ""
    def get(self):
        if psutil:
            try:
                m = psutil.virtual_memory()
                return f"{self.ICON} {m.percent}%"
            except Exception:
                return f"{self.ICON} ?%"
        return f"{self.ICON} n/a"

class BatteryModule(BaseModule):
    ICON_AC = ""
    ICON_FULL = ""
    ICON_HIGH = ""
    ICON_LOW = ""
    ICON_CRIT = ""
    def get(self):
        if psutil and hasattr(psutil, "sensors_battery"):
            try:
                b = psutil.sensors_battery()
                if not b:
                    return f"{self.ICON_AC} AC"
                pct = int(b.percent)
                if pct > 80:
                    icon = self.ICON_FULL
                elif pct > 50:
                    icon = self.ICON_HIGH
                elif pct > 20:
                    icon = self.ICON_LOW
                else:
                    icon = self.ICON_CRIT
                return f"{icon} {pct}%"
            except Exception:
                return f"{self.ICON_FULL} ?%"
        return " n/a"

class WorkspacesModule(BaseModule):
    ICON = ""
    def get(self):
        ws_man = getattr(self.wm, "workspaces_manager", None)
        if not ws_man:
            return f"{self.ICON} ?"
        idx = getattr(ws_man, "current_index", 0) + 1
        total = getattr(ws_man, "count", lambda: None)
        try:
            t = total() if callable(total) else total or "?"
        except Exception:
            t = "?"
        return f"{self.ICON} {idx}/{t}"

class LayoutModule(BaseModule):
    ICON = ""
    def get(self):
        lm = getattr(self.wm, "layout_manager", None)
        if not lm:
            return f"{self.ICON} ?"
        try:
            name = lm.current_name()
        except Exception:
            try:
                name = getattr(lm, "current", "unknown")
            except Exception:
                name = "?"
        return f"{self.ICON} {name}"

class FocusModule(BaseModule):
    ICON = ""
    def get(self):
        focused = getattr(self.wm, "focus", None)
        if not focused:
            return f"{self.ICON} none"
        try:
            title = focused.get_wm_name() or "no-title"
        except Exception:
            title = "no-title"
        # truncate
        if len(title) > 30:
            title = title[:27] + "..."
        return f"{self.ICON} {title}"

class VolumeModule(BaseModule):
    ICON = ""
    # tenta amixer
    def _get_amixer(self):
        if shutil.which("amixer") is None:
            return None
        try:
            out = subprocess.check_output(["amixer", "get", "Master"], text=True, stderr=subprocess.DEVNULL)
            # procura por '[xx%]'
            import re
            m = re.search(r"\[(\d{1,3})%\].*\[(on|off)\]", out)
            if m:
                pct = int(m.group(1))
                on = m.group(2) == "on"
                return pct, on
        except Exception:
            pass
        return None
    def get(self):
        v = self._get_amixer()
        if v is None:
            return f"{self.ICON} n/a"
        pct, on = v
        mutestr = "off" if not on else f"{pct}%"
        return f"{self.ICON} {mutestr}"

# -----------------------
# Notifications Manager
# -----------------------
class Notifications:
    def __init__(self, wm, config=None):
        """
        wm: referência para o window manager (para pegar workspaces, layout, focus, etc.)
        config: dict com chaves:
          - modules: lista de nomes de módulos na ordem desejada
          - lemon_cmd: comando (lista) para lemonbar (opcional)
          - update_interval: float segundos
          - status_socket: caminho do socket unix para status JSON
          - click_socket: caminho do socket unix para clicks
        """
        self.wm = wm
        self.cfg = config or {}
        self.lemon_cmd = self.cfg.get("lemon_cmd", DEFAULT_LEMON_CMD)
        self.update_interval = float(self.cfg.get("update_interval", 1.0))
        self.status_socket = self.cfg.get("status_socket", STATUS_SOCKET_PATH)
        self.click_socket = self.cfg.get("click_socket", CLICK_SOCKET_PATH)
        self.modules = []
        self._build_modules(self.cfg.get("modules", ["workspaces","layout","focus","clock","cpu","mem","battery","volume"]))
        self.running = False
        self._lemon_proc = None
        self._lock = threading.Lock()
        # cache de info (JSON)
        self._last_info = {}
        # threads
        self._t_update = None
        self._t_status_server = None
        self._t_click_server = None

    # -----------------------
    # helper: construir módulos
    # -----------------------
    def _build_modules(self, module_names):
        self.modules = []
        for name in module_names:
            n = name.strip().lower()
            if n == "clock":
                self.modules.append(ClockModule(self.wm, self.cfg))
            elif n == "cpu":
                self.modules.append(CpuModule(self.wm, self.cfg))
            elif n == "mem":
                self.modules.append(MemModule(self.wm, self.cfg))
            elif n == "battery":
                self.modules.append(BatteryModule(self.wm, self.cfg))
            elif n == "workspaces":
                self.modules.append(WorkspacesModule(self.wm, self.cfg))
            elif n == "layout":
                self.modules.append(LayoutModule(self.wm, self.cfg))
            elif n == "focus":
                self.modules.append(FocusModule(self.wm, self.cfg))
            elif n == "volume":
                self.modules.append(VolumeModule(self.wm, self.cfg))
            else:
                # permite módulos customizados registrados dinamicamente se precisar
                pass

    # -----------------------
    # Start / Stop
    # -----------------------
    def start(self):
        if self.running:
            return
        self.running = True
        # limpa sockets antigos se existirem
        for path in (self.status_socket, self.click_socket):
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception:
                pass

        # start lemonbar (se disponível)
        if shutil.which(self.lemon_cmd[0]) is not None:
            self._start_lemonbar_process()
        else:
            print("[Notifications] lemonbar não encontrado; status não será exibido.")

        # threads
        self._t_update = threading.Thread(target=self._loop_update, daemon=True)
        self._t_update.start()

        self._t_status_server = threading.Thread(target=self._status_server_loop, daemon=True)
        self._t_status_server.start()

        self._t_click_server = threading.Thread(target=self._click_server_loop, daemon=True)
        self._t_click_server.start()

    def stop(self):
        self.running = False
        # fechar lemonbar
        try:
            if self._lemon_proc:
                try:
                    self._lemon_proc.stdin.close()
                except Exception:
                    pass
                try:
                    self._lemon_proc.terminate()
                except Exception:
                    pass
                self._lemon_proc = None
        except Exception:
            pass
        # remover sockets
        for path in (self.status_socket, self.click_socket):
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception:
                pass

    # -----------------------
    # lemonbar persistence
    # -----------------------
    def _start_lemonbar_process(self):
        try:
            # mantenha stdin aberto para escrever updates
            self._lemon_proc = subprocess.Popen(self.lemon_cmd, stdin=subprocess.PIPE, text=True)
            print(f"[Notifications] lemonbar iniciado: {' '.join(self.lemon_cmd)}")
        except Exception as e:
            print(f"[Notifications] falha ao iniciar lemonbar: {e}")
            self._lemon_proc = None

    def _write_lemonbar(self, text):
        # escreve uma linha no lemonbar (substitui a barra)
        if not self._lemon_proc:
            # tenta reiniciar
            if shutil.which(self.lemon_cmd[0]) is not None:
                self._start_lemonbar_process()
            else:
                return
        try:
            # garantir thread-safety
            with self._lock:
                # escrevemos linha e flush
                self._lemon_proc.stdin.write(text + "\n")
                self._lemon_proc.stdin.flush()
        except Exception:
            # se deu erro, tenta reiniciar uma vez
            try:
                self._lemon_proc = None
                if shutil.which(self.lemon_cmd[0]) is not None:
                    self._start_lemonbar_process()
            except Exception:
                pass

    # -----------------------
    # Loop de atualização
    # -----------------------
    def _loop_update(self):
        while self.running:
            try:
                self.force_update()
            except Exception:
                pass
            time.sleep(self.update_interval)

    def force_update(self):
        """Força coleta de todos os módulos e atualização (barra + cache JSON)."""
        parts = []
        data = {}
        for m in self.modules:
            try:
                s = m.get()
            except Exception:
                s = ""
            parts.append(s)
            # usar o nome da classe como chave no JSON
            key = type(m).__name__.replace("Module", "").lower()
            data[key] = s
        text = " | ".join(p for p in parts if p)
        data["raw"] = text
        data["timestamp"] = time.time()

        # salva cache
        with self._lock:
            self._last_info = data

        # escreve na lemonbar (se disponível)
        self._write_lemonbar(text)

    # -----------------------
    # Accessor JSON (IPC)
    # -----------------------
    def _status_server_loop(self):
        # socket UNIX que, ao conectar, envia JSON com status atual e fecha
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(self.status_socket)
            sock.listen(1)
            os.chmod(self.status_socket, 0o666)
        except Exception as e:
            print(f"[Notifications] Não foi possível bindar socket status: {e}")
            return
        while self.running:
            try:
                conn, _ = sock.accept()
                with conn:
                    with self._lock:
                        payload = json.dumps(self._last_info)
                    conn.sendall(payload.encode("utf-8"))
            except Exception:
                # loop
                time.sleep(0.1)
        try:
            sock.close()
        except Exception:
            pass

    # -----------------------
    # Click socket (recebe JSON com comando/ id )
    # -----------------------
    def _click_server_loop(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(self.click_socket)
            sock.listen(1)
            os.chmod(self.click_socket, 0o666)
        except Exception as e:
            print(f"[Notifications] Não foi possível bindar socket click: {e}")
            return
        while self.running:
            try:
                conn, _ = sock.accept()
                with conn:
                    data = conn.recv(4096)
                    if not data:
                        continue
                    try:
                        payload = json.loads(data.decode("utf-8"))
                    except Exception:
                        payload = {"raw": data.decode("utf-8", errors="ignore")}
                    # delega para handler
                    try:
                        self.handle_click(payload)
                    except Exception:
                        pass
            except Exception:
                time.sleep(0.1)
        try:
            sock.close()
        except Exception:
            pass

    # -----------------------
    # Handler de click — personalize aqui
    # payload é dicionário enviado pelo cliente
    # Ex.: { "id": "workspace_1" } ou { "action": "open_terminal" }
    # -----------------------
    def handle_click(self, payload):
        # exemplo padrão: se payload tiver "action", tenta executar
        if not payload:
            return
        if isinstance(payload, dict):
            # actions definidos: "change_workspace": n, "open": cmd
            if "change_workspace" in payload:
                n = payload.get("change_workspace")
                try:
                    # esperar que wm tenha método set_workspace(index)
                    if hasattr(self.wm, "set_workspace"):
                        self.wm.set_workspace(int(n) - 1)
                except Exception:
                    pass
                # forçar update
                self.force_update()
                return
            if "open" in payload:
                cmd = payload.get("open")
                if isinstance(cmd, list):
                    try:
                        subprocess.Popen(cmd)
                    except Exception:
                        pass
                elif isinstance(cmd, str):
                    try:
                        subprocess.Popen(cmd.split())
                    except Exception:
                        pass
                return
            if "action" in payload:
                act = payload["action"]
                # tratar ações conhecidas
                if act == "toggle_scratchpad" and hasattr(self.wm, "scratchpad"):
                    try:
                        self.wm.scratchpad.toggle_by_key()
                        self.force_update()
                    except Exception:
                        pass
                    return
        # fallback: log
        print(f"[Notifications] click payload: {payload}")

    # -----------------------
    # Métodos utilitários
    # -----------------------
    def notify(self, message, urgency="low"):
        if shutil.which("notify-send"):
            try:
                subprocess.Popen(["notify-send", "-u", urgency, "MyWM", message])
            except Exception:
                print(f"[Notifications] notify-send falhou: {message}")
        else:
            print(f"[{urgency}] {message}")

    def window_changed(self):
        """Chamar quando janela é criada/removida/foco mudou — força update imediato"""
        self.force_update()
