"""Pruebas de las reglas de negocio:  python -m unittest discover -s tests -v"""
import unittest

from app.logic.calificaciones import (
    Cuatrimestre as C, Estado, RegistroNotas as R, calcular_calificacion_final,
    evaluar, formatear_cf, necesita_intensificacion_cuatrimestral,
)


class TestCalificaciones(unittest.TestCase):
    def test_promedio_exacto(self):
        # (7 + 8) / 2 = 7,5 (sin truncar)
        self.assertEqual(calcular_calificacion_final(7, 8, va_a_if=False), 7.5)
        r = evaluar(R(C(calificacion=7), C(calificacion=8)))
        self.assertEqual((r.estado, r.calificacion_final), (Estado.APROBADO, 7.5))

    def test_cf_manual_pisa_la_calculada(self):
        r = evaluar(R(C(calificacion=7), C(calificacion=8), cf_manual=6.99))
        self.assertEqual((r.estado, r.calificacion_final, r.cf_calculada),
                         (Estado.DESAPROBADO, 6.99, 7.5))

    def test_formatear_cf(self):
        self.assertEqual([formatear_cf(v) for v in (7.0, 7.5, 7.25, None)],
                         ["7", "7,5", "7,25", ""])

    def test_if_reemplaza_al_promedio(self):
        # C1 = 4 (desaprobado) -> IF; CF = nota IF, aunque el promedio sería 7.
        r = evaluar(R(C(calificacion=4), C(calificacion=10), if_nota=7))
        self.assertTrue(r.va_a_if)
        self.assertEqual((r.estado, r.calificacion_final), (Estado.APROBADO, 7))

    def test_if_desaprobada(self):
        r = evaluar(R(C(calificacion=5), C(calificacion=9), if_nota=5))
        self.assertEqual((r.estado, r.calificacion_final), (Estado.DESAPROBADO, 5))

    def test_a_if_sin_nota(self):
        r = evaluar(R(C(calificacion=5), C(calificacion=9)))
        self.assertEqual((r.estado, r.calificacion_final), (Estado.A_IF, None))

    def test_ausente_va_a_if_con_nota_4_por_defecto(self):
        r = evaluar(R(C(ausente=True), C(calificacion=9)))
        self.assertEqual((r.estado, r.cal_c1, r.va_a_if), (Estado.A_IF_AUSENTE, 4, True))

    def test_ausente_puede_aprobar_en_if(self):
        r = evaluar(R(C(ausente=True), C(ausente=True), if_nota=7))
        self.assertEqual((r.estado, r.calificacion_final), (Estado.APROBADO, 7))

    def test_ausente_que_no_rinde_if_desaprueba(self):
        r = evaluar(R(C(ausente=True), C(calificacion=8), if_ausente=True))
        self.assertEqual((r.estado, r.calificacion_final), (Estado.DESAPROBADO, 4))

    def test_ausente_pisa_calificacion_cargada(self):
        r = evaluar(R(C(calificacion=9, ausente=True), C(calificacion=9), if_nota=None))
        self.assertTrue(r.va_a_if)

    def test_pendiente(self):
        r = evaluar(R(C(calificacion=8), C()))
        self.assertEqual(r.estado, Estado.PENDIENTE)

    def test_intensificacion_cuatrimestral(self):
        self.assertTrue(necesita_intensificacion_cuatrimestral(C(nota1=8, nota2=6)))
        self.assertFalse(necesita_intensificacion_cuatrimestral(C(nota1=8, nota2=7)))
        self.assertTrue(necesita_intensificacion_cuatrimestral(C(ausente=True)))


if __name__ == "__main__":
    unittest.main()
