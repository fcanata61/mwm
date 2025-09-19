#!/usr/bin/env python3
# mywm1.0/main.py
# Main funcional e evoluído do MyWM 1.0+

import sys
import time
from mywm.config import config
from mywm.core.layouts import LayoutManager
from mywm.core.ewmh import init_ewmh, update_client_list, set_current_desktop, set_active_window
from mywm.managers.workspaces import WorkspaceManager
from mywm.managers.scratchpad import ScratchpadManager
from mywm.managers.window import WindowManager
from mywm.managers.notificacoes import NotificationManager
from Xlib import X, display

# =======================
# Inicialização do Display
# =======================
dpy = display.Display()
root = dpy.screen().root

# =======================
# Inicialização do WM
# =======================
def initialize_wm():
    # EWMH
    init_ewmh(wm_name=config["wm_name"], workspaces=config["workspaces"]["names"])
    
    # Gerenciadores
    layout_manager = LayoutManager()
    workspace_manager = WorkspaceManager(config)
    scratchpad_manager = ScratchpadManager(config)
    notification_manager = NotificationManager(config)
    window_manager = WindowManager(dpy, root, layout_manager, workspace_manager, scratchpad_manager, notification_manager)

    # Autostart
    for cmd in config["autostart"]:
        import subprocess
        subprocess.Popen(cmd, shell=True)

    return layout_manager, workspace_manager, scratchpad_manager, notification_manager, window_manager

# =======================
# Loop principal
# =======================
def main_loop(layout_manager, workspace_manager, scratchpad_manager, notification_manager, window_manager):
    try:
        while True:
            # Captura eventos do X
            window_manager.handle_events()

            # Atualiza layouts e workspaces
            workspace_manager.update()
            layout_manager.apply(workspace_manager.get_windows(), window_manager.get_screen_geometry())

            # Atualiza scratchpads
            scratchpad_manager.update()

            # Atualiza EWMH
            update_client_list(window_manager.get_windows())
            set_current_desktop(workspace_manager.current_index)
            set_active_window(window_manager.get_focused_window())

            # Atualiza notificações
            notification_manager.update(workspace_manager, scratchpad_manager, window_manager)

            # Delay mínimo para não sobrecarregar CPU
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("Encerrando MyWM...")
        sys.exit(0)

# =======================
# Main
# =======================
def main():
    layout_manager, workspace_manager, scratchpad_manager, notification_manager, window_manager = initialize_wm()
    main_loop(layout_manager, workspace_manager, scratchpad_manager, notification_manager, window_manager)

if __name__ == "__main__":
    main()
