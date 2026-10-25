import re

PREFIJOS_METADATA_JUGADOR = (
    "id:", "player id:", "id del jugador:",
    "nombre:", "nombre completo:", "player name:", "name:",
    "fecha de nacimiento:", "date of birth:", "dob:",
    "categoria:", "categoría:", "age division:", "division:",
)


def calcular_categoria_pokemon(anio_nacimiento: int, temporada: int = 2025) -> str:
    """Calcula la categoría de edad oficial según las reglas de Play! Pokémon TCG.
    Para la temporada 2025:
    - Junior: nacidos en 2013 o posterior
    - Senior: nacidos entre 2009 y 2012
    - Masters: nacidos en 2008 o anterior
    """
    if anio_nacimiento <= (temporada - 17):
        return "Masters"
    elif anio_nacimiento <= (temporada - 13):
        return "Senior"
    else:
        return "Junior"


def parsear_fecha_nacimiento(fecha_str: str) -> tuple[str, str, int] | None:
    """Parsea una fecha de nacimiento en diversos formatos (DD/MM/AAAA, AAAA-MM-DD, etc.)
    Devuelve (fecha_formato_es, fecha_formato_us, anio) o None si no es válida.
    """
    if not fecha_str:
        return None

    fecha_limpia = re.sub(r'[\.\-\s]', '/', str(fecha_str).strip())
    partes = [p for p in fecha_limpia.split('/') if p]

    if len(partes) == 1 and len(partes[0]) == 4 and partes[0].isdigit():
        anio = int(partes[0])
        return f"01/01/{anio}", f"01/01/{anio}", anio

    if len(partes) == 3:
        p1, p2, p3 = partes
        if len(p1) == 4 and p1.isdigit():
            anio = int(p1)
            mes = int(p2)
            dia = int(p3)
        elif len(p3) == 4 and p3.isdigit():
            anio = int(p3)
            v1, v2 = int(p1), int(p2)
            if v1 > 12 >= v2:
                dia, mes = v1, v2
            elif v2 > 12 >= v1:
                mes, dia = v1, v2
            else:
                dia, mes = v1, v2
        elif len(p3) == 2 and p3.isdigit():
            anio = 2000 + int(p3) if int(p3) <= 30 else 1900 + int(p3)
            dia, mes = int(p1), int(p2)
        else:
            return None

        if not (1 <= mes <= 12 and 1 <= dia <= 31 and 1900 <= anio <= 2030):
            return None

        fecha_es = f"{dia:02d}/{mes:02d}/{anio}"
        fecha_us = f"{mes:02d}/{dia:02d}/{anio}"
        return fecha_es, fecha_us, anio

    return None


def extraer_info_jugador(lineas: list[str]) -> dict[str, str]:
    """Extrae información del jugador (Nombre, ID, Fecha de Nacimiento, Categoría) si está presente."""
    info = {"name": "", "id": "", "dob": "", "division": ""}
    for l in lineas:
        strip_l = l.strip()
        low = strip_l.lower()
        if low.startswith(("nombre completo:", "nombre:", "player name:", "name:")):
            info["name"] = strip_l.split(":", 1)[1].strip()
        elif low.startswith(("player id:", "id:", "id del jugador:")):
            info["id"] = strip_l.split(":", 1)[1].strip()
        elif low.startswith(("fecha de nacimiento:", "date of birth:", "dob:")):
            info["dob"] = strip_l.split(":", 1)[1].strip()
        elif low.startswith(("categoria:", "categoría:", "age division:", "division:")):
            info["division"] = strip_l.split(":", 1)[1].strip()
    return info
