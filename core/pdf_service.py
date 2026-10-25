import copy
import shutil
import tempfile
import zipfile
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
import pymupdf

from .config import get_template_path, get_soffice_path
from .deck_parser import (
    extraer_secciones_deck,
    parse_carta,
    parse_carta_simple,
    limpiar_linea_entrenador,
    limpiar_linea_energia,
)
from .player_rules import (
    extraer_info_jugador,
    parsear_fecha_nacimiento,
    calcular_categoria_pokemon,
)

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def set_cell_text(cell, text: str) -> None:
    """Asigna texto a una celda de Word manteniendo el formato y estilo de la celda."""
    p = cell.find('w:p', NS)
    if p is None:
        p = ET.SubElement(cell, f"{{{NS['w']}}}p")
    runs = p.findall('w:r', NS)
    if runs:
        r0 = runs[0]
        for r in runs[1:]:
            p.remove(r)
        t = r0.find('w:t', NS)
        if t is None:
            t = ET.SubElement(r0, f"{{{NS['w']}}}t")
            t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        t.text = str(text) if text else ''
    else:
        r0 = ET.SubElement(p, f"{{{NS['w']}}}r")
        t = ET.SubElement(r0, f"{{{NS['w']}}}t")
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        t.text = str(text) if text else ''


def populate_table(tbl, items: list[str], col_extractors) -> None:
    """Rellena una tabla del documento con las cartas correspondientes.
    - Si la cantidad de cartas supera las filas disponibles, DUPLICA las filas necesarias.
    - Si la cantidad de cartas es menor que las disponibles en la plantilla, ELIMINA las filas
      sobrantes para optimizar y compactar al máximo el documento.
    """
    rows = tbl.findall('w:tr', NS)
    header_count = 2  # Fila 0: Título de sección, Fila 1: Nombres de columna
    data_rows = rows[header_count:]
    available = len(data_rows)
    needed = len(items)

    target_count = max(needed, 1 if needed == 0 else needed)

    if needed > available:
        template_row = data_rows[-1] if data_rows else rows[-1]
        for _ in range(needed - available):
            new_row = copy.deepcopy(template_row)
            for c in new_row.findall('w:tc', NS):
                set_cell_text(c, '')
            tbl.append(new_row)
    elif needed < available:
        rows_to_remove = data_rows[target_count:]
        for r in rows_to_remove:
            tbl.remove(r)

    rows = tbl.findall('w:tr', NS)
    data_rows = rows[header_count:]

    for i, row in enumerate(data_rows):
        cells = row.findall('w:tc', NS)
        if i < needed:
            item = items[i]
            values = col_extractors(item)
            for col_idx, val in enumerate(values):
                if col_idx < len(cells):
                    set_cell_text(cells[col_idx], val)
        else:
            for c in cells:
                set_cell_text(c, '')


def populate_player_info(tbl0, info: dict[str, str]) -> None:
    """Rellena la información del jugador en la tabla 0."""
    if not any(info.values()):
        return

    rows = tbl0.findall('w:tr', NS)
    if len(rows) < 2:
        return

    # Fila 0, Celda 0: Nombre del jugador
    if info.get("name"):
        c00 = rows[0].findall('w:tc', NS)[0]
        p0 = c00.find('w:p', NS)
        if p0 is not None:
            runs = p0.findall('w:r', NS)
            for r in runs:
                t = r.find('w:t', NS)
                if t is not None and "Player Name:" in (t.text or ""):
                    t.text = f"Player Name:  {info['name']}"
                    for r_other in runs:
                        if r_other != r:
                            t_other = r_other.find('w:t', NS)
                            if t_other is not None:
                                t_other.text = ""
                    break

    # Fila 1, Celda 0: Player ID y Fecha de Nacimiento
    c10 = rows[1].findall('w:tc', NS)[0]
    ps10 = c10.findall('w:p', NS)
    if info.get("id") and len(ps10) > 0:
        p_id = ps10[0]
        for r in p_id.findall('w:r', NS):
            t = r.find('w:t', NS)
            if t is not None and "Player ID:" in (t.text or ""):
                t.text = f"Player ID:  {info['id']}"
                for r_other in p_id.findall('w:r', NS):
                    if r_other != r:
                        t_other = r_other.find('w:t', NS)
                        if t_other is not None:
                            t_other.text = ""
                break

    if info.get("dob") and len(ps10) > 1:
        p_dob = ps10[1]
        for r in p_dob.findall('w:r', NS):
            t = r.find('w:t', NS)
            if t is not None and "Date Of Birth" in (t.text or ""):
                t.text = f"Date Of Birth  (MM/DD/YYYY):  {info['dob']}"
                for r_other in p_dob.findall('w:r', NS):
                    if r_other != r:
                        t_other = r_other.find('w:t', NS)
                        if t_other is not None:
                            t_other.text = ""
                break

    # Fila 1, Celda 1: División de edad (Junior / Senior / Masters)
    div = info.get("division", "").lower()
    if div:
        c11 = rows[1].findall('w:tc', NS)[1]
        for p in c11.findall('w:p', NS):
            for r in p.findall('w:r', NS):
                t = r.find('w:t', NS)
                if t is not None and t.text:
                    txt_clean = t.text.strip().lower()
                    if "junior" in txt_clean:
                        t.text = "[X] Junior" if "junior" in div else "[  ] Junior"
                    elif "senior" in txt_clean:
                        t.text = "[X] Senior" if "senior" in div else "[  ] Senior"
                    elif "master" in txt_clean:
                        t.text = "[X] Masters" if "master" in div else "[  ] Masters"


def generar_decklist_pdf(
    deck_origen: Path | str | list[str],
    ruta_plantilla: Path | str | None,
    ruta_salida: Path | str,
    info_jugador: dict[str, str] | None = None
) -> Path:
    """Rellena la plantilla oficial y genera el PDF resultante mediante LibreOffice y PyMuPDF."""
    if ruta_plantilla is None:
        ruta_plantilla = get_template_path()
    else:
        ruta_plantilla = Path(ruta_plantilla)
        if not ruta_plantilla.exists():
            if ruta_plantilla.with_suffix(".docx").exists():
                ruta_plantilla = ruta_plantilla.with_suffix(".docx")
            elif ruta_plantilla.with_suffix(".zip").exists():
                ruta_plantilla = ruta_plantilla.with_suffix(".zip")
            else:
                ruta_plantilla = get_template_path()

    ruta_salida = Path(ruta_salida)

    # Cargar líneas del mazo
    if isinstance(deck_origen, (list, tuple)):
        lineas = [l.strip() for l in deck_origen]
    else:
        with open(deck_origen, "r", encoding="utf-8") as f:
            lineas = [l.strip() for l in f]

    # Datos del jugador
    info_archivo = extraer_info_jugador(lineas)
    if info_jugador:
        info_archivo.update({k: v for k, v in info_jugador.items() if v})

    if info_archivo.get("dob") and not info_archivo.get("division"):
        res_dob = parsear_fecha_nacimiento(info_archivo["dob"])
        if res_dob:
            info_archivo["division"] = calcular_categoria_pokemon(res_dob[2])

    pokemon_lines, trainer_lines, energy_lines = extraer_secciones_deck(lineas)

    # Leer el archivo .docx o .zip
    with zipfile.ZipFile(ruta_plantilla, 'r') as zin:
        xml_content = zin.read('word/document.xml')
        root = ET.fromstring(xml_content)
        other_files = {name: zin.read(name) for name in zin.namelist() if name != 'word/document.xml'}

    body = root.find('w:body', NS)
    # Eliminar el párrafo de la URL del cuerpo del documento para evitar saltos de página innecesarios
    if body is not None:
        for p in list(body.findall('w:p', NS)):
            texto_p = ''.join(p.itertext()).strip().lower()
            if "decklistcreator.com" in texto_p:
                body.remove(p)

    tables = root.findall('.//w:tbl', NS)
    if len(tables) < 4:
        raise ValueError("La plantilla no contiene las 4 tablas esperadas (Info, Pokémon, Trainer, Energy).")

    tbl_info = tables[0]
    tbl_pokemon = tables[1]
    tbl_trainer = tables[2]
    tbl_energy = tables[3]

    populate_player_info(tbl_info, info_archivo)

    def extract_pokemon(line: str) -> list[str]:
        qty, name, c_set, num = parse_carta(line)
        return [qty, name, c_set, num]

    def extract_trainer(line: str) -> list[str]:
        cleaned = limpiar_linea_entrenador(line)
        qty, name = parse_carta_simple(cleaned)
        return [qty, name]

    def extract_energy(line: str) -> list[str]:
        cleaned = limpiar_linea_energia(line)
        qty, name = parse_carta_simple(cleaned)
        return [qty, name]

    populate_table(tbl_pokemon, pokemon_lines, extract_pokemon)
    populate_table(tbl_trainer, trainer_lines, extract_trainer)
    populate_table(tbl_energy, energy_lines, extract_energy)

    soffice_exe = get_soffice_path()
    if not soffice_exe:
        raise RuntimeError(
            "No se encontró LibreOffice en el sistema. Es necesario para convertir el documento .docx a .pdf."
        )

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        temp_docx = tmp_path / "decklist_populated.docx"

        new_xml = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        with zipfile.ZipFile(temp_docx, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            zout.writestr('word/document.xml', new_xml)
            for name, content in other_files.items():
                zout.writestr(name, content)

        cmd = [
            str(soffice_exe),
            "--headless",
            "--convert-to", "pdf",
            str(temp_docx),
            "--outdir", str(tmp_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Error al convertir DOCX a PDF con LibreOffice: {res.stderr or res.stdout}")

        temp_pdf = tmp_path / "decklist_populated.pdf"
        if not temp_pdf.exists():
            raise FileNotFoundError("LibreOffice terminó sin generar el archivo PDF.")

        # Añadir la URL verticalmente en el margen derecho en tamaño pequeño
        doc = pymupdf.open(temp_pdf)
        texto_url = "Created by: www.DecklistCreator.com"
        for page in doc:
            page.insert_text(
                pymupdf.Point(page.rect.width - 15, page.rect.height / 2 + 50),
                texto_url,
                fontsize=6.5,
                fontname="helv",
                rotate=270,
                color=(0.45, 0.45, 0.45)
            )

        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(ruta_salida))
        doc.close()

    return ruta_salida
