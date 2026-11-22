"""Modelo de dominio: clases abstractas, herencia, polimorfismo y encapsulación."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import overload
import math
import re
import uuid

from .excepciones import DatosInvalidosError, ReservaInvalidaError, EstadoInvalidoError


def nuevo_id(prefijo: str) -> str:
    return f"{prefijo}-{uuid.uuid4().hex[:7].upper()}"


def texto_obligatorio(valor: str, nombre: str, minimo: int = 2) -> str:
    if not isinstance(valor, str) or len(valor.strip()) < minimo:
        raise DatosInvalidosError(f"{nombre} debe tener al menos {minimo} caracteres.")
    return valor.strip()


def decimal_positivo(valor: object, nombre: str, cero: bool = False) -> Decimal:
    try:
        if isinstance(valor, bool):
            raise InvalidOperation()
        numero = Decimal(str(valor))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise DatosInvalidosError(f"{nombre} debe ser un número válido.") from exc
    if not numero.is_finite() or (numero < 0 if cero else numero <= 0):
        comparacion = "mayor o igual a cero" if cero else "mayor que cero"
        raise DatosInvalidosError(f"{nombre} debe ser {comparacion} y finito.")
    return numero


def entero_positivo(valor: object, nombre: str) -> int:
    try:
        if isinstance(valor, bool) or str(valor).strip() != str(int(valor)):
            raise ValueError()
        numero = int(valor)
    except (TypeError, ValueError, OverflowError) as exc:
        raise DatosInvalidosError(f"{nombre} debe ser un entero positivo.") from exc
    if numero <= 0:
        raise DatosInvalidosError(f"{nombre} debe ser un entero positivo.")
    return numero


def dinero(numero: Decimal) -> Decimal:
    return numero.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Entidad(ABC):
    """Clase abstracta general, compartida por clientes y servicios."""

    def __init__(self, identificador: str):
        self._id = identificador

    @property
    def id(self) -> str:
        return self._id

    @abstractmethod
    def resumen(self) -> str:
        """Representación breve de la entidad."""


class Cliente(Entidad):
    """Entidad con datos privados y validaciones encapsuladas."""

    _EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    _TELEFONO = re.compile(r"^\+?[\d\s()\-]{7,20}$")

    def __init__(self, nombre: str, correo: str, telefono: str):
        super().__init__(nuevo_id("CLI"))
        self.actualizar(nombre, correo, telefono)

    def actualizar(self, nombre: str, correo: str, telefono: str) -> None:
        nombre = texto_obligatorio(nombre, "El nombre", 3)
        correo = texto_obligatorio(correo, "El correo").lower()
        telefono = texto_obligatorio(telefono, "El teléfono", 7)
        if not self._EMAIL.fullmatch(correo):
            raise DatosInvalidosError("Ingresa un correo electrónico válido.")
        if not self._TELEFONO.fullmatch(telefono):
            raise DatosInvalidosError("Ingresa un teléfono válido (7 a 20 caracteres).")
        self.__nombre, self.__correo, self.__telefono = nombre, correo, telefono

    @property
    def nombre(self) -> str:
        return self.__nombre

    @property
    def correo(self) -> str:
        return self.__correo

    @property
    def telefono(self) -> str:
        return self.__telefono

    def resumen(self) -> str:
        return f"{self.nombre} · {self.correo}"


class TipoServicio(str, Enum):
    SALA = "Sala"
    EQUIPO = "Equipo"
    ASESORIA = "Asesoría"


class Servicio(Entidad, ABC):
    """Clase abstracta para los servicios. El precio se calcula polimórficamente."""

    tipo: TipoServicio
    unidad: str

    def __init__(self, nombre: str, tarifa: object, capacidad: object, detalle: str):
        super().__init__(nuevo_id("SRV"))
        self.disponible = True
        self.actualizar(nombre, tarifa, capacidad, detalle)

    def actualizar(self, nombre: str, tarifa: object, capacidad: object, detalle: str) -> None:
        nombre_ok = texto_obligatorio(nombre, "El nombre del servicio", 3)
        tarifa_ok = decimal_positivo(tarifa, "La tarifa")
        capacidad_ok = entero_positivo(capacidad, "La capacidad")
        detalle_ok = texto_obligatorio(detalle, "El detalle")
        self.nombre, self.tarifa, self.capacidad, self.detalle = (
            nombre_ok, tarifa_ok, capacidad_ok, detalle_ok
        )

    @abstractmethod
    def validar_solicitud(self, horas: object, cantidad: object) -> tuple[Decimal, int]:
        """Valida duración y unidades específicas de cada servicio."""

    @abstractmethod
    def calcular_subtotal(self, horas: Decimal, cantidad: int) -> Decimal:
        """Cada clase hija debe definir su lógica de costos."""

    @abstractmethod
    def descripcion(self) -> str:
        """Descripción particular del servicio."""

    def resumen(self) -> str:
        return f"{self.nombre} · {self.tipo.value}"

    # Las firmas @overload documentan variantes de llamada en Python.
    @overload
    def calcular_costo(self, horas: object, cantidad: object = 1) -> Decimal: ...

    @overload
    def calcular_costo(
        self, horas: object, cantidad: object, descuento: object, impuesto: object = 0
    ) -> Decimal: ...

    def calcular_costo(
        self, horas: object, cantidad: object = 1,
        descuento: object = 0, impuesto: object = 0
    ) -> Decimal:
        """Precio total con variantes opcionales de descuento e impuesto (%)."""
        horas_ok, cantidad_ok = self.validar_solicitud(horas, cantidad)
        descuento_ok = decimal_positivo(descuento, "El descuento", cero=True)
        impuesto_ok = decimal_positivo(impuesto, "El impuesto", cero=True)
        if descuento_ok > 100 or impuesto_ok > 100:
            raise DatosInvalidosError("El descuento y el impuesto deben estar entre 0 y 100%.")
        subtotal = self.calcular_subtotal(horas_ok, cantidad_ok)
        return dinero(subtotal * (1 - descuento_ok / 100) * (1 + impuesto_ok / 100))

    def _validacion_base(self, horas: object, cantidad: object) -> tuple[Decimal, int]:
        horas_ok = decimal_positivo(horas, "La duración")
        cantidad_ok = entero_positivo(cantidad, "La cantidad")
        if horas_ok > 24:
            raise ReservaInvalidaError("Una reserva no puede superar las 24 horas.")
        if cantidad_ok > self.capacidad:
            raise ReservaInvalidaError(
                f"La cantidad supera la capacidad de {self.capacidad} {self.unidad}."
            )
        return horas_ok, cantidad_ok


class Sala(Servicio):
    tipo = TipoServicio.SALA
    unidad = "personas"

    def validar_solicitud(self, horas: object, cantidad: object) -> tuple[Decimal, int]:
        return self._validacion_base(horas, cantidad)

    def calcular_subtotal(self, horas: Decimal, cantidad: int) -> Decimal:
        # La sala tiene un precio fijo por hora, sujeto a su aforo máximo.
        return self.tarifa * horas

    def descripcion(self) -> str:
        return f"Sala para hasta {self.capacidad} personas · {self.detalle}"


class Equipo(Servicio):
    tipo = TipoServicio.EQUIPO
    unidad = "unidades"

    def validar_solicitud(self, horas: object, cantidad: object) -> tuple[Decimal, int]:
        return self._validacion_base(horas, cantidad)

    def calcular_subtotal(self, horas: Decimal, cantidad: int) -> Decimal:
        return self.tarifa * horas * cantidad

    def descripcion(self) -> str:
        return f"Alquiler de hasta {self.capacidad} unidades · {self.detalle}"


class Asesoria(Servicio):
    tipo = TipoServicio.ASESORIA
    unidad = "participantes"

    def validar_solicitud(self, horas: object, cantidad: object) -> tuple[Decimal, int]:
        horas_ok, cantidad_ok = self._validacion_base(horas, cantidad)
        if horas_ok > 8:
            raise ReservaInvalidaError("Una asesoría puede durar como máximo 8 horas.")
        return horas_ok, cantidad_ok

    def calcular_subtotal(self, horas: Decimal, cantidad: int) -> Decimal:
        # Asesoría se factura por hora y por participante.
        return self.tarifa * horas * cantidad

    def descripcion(self) -> str:
        return f"Asesoría de hasta {self.capacidad} participantes · {self.detalle}"


SERVICIO_POR_TIPO = {
    TipoServicio.SALA: Sala,
    TipoServicio.EQUIPO: Equipo,
    TipoServicio.ASESORIA: Asesoria,
}


class EstadoReserva(str, Enum):
    PENDIENTE = "Pendiente"
    CONFIRMADA = "Confirmada"
    CANCELADA = "Cancelada"


@dataclass
class Reserva:
    """Relaciona cliente, servicio, horario, duración, cantidad y estado."""

    cliente: Cliente
    servicio: Servicio
    inicio: datetime
    horas: Decimal
    cantidad: int
    descuento: Decimal = Decimal("0")
    impuesto: Decimal = Decimal("0")
    id: str = field(default_factory=lambda: nuevo_id("RES"))
    estado: EstadoReserva = EstadoReserva.PENDIENTE
    total: Decimal = Decimal("0")

    @property
    def fin(self) -> datetime:
        return self.inicio + timedelta(hours=float(self.horas))

    def confirmar(self, total: Decimal) -> None:
        if self.estado != EstadoReserva.PENDIENTE:
            raise EstadoInvalidoError("Solo se pueden confirmar reservas pendientes.")
        self.total = dinero(total)
        self.estado = EstadoReserva.CONFIRMADA

    def cancelar(self) -> None:
        if self.estado == EstadoReserva.CANCELADA:
            raise EstadoInvalidoError("Esta reserva ya se encuentra cancelada.")
        self.estado = EstadoReserva.CANCELADA

    def resumen(self) -> str:
        return f"{self.cliente.nombre} · {self.servicio.nombre} · {self.estado.value}"
