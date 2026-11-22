"""Interfaz Tkinter de Software FJ: aplicación de escritorio accesible y sin dependencias externas."""
from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Callable

from .excepciones import SoftwareFJError
from .gestor import SistemaGestion
from .modelos import EstadoReserva, TipoServicio
from .registro import LOG_FILE, leer_logs
from .simulaciones import ejecutar_simulaciones, Resultado

BG = "#F5F7FB"
PAPER = "#FFFFFF"
INK = "#243651"
MUTED = "#7B8BA3"
LINE = "#E5EAF2"
BLUE = "#4778BF"
BLUE_HOVER = "#3866A9"
PALE_BLUE = "#EAF1FB"
NAVY = "#263D61"
SOFT_NAVY = "#314D77"
GREEN = "#258F79"
PALE_GREEN = "#E7F5F0"
YELLOW = "#BD8C31"
PALE_YELLOW = "#FFF5DE"
RED = "#B85B68"
PALE_RED = "#FBEDEF"
FONT = "Segoe UI"


def etiqueta(parent, text: str, size: int = 11, color: str = INK,
             bold: bool = False, bg: str | None = None, **kwargs) -> tk.Label:
    return tk.Label(parent, text=text, font=(FONT, size, "bold" if bold else "normal"),
                    fg=color, bg=bg or parent.cget("bg"), **kwargs)


def formato_pesos(valor: object) -> str:
    try:
        return "$" + f"{Decimal(str(valor)):,.0f}".replace(",", ".")
    except Exception:
        return "$0"


def rect_redondeado(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int,
                     radio: int, color: str, borde: str | None = None):
    """Figura redondeada para controles personalizados sin bibliotecas de terceros."""
    r = min(radio, (x2 - x1) // 2, (y2 - y1) // 2)
    pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2,
           x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
    return canvas.create_polygon(pts, smooth=True, splinesteps=16,
                                 fill=color, outline=borde or color, width=1)


class Boton(tk.Canvas):
    """Botón con bordes suaves y cambios de color al pasar el puntero."""

    def __init__(self, parent, text: str, command: Callable[[], None],
                 variant: str = "primary", width: int | None = None,
                 height: int = 39, **kwargs):
        self.variant = variant
        self.colores = {
            "primary": (BLUE, BLUE_HOVER, PAPER, BLUE),
            "secondary": (PALE_BLUE, "#DCE9FA", BLUE_HOVER, PALE_BLUE),
            "ghost": (PAPER, BG, INK, LINE),
            "green": (PALE_GREEN, "#D8EDE6", GREEN, PALE_GREEN),
            "danger": (PALE_RED, "#F7DFE4", RED, PALE_RED),
            "navy": (PAPER, PALE_BLUE, NAVY, PAPER),
        }[variant]
        w = width or max(104, int(len(text) * 7.5 + 34))
        super().__init__(parent, width=w, height=height, highlightthickness=0,
                         bd=0, bg=parent.cget("bg"), cursor="hand2", **kwargs)
        self.command = command
        self.w = w
        self.h = height
        self.rect = rect_redondeado(self, 1, 1, w-2, height-2, 10, self.colores[0], self.colores[3])
        self.title = self.create_text(w / 2, height / 2, text=text,
                                      font=(FONT, 10, "bold"), fill=self.colores[2])
        self.bind("<Enter>", lambda _e: self.itemconfigure(self.rect, fill=self.colores[1]))
        self.bind("<Leave>", lambda _e: self.itemconfigure(self.rect, fill=self.colores[0]))
        self.bind("<Button-1>", lambda _e: self.command())
        self.bind("<Return>", lambda _e: self.command())


class Formulario(tk.Toplevel):
    """Formulario modal reutilizable. Soporta campos, selectores y casillas."""

    def __init__(self, app: "AplicacionFJ", titulo: str, subtitulo: str,
                 campos: list[dict], guardar: Callable[[dict], None],
                 columnas: int = 1, ancho: int = 570):
        super().__init__(app.root)
        self.app = app
        self.guardar_callback = guardar
        self.vars: dict[str, tk.Variable] = {}
        self.title(titulo + " | Software FJ")
        self.configure(bg=BG)
        self.resizable(False, False)
        ancho = max(ancho, 670 if columnas == 2 else 530)
        filas = (len(campos) + columnas - 1) // columnas
        alto = 238 + filas * 91
        alto = max(370, min(740, alto))
        self.geometry(f"{ancho}x{alto}")
        self.transient(app.root)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _e: self.destroy())

        container = tk.Frame(self, bg=PAPER, highlightbackground=LINE, highlightthickness=1)
        container.pack(fill="both", expand=True, padx=19, pady=19)
        top = tk.Frame(container, bg=PAPER)
        top.pack(fill="x", padx=27, pady=(24, 0))
        etiqueta(top, titulo, 19, INK, True).pack(anchor="w")
        etiqueta(top, subtitulo, 10, MUTED, wraplength=ancho-110,
                 justify="left").pack(anchor="w", pady=(6, 0))
        sep = tk.Frame(container, bg=LINE, height=1)
        sep.pack(fill="x", pady=(20, 12), padx=27)

        body = tk.Frame(container, bg=PAPER)
        body.pack(fill="both", expand=True, padx=27)
        for col in range(columnas):
            body.grid_columnconfigure(col, weight=1, uniform="campos")
        for i, campo in enumerate(campos):
            llave = campo["key"]
            marco = tk.Frame(body, bg=PAPER)
            marco.grid(row=i//columnas, column=i % columnas, sticky="ew",
                       padx=(0, 14) if i % columnas == 0 and columnas > 1 else (0, 0), pady=(0, 14))
            etiqueta(marco, campo["label"], 10, INK, True).pack(anchor="w", pady=(0, 6))
            modo = campo.get("type", "text")
            if modo == "check":
                v = tk.BooleanVar(value=campo.get("value", False))
                c = tk.Checkbutton(marco, text=campo.get("help", "Activado"), variable=v,
                                   bg=PAPER, fg=INK, activebackground=PAPER,
                                   font=(FONT, 10), selectcolor=PAPER)
                c.pack(anchor="w", pady=7)
            elif modo == "combo":
                v = tk.StringVar(value=campo.get("value", ""))
                values = campo.get("options", [])
                c = ttk.Combobox(marco, textvariable=v, state="readonly",
                                 values=values, font=(FONT, 10), height=10)
                c.pack(fill="x", ipady=6)
                if not v.get() and values:
                    c.current(0)
            else:
                v = tk.StringVar(value=str(campo.get("value", "")))
                c = tk.Entry(marco, textvariable=v, font=(FONT, 10),
                             bg=PAPER, fg=INK, relief="flat", bd=0,
                             highlightthickness=1, highlightbackground=LINE,
                             highlightcolor=BLUE, insertbackground=INK)
                c.pack(fill="x", ipady=9, ipadx=11)
                if modo == "readonly":
                    c.configure(state="readonly", readonlybackground=BG)
            self.vars[llave] = v
            if i == 0 and modo == "text":
                self.after(100, c.focus_set)
        if campos and any(c.get("help") and c.get("type") != "check" for c in campos):
            etiqueta(container, "* Los cambios se validan antes de guardarse.", 9, MUTED).pack(
                anchor="w", padx=27, pady=(2, 4))
        footer = tk.Frame(container, bg=PAPER)
        footer.pack(fill="x", padx=27, pady=(13, 23))
        Boton(footer, "Guardar cambios", self._guardar, width=151).pack(side="right")
        Boton(footer, "Cancelar", self.destroy, variant="ghost", width=102).pack(side="right", padx=(0, 9))
        self.update_idletasks()
        x = app.root.winfo_rootx() + (app.root.winfo_width() - ancho) // 2
        y = app.root.winfo_rooty() + max(16, (app.root.winfo_height() - alto) // 2)
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.grab_set()

    def _guardar(self) -> None:
        datos = {clave: v.get() for clave, v in self.vars.items()}
        try:
            self.guardar_callback(datos)
        except SoftwareFJError as exc:
            messagebox.showerror("Revisa los datos", str(exc), parent=self)
            return
        except Exception as exc:
            self.app.sistema.logger.exception("Fallo inesperado al guardar formulario")
            messagebox.showerror("No fue posible guardar", f"Ocurrió un error inesperado: {exc}", parent=self)
            return
        self.destroy()
        self.app.renderizar()
        self.app.toast("Información guardada correctamente")


class AplicacionFJ:
    """Controlador de pantallas y formularios de la aplicación."""

    PAGINAS = [
        ("inicio", "▦", "Inicio", "Resumen y actividad de la sesión"),
        ("clientes", "◉", "Clientes", "Registro y administración de clientes"),
        ("servicios", "▣", "Servicios", "Catálogo, precios y disponibilidad"),
        ("reservas", "▤", "Reservas", "Solicitudes, horarios y seguimiento"),
        ("simulaciones", "✓", "Simulaciones", "Validación integral y pruebas de errores"),
        ("registros", "≡", "Registros", "Historial técnico de eventos y errores"),
    ]

    def __init__(self, root: tk.Tk):
        self.root = root
        self.sistema = SistemaGestion(datos_iniciales=True)
        self.pagina = "inicio"
        self.resultados_sim: list[Resultado] = []
        self.nav: dict[str, tuple[tk.Frame, tk.Label, tk.Frame]] = {}
        self.toast_label: tk.Label | None = None
        self.toast_after = None
        self.root.title("Software FJ | Sistema de Gestión")
        self.root.geometry("1240x790")
        self.root.minsize(1020, 650)
        self.root.configure(bg=BG)
        self._estilos()
        self._estructura()
        self.navegar("inicio")
        self.root.bind("<F5>", lambda _e: self.renderizar())
        self.root.bind("<Control-n>", lambda _e: self.accion_nuevo())
        for i, (codigo, *_) in enumerate(self.PAGINAS, start=1):
            self.root.bind(f"<Control-Key-{i}>", lambda _e, p=codigo: self.navegar(p))

    def _estilos(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("FJ.Treeview", background=PAPER, foreground=INK,
                        rowheight=41, fieldbackground=PAPER, borderwidth=0,
                        font=(FONT, 10))
        style.map("FJ.Treeview", background=[("selected", PALE_BLUE)],
                  foreground=[("selected", NAVY)])
        style.configure("FJ.Treeview.Heading", background=BG, foreground=MUTED,
                        relief="flat", borderwidth=0, padding=(10, 12),
                        font=(FONT, 9, "bold"))
        style.map("FJ.Treeview.Heading", background=[("active", PALE_BLUE)])
        style.configure("FJ.TCombobox", bordercolor=LINE, padding=7)

    def _estructura(self):
        self.sidebar = tk.Frame(self.root, bg=NAVY, width=237)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg=NAVY)
        brand.pack(fill="x", padx=23, pady=(30, 38))
        icono = tk.Canvas(brand, width=45, height=45, bg=NAVY, highlightthickness=0)
        icono.pack(side="left", padx=(0, 11))
        rect_redondeado(icono, 1, 1, 44, 44, 12, "#E0EFFF")
        icono.create_text(22, 23, text="FJ", font=(FONT, 15, "bold"), fill=NAVY)
        namebox = tk.Frame(brand, bg=NAVY)
        namebox.pack(side="left", anchor="center")
        etiqueta(namebox, "SOFTWARE FJ", 12, PAPER, True).pack(anchor="w")
        etiqueta(namebox, "GESTIÓN INTEGRAL", 8, "#9DB5D7", True).pack(anchor="w", pady=(4, 0))
        etiqueta(self.sidebar, "ESPACIO DE TRABAJO", 9, "#91ABCE", True).pack(anchor="w", padx=25, pady=(0, 12))
        for codigo, icono, nombre, _ in self.PAGINAS:
            container = tk.Frame(self.sidebar, bg=NAVY, height=49, cursor="hand2")
            container.pack(fill="x", padx=(13, 13), pady=3)
            container.pack_propagate(False)
            rail = tk.Frame(container, bg=NAVY, width=3)
            rail.pack(side="left", fill="y")
            inner = tk.Frame(container, bg=NAVY)
            inner.pack(side="left", fill="both", expand=True)
            label = etiqueta(inner, f"{icono}    {nombre}", 11, "#C8D7EB", bg=NAVY, anchor="w")
            label.pack(fill="both", expand=True, padx=(17, 0))
            self.nav[codigo] = (container, label, rail)
            for widget in (container, inner, label):
                widget.bind("<Button-1>", lambda _e, p=codigo: self.navegar(p))
                widget.bind("<Enter>", lambda _e, p=codigo: self._nav_hover(p, True))
                widget.bind("<Leave>", lambda _e, p=codigo: self._nav_hover(p, False))

        tk.Frame(self.sidebar, bg=NAVY).pack(fill="both", expand=True)
        pie = tk.Frame(self.sidebar, bg=SOFT_NAVY)
        pie.pack(fill="x", padx=18, pady=(10, 22))
        etiqueta(pie, "●  SESIÓN EN MEMORIA", 9, "#D2E9EF", True, bg=SOFT_NAVY).pack(
            anchor="w", padx=14, pady=(13, 5))
        etiqueta(pie, "Los datos no se almacenan\nen una base de datos.", 9,
                 "#B4C8E0", bg=SOFT_NAVY, justify="left").pack(anchor="w", padx=14, pady=(0, 14))

        self.right = tk.Frame(self.root, bg=BG)
        self.right.pack(side="left", fill="both", expand=True)
        self.header = tk.Frame(self.right, bg=PAPER, height=93)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        headleft = tk.Frame(self.header, bg=PAPER)
        headleft.pack(side="left", padx=39, pady=19)
        self.titulo_header = etiqueta(headleft, "", 19, INK, True)
        self.titulo_header.pack(anchor="w")
        self.subtitulo_header = etiqueta(headleft, "", 10, MUTED)
        self.subtitulo_header.pack(anchor="w", pady=(4, 0))
        status = tk.Frame(self.header, bg=PALE_GREEN)
        status.pack(side="right", padx=37, pady=30)
        etiqueta(status, "●  Sistema activo", 10, GREEN, True, bg=PALE_GREEN).pack(padx=15, pady=8)
        tk.Frame(self.right, bg=LINE, height=1).pack(fill="x")
        holder = tk.Frame(self.right, bg=BG)
        holder.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(holder, bg=BG, borderwidth=0, highlightthickness=0)
        self.scroll = ttk.Scrollbar(holder, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")
        self.content = tk.Frame(self.canvas, bg=BG)
        self.scroll_window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.scroll_window, width=e.width))
        self.root.bind_all("<MouseWheel>", self._wheel)

    def _wheel(self, event):
        if self.root.focus_get() is None or not self.root.winfo_exists():
            return
        # No desplazar el contenido oculto cuando un formulario modal tiene el foco.
        if self.root.grab_current() is not None:
            return
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _nav_hover(self, codigo: str, entrado: bool) -> None:
        if codigo == self.pagina:
            return
        container, label, _rail = self.nav[codigo]
        color = SOFT_NAVY if entrado else NAVY
        container.configure(bg=color)
        label.configure(bg=color)
        label.master.configure(bg=color)

    def navegar(self, pagina: str) -> None:
        self.pagina = pagina
        for codigo, (marco, texto, barra) in self.nav.items():
            activo = codigo == pagina
            color = SOFT_NAVY if activo else NAVY
            marco.configure(bg=color)
            texto.configure(bg=color, fg=PAPER if activo else "#C8D7EB",
                            font=(FONT, 11, "bold" if activo else "normal"))
            texto.master.configure(bg=color)
            barra.configure(bg="#91C3EE" if activo else NAVY)
        entrada = next(p for p in self.PAGINAS if p[0] == pagina)
        self.titulo_header.configure(text=entrada[2])
        self.subtitulo_header.configure(text=entrada[3])
        self.renderizar()

    def renderizar(self):
        for child in self.content.winfo_children():
            child.destroy()
        area = tk.Frame(self.content, bg=BG)
        area.pack(fill="both", expand=True, padx=34, pady=(29, 32))
        paginas = {
            "inicio": self.pantalla_inicio,
            "clientes": self.pantalla_clientes,
            "servicios": self.pantalla_servicios,
            "reservas": self.pantalla_reservas,
            "simulaciones": self.pantalla_simulaciones,
            "registros": self.pantalla_registros,
        }
        paginas[self.pagina](area)
        self.canvas.yview_moveto(0)

    def tarjeta(self, parent, padding: int = 22) -> tk.Frame:
        out = tk.Frame(parent, bg=PAPER, highlightthickness=1, highlightbackground=LINE)
        return out

    def cabecera_seccion(self, parent, titulo: str, subtitulo: str = "",
                         acciones: list[tuple[str, Callable, str]] | None = None):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0, 15))
        left = tk.Frame(row, bg=BG)
        left.pack(side="left")
        etiqueta(left, titulo, 15, INK, True).pack(anchor="w")
        if subtitulo:
            etiqueta(left, subtitulo, 10, MUTED).pack(anchor="w", pady=(4, 0))
        for texto, accion, variante in reversed(acciones or []):
            Boton(row, texto, accion, variante, height=36).pack(side="right", padx=(8, 0))
        return row

    def texto_vacio(self, parent, titulo: str, detalle: str, accion: tuple[str, Callable] | None = None):
        frame = tk.Frame(parent, bg=PAPER)
        frame.pack(fill="both", expand=True, padx=20, pady=42)
        etiqueta(frame, "◌", 32, BLUE).pack(pady=(0, 12))
        etiqueta(frame, titulo, 13, INK, True).pack()
        etiqueta(frame, detalle, 10, MUTED, justify="center", wraplength=450).pack(pady=(7, 16))
        if accion:
            Boton(frame, accion[0], accion[1], "secondary").pack()

    def tabla(self, parent, columnas: list[tuple[str, str, int]], alto: int = 10,
              doble_click: Callable | None = None) -> ttk.Treeview:
        marco = tk.Frame(parent, bg=PAPER)
        marco.pack(fill="both", expand=True, padx=22, pady=(8, 22))
        nombres = [c[0] for c in columnas]
        tree = ttk.Treeview(marco, columns=nombres, show="headings", height=alto,
                            selectmode="browse", style="FJ.Treeview")
        for clave, titulo, anchura in columnas:
            tree.heading(clave, text=titulo, anchor="w")
            tree.column(clave, width=anchura, minwidth=70, stretch=True, anchor="w")
        sb = ttk.Scrollbar(marco, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        if doble_click:
            tree.bind("<Double-1>", lambda _e: doble_click())
        tree.tag_configure("alterno", background="#F9FBFE")
        tree.tag_configure("normal", background=PAPER)
        return tree

    def _searchbox(self, parent, variable: tk.StringVar, placeholder: str = "Buscar..."):
        wrapper = tk.Frame(parent, bg=PAPER, highlightthickness=1, highlightbackground=LINE)
        etiqueta(wrapper, "⌕", 16, MUTED, bg=PAPER).pack(side="left", padx=(12, 5), pady=2)
        entry = tk.Entry(wrapper, textvariable=variable, relief="flat", bg=PAPER,
                         fg=INK, insertbackground=INK, font=(FONT, 10), borderwidth=0)
        entry.pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 9))
        # El texto orientativo no se introduce como contenido, evitando búsquedas accidentales.
        entry.configure(highlightthickness=0)
        return wrapper

    def toast(self, mensaje: str, error: bool = False):
        if self.toast_label and self.toast_label.winfo_exists():
            self.toast_label.destroy()
        self.toast_label = etiqueta(self.root, ("!  " if error else "✓  ") + mensaje,
                                   10, PAPER, True, bg=RED if error else GREEN,
                                   padx=20, pady=12)
        self.toast_label.place(relx=1, rely=1, x=-28, y=-25, anchor="se")
        if self.toast_after:
            self.root.after_cancel(self.toast_after)
        self.toast_after = self.root.after(3500, self._quitar_toast)

    def _quitar_toast(self):
        if self.toast_label and self.toast_label.winfo_exists():
            self.toast_label.destroy()
        self.toast_label = None

    def accion_nuevo(self):
        if self.pagina == "clientes":
            self.form_cliente()
        elif self.pagina == "servicios":
            self.form_servicio()
        elif self.pagina == "reservas":
            self.form_reserva()

    # ── Pantalla principal ──────────────────────────────────────────────────────
    def pantalla_inicio(self, parent):
        hero = tk.Frame(parent, bg=NAVY, height=170)
        hero.pack(fill="x", pady=(0, 23))
        hero.pack_propagate(False)
        parte = tk.Frame(hero, bg=NAVY)
        parte.pack(side="left", fill="both", expand=True, padx=(31, 0), pady=24)
        etiqueta(parte, "PANEL DE OPERACIONES", 9, "#A5C6F0", True, bg=NAVY).pack(anchor="w")
        etiqueta(parte, "Organiza tus servicios en un solo lugar.", 18, PAPER, True,
                 bg=NAVY).pack(anchor="w", pady=(8, 6))
        etiqueta(parte, "Clientes, reservas y disponibilidad con seguimiento en tiempo real.",
                 10, "#D1E1F4", bg=NAVY).pack(anchor="w")
        etiqueta(parte, "Datos de esta sesión · Sin base de datos", 9, "#B5CBE5", bg=NAVY).pack(
            anchor="w", pady=(14, 0))
        deco = tk.Canvas(hero, width=158, height=170, bg=NAVY, highlightthickness=0)
        deco.pack(side="right", padx=(0, 14))
        for x, y, r, color in [(91, 75, 60, "#315078"), (91, 75, 42, "#3C608D"),
                               (91, 75, 21, "#AAC6E6")]:
            deco.create_oval(x-r, y-r, x+r, y+r, fill=color, outline=color)
        deco.create_text(91, 76, text="FJ", font=(FONT, 17, "bold"), fill=NAVY)

        datos = self.sistema.resumen()
        metrics = [("Clientes", datos["clientes"], "◉", PALE_BLUE, BLUE),
                   ("Servicios activos", sum(s.disponible for s in self.sistema.servicios.values()), "▣", PALE_GREEN, GREEN),
                   ("Confirmadas", datos["confirmadas"], "✓", PALE_GREEN, GREEN),
                   ("Pendientes", datos["pendientes"], "◷", PALE_YELLOW, YELLOW)]
        fila = tk.Frame(parent, bg=BG)
        fila.pack(fill="x", pady=(0, 26))
        for i, (titulo, numero, simbolo, pale, fuerte) in enumerate(metrics):
            frame = self.tarjeta(fila)
            frame.pack(side="left", expand=True, fill="both", padx=(0, 10) if i < 3 else 0)
            top = tk.Frame(frame, bg=PAPER)
            top.pack(fill="x", padx=19, pady=(16, 8))
            etiqueta(top, titulo, 10, MUTED).pack(side="left")
            icon = tk.Frame(top, bg=pale)
            icon.pack(side="right")
            etiqueta(icon, simbolo, 12, fuerte, True, bg=pale).pack(padx=10, pady=6)
            etiqueta(frame, str(numero), 26, INK, True).pack(anchor="w", padx=20, pady=(0, 17))

        self.cabecera_seccion(parent, "Acciones rápidas", "Empieza por la operación que necesitas realizar.")
        shortcuts = tk.Frame(parent, bg=BG)
        shortcuts.pack(fill="x", pady=(0, 27))
        for i, (icono, title, summary, act) in enumerate([
            ("+", "Nuevo cliente", "Registra datos de contacto", self.form_cliente),
            ("+", "Nuevo servicio", "Añade una opción al catálogo", self.form_servicio),
            ("+", "Nueva reserva", "Programa una solicitud", self.form_reserva),
        ]):
            frame = self.tarjeta(shortcuts)
            frame.pack(side="left", fill="both", expand=True, padx=(0, 11) if i < 2 else 0)
            etiqueta(frame, title, 12, INK, True).pack(anchor="w", padx=18, pady=(15, 3))
            etiqueta(frame, summary, 9, MUTED).pack(anchor="w", padx=18, pady=(0, 11))
            Boton(frame, "Abrir  →", act, "secondary", width=106, height=32).pack(
                anchor="w", padx=17, pady=(0, 15))

        sections = tk.Frame(parent, bg=BG)
        sections.pack(fill="both", expand=True)
        left = self.tarjeta(sections)
        left.pack(side="left", fill="both", expand=True, padx=(0, 14))
        etiqueta(left, "Actividad reciente", 13, INK, True).pack(anchor="w", padx=22, pady=(19, 3))
        etiqueta(left, "Últimas acciones realizadas en el sistema", 9, MUTED).pack(
            anchor="w", padx=22, pady=(0, 12))
        eventos = self.sistema.eventos[:6]
        if not eventos:
            etiqueta(left, "Los movimientos de la sesión aparecerán aquí.", 10, MUTED).pack(
                anchor="w", padx=22, pady=24)
        else:
            for hora, evento in eventos:
                line = tk.Frame(left, bg=PAPER)
                line.pack(fill="x", padx=22, pady=8)
                etiqueta(line, hora, 9, MUTED).pack(side="left", padx=(0, 16))
                etiqueta(line, evento[:65] + ("…" if len(evento) > 65 else ""),
                         9, INK).pack(side="left", anchor="w")
        tk.Frame(left, bg=PAPER).pack(pady=11)
        right = self.tarjeta(sections)
        right.pack(side="left", fill="both", expand=False)
        etiqueta(right, "Flujo recomendado", 13, INK, True).pack(anchor="w", padx=20, pady=(19, 15))
        for i, (nombre, detalle) in enumerate([
            ("Registrar cliente", "Identifica a quien solicita el servicio"),
            ("Elegir servicio", "Revisa las tarifas y la disponibilidad"),
            ("Crear reserva", "Indica fecha, hora y duración"),
            ("Confirmar", "Valida capacidad y calcula el total"),
        ], start=1):
            item = tk.Frame(right, bg=PAPER)
            item.pack(fill="x", padx=19, pady=(0, 14))
            bubble = tk.Frame(item, bg=PALE_BLUE)
            bubble.pack(side="left", padx=(0, 11), anchor="n")
            etiqueta(bubble, str(i), 10, BLUE, True, bg=PALE_BLUE).pack(padx=9, pady=7)
            rest = tk.Frame(item, bg=PAPER)
            rest.pack(side="left", padx=(0, 20))
            etiqueta(rest, nombre, 10, INK, True).pack(anchor="w")
            etiqueta(rest, detalle, 9, MUTED).pack(anchor="w", pady=(3, 0))

    # ── Clientes ────────────────────────────────────────────────────────────────
    def pantalla_clientes(self, parent):
        self.cabecera_seccion(parent, "Directorio de clientes",
                             "Gestiona información de contacto y registros únicos.",
                             [("+  Registrar cliente", self.form_cliente, "primary")])
        card = self.tarjeta(parent)
        card.pack(fill="both", expand=True)
        tools = tk.Frame(card, bg=PAPER)
        tools.pack(fill="x", padx=22, pady=(21, 9))
        self.buscar_cliente = tk.StringVar()
        self._searchbox(tools, self.buscar_cliente).pack(side="left", fill="x", expand=True)
        etiqueta(tools, f"{len(self.sistema.clientes)} registrados", 10, MUTED).pack(
            side="right", padx=(20, 0))
        self.tabla_clientes = self.tabla(card, [
            ("id", "IDENTIFICADOR", 125), ("nombre", "NOMBRE COMPLETO", 185),
            ("correo", "CORREO ELECTRÓNICO", 245), ("telefono", "TELÉFONO", 144),
        ], alto=8, doble_click=self.editar_cliente)
        self.buscar_cliente.trace_add("write", lambda *_: self.actualizar_tabla_clientes())
        self.actualizar_tabla_clientes()
        actions = tk.Frame(card, bg=PAPER)
        actions.pack(fill="x", padx=21, pady=(0, 20))
        Boton(actions, "Editar seleccionado", self.editar_cliente, "secondary").pack(side="left")
        Boton(actions, "Eliminar seleccionado", self.borrar_cliente, "danger").pack(
            side="left", padx=(9, 0))
        etiqueta(actions, "Doble clic en una fila para editar.", 9, MUTED).pack(side="right")

    def actualizar_tabla_clientes(self):
        if not self.tabla_clientes.winfo_exists():
            return
        self.tabla_clientes.delete(*self.tabla_clientes.get_children())
        q = self.buscar_cliente.get().strip().casefold()
        for i, c in enumerate(self.sistema.listar_clientes()):
            if q and q not in f"{c.nombre} {c.correo} {c.telefono} {c.id}".casefold():
                continue
            self.tabla_clientes.insert("", "end", iid=c.id,
                                       values=(c.id, c.nombre, c.correo, c.telefono),
                                       tags=("alterno" if i % 2 else "normal",))

    def seleccionado(self, tabla: ttk.Treeview, tipo: str) -> str | None:
        elegido = tabla.selection()
        if not elegido:
            messagebox.showinfo("Selecciona un elemento", f"Primero selecciona un {tipo} de la tabla.", parent=self.root)
            return None
        return elegido[0]

    def form_cliente(self, cliente_id: str | None = None):
        cliente = self.sistema.clientes.get(cliente_id) if cliente_id else None
        def guardar(v):
            if cliente:
                self.sistema.actualizar_cliente(cliente.id, v["nombre"], v["correo"], v["telefono"])
            else:
                self.sistema.registrar_cliente(v["nombre"], v["correo"], v["telefono"])
        Formulario(self, "Editar cliente" if cliente else "Nuevo cliente",
                   "Completa los datos de contacto del cliente.", [
                       {"key": "nombre", "label": "Nombre completo", "value": cliente.nombre if cliente else ""},
                       {"key": "correo", "label": "Correo electrónico", "value": cliente.correo if cliente else ""},
                       {"key": "telefono", "label": "Teléfono", "value": cliente.telefono if cliente else ""},
                   ], guardar)

    def editar_cliente(self):
        id_ = self.seleccionado(self.tabla_clientes, "cliente")
        if id_:
            self.form_cliente(id_)

    def borrar_cliente(self):
        id_ = self.seleccionado(self.tabla_clientes, "cliente")
        if not id_:
            return
        c = self.sistema.obtener_cliente(id_)
        if messagebox.askyesno("Confirmar eliminación", f"¿Quieres eliminar a {c.nombre}?", parent=self.root):
            try:
                self.sistema.eliminar_cliente(id_)
            except SoftwareFJError as exc:
                messagebox.showerror("No es posible eliminar", str(exc), parent=self.root)
                return
            self.renderizar()
            self.toast("Cliente eliminado")

    # ── Servicios ───────────────────────────────────────────────────────────────
    def pantalla_servicios(self, parent):
        self.cabecera_seccion(parent, "Catálogo de servicios",
                             "Configura salas, equipos y asesorías con tarifas claras.",
                             [("+  Nuevo servicio", self.form_servicio, "primary")])
        fila = tk.Frame(parent, bg=BG)
        fila.pack(fill="x", pady=(0, 21))
        items = [("Salas", TipoServicio.SALA, "Espacios y reuniones", PALE_BLUE, BLUE),
                 ("Equipos", TipoServicio.EQUIPO, "Alquiler por unidades", PALE_YELLOW, YELLOW),
                 ("Asesorías", TipoServicio.ASESORIA, "Soporte especializado", PALE_GREEN, GREEN)]
        for i, (nombre, tipo, descripcion, pale, color) in enumerate(items):
            card = self.tarjeta(fila)
            card.pack(side="left", fill="both", expand=True, padx=(0, 10) if i < 2 else 0)
            etiqueta(card, nombre.upper(), 9, color, True).pack(anchor="w", padx=17, pady=(16, 4))
            cantidad = sum(s.tipo == tipo for s in self.sistema.servicios.values())
            etiqueta(card, str(cantidad) + "  disponibles en catálogo", 14, INK, True).pack(
                anchor="w", padx=17, pady=(0, 5))
            etiqueta(card, descripcion, 9, MUTED).pack(anchor="w", padx=17, pady=(0, 17))
        card = self.tarjeta(parent)
        card.pack(fill="both", expand=True)
        barra = tk.Frame(card, bg=PAPER)
        barra.pack(fill="x", padx=22, pady=(20, 10))
        self.buscar_servicio = tk.StringVar()
        self._searchbox(barra, self.buscar_servicio).pack(side="left", fill="x", expand=True)
        etiqueta(barra, "Tarifas expresadas en COP/hora", 9, MUTED).pack(side="right", padx=(14, 0))
        self.tabla_servicios = self.tabla(card, [
            ("nombre", "SERVICIO", 210), ("tipo", "TIPO", 115),
            ("tarifa", "TARIFA", 100), ("capacidad", "CAPACIDAD", 110),
            ("estado", "ESTADO", 100), ("id", "CÓDIGO", 125),
        ], alto=8, doble_click=self.editar_servicio)
        self.buscar_servicio.trace_add("write", lambda *_: self.actualizar_tabla_servicios())
        self.actualizar_tabla_servicios()
        acciones = tk.Frame(card, bg=PAPER)
        acciones.pack(fill="x", padx=22, pady=(0, 20))
        Boton(acciones, "Editar", self.editar_servicio, "secondary", width=92).pack(side="left")
        Boton(acciones, "Activar / desactivar", self.toggle_servicio, "green", width=164).pack(
            side="left", padx=(8, 0))
        Boton(acciones, "Eliminar", self.borrar_servicio, "danger", width=98).pack(
            side="left", padx=(8, 0))

    def actualizar_tabla_servicios(self):
        if not self.tabla_servicios.winfo_exists():
            return
        self.tabla_servicios.delete(*self.tabla_servicios.get_children())
        q = self.buscar_servicio.get().strip().casefold()
        for i, s in enumerate(self.sistema.listar_servicios()):
            if q and q not in f"{s.nombre} {s.tipo.value} {s.detalle} {s.id}".casefold():
                continue
            self.tabla_servicios.insert("", "end", iid=s.id,
                  values=(s.nombre, s.tipo.value, formato_pesos(s.tarifa),
                          f"{s.capacidad} {s.unidad}", "Disponible" if s.disponible else "Inactivo", s.id),
                  tags=("alterno" if i % 2 else "normal",))

    def form_servicio(self, id_servicio: str | None = None):
        servicio = self.sistema.servicios.get(id_servicio) if id_servicio else None
        def guardar(v):
            if servicio:
                self.sistema.actualizar_servicio(servicio.id, v["nombre"], v["tarifa"], v["capacidad"], v["detalle"])
            else:
                self.sistema.agregar_servicio(v["tipo"], v["nombre"], v["tarifa"], v["capacidad"], v["detalle"])
        Formulario(self, "Editar servicio" if servicio else "Nuevo servicio",
                   "Indica el tipo de servicio y sus condiciones de uso.", [
                       {"key": "tipo", "label": "Categoría", "type": "readonly" if servicio else "combo",
                        "options": [t.value for t in TipoServicio], "value": servicio.tipo.value if servicio else "Sala"},
                       {"key": "nombre", "label": "Nombre del servicio", "value": servicio.nombre if servicio else ""},
                       {"key": "tarifa", "label": "Tarifa COP por hora", "value": str(servicio.tarifa) if servicio else ""},
                       {"key": "capacidad", "label": "Capacidad máxima", "value": str(servicio.capacidad) if servicio else ""},
                       {"key": "detalle", "label": "Descripción o características", "value": servicio.detalle if servicio else ""},
                   ], guardar, columnas=2, ancho=720)

    def editar_servicio(self):
        id_ = self.seleccionado(self.tabla_servicios, "servicio")
        if id_:
            self.form_servicio(id_)

    def toggle_servicio(self):
        id_ = self.seleccionado(self.tabla_servicios, "servicio")
        if id_:
            s = self.sistema.cambiar_disponibilidad(id_)
            self.renderizar()
            self.toast("Servicio habilitado" if s.disponible else "Servicio deshabilitado")

    def borrar_servicio(self):
        id_ = self.seleccionado(self.tabla_servicios, "servicio")
        if not id_:
            return
        s = self.sistema.obtener_servicio(id_)
        if messagebox.askyesno("Confirmar eliminación", f"¿Eliminar «{s.nombre}» del catálogo?", parent=self.root):
            try:
                self.sistema.eliminar_servicio(id_)
            except SoftwareFJError as exc:
                messagebox.showerror("No es posible eliminar", str(exc), parent=self.root)
                return
            self.renderizar()
            self.toast("Servicio eliminado")

    # ── Reservas ────────────────────────────────────────────────────────────────
    def pantalla_reservas(self, parent):
        self.cabecera_seccion(parent, "Agenda de reservas",
                             "Crea solicitudes y confirma según la capacidad disponible.",
                             [("+  Nueva reserva", self.form_reserva, "primary")])
        resumen = self.sistema.resumen()
        contadores = tk.Frame(parent, bg=BG)
        contadores.pack(fill="x", pady=(0, 20))
        for i, (nombre, numero, color, pale) in enumerate([
            ("Pendientes", resumen["pendientes"], YELLOW, PALE_YELLOW),
            ("Confirmadas", resumen["confirmadas"], GREEN, PALE_GREEN),
            ("Canceladas", resumen["canceladas"], RED, PALE_RED),
        ]):
            c = tk.Frame(contadores, bg=pale)
            c.pack(side="left", fill="both", expand=True, padx=(0, 10) if i < 2 else 0)
            etiqueta(c, f"{nombre.upper()}    {numero}", 10, color, True, bg=pale).pack(padx=15, pady=15)
        card = self.tarjeta(parent)
        card.pack(fill="both", expand=True)
        barra = tk.Frame(card, bg=PAPER)
        barra.pack(fill="x", padx=22, pady=(20, 10))
        self.buscar_reserva = tk.StringVar()
        self._searchbox(barra, self.buscar_reserva).pack(side="left", fill="x", expand=True)
        self.filtro_reserva = tk.StringVar(value="Todos los estados")
        filtro = ttk.Combobox(barra, state="readonly", textvariable=self.filtro_reserva,
                              values=["Todos los estados"] + [e.value for e in EstadoReserva],
                              width=20, font=(FONT, 10))
        filtro.pack(side="right", padx=(13, 0), ipady=6)
        self.tabla_reservas = self.tabla(card, [
            ("id", "RESERVA", 118), ("cliente", "CLIENTE", 155),
            ("servicio", "SERVICIO", 170), ("fecha", "FECHA Y HORA", 140),
            ("duracion", "DURACIÓN", 90), ("total", "TOTAL", 105),
            ("estado", "ESTADO", 115),
        ], alto=8, doble_click=self.detalle_reserva)
        self.buscar_reserva.trace_add("write", lambda *_: self.actualizar_tabla_reservas())
        self.filtro_reserva.trace_add("write", lambda *_: self.actualizar_tabla_reservas())
        self.actualizar_tabla_reservas()
        acciones = tk.Frame(card, bg=PAPER)
        acciones.pack(fill="x", padx=22, pady=(0, 19))
        Boton(acciones, "Ver detalle", self.detalle_reserva, "secondary", width=111).pack(side="left")
        Boton(acciones, "Confirmar", self.confirmar_reserva, "green", width=116).pack(
            side="left", padx=(9, 0))
        Boton(acciones, "Cancelar reserva", self.cancelar_reserva, "danger", width=139).pack(
            side="left", padx=(9, 0))

    def actualizar_tabla_reservas(self):
        if not self.tabla_reservas.winfo_exists():
            return
        self.tabla_reservas.delete(*self.tabla_reservas.get_children())
        q = self.buscar_reserva.get().strip().casefold()
        estado = self.filtro_reserva.get()
        for i, r in enumerate(self.sistema.listar_reservas()):
            if estado != "Todos los estados" and estado != r.estado.value:
                continue
            if q and q not in f"{r.id} {r.cliente.nombre} {r.servicio.nombre} {r.estado.value}".casefold():
                continue
            total = formato_pesos(r.total) if r.estado == EstadoReserva.CONFIRMADA else "—"
            self.tabla_reservas.insert("", "end", iid=r.id,
                  values=(r.id, r.cliente.nombre, r.servicio.nombre,
                          r.inicio.strftime("%d/%m/%Y  %H:%M"),
                          f"{r.horas:g} h", total, r.estado.value),
                  tags=("alterno" if i % 2 else "normal",))

    def form_reserva(self):
        if not self.sistema.clientes or not self.sistema.servicios:
            paso = "un cliente" if not self.sistema.clientes else "un servicio"
            messagebox.showinfo("Falta información", f"Primero debes registrar {paso} para crear una reserva.",
                                parent=self.root)
            return
        clientes = {f"{c.nombre} · {c.id}": c.id for c in self.sistema.listar_clientes()}
        servicios = {f"{s.nombre} · {s.id}": s.id for s in self.sistema.listar_servicios() if s.disponible}
        if not servicios:
            messagebox.showwarning("Sin servicios disponibles", "Habilita un servicio antes de reservar.", parent=self.root)
            return
        manana = datetime.now() + timedelta(days=1)
        def guardar(v):
            metodo = self.sistema.crear_y_confirmar_reserva if v["confirmar"] else self.sistema.crear_reserva
            metodo(
                clientes[v["cliente"]], servicios[v["servicio"]],
                v["fecha"], v["hora"], v["horas"], v["cantidad"],
                v["descuento"], v["impuesto"]
            )
        Formulario(self, "Programar reserva",
                   "Elige cliente, servicio y horario. La confirmación valida la disponibilidad.", [
                       {"key": "cliente", "label": "Cliente", "type": "combo", "options": list(clientes)},
                       {"key": "servicio", "label": "Servicio", "type": "combo", "options": list(servicios)},
                       {"key": "fecha", "label": "Fecha (AAAA-MM-DD)", "value": manana.strftime("%Y-%m-%d")},
                       {"key": "hora", "label": "Hora (HH:MM)", "value": "10:00"},
                       {"key": "horas", "label": "Duración en horas", "value": "2"},
                       {"key": "cantidad", "label": "Personas / unidades", "value": "1"},
                       {"key": "descuento", "label": "Descuento (%)", "value": "0"},
                       {"key": "impuesto", "label": "Impuesto (%)", "value": "0"},
                       {"key": "confirmar", "label": "Confirmación", "type": "check",
                        "help": "Confirmar inmediatamente", "value": True},
                   ], guardar, columnas=2, ancho=760)

    def detalle_reserva(self):
        id_ = self.seleccionado(self.tabla_reservas, "reserva")
        if not id_:
            return
        r = self.sistema.obtener_reserva(id_)
        box = tk.Toplevel(self.root)
        box.title("Detalle de reserva | Software FJ")
        box.configure(bg=BG)
        box.geometry("530x510")
        box.resizable(False, False)
        box.transient(self.root)
        box.bind("<Escape>", lambda _e: box.destroy())
        card = tk.Frame(box, bg=PAPER, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="both", expand=True, padx=18, pady=18)
        etiqueta(card, "Detalle de la reserva", 18, INK, True).pack(anchor="w", padx=25, pady=(23, 5))
        etiqueta(card, r.id, 10, MUTED).pack(anchor="w", padx=25, pady=(0, 16))
        estado_color = GREEN if r.estado == EstadoReserva.CONFIRMADA else RED if r.estado == EstadoReserva.CANCELADA else YELLOW
        estado_bg = PALE_GREEN if r.estado == EstadoReserva.CONFIRMADA else PALE_RED if r.estado == EstadoReserva.CANCELADA else PALE_YELLOW
        etiqueta(card, "●  " + r.estado.value.upper(), 10, estado_color, True,
                 bg=estado_bg, padx=12, pady=7).pack(anchor="w", padx=25, pady=(0, 13))
        filas = [
            ("Cliente", r.cliente.nombre), ("Servicio", r.servicio.nombre),
            ("Inicio", r.inicio.strftime("%d/%m/%Y a las %H:%M")),
            ("Duración", f"{r.horas:g} horas"),
            ("Personas / unidades", str(r.cantidad)),
            ("Descuento / impuesto", f"{r.descuento}% / {r.impuesto}%"),
            ("Total", formato_pesos(r.total) if r.estado != EstadoReserva.PENDIENTE else "Pendiente de confirmación"),
        ]
        for label, value in filas:
            row = tk.Frame(card, bg=PAPER)
            row.pack(fill="x", padx=26, pady=8)
            etiqueta(row, label, 10, MUTED).pack(side="left")
            etiqueta(row, value, 10, INK, True).pack(side="right")
        Boton(card, "Cerrar", box.destroy, "secondary", width=109).pack(
            side="bottom", anchor="e", padx=25, pady=(10, 20))
        box.grab_set()

    def confirmar_reserva(self):
        id_ = self.seleccionado(self.tabla_reservas, "reserva")
        if not id_:
            return
        try:
            r = self.sistema.confirmar_reserva(id_)
        except SoftwareFJError as exc:
            messagebox.showerror("No fue posible confirmar", str(exc), parent=self.root)
            return
        self.renderizar()
        self.toast(f"Reserva confirmada · {formato_pesos(r.total)}")

    def cancelar_reserva(self):
        id_ = self.seleccionado(self.tabla_reservas, "reserva")
        if not id_:
            return
        if not messagebox.askyesno("Cancelar reserva", "¿Deseas cancelar esta reserva?", parent=self.root):
            return
        try:
            self.sistema.cancelar_reserva(id_)
        except SoftwareFJError as exc:
            messagebox.showerror("No fue posible cancelar", str(exc), parent=self.root)
            return
        self.renderizar()
        self.toast("Reserva cancelada")

    # ── Simulaciones ────────────────────────────────────────────────────────────
    def pantalla_simulaciones(self, parent):
        self.cabecera_seccion(parent, "Centro de pruebas",
              "Ensayos válidos e inválidos para verificar la estabilidad de la aplicación.",
              [("▶  Ejecutar simulaciones", self.correr_simulaciones, "primary")])
        aviso = tk.Frame(parent, bg=PALE_BLUE)
        aviso.pack(fill="x", pady=(0, 20))
        etiqueta(aviso, "ℹ  Las simulaciones usan datos aislados: no cambian tus clientes, servicios ni reservas.",
                 10, BLUE_HOVER, bg=PALE_BLUE).pack(anchor="w", padx=18, pady=15)
        if not self.resultados_sim:
            card = self.tarjeta(parent)
            card.pack(fill="both", expand=True)
            self.texto_vacio(card, "Las simulaciones aún no se han ejecutado",
                             "Inicia las pruebas para comprobar las reglas de negocio y el manejo de errores.",
                             ("Ejecutar ahora", self.correr_simulaciones))
            return
        aprobadas = sum(r.correcto for r in self.resultados_sim)
        fallidas = len(self.resultados_sim) - aprobadas
        barra = tk.Frame(parent, bg=BG)
        barra.pack(fill="x", pady=(0, 19))
        for i, (label, numero, pale, color) in enumerate([
            ("Pruebas ejecutadas", len(self.resultados_sim), PALE_BLUE, BLUE),
            ("Resultados aprobados", aprobadas, PALE_GREEN, GREEN),
            ("Fallos inesperados", fallidas, PALE_RED if fallidas else PALE_YELLOW, RED if fallidas else YELLOW),
        ]):
            card = tk.Frame(barra, bg=pale)
            card.pack(side="left", expand=True, fill="x", padx=(0, 10) if i < 2 else 0)
            etiqueta(card, label.upper(), 9, color, True, bg=pale).pack(anchor="w", padx=16, pady=(13, 3))
            etiqueta(card, str(numero), 20, INK, True, bg=pale).pack(anchor="w", padx=16, pady=(0, 12))
        card = self.tarjeta(parent)
        card.pack(fill="both", expand=True)
        etiqueta(card, "Detalle de escenarios", 13, INK, True).pack(anchor="w", padx=22, pady=(18, 6))
        tree = self.tabla(card, [("num", "N.º", 60), ("escenario", "ESCENARIO", 355),
                                 ("tipo", "TIPO", 95), ("resultado", "RESULTADO", 108),
                                 ("detalle", "OBSERVACIÓN", 280)], alto=8)
        def ver_observacion(_event=None):
            indices = tree.selection()
            if not indices:
                return
            r = self.resultados_sim[int(indices[0])]
            messagebox.showinfo(
                f"Simulación {r.numero:02d}: {'aprobada' if r.correcto else 'fallida'}",
                f"{r.escenario}\n\nTipo: {r.tipo}\n\nResultado: {r.detalle}",
                parent=self.root,
            )
        tree.bind("<Double-1>", ver_observacion)
        for i, r in enumerate(self.resultados_sim):
            tree.insert("", "end", iid=str(i),
                        values=(f"{r.numero:02d}", r.escenario, r.tipo,
                                "APROBADA" if r.correcto else "FALLIDA", r.detalle),
                        tags=("alterno" if i % 2 else "normal",))
        etiqueta(card, "Doble clic en un escenario para leer el resultado completo. Las situaciones inválidas deben ser rechazadas de manera controlada.", 9, MUTED).pack(
            anchor="w", padx=22, pady=(0, 18))

    def correr_simulaciones(self):
        try:
            self.resultados_sim = ejecutar_simulaciones()
        except Exception as exc:
            self.sistema.logger.exception("Error al ejecutar el conjunto de simulaciones")
            messagebox.showerror("Problema en las pruebas", str(exc), parent=self.root)
            return
        self.renderizar()
        aprobadas = sum(r.correcto for r in self.resultados_sim)
        self.toast(f"Pruebas terminadas · {aprobadas}/{len(self.resultados_sim)} aprobadas",
                   error=aprobadas != len(self.resultados_sim))

    # ── Registros ───────────────────────────────────────────────────────────────
    def pantalla_registros(self, parent):
        self.cabecera_seccion(parent, "Registro de eventos",
                "Consulta las operaciones y los errores sin interrumpir el sistema.",
                [("Abrir archivo", self.abrir_logs, "secondary"),
                 ("↻  Actualizar", self.renderizar, "primary")])
        info = tk.Frame(parent, bg=PALE_BLUE)
        info.pack(fill="x", pady=(0, 18))
        etiqueta(info, "Archivo: logs/sistema.log · Se registran operaciones exitosas y fallos controlados.",
                 10, BLUE_HOVER, bg=PALE_BLUE).pack(anchor="w", padx=17, pady=14)
        card = self.tarjeta(parent)
        card.pack(fill="both", expand=True)
        text_area = tk.Frame(card, bg=PAPER)
        text_area.pack(fill="both", expand=True, padx=22, pady=22)
        txt = tk.Text(text_area, wrap="word", bg="#F9FBFE", fg=INK,
                      relief="flat", borderwidth=0, font=("Consolas", 10),
                      padx=13, pady=13, height=23, highlightthickness=1,
                      highlightbackground=LINE)
        sb = ttk.Scrollbar(text_area, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        try:
            txt.insert("1.0", leer_logs(250))
        except OSError as exc:
            txt.insert("1.0", f"No fue posible leer el registro: {exc}")
        txt.tag_config("error", foreground=RED)
        txt.tag_config("info", foreground=GREEN)
        for num, linea in enumerate(txt.get("1.0", "end").splitlines(), 1):
            if "WARNING" in linea or "ERROR" in linea:
                txt.tag_add("error", f"{num}.0", f"{num}.end")
            elif "SIMULACIÓN" in linea and "APROBADA" in linea:
                txt.tag_add("info", f"{num}.0", f"{num}.end")
        txt.see("end")
        txt.configure(state="disabled")

    def abrir_logs(self):
        if not LOG_FILE.exists():
            messagebox.showinfo("Sin archivo", "No hay registros para abrir todavía.", parent=self.root)
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(LOG_FILE))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(LOG_FILE)])
            else:
                subprocess.Popen(["xdg-open", str(LOG_FILE)])
        except (OSError, AttributeError) as exc:
            messagebox.showerror("No fue posible abrir el archivo", str(exc), parent=self.root)
