# Cómo subir esta aplicación a GitHub

1. **Verifica el funcionamiento en tu computador:** `python main.py` debe abrir una ventana. Prueba registrar un cliente y confirmar una reserva. Ejecuta además `python main.py --demo`.
2. Ingresa a https://github.com/new y crea un repositorio propio llamado `Software-FJ-Tkinter-Fase4`. Puedes usar visibilidad *Public* si necesitas compartirlo con el tutor.
3. En el nuevo repositorio, elige **Add file → Upload files**. Arrastra **el contenido descomprimido de la carpeta** `Software_FJ_Tkinter`, conservando la estructura. No subas solamente el ZIP.
4. No subas carpetas `__pycache__`, `.venv` ni logs con información personal. El `.gitignore` ayuda a prevenirlo si usas Git desde tu computador.
5. Escribe un mensaje de commit como `Versión inicial: gestión de clientes, servicios, reservas e interfaz Tkinter` y confirma.
6. Abre el repositorio y comprueba que `main.py`, `app/`, `tests/` y `README.md` estén visibles. Copia la URL para el PDF de entrega.
7. En la documentación de entrega, especifica que se trata de una propuesta individual; la actividad oficial es colaborativa y su aceptación depende del tutor.

## Alternativa desde Git (consola, opcional)

```bash
git init
git add .
git commit -m "Aplicación Tkinter: proyecto Software FJ"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/Software-FJ-Tkinter-Fase4.git
git push -u origin main
```

Reemplaza `TU_USUARIO` por tu usuario real y crea primero el repositorio vacío. No escribas que colaboraste en un proyecto del grupo si no ocurrió.
