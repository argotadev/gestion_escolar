"""Datos estáticos de la escuela: departamentos, cursos y materias.

Fuente: datos.txt y la planilla de materias del ciclo orientado.
"""

# Departamento -> (jefe de departamento inicial; editable desde la GUI)
DEPARTAMENTOS = {
    "Ciencias Sociales y Construcción de Ciudadanía": "RODRIGUEZ, LIZ ELIZABETH",
    "Lengua y Comunicación": "",
    "Matemáticas": "",
    "Lenguas Extranjeras y Nativa": "",
    "Ciencias Naturales": "",
    "Educación Artística": "",
    "Educación Física": "",
    "Ciencias Económicas y Administrativo Contables": "",
    "Educación Científico-Tecnológica": "",
}

_CS = "Ciencias Sociales y Construcción de Ciudadanía"
_LC = "Lengua y Comunicación"
_MA = "Matemáticas"
_LE = "Lenguas Extranjeras y Nativa"
_CN = "Ciencias Naturales"
_EA = "Educación Artística"
_EF = "Educación Física"
_CE = "Ciencias Económicas y Administrativo Contables"
_CT = "Educación Científico-Tecnológica"

# Materia -> departamento
MATERIA_DEPARTAMENTO = {
    # Ciencias Sociales
    "Geografía": _CS, "Formación Ética y Ciudadana": _CS, "Historia": _CS,
    "Historia Latinoamericana y Argentina I": _CS,
    "Historia Latinoamericana y Argentina II": _CS,
    "Geografía y Latinoamericana": _CS, "Geografía Argentina": _CS,
    "Comunicación Social": _CS, "Psicología": _CS, "Sociología": _CS,
    "Filosofía": _CS, "Filosofía de la Ciencia": _CS, "Ciencias Políticas": _CS,
    "Seminario de los Procesos Políticos, Sociales, Ambientales y Culturales "
    "del Territorio Correntino": _CS,
    # Lengua, Matemática, Lengua extranjera
    "Lengua y Literatura": _LC,
    "Matemática": _MA,
    "Lengua Extranjera": _LE,
    # Ciencias Naturales
    "Biología": _CN, "Físico-Química": _CN, "Química": _CN, "Física": _CN,
    "Ciencias de la Tierra": _CN, "Física y Astronomía": _CN, "Ecología": _CN,
    "Seminario de Integración Salud": _CN,
    "Seminario de Integración Ambiente y Sociedad": _CN,
    # Arte y Educación Física
    "Educación Artística": _EA, "Taller de Lenguajes Artísticos": _EA,
    "Educación Física": _EF,
    # Económicas
    "Introducción a la Administración": _CE, "Economía": _CE,
    "Teoría y Gestión de las Organizaciones": _CE,
    "Sistema de Información Contable": _CE, "Derecho Comercial y Laboral": _CE,
    "Administración de Empresas": _CE, "Gestión Financiera e Impositiva": _CE,
    "Economía Política": _CE,
    # Científico-tecnológica
    "Educación Tecnológica": _CT, "TIC": _CT,
    "EDI (Espacio de Definición Institucional)": _CT,
}

# ---- Ciclo básico (1º a 3º): materias por año -----------------------------
_BASICAS_COMUNES = [
    "Geografía", "Formación Ética y Ciudadana", "Historia",
    "Lengua y Literatura", "Lengua Extranjera", "Matemática",
    "Educación Física", "Educación Artística", "Educación Tecnológica",
]
MATERIAS_BASICO = {
    1: _BASICAS_COMUNES + ["Biología"],
    2: _BASICAS_COMUNES + ["Biología", "Físico-Química"],
    3: _BASICAS_COMUNES + ["Biología", "Físico-Química"],
}

# ---- Ciclo orientado (4º a 6º): por año y orientación ----------------------
ECO = "Bachiller en Economía y Administración"
CNAT = "Bachiller en Ciencias Naturales"
CSOC = "Bachiller en Ciencias Sociales"

# Orientación -> divisiones
ORIENTACIONES = {ECO: (1, 2, 3, 4), CNAT: (5, 6), CSOC: (7, 8)}

_EDI = "EDI (Espacio de Definición Institucional)"
_BASE = ["Lengua y Literatura", "Lengua Extranjera", "Matemática", "Educación Física"]

MATERIAS_ORIENTADO = {
    (4, ECO): _BASE + ["Biología", "Historia", "Introducción a la Administración",
                       "Geografía", "TIC", "Formación Ética y Ciudadana"],
    (4, CNAT): _BASE + ["Historia", "Química", "Geografía", "Biología", "TIC",
                        "Formación Ética y Ciudadana"],
    (4, CSOC): _BASE + ["Historia Latinoamericana y Argentina I", "Biología",
                        "Taller de Lenguajes Artísticos",
                        "Geografía y Latinoamericana", "TIC", "Comunicación Social"],
    (5, ECO): _BASE + ["Física", "Economía", "Teoría y Gestión de las Organizaciones",
                       "Taller de Lenguajes Artísticos",
                       "Sistema de Información Contable", "Química"],
    (5, CNAT): _BASE + ["Física", "Psicología", "Taller de Lenguajes Artísticos",
                        "Química", "Biología", "Ciencias de la Tierra"],
    (5, CSOC): _BASE + ["Historia Latinoamericana y Argentina II", "Psicología",
                        "Química", "Geografía Argentina", "Economía Política", "Física"],
    (6, ECO): _BASE + ["Derecho Comercial y Laboral", "Economía",
                       "Teoría y Gestión de las Organizaciones",
                       "Administración de Empresas",
                       "Gestión Financiera e Impositiva", _EDI],
    (6, CNAT): _BASE + ["Filosofía de la Ciencia", "Física y Astronomía", "Ecología",
                        "Seminario de Integración Salud",
                        "Seminario de Integración Ambiente y Sociedad", _EDI],
    (6, CSOC): _BASE + ["Filosofía", "Sociología",
                        "Seminario de los Procesos Políticos, Sociales, Ambientales "
                        "y Culturales del Territorio Correntino",
                        "Ciencias Políticas", "Formación Ética y Ciudadana", _EDI],
}

DIVISIONES_BASICO = range(1, 11)     # 1.1 ... 1.10 (idem 2º y 3º)
