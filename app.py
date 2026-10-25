import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en sys.path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import atexit
import base64
import io
import json
import mimetypes
import os
import re
import time
import urllib.parse
import uuid
import zipfile
import xml.etree.ElementTree as ET
try:
    from http.server import ThreadingHTTPServer as ServerClass, BaseHTTPRequestHandler
except ImportError:
    from http.server import HTTPServer as ServerClass, BaseHTTPRequestHandler

from core.config import (
    BASE_DIR,
    FRONT_DIR,
    EXAMPLES_DIR,
    EXPORTS_PDF_DIR,
    EXPORTS_TXT_DIR,
    LEGACY_PDF_DIR,
    LEGACY_TRANSFORM_DIR,
    get_template_path,
)
from core.player_rules import (
    parsear_fecha_nacimiento,
    calcular_categoria_pokemon,
    extraer_info_jugador,
)
from core.deck_parser import transformar_lineas_deck, validar_estructura_deck
from core.pdf_service import generar_decklist_pdf
from core.deck_service import (
    listar_barajas_ejemplo,
    exportar_baraja,
    generar_baraja_en_memoria,
)

PORT = int(os.environ.get("PORT", 8000))


def limpiar_carpetas_temporales():
    """Elimina todos los archivos temporales de PDF/ y TRANSFORM/ para no gastar almacenamiento."""
    for carpeta in (LEGACY_PDF_DIR, LEGACY_TRANSFORM_DIR):
        if carpeta.exists():
            for archivo in carpeta.glob("*"):
                if archivo.is_file():
                    try:
                        archivo.unlink()
                    except Exception:
                        pass


def limpiar_archivos_antiguos(segundos_max: int = 300):
    """Elimina archivos temporales huérfanos que lleven más de 5 minutos sin ser descargados."""
    ahora = time.time()
    for carpeta in (LEGACY_PDF_DIR, LEGACY_TRANSFORM_DIR):
        if carpeta.exists():
            for archivo in carpeta.glob("*"):
                if archivo.is_file():
                    try:
                        if ahora - archivo.stat().st_mtime > segundos_max:
                            archivo.unlink()
                    except Exception:
                        pass


# Limpiar al arrancar y registrar limpieza al salir
limpiar_carpetas_temporales()
atexit.register(limpiar_carpetas_temporales)


def extraer_texto_de_archivo(filename: str, bytes_data: bytes | None = None, texto: str | None = None) -> str:
    """Extrae el contenido textual de archivos .txt, .deck o .docx."""
    if texto is not None:
        return texto
    if not bytes_data:
        return ""
    if filename.lower().endswith(".docx"):
        with zipfile.ZipFile(io.BytesIO(bytes_data)) as z:
            xml_c = z.read("word/document.xml")
            root = ET.fromstring(xml_c)
            ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
            lines = []
            for p in root.iter(ns + "p"):
                t = "".join(node.text for node in p.iter(ns + "t") if node.text)
                if t.strip():
                    lines.append(t.strip())
            return "\n".join(lines)
    else:
        try:
            return bytes_data.decode("utf-8")
        except UnicodeDecodeError:
            return bytes_data.decode("latin-1", errors="replace")


class DeckAppHandler(BaseHTTPRequestHandler):

    def _send_json(self, data: dict | list, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: Path, download_name: str | None = None):
        if not file_path.exists():
            self.send_error(404, "Archivo no encontrado")
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"

        with open(file_path, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(content)))
        if download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        limpiar_archivos_antiguos()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        # Rutas de la API
        if path == "/api/decks":
            decks = listar_barajas_ejemplo()
            self._send_json(decks)
            return

        elif path == "/api/deck-content":
            name = params.get("name", [""])[0]
            if not name.endswith(".txt"):
                name += ".txt"
            target = EXAMPLES_DIR / name
            if not target.exists():
                self._send_json({"error": "Mazo no encontrado"}, status=404)
                return
            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
            info = extraer_info_jugador(content.splitlines())
            self._send_json({"name": target.stem, "content": content, "player_info": info})
            return

        elif path == "/api/cleanup-temp":
            limpiar_carpetas_temporales()
            self._send_json({"success": True})
            return

        elif path.startswith("/download/temp/pdf/"):
            filename = urllib.parse.unquote(path[len("/download/temp/pdf/"):])
            file_path = LEGACY_PDF_DIR / filename
            if not file_path.exists():
                self.send_error(404, "El archivo ya fue descargado o eliminado.")
                return
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(content)
            # Eliminar archivo temporal tras ser descargado
            try:
                file_path.unlink()
            except Exception:
                pass
            return

        elif path.startswith("/download/temp/txt/"):
            filename = urllib.parse.unquote(path[len("/download/temp/txt/"):])
            file_path = LEGACY_TRANSFORM_DIR / filename
            if not file_path.exists():
                self.send_error(404, "El archivo ya fue descargado o eliminado.")
                return
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(content)
            # Eliminar archivo temporal tras ser descargado
            try:
                file_path.unlink()
            except Exception:
                pass
            return

        # Archivos estáticos del frontend (Front/)
        if path == "/" or path == "/index.html":
            file_to_serve = FRONT_DIR / "index.html"
        else:
            rel_path = path.lstrip("/")
            file_to_serve = FRONT_DIR / rel_path

        if file_to_serve.exists() and file_to_serve.is_file():
            self._send_file(file_to_serve)
        else:
            self.send_error(404, "Recurso no encontrado")

    def do_POST(self):
        limpiar_archivos_antiguos()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_len)

        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            self._send_json({"error": "JSON no válido"}, status=400)
            return

        # 1. Cálculo de categoría en tiempo real
        if path == "/api/category":
            dob_str = payload.get("dob", "")
            res_dob = parsear_fecha_nacimiento(dob_str)
            if res_dob:
                f_es, f_us, anio = res_dob
                categoria = calcular_categoria_pokemon(anio)
                self._send_json({
                    "valid": True,
                    "year": anio,
                    "division": categoria,
                    "dob_es": f_es,
                    "dob_us": f_us,
                })
            else:
                self._send_json({"valid": False, "error": "Formato de fecha inválido"})
            return

        # 2. Lectura y extracción de archivos subidos (.txt, .docx, .deck)
        elif path == "/api/read-file":
            filename = payload.get("filename", "baraja.txt")
            b64_content = payload.get("content_base64", "")
            raw_text = payload.get("content_text", None)

            bytes_data = None
            if b64_content:
                if "," in b64_content:
                    b64_content = b64_content.split(",", 1)[1]
                try:
                    bytes_data = base64.b64decode(b64_content)
                except Exception as e:
                    self._send_json({"success": False, "error": f"Base64 inválido: {e}"}, status=400)
                    return

            try:
                extracted_text = extraer_texto_de_archivo(filename, bytes_data=bytes_data, texto=raw_text)
                lines = extracted_text.splitlines()
                info = extraer_info_jugador(lines)

                day, month, year, division = "", "", "", ""
                if info.get("dob"):
                    res_dob = parsear_fecha_nacimiento(info["dob"])
                    if res_dob:
                        f_es, _, anio = res_dob
                        partes = f_es.split("/")
                        day = partes[0]
                        month = partes[1]
                        year = str(anio)
                        division = calcular_categoria_pokemon(anio)

                stem = Path(filename).stem
                self._send_json({
                    "success": True,
                    "filename": filename,
                    "name": stem,
                    "content": extracted_text,
                    "player_info": {
                        "name": info.get("name", ""),
                        "id": info.get("id", ""),
                        "dob": info.get("dob", ""),
                        "day": day,
                        "month": month,
                        "year": year,
                        "division": division,
                    }
                })
            except Exception as e:
                self._send_json({"success": False, "error": f"Error al procesar archivo: {e}"}, status=400)
            return

        elif path == "/api/cleanup-temp":
            limpiar_carpetas_temporales()
            self._send_json({"success": True})
            return

        # 3. Formatear y obtener texto estructurado para copiar al portapapeles
        elif path == "/api/format-txt":
            player_name = payload.get("player_name", "").strip()
            player_id = payload.get("player_id", "").strip()
            dob_raw = payload.get("dob", "").strip()
            deck_content = payload.get("deck", "").strip()

            if not player_name or not player_id or not dob_raw or not deck_content:
                self._send_json(
                    {"success": False, "error": "Faltan campos obligatorios (Nombre, ID, Fecha de Nacimiento o Contenido de la Baraja)."},
                    status=400
                )
                return

            es_valido, err_deck = validar_estructura_deck(deck_content.splitlines())
            if not es_valido:
                self._send_json({"success": False, "error": err_deck}, status=400)
                return

            res_dob = parsear_fecha_nacimiento(dob_raw)
            if not res_dob:
                self._send_json(
                    {"success": False, "error": "La fecha de nacimiento no tiene un formato válido (DD/MM/YYYY)."},
                    status=400
                )
                return

            f_es, f_us, anio = res_dob
            categoria = calcular_categoria_pokemon(anio)

            player_info = {
                "name": player_name,
                "id": player_id,
                "dob": f_us,
                "dob_es": f_es,
                "division": categoria,
            }

            lineas_trans = transformar_lineas_deck(deck_content.splitlines())
            cabecera_txt = [
                f"Nombre Completo: {player_name}",
                f"ID: {player_id}",
                f"Fecha de Nacimiento: {f_es}",
                f"Categoria: {categoria}",
                "",
            ]
            formatted_text = "\n".join(cabecera_txt + lineas_trans)

            self._send_json({
                "success": True,
                "formatted_text": formatted_text,
                "player": player_info,
            })
            return

        # 4. Exportación de baraja en PDF
        elif path == "/api/export":
            player_name = payload.get("player_name", "").strip()
            player_id = payload.get("player_id", "").strip()
            dob_raw = payload.get("dob", "").strip()
            deck_content = payload.get("deck", "").strip()
            custom_name = payload.get("custom_name", "").strip() or "deck"
            formato = payload.get("format", "ambos")

            if not player_name or not player_id or not dob_raw or not deck_content:
                self._send_json(
                    {"success": False, "error": "Faltan campos obligatorios (Nombre, ID, Fecha de Nacimiento o Contenido de la Baraja)."},
                    status=400
                )
                return

            # Validar que el texto sea una baraja Pokémon TCG válida (Limitless o PTCG Live)
            es_valido, err_deck = validar_estructura_deck(deck_content.splitlines())
            if not es_valido:
                self._send_json(
                    {"success": False, "error": err_deck},
                    status=400
                )
                return

            res_dob = parsear_fecha_nacimiento(dob_raw)
            if not res_dob:
                self._send_json(
                    {"success": False, "error": "La fecha de nacimiento no tiene un formato válido (DD/MM/AAAA)."},
                    status=400
                )
                return

            f_es, f_us, anio = res_dob
            categoria = calcular_categoria_pokemon(anio)

            player_info = {
                "name": player_name,
                "id": player_id,
                "dob": f_us,
                "dob_es": f_es,
                "division": categoria,
            }

            try:
                # Nombre exacto introducido por el usuario sin sufijos _DECKLIST ni _TRANSFORM
                safe_name = re.sub(r'[\\/*?:"<>|]', '_', custom_name).strip() or "deck"

                downloads = {}
                filenames = {}

                # 1. Generar TXT temporal en TRANSFORM/
                if formato in ("txt", "ambos"):
                    lineas_trans = transformar_lineas_deck(deck_content.splitlines())
                    fecha_txt = player_info.get("dob_es") or player_info.get("dob", "")
                    cabecera_txt = [
                        f"Nombre Completo: {player_info.get('name', '')}",
                        f"ID: {player_info.get('id', '')}",
                        f"Fecha de Nacimiento: {fecha_txt}",
                        f"Categoria: {player_info.get('division', '')}",
                        "",
                    ]
                    txt_path = LEGACY_TRANSFORM_DIR / f"{safe_name}.txt"
                    LEGACY_TRANSFORM_DIR.mkdir(parents=True, exist_ok=True)
                    with open(txt_path, "w", encoding="utf-8") as f:
                        for l in (cabecera_txt + lineas_trans):
                            f.write(f"{l}\n")
                    downloads["txt"] = f"/download/temp/txt/{urllib.parse.quote(safe_name + '.txt')}"
                    filenames["txt"] = f"{safe_name}.txt"

                # 2. Generar PDF temporal en PDF/
                if formato in ("pdf", "ambos"):
                    plantilla = get_template_path()
                    pdf_path = LEGACY_PDF_DIR / f"{safe_name}.pdf"
                    LEGACY_PDF_DIR.mkdir(parents=True, exist_ok=True)
                    generar_decklist_pdf(deck_content.splitlines(), plantilla, pdf_path, info_jugador=player_info)
                    downloads["pdf"] = f"/download/temp/pdf/{urllib.parse.quote(safe_name + '.pdf')}"
                    filenames["pdf"] = f"{safe_name}.pdf"

                self._send_json({
                    "success": True,
                    "deck_name": safe_name,
                    "player": player_info,
                    "downloads": downloads,
                    "filenames": filenames
                })
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        else:
            self.send_error(404, "Endpoint no encontrado")


def run(port=PORT):
    server_address = ("0.0.0.0", port)
    httpd = ServerClass(server_address, DeckAppHandler)
    print(f"\n==================================================")
    print(f"[OK] Servidor Web Pokemon TCG Decklist iniciado!")
    print(f"--> Abre en tu navegador: http://localhost:{port}")
    print(f"==================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        httpd.server_close()


if __name__ == "__main__":
    run()
