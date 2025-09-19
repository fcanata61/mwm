# mywm1.0/managers/workspaces.py
# Workspaces avançados MyWM
# Multi-monitor, layouts independentes, mover janelas, scratchpads, notifications

from Xlib import X
import subprocess
import time

class Workspace:
    """Workspace com suporte a layouts, janelas, scratchpads e notificações."""
    def __init__(self, name, layout="tile"):
        self.name = name
        self.windows = []
        self.layout = layout
        self.focus = None
        self.scratchpads = []
        self.notifications = None

    # -------------------------
    # Gerenciamento de janelas
    # -------------------------
    def add_window(self, win):
        if win not in self.windows:
            self.windows.append(win)
            self.apply_layout()
            self.set_focus(win)
            self.update_notifications()

    def remove_window(self, win):
        if win in self.windows:
            self.windows.remove(win)
            if self.focus == win:
                self.focus = self.windows[0] if self.windows else None
            self.apply_layout()
            self.update_notifications()

    def set_focus(self, win):
        self.focus = win
        try:
            win.window.set_input_focus(X.RevertToParent, X.CurrentTime)
        except Exception:
            pass
        self.update_notifications()

    # -------------------------
    # Layouts
    # -------------------------
    def apply_layout(self, screen_geom=None):
        geom = screen_geom or {"x":0, "y":0, "width":800, "height":600}
        n = len(self.windows)
        if n == 0:
            return
        if self.layout == "tile":
            master = geom["width"] // 2
            for i, w in enumerate(self.windows):
                if i == 0:
                    w.window.configure(x=0, y=0, width=master, height=geom["height"])
                else:
                    w.window.configure(x=master, y=(i-1)*(geom["height"]//(n-1)),
                                       width=geom["width"]-master, height=geom["height"]//(n-1))
                w.map()
        elif self.layout == "monocle":
            for w in self.windows:
                w.window.configure(x=geom["x"], y=geom["y"], width=geom["width"], height=geom["height"])
                w.map()
        elif self.layout == "floating":
            for w in self.windows:
                w.map()

    def set_layout(self, layout):
        self.layout = layout
        self.apply_layout()
        self.update_notifications()

    # -------------------------
    # Scratchpads
    # -------------------------
    def add_scratchpad(self, scratchpad_id):
        if scratchpad_id not in self.scratchpads:
            self.scratchpads.append(scratchpad_id)

    def toggle_scratchpad(self, scratchpad_manager, scratchpad_id):
        if scratchpad_id in self.scratchpads:
            scratchpad_manager.toggle(scratchpad_id)
            self.update_notifications()

    # -------------------------
    # Notifications
    # -------------------------
    def set_notifications(self, notifications_manager):
        self.notifications = notifications_manager
        self.update_notifications()

    def update_notifications(self):
        if self.notifications:
            title = self.focus.title if self.focus else "Nenhuma janela"
            active_scratchpads = ", ".join(self.scratchpads) if self.scratchpads else "Nenhum"
            self.notifications.update_workspace(self.name, title, active_scratchpads)

class WorkspacesManager:
    """Gerencia múltiplos workspaces, layouts, scratchpads e notifications"""
    def __init__(self, wm, names=None):
        self.wm = wm
        self.workspaces = [Workspace(n) for n in (names or [str(i+1) for i in range(9)])]
        self.current_index = 0
        self.autostart_apps = []

    # -------------------------
    # Workspace atual
    # -------------------------
    def current(self):
        return self.workspaces[self.current_index]

    def switch_to(self, index):
        if 0 <= index < len(self.workspaces):
            self.current_index = index
            ws = self.current()
            ws.apply_layout()
            if ws.focus:
                self.wm.set_focus(ws.focus)
            ws.update_notifications()

    def next_workspace(self):
        self.switch_to((self.current_index + 1) % len(self.workspaces))

    def prev_workspace(self):
        self.switch_to((self.current_index - 1) % len(self.workspaces))

    # -------------------------
    # Movimentação de janelas
    # -------------------------
    def move_window_to(self, win, target_index):
        if 0 <= target_index < len(self.workspaces):
            current_ws = self.find_workspace_of(win)
            if current_ws:
                current_ws.remove_window(win)
            self.workspaces[target_index].add_window(win)
            self.workspaces[target_index].apply_layout()
            self.wm.set_focus(win)

    def find_workspace_of(self, win):
        for ws in self.workspaces:
            if win in ws.windows:
                return ws
        return None

    # -------------------------
    # Scratchpad helpers
    # -------------------------
    def add_scratchpad_to_current(self, scratchpad_id):
        self.current().add_scratchpad(scratchpad_id)

    def toggle_scratchpad_current(self, scratchpad_manager, scratchpad_id):
        self.current().toggle_scratchpad(scratchpad_manager, scratchpad_id)

    # -------------------------
    # Autostart
    # -------------------------
    def set_autostart(self, apps):
        self.autostart_apps = apps

    def run_autostart(self, delay=0.1):
        for cmd in self.autostart_apps:
            subprocess.Popen(cmd, shell=True)
            time.sleep(delay)

    # -------------------------
    # Layout e notifications
    # -------------------------
    def apply_current_layout(self):
        self.current().apply_layout()

    def set_notifications(self, notifications_manager):
        for ws in self.workspaces:
            ws.set_notifications(notifications_manager)
