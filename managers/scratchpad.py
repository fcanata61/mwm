# mywm1.0/managers/scratchpad.py
# Scratchpad avançado para MyWM
# Funcionalidades: múltiplos scratchpads, auto-respawn, stack, persistência, integração com notifications

import subprocess
import threading
import time
from Xlib import X

class ScratchpadWindow:
    def __init__(self, identifier, cmd, match=None, geometry=None, floating=True):
        self.identifier = identifier
        self.cmd = cmd
        self.match = match or {}  # {"wm_class": "Alacritty", "wm_name": "Notes"}
        self.geometry = geometry or {}
        self.floating = floating
        self.windows = []   # lista de X windows associados
        self.visible = False

    def is_dead(self, window):
        try:
            _ = window.get_geometry()
            return False
        except Exception:
            return True


class Scratchpad:
    def __init__(self, wm, config=None):
        self.wm = wm
        self.config = config or {}
        self.scratchpads = {}
        self.lock = threading.Lock()
        self._setup_from_config()

    # -------------------------
    # Setup a partir da config
    # -------------------------
    def _setup_from_config(self):
        spad_list = self.config.get("scratchpads", [])
        for sp in spad_list:
            identifier = sp.get("identifier")
            if not identifier:
                continue
            self.scratchpads[identifier] = ScratchpadWindow(
                identifier=identifier,
                cmd=sp.get("cmd"),
                match=sp.get("match"),
                geometry=sp.get("geometry"),
                floating=sp.get("floating", True),
            )

    # -------------------------
    # API pública
    # -------------------------
    def toggle(self, identifier):
        spw = self.scratchpads.get(identifier)
        if not spw:
            return
        with self.lock:
            if not spw.windows or all(spw.is_dead(w) for w in spw.windows):
                self._spawn(spw)
                return
            if spw.visible:
                self._hide(spw)
            else:
                self._show(spw)

    def toggle_all(self):
        for spw in self.scratchpads.values():
            self.toggle(spw.identifier)

    def cycle_next(self):
        """Cicla entre scratchpads ativos, escondendo os outros."""
        active = [s for s in self.scratchpads.values() if s.windows]
        if not active:
            return
        idx = next((i for i, s in enumerate(active) if s.visible), -1)
        for s in active:
            self._hide(s)
        nxt = active[(idx + 1) % len(active)]
        self._show(nxt)

    def check_new_window(self, window):
        """Chamar no MapRequest do WM para associar janelas ao scratchpad."""
        try:
            wm_class = window.get_wm_class() or []
        except Exception:
            wm_class = []
        try:
            wm_name = window.get_wm_name()
        except Exception:
            wm_name = None

        for spw in self.scratchpads.values():
            if spw.match.get("wm_class") and spw.match["wm_class"] in wm_class:
                self._register_window(spw, window)
                return True
            if spw.match.get("wm_name") and spw.match["wm_name"] == wm_name:
                self._register_window(spw, window)
                return True
        return False

    # -------------------------
    # Internos
    # -------------------------
    def _spawn(self, spw):
        try:
            if isinstance(spw.cmd, list):
                subprocess.Popen(spw.cmd)
            else:
                subprocess.Popen(spw.cmd.split())
        except Exception as e:
            print(f"[Scratchpad] Erro ao spawn {spw.identifier}: {e}")

    def _register_window(self, spw, window):
        spw.windows.append(window)
        spw.visible = True
        if spw.floating:
            self._apply_geometry(spw, window)
        self.wm.set_focus(window)
        # atualiza notifications se disponível
        if hasattr(self.wm, "notifications"):
            self.wm.notifications.force_update()

    def _apply_geometry(self, spw, window):
        try:
            mon = self.wm.monitors.get_current_geometry()
            gx = spw.geometry.get("x", mon["x"] + 100)
            gy = spw.geometry.get("y", mon["y"] + 100)
            gw = spw.geometry.get("width", mon["width"] // 2)
            gh = spw.geometry.get("height", mon["height"] // 2)
            bw = spw.geometry.get("border_width", 2)
            window.configure(x=gx, y=gy, width=gw, height=gh, border_width=bw, stack_mode=X.Above)
        except Exception:
            pass

    def _hide(self, spw):
        for w in list(spw.windows):
            try:
                w.unmap()
            except Exception:
                pass
        spw.visible = False
        if hasattr(self.wm, "notifications"):
            self.wm.notifications.force_update()

    def _show(self, spw):
        dead = [w for w in spw.windows if spw.is_dead(w)]
        for w in dead:
            spw.windows.remove(w)
        if not spw.windows:
            self._spawn(spw)
            return
        for w in spw.windows:
            try:
                w.map()
                self.wm.set_focus(w)
                self._apply_geometry(spw, w)
            except Exception:
                pass
        spw.visible = True
        if hasattr(self.wm, "notifications"):
            self.wm.notifications.force_update()
