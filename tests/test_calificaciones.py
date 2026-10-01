"""Pruebas de las reglas de negocio:  python -m unittest discover -s tests -v"""
import unittest

from app.logic.calificaciones import (
    Cuatrimestre as C, Estado, RegistroNotas as R, calcular_calificacion_final,
    estado_cuatrimestre, estado_ifa, evaluar, formatear_cf, necesita_intensificacion_cuatrimestral,
)
from app.logic.estadisticas import resumir, resumir_cuatrimestre, resumir_ifa


class TestCalificaciones(unittest.TestCase):
    def test_promedio_exacto(self):
        # (7 + 8) / 2 = 7,5 (sin truncar)
        self.assertEqual(calcular_calificacion_final(7, 8), 7.5)
        r = evaluar(R(C(calificacion=7), C(calificacion=8)))
        self.assertEqual((r.estado, r.calificacion_final), (Estado.APROBADO, 7.5))

    def test_cf_manual_pisa_la_calculada(self):
        r = evaluar(R(C(calificacion=7), C(calificacion=8), cf_manual=6.99))
        self.assertEqual((r.estado, r.calificacion_final, r.cf_calculada),
                         (Estado.DESAPROBADO, 6.99, 7.5))

    def test_formatear_cf(self):
        self.assertEqual([formatear_cf(v) for v in (7.0, 7.5, 7.25, None)],
                         ["7", "7,5", "7,25", ""])

    def test_cf_es_promedio_aunque_desapruebe_un_cuatrimestre(self):
        # CC1 = 5 (desaprobado) y CC2 = 10: CF 7,5 => aprueba y no va a la IFA.
        r = evaluar(R(C(calificacion=5), C(calificacion=10)))
        self.assertEqual((r.estado, r.calificacion_final, r.va_a_ifa), (Estado.APROBADO, 7.5, False))

    def test_cf_menor_a_7_va_a_ifa(self):
        r = evaluar(R(C(calificacion=5), C(calificacion=8)))
        self.assertEqual((r.estado, r.calificacion_final, r.va_a_ifa), (Estado.DESAPROBADO, 6.5, True))

    def test_ifa_no_cambia_la_cf_ni_el_estado(self):
        for ifa in (dict(if_nota=9), dict(if_nota=3), dict(if_ausente=True)):
            r = evaluar(R(C(calificacion=5), C(calificacion=8), **ifa))
            self.assertEqual((r.estado, r.calificacion_final), (Estado.DESAPROBADO, 6.5))

    def test_cf_manual_decide_si_va_a_ifa(self):
        r = evaluar(R(C(calificacion=7), C(calificacion=8), cf_manual=6))
        self.assertTrue(r.va_a_ifa)

    def test_ausente_con_cc_vacia_cuenta_4(self):
        r = evaluar(R(C(ausente=True), C(calificacion=9)))
        self.assertEqual((r.cal_c1, r.calificacion_final, r.estado), (4, 6.5, Estado.DESAPROBADO))

    def test_ausente_con_cc_cargada_usa_la_cc(self):
        r = evaluar(R(C(calificacion=9, ausente=True), C(calificacion=9)))
        self.assertEqual((r.calificacion_final, r.estado), (9, Estado.APROBADO))
        self.assertEqual(estado_cuatrimestre(C(calificacion=9, ausente=True)), Estado.AUSENTE)

    def test_ausente_todo_el_anio(self):
        aus = C(ausente=True)
        # Desaprobado (CF 4) hasta que se marca Aus. en la IFA.
        self.assertEqual(evaluar(R(aus, aus)).estado, Estado.DESAPROBADO)
        r = evaluar(R(aus, aus, if_ausente=True))
        self.assertEqual((r.estado, r.calificacion_final), (Estado.AUSENTE, 4))
        # Aprobar la IFA no cambia el estado final.
        self.assertEqual(evaluar(R(aus, aus, if_nota=8)).estado, Estado.DESAPROBADO)
        # Con nota en un cuatrimestre no es Ausente.
        self.assertEqual(evaluar(R(aus, C(calificacion=5), if_ausente=True)).estado, Estado.DESAPROBADO)
        # La CF manual manda.
        self.assertEqual(evaluar(R(aus, aus, if_ausente=True, cf_manual=7)).estado, Estado.APROBADO)

    def test_estado_ifa(self):
        self.assertEqual(estado_ifa(R(if_nota=7)), Estado.APROBADO)
        self.assertEqual(estado_ifa(R(if_nota=6)), Estado.DESAPROBADO)
        self.assertEqual(estado_ifa(R(if_ausente=True)), Estado.AUSENTE)
        self.assertEqual(estado_ifa(R()), Estado.PENDIENTE)

    def test_pendiente(self):
        r = evaluar(R(C(calificacion=8), C()))
        self.assertEqual(r.estado, Estado.PENDIENTE)

    def test_intensificacion_cuatrimestral(self):
        self.assertTrue(necesita_intensificacion_cuatrimestral(C(nota1=8, nota2=6)))
        self.assertFalse(necesita_intensificacion_cuatrimestral(C(nota1=8, nota2=7)))
        self.assertTrue(necesita_intensificacion_cuatrimestral(C(ausente=True)))

    def test_estado_cuatrimestre(self):
        self.assertEqual(estado_cuatrimestre(C(calificacion=7)), Estado.APROBADO)
        self.assertEqual(estado_cuatrimestre(C(nota1=9, nota2=9, calificacion=6)), Estado.DESAPROBADO)
        self.assertEqual(estado_cuatrimestre(C(calificacion=9, ausente=True)), Estado.AUSENTE)
        self.assertEqual(estado_cuatrimestre(C(nota1=5, intensificacion=8)), Estado.PENDIENTE)

    def test_resumen_por_cuatrimestre(self):
        regs = [R(C(calificacion=8), C(calificacion=5)),
                R(C(ausente=True), C(calificacion=9)),
                R(C(calificacion=6), C()),
                R(C(), C(calificacion=7))]
        c1 = resumir_cuatrimestre(regs, 1)
        self.assertEqual((c1.total, c1.aprobados, c1.desaprobados, c1.ausentes, c1.pendientes),
                         (4, 1, 1, 1, 1))
        c2 = resumir_cuatrimestre(regs, 2)
        self.assertEqual((c2.total, c2.aprobados, c2.desaprobados, c2.ausentes, c2.pendientes),
                         (4, 2, 1, 0, 1))
        self.assertEqual(c2.pct_aprobados, 50.0)

    def test_resumen_final_por_cf(self):
        aus = C(ausente=True)
        fin = resumir(evaluar(r) for r in [
            R(C(calificacion=8), C(calificacion=9)),                   # aprobado
            R(C(calificacion=5), C(calificacion=8), if_nota=9),        # desaprobado (CF 6,5)
            R(aus, aus, if_ausente=True),                              # ausente
            R(C(calificacion=8), C())])                                # pendiente
        self.assertEqual((fin.total, fin.aprobados, fin.desaprobados, fin.ausentes, fin.pendientes),
                         (4, 1, 1, 1, 1))

    def test_resumen_ifa_cuenta_solo_a_los_que_van(self):
        ifa = resumir_ifa([
            R(C(calificacion=8), C(calificacion=9)),                   # no va (CF 8,5)
            R(C(calificacion=5), C(calificacion=8), if_nota=9),        # aprobado
            R(C(calificacion=5), C(calificacion=6), if_nota=4),        # desaprobado
            R(C(calificacion=5), C(calificacion=6), if_ausente=True),  # ausente
            R(C(calificacion=5), C(calificacion=6))])                  # pendiente
        self.assertEqual((ifa.total, ifa.aprobados, ifa.desaprobados, ifa.ausentes, ifa.pendientes),
                         (4, 1, 1, 1, 1))


if __name__ == "__main__":
    unittest.main()
