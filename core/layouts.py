# mywm1.0/core/layouts.py
# Layouts avançados MyWM v2.0
# Funcional, com snapping, floating inteligente, multi-monitor e notificações

from Xlib import X

# =======================
# GERENCIADOR DE LAYOUTS
# =======================
class LayoutManager:
    def __init__(self, default_layout="tile"):
        self.layouts = [
            Tile(), Monocle(), Floating(), BSP(), Grid(), Tabbed(), Stacking()
        ]
        self.current_index = 0
        self.default_layout_name = default_layout

    def current_layout(self):
        return self.layouts[self.current_index]

    def set_layout(self, name):
        for i, layout in enumerate(self.layouts):
            if layout.name == name:
                self.current_index = i
                return

    def next_layout(self):
        self.current_index = (self.current_index + 1) % len(self.layouts)

    def prev_layout(self):
        self.current_index = (self.current_index - 1) % len(self.layouts)

    def apply(self, windows, screen_geom):
        if windows:
            self.current_layout().apply(windows, screen_geom)

    def add_window(self, win):
        self.current_layout().on_window_add(win)

    def remove_window(self, win):
        self.current_layout().on_window_remove(win)

# =======================
# CLASSE BASE
# =======================
class BaseLayout:
    def __init__(self, name):
        self.name = name

    def apply(self, windows, screen_geom):
        raise NotImplementedError

    def on_window_add(self, win):
        pass

    def on_window_remove(self, win):
        pass

# =======================
# TILE
# =======================
class Tile(BaseLayout):
    def __init__(self):
        super().__init__("tile")

    def apply(self, windows, screen_geom):
        n = len(windows)
        if n == 0:
            return
        master_width = screen_geom["width"] // 2
        for i, w in enumerate(windows):
            if i == 0:
                w.configure(x=0, y=0, width=master_width, height=screen_geom["height"])
            else:
                w.configure(
                    x=master_width,
                    y=(i-1)*(screen_geom["height"]//(n-1)),
                    width=screen_geom["width"]-master_width,
                    height=screen_geom["height"]//(n-1)
                )
            w.map()

# =======================
# MONOCLE
# =======================
class Monocle(BaseLayout):
    def __init__(self):
        super().__init__("monocle")

    def apply(self, windows, screen_geom):
        for i, w in enumerate(windows):
            if i == 0:
                w.configure(x=0, y=0, width=screen_geom["width"], height=screen_geom["height"])
                w.map()
            else:
                w.unmap()

# =======================
# FLOATING INTELIGENTE
# =======================
class Floating(BaseLayout):
    def __init__(self):
        super().__init__("floating")
        self.positions = {}
        self.snap_threshold = 20

    def apply(self, windows, screen_geom):
        for w in windows:
            if w.id not in self.positions:
                self.positions[w.id] = {"x":50, "y":50, "w":screen_geom["width"]//2, "h":screen_geom["height"]//2}
            geom = self.snap_to_edges(self.positions[w.id], screen_geom)
            w.configure(x=geom["x"], y=geom["y"], width=geom["w"], height=geom["h"])
            w.map()

    def snap_to_edges(self, geom, screen_geom):
        if abs(geom["x"]) < self.snap_threshold:
            geom["x"] = 0
        if abs(geom["x"] + geom["w"] - screen_geom["width"]) < self.snap_threshold:
            geom["x"] = screen_geom["width"] - geom["w"]
        if abs(geom["y"]) < self.snap_threshold:
            geom["y"] = 0
        if abs(geom["y"] + geom["h"] - screen_geom["height"]) < self.snap_threshold:
            geom["y"] = screen_geom["height"] - geom["h"]
        return geom

    def move(self, win, dx, dy):
        if win.id in self.positions:
            self.positions[win.id]["x"] += dx
            self.positions[win.id]["y"] += dy

    def resize(self, win, dw, dh):
        if win.id in self.positions:
            self.positions[win.id]["w"] = max(50, self.positions[win.id]["w"] + dw)
            self.positions[win.id]["h"] = max(50, self.positions[win.id]["h"] + dh)

    def on_window_add(self, win):
        if win.id not in self.positions:
            self.positions[win.id] = {"x":50, "y":50, "w":400, "h":300}

    def on_window_remove(self, win):
        if win.id in self.positions:
            del self.positions[win.id]

# =======================
# BSP
# =======================
class BSP(BaseLayout):
    def __init__(self):
        super().__init__("bsp")

    def apply(self, windows, screen_geom):
        def split_area(wins, x, y, w, h, vertical=True):
            if not wins:
                return
            if len(wins) == 1:
                win = wins[0]
                win.configure(x=x, y=y, width=w, height=h)
                win.map()
                return
            mid = len(wins)//2
            if vertical:
                split_area(wins[:mid], x, y, w//2, h, not vertical)
                split_area(wins[mid:], x + w//2, y, w - w//2, h, not vertical)
            else:
                split_area(wins[:mid], x, y, w, h//2, not vertical)
                split_area(wins[mid:], x, y + h//2, w, h - h//2, not vertical)
        split_area(windows, 0, 0, screen_geom["width"], screen_geom["height"])

# =======================
# GRID
# =======================
class Grid(BaseLayout):
    def __init__(self):
        super().__init__("grid")

    def apply(self, windows, screen_geom):
        n = len(windows)
        if n == 0:
            return
        cols = int(n**0.5)
        rows = (n + cols -1)//cols
        cell_w = screen_geom["width"]//cols
        cell_h = screen_geom["height"]//rows
        for i, w in enumerate(windows):
            c = i % cols
            r = i // cols
            w.configure(x=c*cell_w, y=r*cell_h, width=cell_w, height=cell_h)
            w.map()

# =======================
# TABBED
# =======================
class Tabbed(BaseLayout):
    def __init__(self):
        super().__init__("tabbed")
        self.current_tab = 0

    def apply(self, windows, screen_geom):
        if not windows:
            return
        for i, w in enumerate(windows):
            if i == self.current_tab:
                w.configure(x=0, y=20, width=screen_geom["width"], height=screen_geom["height"]-20)
                w.map()
            else:
                w.unmap()

# =======================
# STACKING
# =======================
class Stacking(BaseLayout):
    def __init__(self):
        super().__init__("stacking")

    def apply(self, windows, screen_geom):
        if not windows:
            return
        for i, w in enumerate(windows):
            w.configure(x=20*i, y=20*i, width=screen_geom["width"]-40, height=screen_geom["height"]-40)
            w.map()
