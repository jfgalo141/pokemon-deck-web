from pathlib import Path
from typing import Literal
import re
import tempfile
import shutil

from .config import (
    EXAMPLES_DIR,
    EXPORTS_PDF_DIR,
    EXPORTS_TXT_DIR,
    LEGACY_PDF_DIR,
    LEGACY_TRANSFORM_DIR,
    get_template_path,
)
from .deck_parser import (
    extraer_secciones_deck,
    transformar_lineas_deck,
)
from .player_rules import (
    parsear_fecha_nacimiento,
    calcular_categoria_pokemon,
    extraer_info_jugador,
)
from .pdf_service import generar_decklist_pdf


def obtener_ruta_unica(carpeta: Path, nombre_base: str, extension: str) -> Path:
    """Genera una ruta que no colisione con archivos existentes."""
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{nombre_base}{extension}"
    contador = 1
    while ruta.exists():
        ruta = carpeta / f"{nombre_base} ({contador}){extension}"
        contador += 1
    return ruta


def listar_barajas_ejemplo() -> list[dict]:
    """Devuelve la lista de barajas disponibles en la carpeta de ejemplos."""
    barajas = []
    if not EXAMPLES_DIR.exists():
        return barajas

    for archivo in sorted(EXAMPLES_DIR.glob("*.txt")):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                lineas = [l.strip() for l in f]
            pk, tr, en = extraer_secciones_deck(lineas)
            info = extraer_info_jugador(lineas)
            barajas.append({
                "filename": archivo.name,
                "name": archivo.stem,
                "path": str(archivo),
                "pokemon_count": len(pk),
                "trainer_count": len(tr),
                "energy_count": len(en),
                "total_cards": len(pk) + len(tr) + len(en),
                "player_info": info,
            })
        except Exception:
            continue
    return barajas


def procesar_datos_jugador(nombre: str, player_id: str, fecha_nacimiento_raw: str) -> dict:
    """Valida y estructura los datos del jugador, calculando su categoría oficial."""
    res_dob = parsear_fecha_nacimiento(fecha_nacimiento_raw)
    if not res_dob:
        raise ValueError(
            f"La fecha de nacimiento '{fecha_nacimiento_raw}' no es válida. Debe tener formato DD/MM/AAAA o AAAA-MM-DD."
        )

    fecha_es, fecha_us, anio = res_dob
    categoria = calcular_categoria_pokemon(anio)

    return {
        "name": nombre.strip(),
        "id": player_id.strip(),
        "dob": fecha_us,       # Formato MM/DD/YYYY para PDF
        "dob_es": fecha_es,    # Formato DD/MM/AAAA para TXT
        "year": anio,
        "division": categoria,
    }


def generar_baraja_en_memoria(
    deck_input: list[str] | str,
    player_info: dict,
    formato: Literal["pdf", "txt", "ambos"] = "ambos",
    nombre_base: str = "deck"
) -> dict:
    """Genera los documentos en memoria (bytes) sin guardar absolutamente nada en disco
    ni buscar duplicados. Mantiene el nombre exacto especificado por el usuario (sin sufijo _DECKLIST).
    """
    if isinstance(deck_input, str):
        lineas = [l.strip() for l in deck_input.splitlines()]
    else:
        lineas = [l.strip() for l in deck_input]

    # Validar y completar datos del jugador
    if not player_info.get("division") and player_info.get("dob"):
        res = parsear_fecha_nacimiento(player_info["dob"])
        if res:
            player_info["division"] = calcular_categoria_pokemon(res[2])
            player_info["dob_es"] = res[0]
            player_info["dob"] = res[1]

    # Limpiar nombre para nombre de archivo seguro manteniendo el texto del usuario
    safe_name = re.sub(r'[\\/*?:"<>|]', '_', nombre_base.strip()) or "deck"

    archivos = {}

    # 1. Exportar TXT en memoria
    if formato in ("txt", "ambos", "2", "3"):
        lineas_trans = transformar_lineas_deck(lineas)
        fecha_txt = player_info.get("dob_es") or player_info.get("dob", "")
        cabecera_txt = [
            f"Nombre Completo: {player_info.get('name', '')}",
            f"ID: {player_info.get('id', '')}",
            f"Fecha de Nacimiento: {fecha_txt}",
            f"Categoria: {player_info.get('division', '')}",
            "",
        ]
        txt_str = "\n".join(cabecera_txt + lineas_trans) + "\n"
        archivos["txt"] = {
            "filename": f"{safe_name}.txt",
            "bytes": txt_str.encode("utf-8"),
            "mime": "text/plain; charset=utf-8",
        }

    # 2. Exportar PDF en memoria (usando directorio temporal que se destruye de inmediato)
    if formato in ("pdf", "ambos", "1", "3"):
        plantilla = get_template_path()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_pdf = Path(tmp_dir) / f"{safe_name}.pdf"
            generar_decklist_pdf(lineas, plantilla, tmp_pdf, info_jugador=player_info)
            with open(tmp_pdf, "rb") as f:
                pdf_bytes = f.read()

        archivos["pdf"] = {
            "filename": f"{safe_name}.pdf",
            "bytes": pdf_bytes,
            "mime": "application/pdf",
        }

    return {
        "success": True,
        "deck_name": safe_name,
        "player": player_info,
        "files_data": archivos,
    }


def exportar_baraja(
    deck_input: list[str] | str | Path,
    player_info: dict,
    formato: Literal["pdf", "txt", "ambos"] = "ambos",
    nombre_base: str = "deck",
    guardar_en_disco: bool = False
) -> dict:
    """Servicio principal de exportación.
    Por defecto (guardar_en_disco=False), genera los documentos en memoria sin tocar el disco.
    Si guardar_en_disco=True, guarda en disco usando el nombre exacto sin sufijos obligatorios.
    """
    if not guardar_en_disco:
        return generar_baraja_en_memoria(
            deck_input=deck_input if not isinstance(deck_input, Path) else [l.strip() for l in open(deck_input, 'r', encoding='utf-8')],
            player_info=player_info,
            formato=formato,
            nombre_base=nombre_base
        )

    if isinstance(deck_input, (str, Path)) and Path(str(deck_input)).exists():
        with open(deck_input, "r", encoding="utf-8") as f:
            lineas = [l.rstrip("\r\n") for l in f]
    elif isinstance(deck_input, str):
        lineas = [l.strip() for l in deck_input.splitlines()]
    else:
        lineas = [l.strip() for l in deck_input]

    if not player_info.get("division") and player_info.get("dob"):
        res = parsear_fecha_nacimiento(player_info["dob"])
        if res:
            player_info["division"] = calcular_categoria_pokemon(res[2])
            player_info["dob_es"] = res[0]
            player_info["dob"] = res[1]

    safe_name = re.sub(r'[\\/*?:"<>|]', '_', nombre_base.strip()) or "deck"
    resultados = {
        "success": True,
        "deck_name": safe_name,
        "player": player_info,
        "files": {},
    }

    if formato in ("txt", "ambos", "2", "3"):
        lineas_trans = transformar_lineas_deck(lineas)
        fecha_txt = player_info.get("dob_es") or player_info.get("dob", "")
        cabecera_txt = [
            f"Nombre Completo: {player_info.get('name', '')}",
            f"ID: {player_info.get('id', '')}",
            f"Fecha de Nacimiento: {fecha_txt}",
            f"Categoria: {player_info.get('division', '')}",
            "",
        ]
        lineas_finales = cabecera_txt + lineas_trans
        ruta_txt = EXPORTS_TXT_DIR / f"{safe_name}.txt"
        EXPORTS_TXT_DIR.mkdir(parents=True, exist_ok=True)
        with open(ruta_txt, "w", encoding="utf-8") as f:
            for l in lineas_finales:
                f.write(f"{l}\n")
        resultados["files"]["txt"] = str(ruta_txt)

    if formato in ("pdf", "ambos", "1", "3"):
        plantilla = get_template_path()
        ruta_pdf = EXPORTS_PDF_DIR / f"{safe_name}.pdf"
        EXPORTS_PDF_DIR.mkdir(parents=True, exist_ok=True)
        generar_decklist_pdf(lineas, plantilla, ruta_pdf, info_jugador=player_info)
        resultados["files"]["pdf"] = str(ruta_pdf)

    return resultados
