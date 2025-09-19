#!/usr/bin/env python3
# main.py - Inicialização completa do MyWM 1.0+

import os
import sys

config_path = os.path.expanduser("~/.config/mwm/config.py")
if os.path.exists(config_path):
    sys.path.insert(0, os.path.dirname(config_path))
    try:
        from config import config
    except Exception:
        config = {}
else:
    config = {}

from Xlib import X, display
from managers import (
    ewmh,
    layouts,
    scratchpad,
    multimonitor,
    decorations,
    workspaces,
    keybindings,
    notifications,
)

class MyWM:
    def __init__(self, config=None):
        self.config = config or {}
        self.dpy = display.Display()
        self.root = self.dpy.screen().root

        # Módulos
        self.layout_manager = layouts.LayoutManager()
        self.monitors = multimonitor.MultiMonitorWM(self.dpy).monitors
        self.scratchpad = scratchpad.Scratchpad(self)
        self.decorations = decorations.Decorations(self, self.config.get("decorations", {}))
        self.workspaces_manager = workspaces.WorkspacesManager(self, self.config.get("workspaces", {}))
        self.keybindings = keybindings.KeyBindings(self, self.config.get("keybindings", {}))
        self.notifications = notifications.Notifications(self, self.config.get("notifications", {}))

        self.windows = []  # Lista de todas as janelas
        self.focus = None
        self.screen_geom = self.root.get_geometry()

    # =======================
    # FOCUS
    # =======================
    def set_focus(self, win):
        self.focus = win
        try:
            ewmh.set_active_window(win)
        except Exception:
            pass
        if win:
            try:
                win.set_input_focus(X.RevertToParent, X.CurrentTime)
            except Exception:
                pass

    # =======================
    # ADICIONAR/REMOVER JANELA
    # =======================
    def add_window(self, win, monitor_index=0):
        self.windows.append(win)
        if monitor_index < len(self.monitors):
            self.monitors[monitor_index].windows.append(win)
        self.layout_manager.add_window(win)
        self.layout_manager.apply(self.windows, self.screen_geom)
        self.set_focus(win)
        if hasattr(self, "notifications"):
            self.notifications.window_changed()

    def remove_focused(self):
        if self.focus:
            win = self.focus
            if win in self.windows:
                self.windows.remove(win)
            for mon in self.monitors:
                if win in getattr(mon, "windows", []):
                    mon.windows.remove(win)
            self.layout_manager.remove_window(win)
            self.focus = self.windows[0] if self.windows else None
            if self.focus:
                self.set_focus(self.focus)
            if hasattr(self, "notifications"):
                self.notifications.notify("Janela fechada", "normal")
                self.notifications.window_changed()

    # =======================
    # INICIALIZAÇÃO
    # =======================
    def run(self):
        # Autostart apps
        try:
            self.workspaces_manager.run_autostart()
        except Exception:
            pass

        # Registrar teclas
        self.keybindings.grab_keys()

        print("MyWM iniciado")
        while True:
            ev = self.dpy.next_event()
            # Tratar eventos mínimos: KeyPress e MapRequest
            if ev.type == X.KeyPress:
                self.keybindings.handle_key_press(ev)
            elif ev.type == X.MapRequest:
                # quando uma janela solicita mapeamento, adiciona ao WM
                try:
                    w = ev.window
                    self.add_window(w)
                except Exception:
                    pass
