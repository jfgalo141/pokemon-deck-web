import re

MAPA_ENERGIAS = {
    "{G}": "Grass",
    "{R}": "Fire",
    "{W}": "Water",
    "{L}": "Lightning",
    "{P}": "Psychic",
    "{F}": "Fighting",
    "{D}": "Darkness",
    "{M}": "Metal",
    "{C}": "Colorless",
    "{Y}": "Fairy",
    "{N}": "Dragon",
}

PREFIJOS_IGNORAR_METADATA = (
    "id:", "player id:", "id del jugador:",
    "nombre:", "nombre completo:", "player name:", "name:",
    "fecha de nacimiento:", "date of birth:", "dob:",
    "categoria:", "categoría:", "age division:", "division:",
    "cartas totales:", "total cards:"
)

RE_HEADER_POKEMON = re.compile(
    r"^(?:lista\s+)?pok[eé]mon(?:\s*(?:cards|cartas))?(?:\s*[:\-]?\s*\(?\d*\)?)?$",
    re.IGNORECASE
)
RE_HEADER_TRAINER = re.compile(
    r"^(?:lista\s+)?(?:trainer|trainers|entrenador|entrenadores)(?:\s*(?:cards|cartas))?(?:\s*[:\-]?\s*\(?\d*\)?)?$",
    re.IGNORECASE
)
RE_HEADER_ENERGY = re.compile(
    r"^(?:lista\s+)?(?:energy|energies|energ[ií]as?)(?:\s*(?:cards|cartas))?(?:\s*[:\-]?\s*\(?\d*\)?)?$",
    re.IGNORECASE
)
PATRON_CABECERA_SECCION = re.compile(
    r"^(?:lista\s+)?(?:pok[eé]mon|trainer|trainers|entrenador|entrenadores|energy|energies|energ[ií]as?)(?:\s*(?:cards|cartas))?(?:\s*[:\-]?\s*\(?\d*\)?)?$",
    re.IGNORECASE
)
PATRON_LINEA_CARTA = re.compile(
    r"^(\d+)\s+([A-Za-zÀ-ÿ0-9'’\-\.\s&{}\(\):/]+)$"
)


def es_cabecera_pokemon(linea: str) -> bool:
    return bool(RE_HEADER_POKEMON.match(linea.strip()))


def es_cabecera_trainer(linea: str) -> bool:
    return bool(RE_HEADER_TRAINER.match(linea.strip()))


def es_cabecera_energy(linea: str) -> bool:
    return bool(RE_HEADER_ENERGY.match(linea.strip()))


def es_cabecera_seccion(linea: str) -> bool:
    return es_cabecera_pokemon(linea) or es_cabecera_trainer(linea) or es_cabecera_energy(linea)


def validar_estructura_deck(lineas: list[str]) -> tuple[bool, str]:
    """Valida que el texto introducido cumpla con la estructura de Pokémon TCG Live o Limitless TCG.
    Rechaza textos arbitrarios, conversaciones o líneas que no correspondan a una baraja.
    Devuelve (True, '') si es válida, o (False, mensaje_error) si no cumple la estructura.
    """
    lineas_utiles = []
    for l in lineas:
        s = l.strip()
        if not s:
            continue
        low = s.lower()
        if low.startswith(PREFIJOS_IGNORAR_METADATA):
            continue
        lineas_utiles.append(s)

    if not lineas_utiles:
        return False, "La lista de cartas está vacía. Pega o escribe una baraja en formato Pokémon TCG Live o Limitless."

    cartas_detectadas = 0

    for linea in lineas_utiles:
        # Cabecera de sección válida (Pokémon:, Trainer:, Energy:)
        if es_cabecera_seccion(linea):
            continue

        # Líneas separadoras permitidas (ej. --- o ===)
        if re.match(r"^[-=_*~]{3,}$", linea):
            continue

        # Línea de carta (debe empezar por la cantidad numérica)
        m = PATRON_LINEA_CARTA.match(linea)
        if m:
            qty_str = m.group(1)
            name = m.group(2).strip()
            qty = int(qty_str)
            if qty < 1 or qty > 59:
                return False, f"Cantidad de cartas inválida ({qty}) en la línea: '{linea}'."
            if len(name) < 2:
                return False, f"Nombre de carta no válido en la línea: '{linea}'."
            cartas_detectadas += 1
        else:
            return False, (
                f"El texto no tiene la estructura de una baraja Pokémon TCG (Limitless o Pokémon TCG Live). "
                f"Línea no válida: '{linea}'. Cada carta debe comenzar por su cantidad (ej. '4 Cynthia\\'s Gible DRI 102' o '4 Ultra Ball')."
            )

    if cartas_detectadas == 0:
        return False, "No se encontró ninguna carta válida. Recuerda incluir la cantidad al inicio de cada carta."

    return True, ""


def parse_carta(linea: str) -> tuple[str, str, str, str]:
    """Separa una línea en (cantidad, nombre, expansión/set, número de colección).
    Soporta números de colección numéricos (125) y alfanuméricos (TG09, GG44, etc.).
    """
    m = re.match(
        r"^(\d+)\s+(.+?)(?:\s+([A-Za-z0-9\-]{2,8})\s+([A-Za-z0-9\-/]*\d+[A-Za-z0-9\-/]*))(?:\s+[A-Z]{2})?$",
        linea.strip()
    )
    if m:
        qty = m.group(1)
        name = m.group(2).strip()
        c_set = m.group(3) or ""
        num = m.group(4) or ""
        return qty, name, c_set, num

    partes = linea.strip().split(maxsplit=1)
    if len(partes) == 2 and partes[0].isdigit():
        return partes[0], partes[1], "", ""
    return "1", linea.strip(), "", ""


def parse_carta_simple(linea: str) -> tuple[str, str]:
    """Separa una línea en (cantidad, nombre), ideal para entrenadores y energías."""
    partes = linea.strip().split(maxsplit=1)
    if len(partes) == 2 and partes[0].isdigit():
        return partes[0], partes[1]
    return "1", linea.strip()


def limpiar_linea_entrenador(linea: str) -> str:
    """Elimina el código de expansión y el número de colección al final de una carta de entrenador."""
    return re.sub(
        r'\s+[A-Za-z0-9\-]{2,8}\s+[A-Za-z0-9\-/]*\d+[A-Za-z0-9\-/]*(?:\s+[A-Z]{2})?$',
        '',
        linea.strip()
    ).strip()


def limpiar_linea_energia(linea: str) -> str:
    """Reemplaza {X} por su nombre en inglés y elimina el código de expansión y número final."""
    linea_procesada = linea.strip()
    for abreviatura, nombre_en in MAPA_ENERGIAS.items():
        linea_procesada = re.sub(re.escape(abreviatura), nombre_en, linea_procesada, flags=re.IGNORECASE)
    return re.sub(
        r'\s+[A-Za-z0-9\-]{2,8}\s+[A-Za-z0-9\-/]*\d+[A-Za-z0-9\-/]*(?:\s+[A-Z]{2})?$',
        '',
        linea_procesada
    ).strip()


def extraer_secciones_deck(lineas: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Extrae las cartas de las secciones Pokémon, Trainer y Energy.
    Ignora líneas de metadatos del jugador.
    """
    lineas_limpias = []
    for l in lineas:
        strip_l = l.strip()
        low = strip_l.lower()
        if not low:
            lineas_limpias.append("")
            continue
        if low.startswith(PREFIJOS_IGNORAR_METADATA):
            continue
        lineas_limpias.append(strip_l)

    tiene_cabeceras = any(
        es_cabecera_seccion(l)
        for l in lineas_limpias
    )

    if tiene_cabeceras:
        pokemon_lineas = []
        trainer_lineas = []
        energy_lineas = []
        seccion_actual = None

        for linea in lineas_limpias:
            if not linea:
                continue

            if es_cabecera_pokemon(linea):
                seccion_actual = 'pokemon'
                continue
            elif es_cabecera_trainer(linea):
                seccion_actual = 'trainer'
                continue
            elif es_cabecera_energy(linea):
                seccion_actual = 'energy'
                continue

            if seccion_actual == 'pokemon':
                pokemon_lineas.append(linea)
            elif seccion_actual == 'trainer':
                trainer_lineas.append(linea)
            elif seccion_actual == 'energy':
                energy_lineas.append(linea)

        return pokemon_lineas, trainer_lineas, energy_lineas
    else:
        bloques = []
        bloque_actual = []
        for l in lineas_limpias:
            if l:
                bloque_actual.append(l)
            elif bloque_actual:
                bloques.append(bloque_actual)
                bloque_actual = []
        if bloque_actual:
            bloques.append(bloque_actual)

        pk = bloques[0] if len(bloques) > 0 else []
        tr = bloques[1] if len(bloques) > 1 else []
        en = bloques[2] if len(bloques) > 2 else []
        return pk, tr, en


def transformar_lineas_deck(lineas: list[str]) -> list[str]:
    """Elimina cabeceras de sección y limpia expansión/número de entrenadores y energías,
    traduciendo además las abreviaturas {X} de las energías a su nombre en inglés.
    """
    lineas_limpias = [
        l.strip() for l in lineas
        if not l.strip().lower().startswith(PREFIJOS_IGNORAR_METADATA)
    ]

    tiene_cabeceras = any(
        es_cabecera_seccion(l)
        for l in lineas_limpias
    )

    if tiene_cabeceras:
        resultado = []
        seccion_actual = None

        for linea in lineas_limpias:
            if not linea:
                if resultado and resultado[-1] != "":
                    resultado.append("")
                continue

            if es_cabecera_pokemon(linea):
                if resultado and resultado[-1] != "":
                    resultado.append("")
                seccion_actual = "pokemon"
                continue
            elif es_cabecera_trainer(linea):
                if resultado and resultado[-1] != "":
                    resultado.append("")
                seccion_actual = "entrenador"
                continue
            elif es_cabecera_energy(linea):
                if resultado and resultado[-1] != "":
                    resultado.append("")
                seccion_actual = "energia"
                continue

            if seccion_actual == "entrenador":
                resultado.append(limpiar_linea_entrenador(linea))
            elif seccion_actual == "energia":
                resultado.append(limpiar_linea_energia(linea))
            else:
                resultado.append(linea)

        while resultado and resultado[0] == "":
            resultado.pop(0)
        while resultado and resultado[-1] == "":
            resultado.pop()

        return resultado
    else:
        bloques = []
        bloque_actual = []
        for linea in lineas_limpias:
            if linea:
                bloque_actual.append(linea)
            elif bloque_actual:
                bloques.append(bloque_actual)
                bloque_actual = []
        if bloque_actual:
            bloques.append(bloque_actual)

        resultado = []
        if len(bloques) > 0:
            resultado.extend(bloques[0])
        if len(bloques) > 1:
            resultado.append("")
            resultado.extend(limpiar_linea_entrenador(c) for c in bloques[1])
        if len(bloques) > 2:
            resultado.append("")
            resultado.extend(limpiar_linea_energia(c) for c in bloques[2])

        return resultado
