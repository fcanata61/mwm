# mywm1.0/managers/window.py
# Window manager principal para MyWM
# Funcionalidades: workspaces, layouts, foco, scratchpads, integração com notifications

from Xlib import X, display
from Xlib.protocol import event
import threading
import time

class Window:
    """Representa uma janela gerenciada pelo WM"""
    def __init__(self, window, wm):
        self.window = window
        self.wm = wm
        self.title = self.get_title()
        self.workspace = None
        self.floating = False

    def get_title(self):
        try:
            return self.window.get_wm_name() or "no-title"
        except Exception:
            return "no-title"

    def focus(self):
        try:
            self.window.set_input_focus(X.RevertToPointerRoot, X.CurrentTime)
        except Exception:
            pass

    def map(self):
        try:
            self.window.map()
        except Exception:
            pass

    def unmap(self):
        try:
            self.window.unmap()
        except Exception:
            pass

    def kill(self):
        try:
            self.window.destroy()
        except Exception:
            pass

class WindowManager:
    """Gerenciador de janelas principal"""
    def __init__(self, config=None):
        self.config = config or {}
        self.d = display.Display()
        self.root = self.d.screen().root
        self.windows = []
        self.focused_window = None
        self.workspaces = [[] for _ in range(10)]
        self.current_workspace = 0
        self.layouts = ["tile", "monocle", "floating"]
        self.current_layout = "tile"
        self.scratchpad = None
        self.notifications = None
        self.running = False

    # -------------------------
    # Inicialização
    # -------------------------
    def start(self):
        self.running = True
        # captura eventos de criação de janela
        self.root.change_attributes(event_mask=X.SubstructureNotifyMask)
        threading.Thread(target=self.event_loop, daemon=True).start()

    # -------------------------
    # Loop de eventos
    # -------------------------
    def event_loop(self):
        while self.running:
            e = self.d.next_event()
            if isinstance(e, event.MapRequest):
                self.manage_window(e.window)
            elif isinstance(e, event.DestroyNotify):
                self.unmanage_window(e.window)
            elif isinstance(e, event.ConfigureRequest):
                self.handle_configure(e)

    # -------------------------
    # Gerenciamento de janelas
    # -------------------------
    def manage_window(self, window):
        # verifica se é scratchpad
        if self.scratchpad and self.scratchpad.check_new_window(window):
            return

        w = Window(window, self)
        self.windows.append(w)
        self.workspaces[self.current_workspace].append(w)
        self.focus_window(w)
        self.apply_layout()

        if self.notifications:
            self.notifications.window_changed()

    def unmanage_window(self, window):
        w = next((win for win in self.windows if win.window == window), None)
        if w:
            self.windows.remove(w)
            for ws in self.workspaces:
                if w in ws:
                    ws.remove(w)
            if self.focused_window == w:
                self.focused_window = None
            self.apply_layout()
            if self.notifications:
                self.notifications.window_changed()

    def focus_window(self, window):
        self.focused_window = window
        window.focus()
        if self.notifications:
            self.notifications.window_changed()

    # -------------------------
    # Layouts
    # -------------------------
    def apply_layout(self):
        ws = self.workspaces[self.current_workspace]
        if self.current_layout == "tile":
            self.tile(ws)
        elif self.current_layout == "monocle":
            self.monocle(ws)
        elif self.current_layout == "floating":
            for w in ws:
                w.map()

    def tile(self, ws):
        n = len(ws)
        if n == 0:
            return
        screen = self.d.screen()
        width = screen.width_in_pixels
        height = screen.height_in_pixels
        master_area = width // 2
        for i, w in enumerate(ws):
            if i == 0:
                w.window.configure(x=0, y=0, width=master_area, height=height)
            else:
                w.window.configure(x=master_area, y=(i-1)*(height//(n-1)),
                                   width=width-master_area, height=height//(n-1))
            w.map()

    def monocle(self, ws):
        screen = self.d.screen()
        width = screen.width_in_pixels
        height = screen.height_in_pixels
        for w in ws:
            w.window.configure(x=0, y=0, width=width, height=height)
            w.map()

    # -------------------------
    # Layout/Workspace management
    # -------------------------
    def next_workspace(self):
        self.current_workspace = (self.current_workspace + 1) % len(self.workspaces)
        self.apply_layout()
        if self.notifications:
            self.notifications.force_update()

    def prev_workspace(self):
        self.current_workspace = (self.current_workspace - 1) % len(self.workspaces)
        self.apply_layout()
        if self.notifications:
            self.notifications.force_update()

    def set_layout(self, layout):
        if layout in self.layouts:
            self.current_layout = layout
            self.apply_layout()
            if self.notifications:
                self.notifications.force_update()

    # -------------------------
    # ConfigureRequest handler
    # -------------------------
    def handle_configure(self, e):
        try:
            e.window.configure(x=e.x, y=e.y, width=e.width, height=e.height,
                               border_width=e.border_width, stack_mode=e.detail)
        except Exception:
            pass

    # -------------------------
    # Scratchpad integration
    # -------------------------
    def setup_scratchpad(self, scratchpad_manager):
        self.scratchpad = scratchpad_manager

    # -------------------------
    # Notifications integration
    # -------------------------
    def setup_notifications(self, notifications_manager):
        self.notifications = notifications_manager
