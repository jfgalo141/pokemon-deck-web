# Exportador / Importador de Decks Pokémon TCG

Aplicación modular diseñada para generar hojas de torneo oficiales (*Decklists*) en formato **PDF interactivo** y listas limpias en formato **TXT**, tanto a través de la consola (CLI) como mediante una interfaz web local.

---

## 📁 Estructura del Proyecto

```text
aplicacion_exportar_importar_DECKS_POKEMON/
│
├── core/                        # Lógica de negocio desacoplada (reutilizable en CLI o Web)
│   ├── config.py                # Rutas y configuración centralizada
│   ├── deck_parser.py           # Parseo de cartas, secciones y limpieza
│   ├── player_rules.py          # Reglas Pokémon TCG (Junior, Senior, Masters y fechas)
│   ├── pdf_service.py           # Generación de PDF oficial, LibreOffice y URL vertical
│   └── deck_service.py          # Orquestador de exportación unificado
│
├── templates/                   # Plantillas oficiales (DOCX / ZIP)
│   ├── Pokemon_TCG_Decklist.docx
│   └── Pokemon_TCG_Decklist.zip
│
├── EJEMPLOS/                    # Archivos de texto con barajas de ejemplo
│   ├── cynthia_garchomp.txt
│   ├── Raging Bolt.txt
│   ├── manzanas.txt
│   └── Jaime_Fernandez_Galofre.txt
│
├── exports/                     # Archivos exportados generados
│   ├── pdf/                     # PDFs oficiales generados
│   └── txt/                     # Listas transformadas en TXT
│
├── Front/                       # Interfaz Web del Frontend
│   ├── index.html               # Página web principal
│   ├── css/
│   │   └── styles.css           # Estilos visuales
│   └── js/
│       └── app.js               # Lógica interactiva y conexión con la API
│
├── Library/                     # Capa de compatibilidad retroactiva para scripts existentes
├── EXPORT_DECKS.py              # Ejecución desde consola (CLI)
├── app.py                       # Servidor Web local (ejecutable directamente)
└── requirements.txt             # Dependencias del proyecto
```

---

## 🚀 Modos de Uso

### 1. Aplicación Web Local
Puedes iniciar la aplicación web ejecutando:
```bash
python app.py
```
Abre tu navegador en: [http://localhost:8000](http://localhost:8000)

- Selector de fecha cómodo (Día, Mes y Año con auto-avance numérico, sin tener que escribir barras `/`).
- Cálculo en tiempo real de la categoría oficial (Junior, Senior, Masters).
- Subida de documentos (.txt, .deck, .docx) mediante arrastrar y soltar o pegado manual directo con contador de cartas.
- Descarga directa de los PDFs oficiales y archivos TXT con un solo clic.

### 2. Consola de Comandos (CLI)
Puedes continuar usando el script interactivo tradicional:
```bash
python EXPORT_DECKS.py
```
Te solicitará los datos del jugador de forma obligatoria, calculará la categoría e imprimirá las rutas de los archivos generados en `exports/`.
