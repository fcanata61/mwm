# managers/multimonitor.py
# Suporte Multi-Monitor melhorado para MyWM

from Xlib import X, Xatom
from core import layouts, ewmh
from Xlib.ext import randr

class Monitor:
    def __init__(self, name, x, y, width, height):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.windows = []

    def geom(self):
        """Retorna objeto com atributos x, y, width, height"""
        return type("Geom", (), {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height
        })()

    def contains_geom(self, win_geom):
        """Verifica se a geometria de uma janela pertence/está dentro deste monitor"""
        # win_geom deve ter x, y
        wx, wy = win_geom.x, win_geom.y
        return (wx >= self.x and wy >= self.y and
                wx < self.x + self.width and wy < self.y + self.height)

class MultiMonitorWM:
    def __init__(self, wm):
        """
        wm: instância principal do WM, para usar seu display, root e layout_manager central.
        """
        self.wm = wm
        self.dpy = wm.dpy
        self.root = wm.root
        self.monitors = []
        self.focus = None
        # inicializar monitores
        self.detect_monitors()
        # conectar eventos de mudança de tela (XRandR)
        self.setup_randr()

    # =======================
    # DETECÇÃO DE MONITORES
    # =======================
    def detect_monitors(self):
        """Detecta monitores ativos via XRandR e popula self.monitors."""
        try:
            res = self.root.xrandr_get_screen_resources()._data
            monitors = []
            for crtc in res['crtcs']:
                info = self.dpy.xrandr_get_crtc_info(crtc, res['config_timestamp'])._data
                # requer que output ativo (ha outputs ligados a esse crtc)
                if info['width'] > 0 and info['height'] > 0:
                    mon = Monitor(
                        name = str(crtc),
                        x = info['x'],
                        y = info['y'],
                        width = info['width'],
                        height = info['height']
                    )
                    monitors.append(mon)
            if monitors:
                self.monitors = monitors
            else:
                # fallback para monitor root
                geom = self.root.get_geometry()
                self.monitors = [Monitor("default", 0, 0, geom.width, geom.height)]
        except Exception as e:
            # fallback simples
            geom = self.root.get_geometry()
            self.monitors = [Monitor("default", 0, 0, geom.width, geom.height)]

    def setup_randr(self):
        """Registra interesse em eventos de mudança de monitor."""
        try:
            self.root.change_attributes(event_mask=X.SubstructureNotifyMask | randr.RRScreenChangeNotifyMask)
            # Pode ser necessário tirar permissões / registrar para events randr
        except Exception:
            pass

    # =======================
    # GERENCIAMENTO DE JANELAS POR MONITOR
    # =======================
    def add_window(self, win):
        """Adiciona janela ao monitor apropriado baseado em geometria."""
        try:
            geom = win.get_geometry()
        except Exception:
            # coloque no monitor 0 por padrão
            target = self.monitors[0]
        else:
            target = None
            for mon in self.monitors:
                if mon.contains_geom(geom):
                    target = mon
                    break
            if target is None:
                # se não estiver completamente em nenhum monitor, escolhe aquele que contém o centro
                cx = geom.x + geom.width // 2
                cy = geom.y + geom.height // 2
                for mon in self.monitors:
                    if (cx >= mon.x and cy >= mon.y and
                       cx < mon.x + mon.width and cy < mon.y + mon.height):
                        target = mon
                        break
                if target is None:
                    # fallback
                    target = self.monitors[0]
        target.windows.append(win)
        # usa layout do WM principal
        self.wm.layout_manager.add_window(win)
        self.apply_layout(target)

        # foco
        self.set_focus(win)

    def remove_window(self, win):
        for mon in self.monitors:
            if win in mon.windows:
                mon.windows.remove(win)
        self.wm.layout_manager.remove_window(win)
        self.apply_all_layouts()
        if self.focus == win:
            self.focus = self.get_focused_window()
            if self.focus:
                self.set_focus(self.focus)

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

    def get_focused_window(self):
        # retorna foco do monitor que contém foco ou o primeiro
        for mon in self.monitors:
            if self.focus and self.focus in mon.windows:
                return self.focus
        for mon in self.monitors:
            if mon.windows:
                return mon.windows[0]
        return None

    # =======================
    # APLICAR LAYOUTS
    # =======================
    def apply_layout(self, monitor):
        """Aplica layout para um monitor específico."""
        self.wm.layout_manager.apply(monitor.windows, monitor.geom())

    def apply_all_layouts(self):
        for mon in self.monitors:
            self.apply_layout(mon)

    def next_layout(self, monitor_index):
        self.wm.layout_manager.next_layout()
        if 0 <= monitor_index < len(self.monitors):
            self.apply_layout(self.monitors[monitor_index])

    def prev_layout(self, monitor_index):
        self.wm.layout_manager.prev_layout()
        if 0 <= monitor_index < len(self.monitors):
            self.apply_layout(self.monitors[monitor_index])

    # =======================
    # MOVER JANELAS ENTRE MONITORES
    # =======================
    def move_window_to_monitor(self, win, target_monitor_index):
        if target_monitor_index < 0 or target_monitor_index >= len(self.monitors):
            return
        # remove de onde está
        for mon in self.monitors:
            if win in mon.windows:
                mon.windows.remove(win)
        # adiciona ao monitor alvo
        self.monitors[target_monitor_index].windows.append(win)
        # Reaplica layouts
        self.apply_all_layouts()
        self.set_focus(win)

    # =======================
    # FLOATING INTELIGENTE POR MONITOR
    # =======================
    def move_floating(self, dx, dy):
        if not self.focus:
            return
        current_layout = self.wm.layout_manager.layouts[self.wm.layout_manager.current]
        if hasattr(current_layout, "move"):
            current_layout.move(self.focus, dx, dy)
            self.apply_all_layouts()

    def resize_floating(self, dw, dh):
        if not self.focus:
            return
        current_layout = self.wm.layout_manager.layouts[self.wm.layout_manager.current]
        if hasattr(current_layout, "resize"):
            current_layout.resize(self.focus, dw, dh)
            self.apply_all_layouts()
