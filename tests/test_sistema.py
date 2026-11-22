"""Pruebas automáticas del dominio y la capa de gestión de Software FJ."""
import unittest
from abc import ABC
from datetime import datetime, timedelta
from decimal import Decimal

from app.excepciones import (
    DatosInvalidosError, EntidadNoEncontradaError, EstadoInvalidoError,
    RegistroDuplicadoError, ReservaInvalidaError, ServicioNoDisponibleError,
)
from app.gestor import SistemaGestion
from app.modelos import Cliente, Entidad, Servicio, EstadoReserva, Sala, Equipo, Asesoria
from app.simulaciones import ejecutar_simulaciones


class TestSoftwareFJ(unittest.TestCase):
    def setUp(self):
        self.g = SistemaGestion()
        self.cliente = self.g.registrar_cliente("María López", "maria@example.com", "3001234567")
        self.sala = self.g.agregar_servicio("Sala", "Sala de reuniones", 85000, 8, "Proyector incluido")
        self.equipo = self.g.agregar_servicio("Equipo", "Computadores", 30000, 5, "Portátiles")
        self.asesoria = self.g.agregar_servicio("Asesoría", "Soporte informático", 45000, 3, "Orientación")
        futuro = datetime.now() + timedelta(days=4)
        self.fecha = futuro.strftime("%Y-%m-%d")
        self.hora = "10:00"

    def reservar(self, servicio=None, **kwargs):
        return self.g.crear_reserva(
            self.cliente.id, (servicio or self.sala).id,
            self.fecha, self.hora, 2, **kwargs
        )

    def test_01_clases_abstractas(self):
        with self.assertRaises(TypeError):
            Entidad("ID")
        with self.assertRaises(TypeError):
            Servicio("Mal", 10, 2, "Detalle")

    def test_02_herencia_y_polimorfismo(self):
        self.assertIsInstance(self.sala, Entidad)
        self.assertIsInstance(self.equipo, Servicio)
        self.assertIsInstance(self.asesoria, Servicio)
        self.assertIsInstance(self.sala, Sala)
        self.assertIsInstance(self.equipo, Equipo)
        self.assertIsInstance(self.asesoria, Asesoria)
        self.assertNotEqual(self.sala.descripcion(), self.equipo.descripcion())

    def test_03_encapsulacion_cliente(self):
        self.assertEqual(self.cliente.correo, "maria@example.com")
        self.assertFalse(hasattr(self.cliente, "__correo"))
        self.assertTrue(hasattr(self.cliente, "_Cliente__correo"))

    def test_04_validacion_cliente_y_atomia(self):
        with self.assertRaises(DatosInvalidosError):
            self.g.actualizar_cliente(self.cliente.id, "María", "correo-sin-arroba", "3101234567")
        self.assertEqual(self.cliente.nombre, "María López")
        self.assertEqual(self.cliente.correo, "maria@example.com")

    def test_05_correo_duplicado(self):
        with self.assertRaises(RegistroDuplicadoError):
            self.g.registrar_cliente("Otro Nombre", "MARIA@example.com", "3202222222")

    def test_06_correo_y_telefono_invalidos(self):
        with self.assertRaises(DatosInvalidosError):
            self.g.registrar_cliente("Nombre Uno", "invalido", "3112222222")
        with self.assertRaises(DatosInvalidosError):
            self.g.registrar_cliente("Nombre Dos", "dos@example.com", "abc")

    def test_07_no_permitir_cliente_inexistente(self):
        with self.assertRaises(EntidadNoEncontradaError) as contexto:
            self.g.obtener_cliente("no-existe")
        self.assertIsInstance(contexto.exception.__cause__, KeyError)

    def test_08_costo_sala(self):
        self.assertEqual(self.sala.calcular_costo(2), Decimal("170000.00"))

    def test_09_costo_equipos_con_descuento_e_impuesto(self):
        self.assertEqual(self.equipo.calcular_costo(2, 2, 10, 19), Decimal("128520.00"))

    def test_10_costo_asesoria_por_participante(self):
        self.assertEqual(self.asesoria.calcular_costo(2, 3), Decimal("270000.00"))

    def test_11_decimal_no_finito(self):
        for valor in ["NaN", "Infinity", "-Infinity"]:
            with self.subTest(valor=valor), self.assertRaises(DatosInvalidosError):
                self.sala.calcular_costo(valor)

    def test_12_descuento_no_permitido(self):
        with self.assertRaises(DatosInvalidosError):
            self.sala.calcular_costo(2, 1, 120, 0)

    def test_13_tarifa_invalida(self):
        with self.assertRaises(DatosInvalidosError):
            self.g.agregar_servicio("Sala", "Servicio mal", 0, 4, "Detalle")

    def test_14_reserva_valida_pendiente(self):
        r = self.reservar()
        self.assertEqual(r.estado, EstadoReserva.PENDIENTE)
        self.assertEqual(r.total, Decimal("0"))

    def test_15_confirmacion_total(self):
        r = self.reservar()
        self.g.confirmar_reserva(r.id)
        self.assertEqual(r.estado, EstadoReserva.CONFIRMADA)
        self.assertEqual(r.total, Decimal("170000.00"))

    def test_16_no_confirmar_dos_veces(self):
        r = self.reservar()
        self.g.confirmar_reserva(r.id)
        with self.assertRaises(EstadoInvalidoError):
            self.g.confirmar_reserva(r.id)

    def test_17_rechazar_sala_solapada(self):
        r1 = self.reservar()
        self.g.confirmar_reserva(r1.id)
        r2 = self.reservar()
        with self.assertRaises(ServicioNoDisponibleError):
            self.g.confirmar_reserva(r2.id)
        self.assertEqual(r2.estado, EstadoReserva.PENDIENTE)

    def test_18_sala_en_horario_distinto(self):
        r1 = self.reservar()
        self.g.confirmar_reserva(r1.id)
        r2 = self.g.crear_reserva(self.cliente.id, self.sala.id, self.fecha, "12:00", 1)
        self.g.confirmar_reserva(r2.id)
        self.assertEqual(r2.estado, EstadoReserva.CONFIRMADA)

    def test_19_capacidad_equipo_solapado(self):
        r1 = self.reservar(self.equipo, cantidad=4)
        self.g.confirmar_reserva(r1.id)
        r2 = self.reservar(self.equipo, cantidad=2)
        with self.assertRaises(ServicioNoDisponibleError):
            self.g.confirmar_reserva(r2.id)

    def test_20_capacidad_equipo_compatible(self):
        r1 = self.reservar(self.equipo, cantidad=4)
        self.g.confirmar_reserva(r1.id)
        r2 = self.reservar(self.equipo, cantidad=1)
        self.g.confirmar_reserva(r2.id)
        self.assertEqual(r2.estado, EstadoReserva.CONFIRMADA)

    def test_21_capacidad_dinamica(self):
        r = self.reservar(self.equipo, cantidad=4)
        self.g.confirmar_reserva(r.id)
        with self.assertRaises(EstadoInvalidoError):
            self.g.actualizar_servicio(self.equipo.id, "Computadores", 10000, 3, "Portátiles")
        self.assertEqual(self.equipo.capacidad, 5)

    def test_22_reserva_no_disponible(self):
        self.g.cambiar_disponibilidad(self.sala.id)
        with self.assertRaises(ServicioNoDisponibleError):
            self.reservar()

    def test_23_cancelar_y_liberar_capacidad(self):
        r1 = self.reservar()
        self.g.confirmar_reserva(r1.id)
        self.g.cancelar_reserva(r1.id)
        r2 = self.reservar()
        self.g.confirmar_reserva(r2.id)
        self.assertEqual(r2.estado, EstadoReserva.CONFIRMADA)

    def test_24_cancelar_duplicado(self):
        r = self.reservar()
        self.g.cancelar_reserva(r.id)
        with self.assertRaises(EstadoInvalidoError):
            self.g.cancelar_reserva(r.id)

    def test_25_fecha_invalida(self):
        with self.assertRaises(ReservaInvalidaError):
            self.g.crear_reserva(self.cliente.id, self.sala.id, "2026-02-30", "10:00", 2)

    def test_26_fecha_pasada(self):
        with self.assertRaises(ReservaInvalidaError):
            self.g.crear_reserva(self.cliente.id, self.sala.id, "2020-01-01", "10:00", 2)

    def test_27_duracion_invalida(self):
        with self.assertRaises(DatosInvalidosError):
            self.g.crear_reserva(self.cliente.id, self.sala.id, self.fecha, self.hora, 0)

    def test_28_no_eliminar_cliente_con_historial(self):
        self.reservar()
        with self.assertRaises(EstadoInvalidoError):
            self.g.eliminar_cliente(self.cliente.id)

    def test_29_no_eliminar_servicio_con_historial(self):
        self.reservar()
        with self.assertRaises(EstadoInvalidoError):
            self.g.eliminar_servicio(self.sala.id)

    def test_30_transaccion_conflicto_revierte_reserva(self):
        reserva = self.reservar()
        self.g.confirmar_reserva(reserva.id)
        antes = len(self.g.reservas)
        with self.assertRaises(ServicioNoDisponibleError):
            self.g.crear_y_confirmar_reserva(self.cliente.id, self.sala.id, self.fecha, self.hora, 2)
        self.assertEqual(len(self.g.reservas), antes)

    def test_31_invariantes_de_resumen(self):
        self.assertEqual(self.g.resumen()["clientes"], 1)
        self.assertEqual(self.g.resumen()["servicios"], 3)
        self.assertEqual(self.g.resumen()["confirmadas"], 0)

    def test_32_simulaciones_completas(self):
        resultados = ejecutar_simulaciones()
        self.assertGreaterEqual(len(resultados), 10)
        self.assertTrue(all(r.correcto for r in resultados), [r for r in resultados if not r.correcto])
        self.assertTrue(any(r.tipo == "Válido" for r in resultados))
        self.assertTrue(any(r.tipo == "Inválido" for r in resultados))


if __name__ == "__main__":
    unittest.main()
