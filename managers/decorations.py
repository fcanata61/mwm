# managers/decorations.py
# Bordas internas/externas e gaps para MyWM 1.0+

from Xlib import X
# Não importar core.layouts; usaremos o layout_manager via WM referência

class Decorations:
    def __init__(self, wm, config):
        """ wm: referência ao WindowManager
            config: dict externo com cores, gaps e bordas
        """
        self.wm = wm
        self.config = config or {}

        # Configurações padrão caso não existam
        self.border_width = self.config.get("border_width", 2)
        self.inner_gap = self.config.get("inner_gap", 5)
        self.outer_gap = self.config.get("outer_gap", 10)
        self.border_color_active = self.config.get("border_color_active", "#ff0000")
        self.border_color_inactive = self.config.get("border_color_inactive", "#555555")

    # =======================
    # APLICAR DECORAÇÕES
    # =======================
    def apply_decorations(self):
        """ Aplica bordas e gaps para todas as janelas visíveis.
            Deve ser chamado sempre que o layout ou janelas mudarem.
        """
        for monitor in getattr(self.wm, "monitors", []):
            if monitor:
                self._apply_monitor(monitor)

    def _apply_monitor(self, monitor):
        # current layout pode ser obtido via layout_manager
        layout_manager = getattr(self.wm, "layout_manager", None)
        try:
            layout = layout_manager.layouts[layout_manager.current]
        except Exception:
            layout = None

        n = len(getattr(monitor, "windows", []))
        for i, win in enumerate(list(getattr(monitor, "windows", []))):
            try:
                geom = win.get_geometry()
            except Exception:
                continue

            # Bordas internas
            x = geom.x + self.inner_gap
            y = geom.y + self.inner_gap
            w = geom.width - 2 * self.inner_gap
            h = geom.height - 2 * self.inner_gap

            # Bordas externas para a primeira janela do monitor (exemplo)
            if i == 0:
                x += self.outer_gap
                y += self.outer_gap
                w -= 2 * self.outer_gap
                h -= 2 * self.outer_gap

            # Determinar cor da borda (placeholder — precisa conversão para pixel)
            color = self.border_color_active if win == getattr(self.wm, "focus", None) else self.border_color_inactive

            # Aplicar configuração
            try:
                win.configure(x=x, y=y, width=max(1, w), height=max(1, h), border_width=self.border_width)
                # Para mudar cor da borda é necessário converter "#rrggbb" para pixel usando colormap.
                # Exemplo (placeholder): win.change_attributes(border_pixel=color_pixel)
            except Exception:
                pass

            try:
                win.map()
            except Exception:
                pass

    # =======================
    # RECARREGAR CONFIG
    # =======================
    def reload_config(self, new_config):
        """ Recarrega configuração sem reiniciar o WM """
        self.config = new_config or {}
        self.border_width = self.config.get("border_width", self.border_width)
        self.inner_gap = self.config.get("inner_gap", self.inner_gap)
        self.outer_gap = self.config.get("outer_gap", self.outer_gap)
        self.border_color_active = self.config.get("border_color_active", self.border_color_active)
        self.border_color_inactive = self.config.get("border_color_inactive", self.border_color_inactive)
        self.apply_decorations()

    # =======================
    # INTEGRAÇÃO COM LEMONBAR
    # =======================
    def get_status_info(self):
        """ Retorna dados que podem ser exibidos na lemonbar """
        layout_name = self.wm.layout_manager.current_name() if getattr(self.wm, "layout_manager", None) else "none"
        focused_win = getattr(self.wm, "focus", None)
        return {
            "layout": layout_name,
            "focus_window": getattr(focused_win, "id", None),
            "monitor_count": len(getattr(self.wm, "monitors", [])),
        }
