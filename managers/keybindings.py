# managers/keybindings.py
# Keybindings avançados MyWM 1.2+

from Xlib import X, XK
import subprocess

# Masks úteis (padrão X)
MOD_MAP = {
    "Shift": X.ShiftMask,
    "Lock": X.LockMask,
    "Control": X.ControlMask,
    "Mod1": X.Mod1Mask,
    "Mod2": X.Mod2Mask,
    "Mod3": X.Mod3Mask,
    "Mod4": X.Mod4Mask,
    "Mod5": X.Mod5Mask,
}

# máscaras extras para NumLock/Caps (valores comuns; o ideal é obter do display)
NUMLOCK_MASK = 1 << 5  # fallback — o ideal é detectar dinamicamente
CAPSLOCK_MASK = X.LockMask

class KeyBindings:
    def __init__(self, wm, config=None):
        """ wm: referência ao WindowManager
            config: dict com atalhos, terminal, etc.
        """
        self.wm = wm
        self.config = config or {}
        self.bindings = {}  # map: (keysym, mod_mask) -> callable
        self._setup_default_bindings()

    # =======================
    # ATALHOS PADRÃO
    # =======================
    def _setup_default_bindings(self):
        # limpa e registra
        self.bindings.clear()
        self._bind_from_string(self.config.get("alt_tab", "Mod1+Tab"), self.cycle_windows)
        self._bind_from_string(self.config.get("mod_enter", "Mod4+Return"), self.launch_terminal)
        self._bind_from_string(self.config.get("mod_shift_q", "Mod4+Shift+q"), self.close_focused)
        self._bind_from_string(self.config.get("mod_space", "Mod4+space"), self.next_layout)
        self._bind_from_string(self.config.get("mod_shift_space", "Mod4+Shift+space"), self.prev_layout)
        self._bind_from_string(self.config.get("mod_shift_s", "Mod4+Shift+s"), self.toggle_scratchpad)
        self._bind_from_string(self.config.get("mod_r", "Mod4+r"), self.reload_config)

    def _normalize_token(self, tok):
        tok = tok.strip()
        # mapeamentos comuns
        if tok.lower() in ("alt", "alt_l", "alt_r"):
            return "Mod1"
        if tok.lower() in ("win", "super", "mod4"):
            return "Mod4"
        return tok

    def _parse_combo(self, combo):
        """Recebe string tipo 'Mod4+Shift+Return' e retorna (keysym, mask)"""
        parts = [self._normalize_token(p) for p in combo.split("+") if p]
        mask = 0
        key_token = parts[-1]
        for p in parts[:-1]:
            if p in MOD_MAP:
                mask |= MOD_MAP[p]
            elif p.startswith("Mod"):
                # tentar mapear ModN para mask se existir
                mask |= MOD_MAP.get(p, 0)
        # obter keysym
        keysym = XK.string_to_keysym(key_token)
        if keysym == 0:
            # tentar nomes alternativos (ex: space)
            keysym = XK.string_to_keysym(key_token.capitalize())
        return keysym, mask

    def _bind_from_string(self, combo, action):
        keysym, mask = self._parse_combo(combo)
        if keysym:
            self.bindings[(keysym, mask)] = action

    # =======================
    # FUNÇÕES DE TECLA
    # =======================
    def cycle_windows(self):
        ws = getattr(self.wm, "workspaces_manager", None)
        if ws:
            windows = getattr(ws.current(), "windows", [])
        else:
            windows = getattr(self.wm, "windows", [])
        if not windows or len(windows) < 2:
            return
        try:
            idx = windows.index(self.wm.focus) if self.wm.focus in windows else 0
            next_win = windows[(idx + 1) % len(windows)]
            self.wm.set_focus(next_win)
        except Exception:
            pass
        if hasattr(self.wm, "notifications"):
            self.wm.notifications.window_changed()

    def next_layout(self):
        if hasattr(self.wm, "layout_manager"):
            self.wm.layout_manager.next_layout()
            self.wm.layout_manager.apply(getattr(self.wm, "windows", []), getattr(self.wm, "screen_geom", None))
        if hasattr(self.wm, "notifications"):
            self.wm.notifications.window_changed()

    def prev_layout(self):
        if hasattr(self.wm, "layout_manager"):
            self.wm.layout_manager.prev_layout()
            self.wm.layout_manager.apply(getattr(self.wm, "windows", []), getattr(self.wm, "screen_geom", None))
        if hasattr(self.wm, "notifications"):
            self.wm.notifications.window_changed()

    def toggle_scratchpad(self):
        if hasattr(self.wm, "scratchpad"):
            self.wm.scratchpad.toggle_by_key()
        if hasattr(self.wm, "notifications"):
            self.wm.notifications.window_changed()

    def launch_terminal(self):
        terminal = self.config.get("terminal", "xterm")
        try:
            # prefer passar como lista quando possível
            subprocess.Popen([terminal])
        except Exception:
            # fallback
            subprocess.Popen(terminal, shell=True)

    def close_focused(self):
        if hasattr(self.wm, "remove_focused"):
            self.wm.remove_focused()
        if hasattr(self.wm, "notifications"):
            self.wm.notifications.notify("Janela fechada", "normal")
            self.wm.notifications.window_changed()

    def reload_config(self):
        if hasattr(self.wm, "decorations"):
            self.wm.decorations.reload_config(self.config.get("decorations", {}))
        self._setup_default_bindings()
        if hasattr(self.wm, "notifications"):
            self.wm.notifications.notify("Configuração recarregada", "low")

    # =======================
    # REGISTRAR ATALHOS NO X SERVER
    # =======================
    def grab_keys(self):
        """ Registra todas as teclas no X server, considerando máscaras comuns """
        # máscaras adicionais para NumLock/Caps — ideal detectar dinamicamente
        extra_masks = [0, NUMLOCK_MASK, CAPSLOCK_MASK, NUMLOCK_MASK | CAPSLOCK_MASK]
        for (keysym, base_mod), action in list(self.bindings.items()):
            keycode = self.wm.dpy.keysym_to_keycode(keysym)
            for extra in extra_masks:
                mod = base_mod | extra
                try:
                    self.wm.root.grab_key(keycode, mod, True, X.GrabModeAsync, X.GrabModeAsync)
                except Exception:
                    pass

    # =======================
    # TRATAR EVENTO DE TECLA
    # =======================
    def handle_key_press(self, event):
        # Obtém keysym e máscara do evento
        try:
            state = event.state
            keysym = self.wm.dpy.keycode_to_keysym(event.detail, 0)
            # Normalizar máscara removendo NumLock/Caps para procurar binding
            norm_state = state & ~NUMLOCK_MASK & ~CAPSLOCK_MASK
            action = self.bindings.get((keysym, norm_state))
            if action:
                action()
        except Exception:
            pass
