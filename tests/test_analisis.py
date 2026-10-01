"""Pruebas de los datos de la vista Análisis:  python -m unittest discover -s tests -v"""
import unittest
from types import SimpleNamespace

from app.logic.analisis import (
    NOTA_CC1, NOTA_CF, histograma, resumen_por_etapa, resumen_por_grupo, riesgo, transiciones,
)
from app.logic.calificaciones import Cuatrimestre as C, Estado, RegistroNotas as R

DESAPRUEBA = R(C(calificacion=5), C(calificacion=6))   # CF 5,5
APRUEBA = R(C(calificacion=8), C(calificacion=8))      # CF 8


def fila(alumno_id: int, materia: str, reg: R):
    return SimpleNamespace(alumno_id=alumno_id, nombre_completo=f"Alumno {alumno_id}",
                           curso=SimpleNamespace(etiqueta="1°1°"), materia=materia, registro=reg)


class TestAnalisis(unittest.TestCase):
    def test_resumen_por_etapa_en_orden_de_cursada(self):
        regs = [R(C(calificacion=8), C(calificacion=9)),     # CF 8,5
                R(C(calificacion=5), C(calificacion=6), if_nota=8)]  # CF 5,5 -> IFA aprobada
        etapas = resumen_por_etapa(regs)
        self.assertEqual([clave for clave, _, _ in etapas], ["1", "2", "final", "ifa"])
        final, ifa = etapas[2][2], etapas[3][2]
        self.assertEqual((final.total, final.aprobados, final.desaprobados), (2, 1, 1))
        self.assertEqual((ifa.total, ifa.aprobados), (1, 1))

    def test_resumen_por_grupo_ordena_por_desaprobados(self):
        items = [("Lengua", R(C(calificacion=8), C(calificacion=8))),
                 ("Matemática", R(C(calificacion=4), C(calificacion=5))),
                 ("Lengua", R(C(calificacion=5), C(calificacion=5)))]
        grupos = resumen_por_grupo(items, lambda it: it[0], lambda it: it[1], "final")
        self.assertEqual([(n, r.total, r.desaprobados) for n, r in grupos],
                         [("Matemática", 1, 1), ("Lengua", 2, 1)])

    def test_resumen_por_grupo_omite_grupos_vacios_en_ifa(self):
        items = [("A", R(C(calificacion=8), C(calificacion=8))),
                 ("B", R(C(calificacion=5), C(calificacion=5)))]
        grupos = resumen_por_grupo(items, lambda it: it[0], lambda it: it[1], "ifa")
        self.assertEqual([n for n, _ in grupos], ["B"])

    def test_histograma_de_cf_con_zona_limite(self):
        regs = [R(C(calificacion=6), C(calificacion=7)),     # 6,5 -> zona límite, cuenta en el 6
                R(C(calificacion=7), C(calificacion=7)),     # 7
                R(C(calificacion=10), C(calificacion=10)),   # 10
                R(C(calificacion=8), C())]                   # sin CF
        h = histograma(regs, NOTA_CF)
        self.assertEqual((h.conteos[5], h.conteos[6], h.conteos[9]), (1, 1, 1))
        self.assertEqual((h.con_nota, h.sin_nota, h.zona_limite), (3, 1, 1))

    def test_histograma_de_cc_ignora_el_4_del_ausente(self):
        regs = [R(C(ausente=True), C()), R(C(calificacion=6), C())]
        h = histograma(regs, NOTA_CC1)
        self.assertEqual((h.conteos[3], h.conteos[5], h.sin_nota, h.zona_limite), (0, 1, 1, 1))

    def test_transiciones_por_fila(self):
        t = transiciones([R(C(calificacion=5), C(calificacion=8)),     # desaprobó -> aprobó
                          R(C(calificacion=5), C(calificacion=4)),     # desaprobó -> desaprobó
                          R(C(calificacion=5), C(ausente=True)),       # desaprobó -> ausente
                          R(C(calificacion=9), C(calificacion=9))])    # aprobó -> aprobó
        self.assertEqual(t.total_fila(Estado.DESAPROBADO), 3)
        self.assertEqual(t.cantidad(Estado.DESAPROBADO, Estado.APROBADO), 1)
        self.assertAlmostEqual(t.pct_fila(Estado.DESAPROBADO, Estado.AUSENTE), 100 / 3)
        self.assertEqual(t.pct_fila(Estado.AUSENTE, Estado.APROBADO), 0.0)

    def test_riesgo_cuenta_materias_con_cf_menor_a_7(self):
        filas = ([fila(1, m, DESAPRUEBA) for m in ("Lengua", "Matemática", "Historia", "Biología")]
                 + [fila(2, "Lengua", DESAPRUEBA), fila(2, "Matemática", APRUEBA)]
                 + [fila(3, "Lengua", APRUEBA), fila(3, "Matemática", R(C(calificacion=8), C()))]  # pendiente no suma
                 + [fila(4, m, DESAPRUEBA) for m in ("Lengua", "Matemática", "Historia")])
        r = riesgo(filas, minimo=3)
        self.assertEqual(r.por_cantidad, [1, 1, 0, 2])
        self.assertEqual([(a.alumno_id, len(a.materias)) for a in r.en_riesgo], [(1, 4), (4, 3)])


if __name__ == "__main__":
    unittest.main()
