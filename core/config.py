import os
import shutil
from pathlib import Path

# Raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Carpetas estructuradas
TEMPLATES_DIR = BASE_DIR / "templates"
EXAMPLES_DIR = BASE_DIR / "EJEMPLOS"
EXPORTS_DIR = BASE_DIR / "exports"
EXPORTS_PDF_DIR = EXPORTS_DIR / "pdf"
EXPORTS_TXT_DIR = EXPORTS_DIR / "txt"
FRONT_DIR = BASE_DIR / "Front"

# Carpetas heredadas para retrocompatibilidad
LEGACY_PDF_DIR = BASE_DIR / "PDF"
LEGACY_TRANSFORM_DIR = BASE_DIR / "TRANSFORM"

# Garantizar existencia de directorios de exportación
EXPORTS_PDF_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_TXT_DIR.mkdir(parents=True, exist_ok=True)
LEGACY_PDF_DIR.mkdir(parents=True, exist_ok=True)
LEGACY_TRANSFORM_DIR.mkdir(parents=True, exist_ok=True)


def get_template_path() -> Path:
    """Devuelve la ruta a la plantilla oficial (DOCX o ZIP), priorizando 'templates/' y fallback a 'EJEMPLOS/'."""
    rutas = [
        TEMPLATES_DIR / "Pokemon_TCG_Decklist.docx",
        TEMPLATES_DIR / "Pokemon_TCG_Decklist.zip",
        EXAMPLES_DIR / "Pokemon_TCG_Decklist.docx",
        EXAMPLES_DIR / "Pokemon_TCG_Decklist.zip",
    ]
    for r in rutas:
        if r.exists():
            return r
    raise FileNotFoundError(
        f"No se encontró la plantilla 'Pokemon_TCG_Decklist.docx' ni '.zip' en {TEMPLATES_DIR} ni en {EXAMPLES_DIR}"
    )


def get_soffice_path() -> Path | None:
    """Localiza el ejecutable de LibreOffice en el sistema."""
    which_soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if which_soffice:
        return Path(which_soffice)

    candidatas = [
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
        Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "LibreOffice" / "program" / "soffice.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "LibreOffice" / "program" / "soffice.exe",
    ]
    for c in candidatas:
        if c.exists():
            return c
    return None
