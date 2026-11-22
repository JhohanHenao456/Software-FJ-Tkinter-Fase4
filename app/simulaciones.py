"""Simulaciones controladas e independientes de la sesión real de la interfaz."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Callable

from .excepciones import SoftwareFJError
from .gestor import SistemaGestion


@dataclass(frozen=True)
class Resultado:
    numero: int
    escenario: str
    tipo: str
    correcto: bool
    detalle: str


def ejecutar_simulaciones() -> list[Resultado]:
    """Ejecuta pruebas válidas e inválidas. No modifica clientes/reservas del usuario."""
    sistema = SistemaGestion()
    resultados: list[Resultado] = []
    futuro = datetime.now().replace(second=0, microsecond=0) + timedelta(days=3)
    fecha, hora = futuro.strftime("%Y-%m-%d"), "10:00"
    un_dia_despues = (futuro + timedelta(days=1)).strftime("%Y-%m-%d")

    def caso(nombre: str, funcion: Callable[[], object], falla_esperada: bool = False):
        numero = len(resultados) + 1
        try:
            resultado = funcion()
        except SoftwareFJError as exc:
            correcto = falla_esperada
            detalle = f"Error controlado: {exc}"
        except Exception as exc:  # Los errores inesperados quedan registrados con traceback.
            sistema.logger.exception("Fallo inesperado en simulación %s", numero)
            correcto = False
            detalle = f"Fallo inesperado: {type(exc).__name__}: {exc}"
        else:
            correcto = not falla_esperada
            detalle = "Operación realizada correctamente" if correcto else "Se esperaba un rechazo y se aceptó"
        resultados.append(Resultado(numero, nombre, "Inválido" if falla_esperada else "Válido", correcto, detalle))
        sistema.logger.info("SIMULACIÓN %02d | %s | %s | %s", numero, "APROBADA" if correcto else "FALLIDA", nombre, detalle)
        return resultado if correcto and not falla_esperada else None

    cliente = caso("Registrar cliente con datos correctos", lambda: sistema.registrar_cliente("Laura Pérez", "laura@example.com", "3101234567"))
    caso("Rechazar correo duplicado", lambda: sistema.registrar_cliente("Laura Otra", "laura@example.com", "3111234567"), True)
    caso("Rechazar correo electrónico inválido", lambda: sistema.registrar_cliente("Carlos Ruiz", "sin-arroba", "3201234567"), True)
    caso("Rechazar cliente sin nombre", lambda: sistema.registrar_cliente("", "otro@example.com", "3201234567"), True)
    sala = caso("Crear servicio de salas", lambda: sistema.agregar_servicio("Sala", "Sala de reuniones", 90000, 12, "Videobeam"))
    equipo = caso("Crear alquiler de equipos", lambda: sistema.agregar_servicio("Equipo", "Computadores portátiles", 20000, 3, "Equipos para eventos"))
    asesoria = caso("Crear asesoría especializada", lambda: sistema.agregar_servicio("Asesoría", "Asesoría en redes", 50000, 4, "Acompañamiento especializado"))
    caso("Rechazar servicio con tarifa negativa", lambda: sistema.agregar_servicio("Sala", "Sala incorrecta", -5, 5, "Espacio"), True)
    caso("Rechazar servicio de tipo desconocido", lambda: sistema.agregar_servicio("Otro", "Servicio extraño", 10, 2, "No válido"), True)
    reserva = caso("Crear reserva válida pendiente", lambda: sistema.crear_reserva(cliente.id, sala.id, fecha, hora, 2, 5))
    caso("Confirmar reserva con éxito", lambda: sistema.confirmar_reserva(reserva.id))
    conflicto = caso("Crear segunda reserva para la misma sala", lambda: sistema.crear_reserva(cliente.id, sala.id, fecha, hora, 1, 3))
    caso("Detectar conflicto de horario de sala", lambda: sistema.confirmar_reserva(conflicto.id), True)
    caso("Rechazar reserva con duración cero", lambda: sistema.crear_reserva(cliente.id, equipo.id, fecha, hora, 0), True)
    caso("Rechazar cantidad superior a capacidad", lambda: sistema.crear_reserva(cliente.id, equipo.id, fecha, hora, 1, 99), True)
    caso("Rechazar descuento superior al 100%", lambda: sistema.crear_reserva(cliente.id, equipo.id, fecha, hora, 1, 1, 101), True)
    caso("Rechazar fecha inexistente", lambda: sistema.crear_reserva(cliente.id, equipo.id, "2026-02-30", hora, 1), True)
    caso("Rechazar cliente no registrado", lambda: sistema.crear_reserva("CLI-INEXISTENTE", equipo.id, fecha, hora, 1), True)
    caso("Deshabilitar servicio disponible", lambda: sistema.cambiar_disponibilidad(asesoria.id))
    caso("Rechazar reserva de servicio deshabilitado", lambda: sistema.crear_reserva(cliente.id, asesoria.id, fecha, hora, 1), True)
    valida2 = caso("Crear reserva de equipos", lambda: sistema.crear_reserva(cliente.id, equipo.id, un_dia_despues, hora, 3, 2, 10, 19))
    caso("Confirmar reserva con impuesto y descuento", lambda: sistema.confirmar_reserva(valida2.id))
    caso("Cancelar reserva confirmada", lambda: sistema.cancelar_reserva(valida2.id))
    caso("Rechazar doble cancelación", lambda: sistema.cancelar_reserva(valida2.id), True)
    caso("Impedir borrar cliente con historial", lambda: sistema.eliminar_cliente(cliente.id), True)
    return resultados


def main() -> None:
    resultados = ejecutar_simulaciones()
    for r in resultados:
        print(f"{r.numero:02d}. {'OK' if r.correcto else 'FALLO'} | {r.tipo:8} | {r.escenario}")
        print(f"    {r.detalle}")
    print("\nRESUMEN")
    print("Simulaciones:", len(resultados))
    print("Aprobadas:", sum(r.correcto for r in resultados))
    print("Fallidas:", sum(not r.correcto for r in resultados))


if __name__ == "__main__":
    main()
