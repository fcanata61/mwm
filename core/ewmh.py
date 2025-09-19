# mywm1.0/core/ewmh.py
# EWMH avançado para MyWM com suporte a scratchpads e notifications

from Xlib import X, Xatom, display

dpy = display.Display()
root = dpy.screen().root

# =======================
# ATOMS EWMH
# =======================
NET_SUPPORTED = dpy.intern_atom("_NET_SUPPORTED")
NET_WM_NAME = dpy.intern_atom("_NET_WM_NAME")
NET_CLIENT_LIST = dpy.intern_atom("_NET_CLIENT_LIST")
NET_ACTIVE_WINDOW = dpy.intern_atom("_NET_ACTIVE_WINDOW")
NET_NUMBER_OF_DESKTOPS = dpy.intern_atom("_NET_NUMBER_OF_DESKTOPS")
NET_CURRENT_DESKTOP = dpy.intern_atom("_NET_CURRENT_DESKTOP")
NET_DESKTOP_NAMES = dpy.intern_atom("_NET_DESKTOP_NAMES")
NET_DESKTOP_VIEWPORT = dpy.intern_atom("_NET_DESKTOP_VIEWPORT")
NET_SHOWING_DESKTOP = dpy.intern_atom("_NET_SHOWING_DESKTOP")
NET_WM_STATE = dpy.intern_atom("_NET_WM_STATE")
NET_WM_STATE_FULLSCREEN = dpy.intern_atom("_NET_WM_STATE_FULLSCREEN")
NET_WM_STATE_MAXIMIZED_VERT = dpy.intern_atom("_NET_WM_STATE_MAXIMIZED_VERT")
NET_WM_STATE_MAXIMIZED_HORZ = dpy.intern_atom("_NET_WM_STATE_MAXIMIZED_HORZ")
NET_SUPPORTING_WM_CHECK = dpy.intern_atom("_NET_SUPPORTING_WM_CHECK")
UTF8_STRING = dpy.intern_atom("UTF8_STRING")

# =======================
# WM CHECK WINDOW
# =======================
wm_check = None
workspace_names = []
current_desktop = 0
scratchpads = {}

# -----------------------
# Inicialização EWMH
# -----------------------
def init_ewmh(wm_name="MyWM", workspaces=None):
    global wm_check, workspace_names, current_desktop
    workspace_names = workspaces if workspaces else [str(i+1) for i in range(9)]
    current_desktop = 0

    wm_check = root.create_window(0,0,1,1,0,X.CopyFromParent,X.InputOutput,X.CopyFromParent)
    wm_check.change_property(NET_SUPPORTING_WM_CHECK, Xatom.WINDOW, 32, [wm_check.id])
    wm_check.change_property(NET_WM_NAME, UTF8_STRING, 8, wm_name.encode())

    root.change_property(NET_SUPPORTING_WM_CHECK, Xatom.WINDOW, 32, [wm_check.id])
    root.change_property(NET_WM_NAME, UTF8_STRING, 8, wm_name.encode())
    root.change_property(dpy.intern_atom("WM_NAME"), Xatom.STRING, 8, wm_name.encode())
    root.change_property(dpy.intern_atom("WM_CLASS"), Xatom.STRING, 8, wm_name.encode())
    root.change_property(NET_NUMBER_OF_DESKTOPS, Xatom.CARDINAL, 32, [len(workspace_names)])
    root.change_property(NET_CURRENT_DESKTOP, Xatom.CARDINAL, 32, [current_desktop])

    names_bytes = b"\0".join([n.encode() for n in workspace_names])
    root.change_property(NET_DESKTOP_NAMES, UTF8_STRING, 8, names_bytes)

    viewports = []
    for _ in workspace_names:
        viewports += [0, 0]
    root.change_property(NET_DESKTOP_VIEWPORT, Xatom.CARDINAL, 32, viewports)
    root.change_property(NET_SHOWING_DESKTOP, Xatom.CARDINAL, 32, [0])

    supported_atoms = [
        NET_SUPPORTED, NET_WM_NAME, NET_CLIENT_LIST, NET_ACTIVE_WINDOW,
        NET_NUMBER_OF_DESKTOPS, NET_CURRENT_DESKTOP, NET_DESKTOP_NAMES,
        NET_DESKTOP_VIEWPORT, NET_SHOWING_DESKTOP, NET_WM_STATE,
        NET_WM_STATE_FULLSCREEN, NET_WM_STATE_MAXIMIZED_VERT,
        NET_WM_STATE_MAXIMIZED_HORZ, NET_SUPPORTING_WM_CHECK
    ]
    root.change_property(NET_SUPPORTED, Xatom.ATOM, 32, supported_atoms)
    dpy.flush()

# -----------------------
# Janelas e Workspaces
# -----------------------
def update_client_list(windows):
    ids = [w.id for w in windows if hasattr(w, "id")]
    root.change_property(NET_CLIENT_LIST, Xatom.WINDOW, 32, ids)
    dpy.flush()

def set_active_window(win):
    wid = win.id if win else 0
    root.change_property(NET_ACTIVE_WINDOW, Xatom.WINDOW, 32, [wid])
    dpy.flush()

def set_current_desktop(idx):
    global current_desktop
    current_desktop = idx
    root.change_property(NET_CURRENT_DESKTOP, Xatom.CARDINAL, 32, [idx])
    dpy.flush()

def set_fullscreen(win, enable=True):
    if not win:
        return
    if enable:
        win.change_property(NET_WM_STATE, Xatom.ATOM, 32, [NET_WM_STATE_FULLSCREEN])
    else:
        win.delete_property(NET_WM_STATE)
    dpy.flush()

def set_maximized(win, enable=True):
    if not win:
        return
    if enable:
        win.change_property(NET_WM_STATE, Xatom.ATOM, 32, [NET_WM_STATE_MAXIMIZED_VERT, NET_WM_STATE_MAXIMIZED_HORZ])
    else:
        win.delete_property(NET_WM_STATE)
    dpy.flush()

# -----------------------
# Scratchpads avançados
# -----------------------
def add_scratchpad(win, name, floating=True, geometry=None):
    """Adiciona um scratchpad com propriedades avançadas"""
    scratchpads[name] = {
        "window": win,
        "visible": False,
        "floating": floating,
        "geometry": geometry or {}
    }

def toggle_scratchpad(name):
    """Alterna visibilidade do scratchpad"""
    if name not in scratchpads:
        return
    sp = scratchpads[name]
    if sp["visible"]:
        sp["window"].unmap()
    else:
        wgeom = sp["geometry"]
        if sp["floating"] and wgeom:
            sp["window"].configure(
                x=wgeom.get("x", 100),
                y=wgeom.get("y", 100),
                width=wgeom.get("width", 800),
                height=wgeom.get("height", 600),
                border_width=wgeom.get("border_width", 2),
                stack_mode=X.Above
            )
        sp["window"].map()
    sp["visible"] = not sp["visible"]
    dpy.flush()

def hide_all_scratchpads():
    for sp in scratchpads.values():
        if sp["visible"]:
            sp["window"].unmap()
            sp["visible"] = False
    dpy.flush()

# -----------------------
# Notificações EWMH
# -----------------------
def notify_workspace_change(workspace_name, focused_title, scratchpads_active=None):
    """Atualiza propriedades EWMH simulando notifications"""
    scratchpads_str = ", ".join(scratchpads_active) if scratchpads_active else ""
    message = f"Workspace: {workspace_name} | Focus: {focused_title} | Scratchpads: {scratchpads_str}"
    # Aqui você pode integrar com seu módulo de notifications
    print("[EWMH Notify]", message)
