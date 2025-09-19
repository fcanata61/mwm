# =======================
# Configuração do MyWM 1.0+
# =======================
config = {
    # =======================
    # Terminal padrão
    # =======================
    "terminal": "xterm",

    # =======================
    # Decorações: bordas e gaps
    # =======================
    "decorations": {
        "border_width": 2,
        "inner_gap": 5,
        "outer_gap": 10,
        "border_color_active": "#ff0000",
        "border_color_inactive": "#555555"
    },

    # =======================
    # Workspaces
    # =======================
    "workspaces": {
        "names": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        "layouts": ["monocle", "tile", "tile", "monocle", "tile", "tile", "monocle", "tile", "tile"],
        "scratchpads": ["term1", "term2", "term3"]  # Exemplo de scratchpads
    },

    # =======================
    # Keybindings
    # =======================
    "keybindings": {
        "mod_enter": "Mod4+Return",  # Abrir terminal
        "mod_shift_q": "Mod4+Shift+Q",  # Fechar janela
        "mod_space": "Mod4+space",  # Próximo layout
        "mod_shift_space": "Mod4+Shift+space",  # Layout anterior
        "mod_shift_s": "Mod4+Shift+S",  # Toggle scratchpad
        "mod_r": "Mod4+r",  # Recarregar configuração
        "mod_1": "Mod4+1",  # Mudar para workspace 1
        "mod_2": "Mod4+2",  # Mudar para workspace 2
        # Adicione outros keybindings conforme necessário
    },

    # =======================
    # Autostart
    # =======================
    "autostart": [
        "nm-applet",
        "pasystray",
        "picom --experimental-backends",
        "xsetroot -cursor_name left_ptr"
    ],

    # =======================
    # Lemonbar e notificações
    # =======================
    "notifications": {
        "lemonbar_cmd": "lemonbar -p -g 1920x24+0+0 -B '#222' -F '#fff'",
        "notify_app": "notify-send"
    },

    # =======================
    # Outros ajustes
    # =======================
    "multi_monitor": True,  # Suporte a múltiplos monitores
    "scratchpad_geometry": "800x600+100+100",  # Posição inicial do scratchpad
    "floating_default": False,  # Janelas padrão como floating ou tile
    "focus_follows_mouse": True,  # Foco segue o mouse
    "click_to_focus": False,  # Clique para focar
    "border_width": 2,  # Largura da borda
    "border_color": "#ff0000",  # Cor da borda
    "gap": 10,  # Espaçamento entre janelas
    "wm_name": "MyWM 1.0+"  # Nome do gerenciador de janelas
}
