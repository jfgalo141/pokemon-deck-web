document.addEventListener("DOMContentLoaded", () => {
  // Limpiar cualquier dato antiguo guardado en localStorage para que todos los campos arranquen vacíos
  try {
    localStorage.removeItem("ptcg_decklist_player_data");
  } catch (e) {}

  // Elementos de datos del jugador
  const inputName = document.getElementById("player-name");
  const inputId = document.getElementById("player-id");
  const dobContainer = document.getElementById("dob-container");
  const dobDay = document.getElementById("dob-day");
  const dobMonth = document.getElementById("dob-month");
  const dobYear = document.getElementById("dob-year");
  const divisionBadge = document.getElementById("division-badge");

  // Elementos de la baraja
  const customName = document.getElementById("custom-name");
  const deckTextarea = document.getElementById("deck-text");
  const cardCounter = document.getElementById("card-counter");
  const chipPokemon = document.getElementById("chip-pokemon");
  const chipTrainer = document.getElementById("chip-trainer");
  const chipEnergy = document.getElementById("chip-energy");

  // Botones de utilidad
  const btnPasteDeck = document.getElementById("btn-paste-deck");
  const btnClearDeck = document.getElementById("btn-clear-deck");

  // Botones y resultados de exportación
  const btnExportPdf = document.getElementById("btn-export-pdf");
  const btnCopyTxt = document.getElementById("btn-copy-txt");
  const resultBox = document.getElementById("result-box");
  const toastContainer = document.getElementById("toast-container");

  // ============================================================
  // NOTIFICACIONES FLOTANTES (TOASTS)
  // ============================================================
  function showToast(message, type = "success", duration = 3200) {
    if (!toastContainer) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    let iconSvg = "";
    if (type === "success") {
      iconSvg = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#34d399" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
    } else if (type === "error") {
      iconSvg = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#f87171" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
    } else {
      iconSvg = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#38bdf8" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
    }

    toast.innerHTML = `${iconSvg} <span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.classList.add("toast-hide");
      setTimeout(() => toast.remove(), 260);
    }, duration);
  }

  // ============================================================
  // GESTIÓN DE ERRORES Y SEÑALIZACIÓN EN ROJO
  // ============================================================
  function markError(element) {
    if (!element) return;
    element.classList.add("input-error");
  }

  function clearError(element) {
    if (!element) return;
    element.classList.remove("input-error");
  }

  function clearAllErrors() {
    document.querySelectorAll(".input-error").forEach((el) => {
      el.classList.remove("input-error");
    });
  }

  // Quitar el color rojo ÚNICAMENTE cuando el usuario empiece a escribir/corregir
  [inputName, inputId, customName].forEach((el) => {
    if (el) {
      el.addEventListener("input", () => clearError(el));
    }
  });

  [dobDay, dobMonth, dobYear].forEach((el) => {
    if (el) {
      el.addEventListener("input", () => {
        clearError(el);
        if (dobDay.value.trim() && dobMonth.value.trim() && dobYear.value.trim().length === 4) {
          clearError(dobContainer);
        }
      });
    }
  });

  if (deckTextarea) {
    deckTextarea.addEventListener("input", () => clearError(deckTextarea));
  }

  // Limpieza de archivos temporales al cerrar o recargar la pestaña
  window.addEventListener("beforeunload", () => {
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/api/cleanup-temp");
    }
  });

  window.addEventListener("pagehide", () => {
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/api/cleanup-temp");
    }
  });

  // ============================================================
  // 1. GESTIÓN DE FECHA DE NACIMIENTO (Día, Mes, Año sin '/')
  // ============================================================
  dobDay.addEventListener("input", () => {
    dobDay.value = dobDay.value.replace(/\D/g, "");
    if (dobDay.value.length >= 2) {
      const num = parseInt(dobDay.value, 10);
      if (num > 31) dobDay.value = "31";
      dobMonth.focus();
      dobMonth.select();
    }
    triggerCategoryCheck();
  });

  dobMonth.addEventListener("input", () => {
    dobMonth.value = dobMonth.value.replace(/\D/g, "");
    if (dobMonth.value.length >= 2) {
      const num = parseInt(dobMonth.value, 10);
      if (num > 12) dobMonth.value = "12";
      dobYear.focus();
      dobYear.select();
    }
    triggerCategoryCheck();
  });

  dobMonth.addEventListener("keydown", (e) => {
    if (e.key === "Backspace" && !dobMonth.value) {
      dobDay.focus();
    }
  });

  dobYear.addEventListener("input", () => {
    dobYear.value = dobYear.value.replace(/\D/g, "");
    triggerCategoryCheck();
  });

  dobYear.addEventListener("keydown", (e) => {
    if (e.key === "Backspace" && !dobYear.value) {
      dobMonth.focus();
    }
  });

  function handleDobPaste(e) {
    const paste = (e.clipboardData || window.clipboardData).getData("text").trim();
    const dateRegex = /(\d{1,4})[\/\-\.\s](\d{1,2})[\/\-\.\s](\d{1,4})/;
    const match = paste.match(dateRegex);

    if (match) {
      e.preventDefault();
      let d = "", m = "", y = "";
      if (match[1].length === 4) {
        y = match[1];
        m = match[2];
        d = match[3];
      } else {
        d = match[1];
        m = match[2];
        y = match[3];
      }
      dobDay.value = d.padStart(2, "0").slice(-2);
      dobMonth.value = m.padStart(2, "0").slice(-2);
      dobYear.value = y.slice(0, 4);
      clearError(dobDay);
      clearError(dobMonth);
      clearError(dobYear);
      clearError(dobContainer);
      triggerCategoryCheck();
      dobYear.focus();
    } else {
      const digits = paste.replace(/\D/g, "");
      if (digits.length === 8) {
        e.preventDefault();
        dobDay.value = digits.slice(0, 2);
        dobMonth.value = digits.slice(2, 4);
        dobYear.value = digits.slice(4, 8);
        clearError(dobDay);
        clearError(dobMonth);
        clearError(dobYear);
        clearError(dobContainer);
        triggerCategoryCheck();
        dobYear.focus();
      }
    }
  }

  dobDay.addEventListener("paste", handleDobPaste);
  dobMonth.addEventListener("paste", handleDobPaste);
  dobYear.addEventListener("paste", handleDobPaste);

  // Comprobación de categoría en tiempo real
  let categoryTimeout = null;
  function triggerCategoryCheck() {
    clearTimeout(categoryTimeout);
    const yVal = dobYear.value.trim();
    if (yVal.length !== 4) {
      divisionBadge.style.display = "none";
      return;
    }
    const dVal = (dobDay.value.trim() || "01").padStart(2, "0");
    const mVal = (dobMonth.value.trim() || "01").padStart(2, "0");
    const formatted = `${dVal}/${mVal}/${yVal}`;

    categoryTimeout = setTimeout(() => {
      fetch("/api/category", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dob: formatted }),
      })
        .then((r) => r.json())
        .then((res) => {
          if (res.valid) {
            divisionBadge.textContent = `🎯 Categoría: ${res.division} (Nacido en ${res.year})`;
            divisionBadge.className = `division-badge ${res.division.toLowerCase()}`;
            divisionBadge.style.display = "inline-flex";
          } else {
            divisionBadge.style.display = "none";
          }
        })
        .catch(() => {
          divisionBadge.style.display = "none";
        });
    }, 120);
  }

  // ============================================================
  // 2. VALIDACIÓN Y DIAGNÓSTICO EN TIEMPO REAL DE LA BARAJA
  // ============================================================
  const sectionHeaderRegex = /^(?:lista\s+)?(?:pok[eé]mon|trainer|trainers|entrenador|entrenadores|energy|energies|energ[ií]as?)(?:\s*(?:cards|cartas))?(?:\s*[:\-]?\s*\(?\d*\)?)?$/i;
  const separatorRegex = /^[-=_*~]{3,}$/;
  const cardLineRegex = /^(\d+)\s+([A-Za-zÀ-ÿ0-9'’\-\.\s&{}\(\):/]{2,})$/;
  const metadataPrefixes = ["nombre:", "name:", "id:", "fecha", "dob:", "categor", "total cards:", "cartas totales:"];

  function validateDeckStructure(text) {
    const rawLines = text.split("\n");
    const usefulLines = [];

    for (const l of rawLines) {
      const s = l.trim();
      if (!s) continue;
      const low = s.toLowerCase();
      if (metadataPrefixes.some((p) => low.startsWith(p))) continue;
      usefulLines.push(s);
    }

    if (usefulLines.length === 0) {
      return {
        valid: false,
        error: "La lista de cartas está vacía. Pega o escribe una baraja en formato Limitless o Pokémon TCG Live.",
      };
    }

    let cardCount = 0;

    for (const line of usefulLines) {
      if (sectionHeaderRegex.test(line)) continue;
      if (separatorRegex.test(line)) continue;

      const match = line.match(cardLineRegex);
      if (match) {
        const qty = parseInt(match[1], 10);
        if (qty < 1 || qty > 59) {
          return { valid: false, error: `Cantidad de cartas inválida (${qty}) en la línea: '${line}'.` };
        }
        cardCount++;
      } else {
        return {
          valid: false,
          error: `El texto introducido no tiene la estructura de una baraja Pokémon TCG válida. Línea no reconocida: '${line}'. Cada carta debe comenzar por su cantidad (ej. '4 Cynthia's Gible DRI 102').`,
        };
      }
    }

    if (cardCount === 0) {
      return {
        valid: false,
        error: "No se detectó ninguna carta válida en el texto. Asegúrate de incluir la cantidad al inicio de cada carta.",
      };
    }

    return { valid: true };
  }

  // Análisis detallado y desglose por tipo (Pokémon, Trainer, Energy)
  function analyzeDeckBreakdown(text) {
    const lines = text.split("\n");
    let totalCards = 0;
    let pkCount = 0;
    let trCount = 0;
    let enCount = 0;

    const hasHeaders = lines.some((l) => sectionHeaderRegex.test(l.trim()));

    if (hasHeaders) {
      let currentSection = null; // 'pk', 'tr', 'en'
      for (const rawLine of lines) {
        const l = rawLine.trim();
        if (!l) continue;

        if (/^(?:lista\s+)?pok[eé]mon(?:\s*(?:cards|cartas))?(?:\s*[:\-]?\s*\(?\d*\)?)?$/i.test(l)) {
          currentSection = "pk";
          continue;
        } else if (/^(?:lista\s+)?(?:trainer|trainers|entrenador|entrenadores)(?:\s*(?:cards|cartas))?(?:\s*[:\-]?\s*\(?\d*\)?)?$/i.test(l)) {
          currentSection = "tr";
          continue;
        } else if (/^(?:lista\s+)?(?:energy|energies|energ[ií]as?)(?:\s*(?:cards|cartas))?(?:\s*[:\-]?\s*\(?\d*\)?)?$/i.test(l)) {
          currentSection = "en";
          continue;
        }

        if (separatorRegex.test(l)) continue;
        if (metadataPrefixes.some((p) => l.toLowerCase().startsWith(p))) continue;

        const match = l.match(cardLineRegex);
        if (match) {
          const qty = parseInt(match[1], 10);
          totalCards += qty;
          if (currentSection === "pk") pkCount += qty;
          else if (currentSection === "tr") trCount += qty;
          else if (currentSection === "en") enCount += qty;
        }
      }
    } else {
      // Bloques separados por línea vacía (Limitless format sin cabeceras)
      const blocks = [];
      let curBlock = [];
      for (const rawLine of lines) {
        const s = rawLine.trim();
        if (metadataPrefixes.some((p) => s.toLowerCase().startsWith(p))) continue;
        if (s) {
          curBlock.push(s);
        } else if (curBlock.length > 0) {
          blocks.push(curBlock);
          curBlock = [];
        }
      }
      if (curBlock.length > 0) blocks.push(curBlock);

      const countBlock = (blk) => {
        let cnt = 0;
        if (!blk) return 0;
        for (const line of blk) {
          const m = line.match(/^(\d+)\s+/);
          if (m) cnt += parseInt(m[1], 10);
        }
        return cnt;
      };

      if (blocks.length > 0) pkCount = countBlock(blocks[0]);
      if (blocks.length > 1) trCount = countBlock(blocks[1]);
      if (blocks.length > 2) enCount = countBlock(blocks[2]);
      totalCards = pkCount + trCount + enCount;
    }

    return { total: totalCards, pokemon: pkCount, trainer: trCount, energy: enCount };
  }

  function updateDiagnosticDashboard() {
    const text = deckTextarea.value.trim();

    if (!text) {
      cardCounter.textContent = "0 / 60 Cartas";
      cardCounter.className = "card-counter";
      chipPokemon.innerHTML = `<span class="chip-dot"></span> Pokémon: 0`;
      chipTrainer.innerHTML = `<span class="chip-dot"></span> Trainer: 0`;
      chipEnergy.innerHTML = `<span class="chip-dot"></span> Energy: 0`;
      return;
    }

    const struct = validateDeckStructure(text);
    if (!struct.valid) {
      cardCounter.textContent = "⚠️ Formato no válido";
      cardCounter.className = "card-counter error";
      return;
    }

    const stats = analyzeDeckBreakdown(text);
    chipPokemon.innerHTML = `<span class="chip-dot"></span> Pokémon: ${stats.pokemon}`;
    chipTrainer.innerHTML = `<span class="chip-dot"></span> Trainer: ${stats.trainer}`;
    chipEnergy.innerHTML = `<span class="chip-dot"></span> Energy: ${stats.energy}`;

    if (stats.total === 60) {
      cardCounter.textContent = `✓ Baraja Legal (60/60)`;
      cardCounter.className = "card-counter valid";
    } else if (stats.total < 60) {
      const faltan = 60 - stats.total;
      cardCounter.textContent = `⚠️ ${stats.total} / 60 Cartas (Faltan ${faltan})`;
      cardCounter.className = "card-counter warning";
    } else {
      const sobran = stats.total - 60;
      cardCounter.textContent = `⚠️ ${stats.total} / 60 Cartas (Sobran ${sobran})`;
      cardCounter.className = "card-counter error";
    }
  }

  deckTextarea.addEventListener("input", updateDiagnosticDashboard);

  // ============================================================
  // BOTONERA DE UTILIDADES SOBRE EL TEXTAREA
  // ============================================================

  // 1. Botón Pegar Portapapeles
  if (btnPasteDeck) {
    btnPasteDeck.addEventListener("click", async () => {
      try {
        if (navigator.clipboard && navigator.clipboard.readText) {
          const clipText = await navigator.clipboard.readText();
          if (clipText.trim()) {
            deckTextarea.value = clipText.trim();
            clearError(deckTextarea);
            updateDiagnosticDashboard();
            showToast("Lista pegada desde el portapapeles", "success");
            deckTextarea.focus();
          } else {
            showToast("El portapapeles está vacío", "info");
          }
        } else {
          showToast("Usa Ctrl + V para pegar en este navegador", "info");
          deckTextarea.focus();
        }
      } catch (err) {
        showToast("Permiso denegado. Usa Ctrl + V para pegar", "info");
        deckTextarea.focus();
      }
    });
  }

  // 2. Botón Limpiar
  if (btnClearDeck) {
    btnClearDeck.addEventListener("click", () => {
      if (deckTextarea.value.trim() && !confirm("¿Seguro que deseas vaciar el contenido de la baraja?")) {
        return;
      }
      deckTextarea.value = "";
      clearError(deckTextarea);
      updateDiagnosticDashboard();
      showToast("Área de baraja limpiada", "info");
      deckTextarea.focus();
    });
  }

  // ============================================================
  // VALIDACIÓN CENTRALIZADA DEL FORMULARIO
  // ============================================================
  function validateForm() {
    clearAllErrors();

    const name = inputName.value.trim();
    const id = inputId.value.trim();
    const day = dobDay.value.trim();
    const month = dobMonth.value.trim();
    const year = dobYear.value.trim();
    const deckContent = deckTextarea.value.trim();
    const cName = customName.value.trim() || "mi_baraja";

    resultBox.style.display = "none";
    resultBox.className = "result-box";

    let hasErrors = false;
    let firstErrorElement = null;

    // Validación Nombre Completo
    if (!name) {
      markError(inputName);
      if (!firstErrorElement) firstErrorElement = inputName;
      hasErrors = true;
    }

    // Validación ID de Jugador
    if (!id) {
      markError(inputId);
      if (!firstErrorElement) firstErrorElement = inputId;
      hasErrors = true;
    }

    // Validación Fecha de Nacimiento
    const dNum = parseInt(day, 10);
    const mNum = parseInt(month, 10);
    const yNum = parseInt(year, 10);
    let dobError = false;

    if (!day || isNaN(dNum) || dNum < 1 || dNum > 31) {
      markError(dobDay);
      dobError = true;
      if (!firstErrorElement) firstErrorElement = dobDay;
    }
    if (!month || isNaN(mNum) || mNum < 1 || mNum > 12) {
      markError(dobMonth);
      dobError = true;
      if (!firstErrorElement) firstErrorElement = dobMonth;
    }
    if (!year || year.length !== 4 || isNaN(yNum) || yNum < 1920 || yNum > 2030) {
      markError(dobYear);
      dobError = true;
      if (!firstErrorElement) firstErrorElement = dobYear;
    }

    if (dobError) {
      markError(dobContainer);
      hasErrors = true;
    }

    // Validación Contenido del Mazo
    if (!deckContent) {
      markError(deckTextarea);
      if (!firstErrorElement) firstErrorElement = deckTextarea;
      hasErrors = true;
    } else {
      const structCheck = validateDeckStructure(deckContent);
      if (!structCheck.valid) {
        markError(deckTextarea);
        if (!firstErrorElement) firstErrorElement = deckTextarea;
        showError(structCheck.error);
        if (firstErrorElement) {
          firstErrorElement.focus();
          firstErrorElement.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        return null;
      }
    }

    if (hasErrors) {
      showError("Faltan datos obligatorios. Por favor, revisa y completa los campos señalados en rojo.");
      if (firstErrorElement) {
        firstErrorElement.focus();
        firstErrorElement.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      return null;
    }

    const formattedDob = `${day.padStart(2, "0")}/${month.padStart(2, "0")}/${year}`;
    return { name, id, formattedDob, deckContent, cName };
  }

  // ============================================================
  // ACCIÓN 1: EXPORTAR BARAJA .PDF (Descarga directa automática)
  // ============================================================
  btnExportPdf.addEventListener("click", () => {
    const formData = validateForm();
    if (!formData) return;

    btnExportPdf.disabled = true;
    const originalText = btnExportPdf.innerHTML;
    btnExportPdf.innerHTML = `<span>⏳ Generando PDF oficial...</span>`;

    fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        player_name: formData.name,
        player_id: formData.id,
        dob: formData.formattedDob,
        deck: formData.deckContent,
        custom_name: formData.cName,
        format: "pdf",
      }),
    })
      .then((r) => r.json())
      .then((res) => {
        btnExportPdf.disabled = false;
        btnExportPdf.innerHTML = originalText;

        if (!res.success) {
          showError(res.error || "Ocurrió un error al generar el PDF.");
          return;
        }

        const pdfFilename = res.filenames?.pdf || `${formData.cName}.pdf`;
        const downloadUrl = res.downloads?.pdf;

        // Descarga directa automática en el navegador
        if (downloadUrl) {
          const dlLink = document.createElement("a");
          dlLink.href = downloadUrl;
          dlLink.download = pdfFilename;
          document.body.appendChild(dlLink);
          dlLink.click();
          document.body.removeChild(dlLink);
        }

        showToast("¡PDF oficial generado y descarga iniciada!", "success");

        resultBox.className = "result-box";
        resultBox.style.display = "block";

        let html = `<p><strong>✅ ¡PDF oficial generado con éxito!</strong></p>`;
        html += `<p style="font-size:0.85rem; color:#94a3b8; margin-top:0.25rem;">Archivo: <strong>${pdfFilename}</strong> | Categoría: <strong>${res.player.division}</strong></p>`;
        if (downloadUrl) {
          html += `<div class="download-buttons" style="margin-top:0.6rem;">`;
          html += `<a href="${downloadUrl}" class="btn-download" download="${pdfFilename}">⬇️ Volver a descargar ${pdfFilename}</a>`;
          html += `</div>`;
        }
        resultBox.innerHTML = html;
      })
      .catch((err) => {
        btnExportPdf.disabled = false;
        btnExportPdf.innerHTML = originalText;
        showError("Error de comunicación con el servidor: " + err.message);
      });
  });

  // ============================================================
  // ACCIÓN 2: COPIAR FORMATO TEXTO AL PORTAPAPELES
  // ============================================================
  btnCopyTxt.addEventListener("click", () => {
    const formData = validateForm();
    if (!formData) return;

    btnCopyTxt.disabled = true;
    const originalText = btnCopyTxt.innerHTML;
    btnCopyTxt.innerHTML = `<span>⏳ Formateando lista...</span>`;

    fetch("/api/format-txt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        player_name: formData.name,
        player_id: formData.id,
        dob: formData.formattedDob,
        deck: formData.deckContent,
      }),
    })
      .then((r) => r.json())
      .then((res) => {
        btnCopyTxt.disabled = false;
        btnCopyTxt.innerHTML = originalText;

        if (!res.success) {
          showError(res.error || "Ocurrió un error al formatear el texto.");
          return;
        }

        const textToCopy = res.formatted_text;

        // Copiar al portapapeles del sistema
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(textToCopy).catch(() => {
            fallbackCopy(textToCopy);
          });
        } else {
          fallbackCopy(textToCopy);
        }

        showToast("¡Formato texto copiado al portapapeles!", "success");

        // Animación visual de éxito en el botón
        btnCopyTxt.classList.add("copied");
        btnCopyTxt.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> <span>¡Copiado al portapapeles!</span>`;
        setTimeout(() => {
          btnCopyTxt.classList.remove("copied");
          btnCopyTxt.innerHTML = originalText;
        }, 2500);

        // Mensaje de confirmación en la caja
        resultBox.className = "result-box";
        resultBox.style.display = "block";
        resultBox.innerHTML = `
          <p><strong>📋 ¡Estructura de la baraja copiada al portapapeles!</strong></p>
          <p style="font-size:0.85rem; color:#94a3b8; margin-top:0.25rem;">
            Se ha copiado la lista formateada con cabecera de jugador (Categoría: <strong>${res.player.division}</strong>). Puedes pegarla con <kbd>Ctrl + V</kbd> en Word, Bloc de Notas o donde necesites.
          </p>
        `;
      })
      .catch((err) => {
        btnCopyTxt.disabled = false;
        btnCopyTxt.innerHTML = originalText;
        showError("Error al copiar texto: " + err.message);
      });
  });

  function fallbackCopy(text) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
    } catch (e) {}
    document.body.removeChild(ta);
  }

  function showError(msg) {
    resultBox.className = "result-box error";
    resultBox.textContent = `❌ ${msg}`;
    resultBox.style.display = "block";
    showToast(msg, "error", 4000);
  }

  updateDiagnosticDashboard();
});
