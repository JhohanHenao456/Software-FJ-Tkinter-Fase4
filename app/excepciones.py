"""Excepciones de dominio del sistema Software FJ."""


class SoftwareFJError(Exception):
    """Clase base de errores controlados de la aplicación."""


class DatosInvalidosError(SoftwareFJError):
    """Los datos recibidos no cumplen las validaciones."""


class RegistroDuplicadoError(SoftwareFJError):
    """Ya existe un elemento con la misma identidad única."""


class EntidadNoEncontradaError(SoftwareFJError):
    """No se encontró el elemento solicitado."""


class ServicioNoDisponibleError(SoftwareFJError):
    """El servicio está desactivado o no tiene capacidad suficiente."""


class ReservaInvalidaError(SoftwareFJError):
    """La reserva presenta valores o disponibilidad no válidos."""


class EstadoInvalidoError(SoftwareFJError):
    """La operación no está permitida para el estado actual."""
