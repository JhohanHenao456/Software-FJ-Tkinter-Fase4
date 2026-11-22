"""Punto de entrada de Software FJ.

    python main.py           -> aplicación gráfica Tkinter
    python main.py --demo    -> simulaciones de consola para auditoría
"""
import sys


def main() -> None:
    if "--demo" in sys.argv:
        from app.simulaciones import main as demo
        demo()
        return
    try:
        import tkinter as tk
        from app.interfaz import AplicacionFJ

        ventana = tk.Tk()
        AplicacionFJ(ventana)
        ventana.mainloop()
    except ImportError as exc:
        print("No se pudo iniciar Tkinter. Instala Python 3.10+ con soporte para Tcl/Tk.")
        raise SystemExit(1) from exc
    except tk.TclError as exc:
        print(f"No se pudo abrir la ventana gráfica: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
