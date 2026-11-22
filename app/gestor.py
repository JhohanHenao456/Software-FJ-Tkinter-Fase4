"""Operaciones del negocio: memoria, validaciones y registro de eventos."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Callable

from .excepciones import (
    DatosInvalidosError,
    EntidadNoEncontradaError,
    EstadoInvalidoError,
    RegistroDuplicadoError,
    ReservaInvalidaError,
    ServicioNoDisponibleError,
    SoftwareFJError,
)
from .modelos import (
    Asesoria, Cliente, Equipo, EstadoReserva, Reserva, Sala, SERVICIO_POR_TIPO,
    Servicio, TipoServicio, decimal_positivo, entero_positivo,
)
from .registro import obtener_logger


class SistemaGestion:
    """Gestor sin bases de datos: todos los objetos se guardan en diccionarios."""

    def __init__(self, datos_iniciales: bool = False):
        self.clientes: dict[str, Cliente] = {}
        self.servicios: dict[str, Servicio] = {}
        self.reservas: dict[str, Reserva] = {}
        self.eventos: list[tuple[str, str]] = []
        self.logger = obtener_logger()
        self.logger.info("Se inició una nueva sesión de Software FJ")
        if datos_iniciales:
            self.cargar_catalogo_base()

    def _evento(self, mensaje: str) -> None:
        self.eventos.insert(0, (datetime.now().strftime("%H:%M"), mensaje))
        self.eventos = self.eventos[:80]
        self.logger.info(mensaje)

    def _error(self, error: Exception, contexto: str) -> None:
        self.logger.warning("%s | %s: %s", contexto, type(error).__name__, error)

    def cargar_catalogo_base(self) -> None:
        """Carga únicamente servicios de ejemplo; no genera clientes ni reservas ficticios."""
        if self.servicios:
            return
        self.agregar_servicio("Sala", "Sala Ejecutiva", 85000, 12, "Pantalla y videoconferencia")
        self.agregar_servicio("Equipo", "Kit de proyección", 25000, 6, "Proyector, cable HDMI y soporte")
        self.agregar_servicio("Asesoría", "Asesoría tecnológica", 70000, 4, "Soporte en soluciones digitales")

    def listar_clientes(self) -> list[Cliente]:
        return sorted(self.clientes.values(), key=lambda c: c.nombre.casefold())

    def listar_servicios(self) -> list[Servicio]:
        return sorted(self.servicios.values(), key=lambda s: s.nombre.casefold())

    def listar_reservas(self) -> list[Reserva]:
        return sorted(self.reservas.values(), key=lambda r: r.inicio, reverse=True)

    def obtener_cliente(self, id_cliente: str) -> Cliente:
        try:
            return self.clientes[id_cliente]
        except KeyError as exc:
            raise EntidadNoEncontradaError("El cliente indicado no existe.") from exc

    def obtener_servicio(self, id_servicio: str) -> Servicio:
        try:
            return self.servicios[id_servicio]
        except KeyError as exc:
            raise EntidadNoEncontradaError("El servicio indicado no existe.") from exc

    def obtener_reserva(self, id_reserva: str) -> Reserva:
        try:
            return self.reservas[id_reserva]
        except KeyError as exc:
            raise EntidadNoEncontradaError("La reserva indicada no existe.") from exc

    def registrar_cliente(self, nombre: str, correo: str, telefono: str) -> Cliente:
        try:
            nuevo = Cliente(nombre, correo, telefono)
            if any(c.correo == nuevo.correo for c in self.clientes.values()):
                raise RegistroDuplicadoError("Ya hay un cliente registrado con este correo.")
        except SoftwareFJError as exc:
            self._error(exc, "Registro de cliente rechazado")
            raise
        else:
            self.clientes[nuevo.id] = nuevo
            self._evento(f"Cliente registrado: {nuevo.nombre} [{nuevo.id}]")
            return nuevo

    def actualizar_cliente(self, id_cliente: str, nombre: str, correo: str, telefono: str) -> Cliente:
        try:
            cliente = self.obtener_cliente(id_cliente)
            correo_normalizado = correo.strip().lower() if isinstance(correo, str) else ""
            if any(c.id != id_cliente and c.correo == correo_normalizado for c in self.clientes.values()):
                raise RegistroDuplicadoError("El correo pertenece a otro cliente.")
            cliente.actualizar(nombre, correo, telefono)
        except SoftwareFJError as exc:
            self._error(exc, "Actualización de cliente rechazada")
            raise
        self._evento(f"Cliente actualizado: {cliente.nombre} [{cliente.id}]")
        return cliente

    def eliminar_cliente(self, id_cliente: str) -> None:
        try:
            cliente = self.obtener_cliente(id_cliente)
            if any(r.cliente.id == id_cliente for r in self.reservas.values()):
                raise EstadoInvalidoError("No es posible borrar un cliente que tiene historial de reservas.")
            del self.clientes[id_cliente]
        except SoftwareFJError as exc:
            self._error(exc, "Eliminación de cliente rechazada")
            raise
        self._evento(f"Cliente eliminado: {cliente.nombre} [{cliente.id}]")

    def agregar_servicio(self, tipo: str, nombre: str, tarifa: object, capacidad: object, detalle: str) -> Servicio:
        try:
            try:
                tipo_enum = TipoServicio(tipo)
            except (ValueError, TypeError) as exc:
                raise DatosInvalidosError("El tipo de servicio debe ser Sala, Equipo o Asesoría.") from exc
            nuevo = SERVICIO_POR_TIPO[tipo_enum](nombre, tarifa, capacidad, detalle)
        except SoftwareFJError as exc:
            self._error(exc, "Creación de servicio rechazada")
            raise
        self.servicios[nuevo.id] = nuevo
        self._evento(f"Servicio creado: {nuevo.nombre} ({nuevo.tipo.value}) [{nuevo.id}]")
        return nuevo

    def actualizar_servicio(self, id_servicio: str, nombre: str, tarifa: object, capacidad: object, detalle: str) -> Servicio:
        try:
            servicio = self.obtener_servicio(id_servicio)
            # Se validan los nuevos datos antes de modificar un servicio en uso.
            nueva_capacidad = entero_positivo(capacidad, "La capacidad")
            confirmadas = [r for r in self.reservas.values()
                           if r.servicio.id == id_servicio and r.estado == EstadoReserva.CONFIRMADA]
            if confirmadas:
                if servicio.tipo == TipoServicio.SALA and any(r.cantidad > nueva_capacidad for r in confirmadas):
                    raise EstadoInvalidoError("El nuevo aforo es menor que los asistentes de una reserva confirmada.")
                puntos = sorted({instante for r in confirmadas for instante in (r.inicio, r.fin)})
                for instante in puntos:
                    ocupados = sum(r.cantidad for r in confirmadas if r.inicio <= instante < r.fin)
                    if ocupados > nueva_capacidad:
                        raise EstadoInvalidoError("La capacidad propuesta no cubre las reservas confirmadas.")
            servicio.actualizar(nombre, tarifa, capacidad, detalle)
        except SoftwareFJError as exc:
            self._error(exc, "Actualización de servicio rechazada")
            raise
        self._evento(f"Servicio actualizado: {servicio.nombre} [{servicio.id}]")
        return servicio

    def cambiar_disponibilidad(self, id_servicio: str) -> Servicio:
        try:
            servicio = self.obtener_servicio(id_servicio)
            servicio.disponible = not servicio.disponible
        except SoftwareFJError as exc:
            self._error(exc, "Cambio de disponibilidad rechazado")
            raise
        self._evento(f"Servicio {'habilitado' if servicio.disponible else 'deshabilitado'}: {servicio.nombre}")
        return servicio

    def eliminar_servicio(self, id_servicio: str) -> None:
        try:
            servicio = self.obtener_servicio(id_servicio)
            if any(r.servicio.id == id_servicio for r in self.reservas.values()):
                raise EstadoInvalidoError("No es posible borrar un servicio que tiene historial de reservas.")
            del self.servicios[id_servicio]
        except SoftwareFJError as exc:
            self._error(exc, "Eliminación de servicio rechazada")
            raise
        self._evento(f"Servicio eliminado: {servicio.nombre} [{servicio.id}]")

    @staticmethod
    def interpretar_fecha(fecha: str, hora: str) -> datetime:
        try:
            return datetime.strptime(f"{fecha.strip()} {hora.strip()}", "%Y-%m-%d %H:%M")
        except (ValueError, AttributeError) as exc:
            raise ReservaInvalidaError("Fecha y hora inválidas. Usa AAAA-MM-DD y HH:MM.") from exc

    def crear_reserva(
        self, id_cliente: str, id_servicio: str, fecha: str, hora: str,
        horas: object, cantidad: object = 1, descuento: object = 0,
        impuesto: object = 0,
    ) -> Reserva:
        """Crea una reserva pendiente; confirma con operación separada."""
        try:
            cliente = self.obtener_cliente(id_cliente)
            servicio = self.obtener_servicio(id_servicio)
            if not servicio.disponible:
                raise ServicioNoDisponibleError("Este servicio no está disponible para nuevas reservas.")
            inicio = self.interpretar_fecha(fecha, hora)
            if inicio <= datetime.now():
                raise ReservaInvalidaError("Selecciona una fecha y hora actuales o futuras.")
            horas_ok, cantidad_ok = servicio.validar_solicitud(horas, cantidad)
            descuento_ok = decimal_positivo(descuento, "El descuento", cero=True)
            impuesto_ok = decimal_positivo(impuesto, "El impuesto", cero=True)
            servicio.calcular_costo(horas_ok, cantidad_ok, descuento_ok, impuesto_ok)
            reserva = Reserva(cliente, servicio, inicio, horas_ok, cantidad_ok, descuento_ok, impuesto_ok)
        except SoftwareFJError as exc:
            self._error(exc, "Creación de reserva rechazada")
            raise
        else:
            self.reservas[reserva.id] = reserva
            self._evento(f"Reserva pendiente: {reserva.id} | {cliente.nombre} | {servicio.nombre}")
            return reserva
        finally:
            # El bloque finally se ejecuta tanto cuando la creación tiene éxito como si falla.
            self.logger.debug("Terminó el intento de creación de reserva")

    def crear_y_confirmar_reserva(
        self, id_cliente: str, id_servicio: str, fecha: str, hora: str,
        horas: object, cantidad: object = 1, descuento: object = 0,
        impuesto: object = 0,
    ) -> Reserva:
        """Procesa una reserva en forma atómica: revierte la creación si falla la confirmación."""
        reserva = self.crear_reserva(
            id_cliente, id_servicio, fecha, hora, horas, cantidad, descuento, impuesto
        )
        try:
            return self.confirmar_reserva(reserva.id)
        except Exception:
            self.reservas.pop(reserva.id, None)
            self._evento(f"Reserva revertida tras error de confirmación: {reserva.id}")
            raise

    def confirmar_reserva(self, id_reserva: str) -> Reserva:
        """Comprueba simultaneidad y capacidad antes de confirmar."""
        try:
            reserva = self.obtener_reserva(id_reserva)
            if reserva.estado != EstadoReserva.PENDIENTE:
                raise EstadoInvalidoError("Solo puedes confirmar una reserva pendiente.")
            servicio = reserva.servicio
            if not servicio.disponible:
                raise ServicioNoDisponibleError("El servicio fue deshabilitado antes de confirmar.")
            if reserva.inicio < datetime.now():
                raise ReservaInvalidaError("No se puede confirmar una reserva con horario pasado.")
            servicio.validar_solicitud(reserva.horas, reserva.cantidad)
            solapadas = [
                r for r in self.reservas.values()
                if r.id != reserva.id and r.servicio.id == servicio.id
                and r.estado == EstadoReserva.CONFIRMADA
                and reserva.inicio < r.fin and r.inicio < reserva.fin
            ]
            if servicio.tipo == TipoServicio.SALA and solapadas:
                raise ServicioNoDisponibleError("La sala ya está reservada en esa franja horaria.")
            ocupacion = sum(r.cantidad for r in solapadas)
            if servicio.tipo != TipoServicio.SALA and ocupacion + reserva.cantidad > servicio.capacidad:
                raise ServicioNoDisponibleError(
                    f"Capacidad insuficiente: {ocupacion}/{servicio.capacidad} ocupadas en esa franja."
                )
            total = servicio.calcular_costo(
                reserva.horas, reserva.cantidad, reserva.descuento, reserva.impuesto
            )
            reserva.confirmar(total)
        except SoftwareFJError as exc:
            self._error(exc, "Confirmación de reserva rechazada")
            raise
        else:
            self._evento(f"Reserva confirmada: {reserva.id} | Total COP {reserva.total:,.2f}")
            return reserva
        finally:
            self.logger.debug("Finalizó el procesamiento de confirmación")

    def cancelar_reserva(self, id_reserva: str) -> Reserva:
        try:
            reserva = self.obtener_reserva(id_reserva)
            reserva.cancelar()
        except SoftwareFJError as exc:
            self._error(exc, "Cancelación de reserva rechazada")
            raise
        self._evento(f"Reserva cancelada: {reserva.id}")
        return reserva

    def resumen(self) -> dict[str, int]:
        return {
            "clientes": len(self.clientes),
            "servicios": len(self.servicios),
            "confirmadas": sum(r.estado == EstadoReserva.CONFIRMADA for r in self.reservas.values()),
            "pendientes": sum(r.estado == EstadoReserva.PENDIENTE for r in self.reservas.values()),
            "canceladas": sum(r.estado == EstadoReserva.CANCELADA for r in self.reservas.values()),
        }
