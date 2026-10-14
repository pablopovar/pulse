from __future__ import annotations

import re

from bs4 import BeautifulSoup, NavigableString
from reports.localization_es_detectors import (
    DETECTOR_EXPLANATIONS_ES,
    DETECTOR_RECOMMENDATIONS_ES,
    DETECTOR_TITLES_ES,
)


SUPPORTED_REPORT_LOCALES = {"en", "es"}


ES = {
    "LIVING DOMAIN PULSE": "PULSO DEL DOMINIO",
    "Your visibility and website report": "Tu informe de visibilidad y sitio web",
    "What is working, what needs attention, and the most useful next actions.": "Qué está funcionando, qué necesita atención y cuáles son las acciones más útiles.",
    "Current verdict": "Conclusión actual",
    "What matters most now": "Lo más importante ahora",
    "WHAT MATTERS MOST NOW": "LO MÁS IMPORTANTE AHORA",
    "High-signal findings": "Hallazgos principales",
    "Highest-value actions": "Acciones prioritarias",
    "TOP ACTIONS": "ACCIONES PRIORITARIAS",
    "Resolved pages": "Páginas resueltas",
    "Improved pages": "Páginas mejoradas",
    "Worsened pages": "Páginas empeoradas",
    "Discovered pages": "Páginas descubiertas",
    "What does Benefit-to-fix mean?": "¿Qué significa beneficio de resolverlo?",
    "About this report": "Acerca de este informe",
    "REPORT REFERENCE": "REFERENCIA DEL INFORME",
    "Language": "Idioma",
    "English": "Inglés",
    "Spanish": "Español",
    "Download this report": "Descargar este informe",
    "Observation, display & source dates": "Observación, visualización y fechas de las fuentes",
    "Last checked": "Última comprobación",
    "Viewing observation": "Observación visualizada",
    "Display": "Visualización",
    "System": "Sistema",
    "Light": "Claro",
    "Dark": "Oscuro",
    "Quick links": "Enlaces rápidos",
    "Observation metadata": "Metadatos de la observación",
    "Methodology & scope": "Metodología y alcance",
    "Monitoring coverage": "Cobertura del monitoreo",
    "SITEMAP RECONCILIATION": "CONCILIACIÓN DEL MAPA DEL SITIO",
    "Sitemap URL evidence": "Evidencia de URL del mapa del sitio",
    "Confirmed findings": "Hallazgos confirmados",
    "Review required": "Revisión necesaria",
    "Pages affected": "Páginas afectadas",
    "Value to fix": "Beneficio de resolverlo",
    "Benefit to fix": "Beneficio de resolverlo",
    "Checks": "Comprobaciones",
    "Confirmed issues": "Problemas confirmados",
    "Pages tested": "Páginas analizadas",
    "AI Visibility": "Visibilidad en IA",
    "Identity & Authority": "Identidad y autoridad",
    "Evidence & Trust": "Evidencia y confianza",
    "Content & Answer Readiness": "Preparación de contenido y respuestas",
    "Machine Readability & Eligibility": "Legibilidad para máquinas y elegibilidad",
    "SEO Audit": "Auditoría SEO",
    "Onsite Audit": "Auditoría del sitio",
    "Expand section": "Expandir sección",
    "Collapse section": "Contraer sección",
    "Expand all": "Expandir todo",
    "Collapse all": "Contraer todo",
    "Show passes": "Mostrar aprobados",
    "All statuses": "Todos los estados",
    "All movement": "Todos los movimientos",
    "All sections": "Todas las secciones",
    "From": "Desde",
    "To": "Hasta",
    "Details": "Detalles",
    "Recommendation": "Recomendación",
    "Recommendations": "Recomendaciones",
    "Current evidence & material history": "Evidencia actual e historial relevante",
    "No human interpretation has been added.": "Todavía no se agregó una interpretación humana.",
    "Human interpretation": "Interpretación humana",
    "Discussion": "Conversación",
    "Send reply": "Enviar respuesta",
    "Available": "Disponible",
    "Absent": "Ausente",
    "Unavailable": "No disponible",
    "Status": "Estado",
    "Source": "Fuente",
    "Observed": "Observado",
    "Observed at": "Observado el",
    "Content type": "Tipo de contenido",
    "Size": "Tamaño",
    "Findings": "Hallazgos",
    "Pages": "Páginas",
    "Page": "Página",
    "Pass": "Aprobado",
    "PASS": "APROBADO",
    "Fail": "No aprobado",
    "FAIL": "NO APROBADO",
    "Partial": "Parcial",
    "PARTIAL": "PARCIAL",
    "LOW": "BAJA",
    "MEDIUM": "MEDIA",
    "HIGH": "ALTA",
    "CRITICAL": "CRÍTICA",
    "low": "baja",
    "medium": "media",
    "high": "alta",
    "critical": "crítica",
    "completed": "completado",
    "partial": "parcial",
    "failed": "fallido",
    "unknown": "desconocido",
    "MANUAL_REVIEW": "REVISIÓN",
    "DATA_UNAVAILABLE": "NO DISPONIBLE",
    "NOT_APPLICABLE": "NO APLICA",
    "Not applicable": "No aplicable",
    "Unknown": "Desconocido",
    "Unchanged": "Sin cambios",
    "New issue": "Problema nuevo",
    "New Issue": "Problema nuevo",
    "Data unavailable": "Datos no disponibles",
    "Mixed changes": "Cambios mixtos",
    "Requires human determination": "Requiere determinación humana",
    "Problem:": "Problema:",
    "Why it matters:": "Por qué importa:",
    "Affected scope:": "Alcance afectado:",
    "Owner:": "Responsable:",
    "Verify:": "Cómo verificarlo:",
    "Supporting diagnostics": "Diagnósticos de respaldo",
    "Affected": "Afectadas",
    "Check": "Control",
    "Audit run": "Ejecución de auditoría",
    "Core Page": "Página principal",
    "Eligible": "Elegible",
    "crawled": "rastreada",
    "Crawled": "Rastreadas",
    "Failed": "Fallidas",
    "Duplicate": "Duplicada",
    "Outcome": "Resultado",
    "All URL changes": "Todos los cambios de URL",
    "Changed": "Modificadas",
    "New": "Nuevas",
    "Classification": "Clasificación",
    "Decision": "Decisión",
    "Monitoring coverage & URL history": "Cobertura del monitoreo e historial de URL",
    "AI RESPONSE ANALYSIS": "ANÁLISIS DE RESPUESTAS DE IA",
    "AI RESPONSE SOURCE": "FUENTE DE RESPUESTAS DE IA",
    "Observation ID": "ID de observación",
    "Updated": "Actualizado",
    "Scope": "Alcance",
    "Baseline": "Línea de base",
    "Methodology": "Metodología",
    "Scoring": "Puntuación",
    "Report quality validation": "Validación de calidad del informe",
    "GEO / AEO / AIO glossary": "Glosario GEO / AEO / AIO",
    "Living pulse:": "Pulso continuo:",
    "Observation semantics:": "Criterios de la observación:",
    "Observed queries": "Consultas observadas",
    "Ranking pages": "Páginas posicionadas",
    "Search clicks": "Clics desde búsquedas",
    "Landing page": "Página de destino",
    "Clicks": "Clics",
    "Organic Search Performance": "Rendimiento en búsquedas orgánicas",
    "Search Opportunities": "Oportunidades de búsqueda",
    "Keyword Demand": "Demanda de palabras clave",
    "Competitive Search Gaps": "Brechas competitivas en búsquedas",
    "Backlinks & Search Authority": "Enlaces entrantes y autoridad de búsqueda",
    "Audience / Search Performance Context": "Contexto de audiencia y rendimiento en búsquedas",
    "Onsite Issue Summary": "Resumen de problemas del sitio",
    "Technical SEO Crawl": "Rastreo SEO técnico",
    "Site Audit": "Auditoría del sitio",
    "Indexing & Sitemap": "Indexación y mapa del sitio",
    "AI Crawler Accessibility": "Accesibilidad para rastreadores de IA",
    "Site Health": "Salud del sitio",
    "Internal links": "Enlaces internos",
    "Severity": "Gravedad",
    "Family": "Familia",
    "Finding": "Hallazgo",
    "Issue": "Problema",
    "Detail": "Detalle",
    "Query": "Consulta",
    "Best": "Mejor",
    "Latest": "Más reciente",
    "Keyword": "Palabra clave",
    "Target page": "Página objetivo",
    "Monthly searches": "Búsquedas mensuales",
    "Competition": "Competencia",
    "Indexable": "Indexable",
    "Words": "Palabras",
    "Schema": "Esquema",
    "Combined": "Combinado",
    "Evidence / Recommendation": "Evidencia / Recomendación",
    "Observed keywords": "Palabras clave observadas",
    "GEO score": "Puntuación GEO",
    "AEO score": "Puntuación AEO",
    "Top actions": "Acciones prioritarias",
    "AIO / AI visibility": "AIO / visibilidad en IA",
    "Page returned an HTTP error": "La página devolvió un error HTTP",
    "Page redirects": "La página redirige",
    "Missing title tag": "Falta la etiqueta title",
    "Very short title tag": "Etiqueta title demasiado corta",
    "Long title tag": "Etiqueta title demasiado larga",
    "Missing meta description": "Falta la meta descripción",
    "Missing H1": "Falta el H1",
    "Multiple H1 headings": "Hay varios encabezados H1",
    "Missing canonical URL": "Falta la URL canónica",
    "Missing viewport meta tag": "Falta la metaetiqueta viewport",
    "Images missing alt text": "Hay imágenes sin texto alternativo",
    "No JSON-LD schema detected": "No se detectó esquema JSON-LD",
    "Low visible word count": "Poca cantidad de palabras visibles",
    "Page has noindex directive": "La página tiene una directiva noindex",
    "Blocked by robots.txt": "Bloqueada por robots.txt",
    "Broken internal link": "Enlace interno roto",
    "Entity Clarity & Identity": "Claridad e identidad de la entidad",
    "Authority & Trust": "Autoridad y confianza",
    "Evidence & Citations": "Evidencia y citas",
    "Question & Intent Alignment": "Alineación con preguntas e intención",
    "Answer Extractability": "Facilidad para extraer respuestas",
    "Content Depth & Originality": "Profundidad y originalidad del contenido",
    "Clarity & Readability": "Claridad y legibilidad",
    "Search & Answer Eligibility": "Elegibilidad para búsquedas y respuestas",
    "Structured Data": "Datos estructurados",
    "Semantic Structure": "Estructura semántica",
    "Crawlability & Indexability": "Rastreabilidad e indexabilidad",
    "Technical Delivery & Consistency": "Entrega técnica y coherencia",
    "Page Experience & Accessibility": "Experiencia de página y accesibilidad",
    "Does the company's published information carry evidence, attribution and accountability?": "¿La información publicada por la empresa incluye evidencia, atribución y responsabilidad?",
    "Does the company publish substantive information in a form that people, search engines and answer systems can understand and reuse?": "¿La empresa publica información sustancial de una forma que las personas, los buscadores y los sistemas de respuestas puedan comprender y reutilizar?",
    "Is the company's information technically expressed in a form search and answer systems can identify, interpret and use?": "¿La información de la empresa está expresada técnicamente de una forma que los buscadores y sistemas de respuestas puedan identificar, interpretar y usar?",
    "How is the site performing in organic search, where is demand, and where are the highest-value search opportunities?": "¿Cómo rinde el sitio en búsquedas orgánicas, dónde está la demanda y cuáles son las oportunidades de mayor valor?",
    "Is the site technically crawlable, indexable, accessible and healthy?": "¿El sitio es técnicamente rastreable, indexable, accesible y saludable?",
    "A human determination is required before this item can be treated as a confirmed defect.": "Se necesita una determinación humana antes de considerar este punto como un defecto confirmado.",
    "No OpenGSC Site Audit observation is stored.": "No hay una observación de auditoría de sitio de OpenGSC almacenada.",
    "No sitemap inventory is stored.": "No hay un inventario de mapa del sitio almacenado.",
    "No backlink dataset is stored.": "No hay un conjunto de datos de enlaces entrantes almacenado.",
    "No GA4/Clarity observation is included.": "No se incluye una observación de GA4 o Clarity.",
    "No wanted/intended keyword targets are stored.": "No hay objetivos de palabras clave deseadas almacenados.",
    "No persisted competitor-gap rows are available.": "No hay datos almacenados sobre brechas frente a competidores.",
    "Related-intent analysis is not persisted in the current observation.": "El análisis de intenciones relacionadas no está almacenado en la observación actual.",
    "Content Decay is not persisted in the current observation.": "El deterioro del contenido no está almacenado en la observación actual.",
    "SEO / GEO / AEO Domain Audit": "Auditoría de dominio SEO / GEO / AEO",
    "Domain Audit Report": "Informe de auditoría del dominio",
    "Client-facing audit combining observed Google Search Console visibility, technical crawl evidence, and structured GEO/AEO findings.": "Auditoría para clientes que combina la visibilidad observada en Google Search Console, la evidencia del rastreo técnico y los hallazgos estructurados de GEO/AEO.",
    "Executive Summary": "Resumen ejecutivo",
    "GEO / AEO / AIO glossary": "Glosario GEO / AEO / AIO",
    "The PDF is intentionally concise. Detailed page-level checks, SEO tables, technical evidence, filters, and historical drill-down remain in the online HTML report.": "El PDF es intencionalmente conciso. Los controles detallados por página, las tablas SEO, la evidencia técnica, los filtros y el historial completo permanecen disponibles en el informe HTML en línea.",
    "Priority Findings": "Hallazgos prioritarios",
    "Organic Search Visibility": "Visibilidad en búsquedas orgánicas",
    "Technical SEO Crawl": "Rastreo SEO técnico",
    "GEO / AEO Readiness": "Preparación GEO / AEO",
    "Scope, Methodology and Limitations": "Alcance, metodología y limitaciones",
    "This report is generated from evidence currently stored by the audit application. It combines Google Search Console keyword/page observations, the latest technical crawl, and the latest structured GEO/AEO audit. Scores are evidence-based outputs of the current rule set and should be interpreted alongside the underlying findings.": "Este informe se genera a partir de la evidencia almacenada por la aplicación de auditoría. Combina observaciones de palabras clave y páginas de Google Search Console, el rastreo técnico más reciente y la última auditoría estructurada de GEO/AEO. Las puntuaciones se basan en la evidencia y en el conjunto de reglas vigente, y deben interpretarse junto con los hallazgos subyacentes.",
    "Not yet measured in this report: inbound backlink authority, cross-platform entity consistency, live AI citations/mentions, AI Overview visibility, LLM share of voice, and the future AIO scoring layer. These are intentionally shown as out of scope rather than inferred.": "Este informe todavía no mide la autoridad de enlaces entrantes, la coherencia de entidad entre plataformas, las citas o menciones en vivo por sistemas de IA, la visibilidad en AI Overviews, la participación de voz en LLM ni la futura capa de puntuación AIO. Estos elementos se muestran fuera de alcance en vez de inferirse.",
    "No stored GEO/AEO priority findings are available.": "No hay hallazgos prioritarios GEO/AEO almacenados.",
    "Technical Issues": "Problemas técnicos",
    "No GSC keyword-discovery dataset is currently available.": "Actualmente no hay un conjunto de datos de descubrimiento de palabras clave de GSC disponible.",
    "Wanted / Intended Keyword Targets": "Objetivos de palabras clave deseadas o previstas",
    "No technical crawl has been stored for this domain.": "No hay un rastreo técnico almacenado para este dominio.",
    "No completed GEO/AEO audit is currently stored.": "Actualmente no hay una auditoría GEO/AEO completa almacenada.",
    "GEO / AEO Findings Appendix": "Anexo de hallazgos GEO / AEO",
    "How well content can be understood, selected, and cited by generative systems.": "Qué tan bien los sistemas generativos pueden comprender, seleccionar y citar el contenido.",
    "How clearly the site provides extractable answers to questions and intents.": "Con qué claridad el sitio ofrece respuestas extraíbles para preguntas e intenciones.",
    "What AI systems actually say, cite, omit, or attribute about the entity.": "Qué dicen, citan, omiten o atribuyen realmente los sistemas de IA sobre la entidad.",
    "A check that cannot be established automatically and requires a human determination; it is not a confirmed defect.": "Un control que no puede establecerse automáticamente y requiere una determinación humana; no es un defecto confirmado.",
    "A source or observation required for the check was not available; it is not a failed check.": "Una fuente u observación necesaria para el control no estuvo disponible; no es un control fallido.",
    "Value to fix": "Beneficio de resolverlo",
    "severity × status factor × (1 + 2×traffic exposure) × (1 + site-wide prevalence). Traffic exposure is the mean normalized search visibility of the pages where the finding is actually FAIL/PARTIAL; prevalence is measured separately. If search exposure is unavailable, the report marks the score as based on partial inputs and uses zero traffic exposure rather than inventing it.": "gravedad × factor de estado × (1 + 2×exposición en búsquedas) × (1 + prevalencia en el sitio). La exposición es la visibilidad media normalizada en búsquedas de las páginas donde el hallazgo está realmente en FAIL/PARTIAL; la prevalencia se mide por separado. Si no hay exposición disponible, el informe indica que la puntuación usa datos parciales y asigna exposición cero en vez de inventarla.",
    "The report separates confirmed observations, review-required items, not-applicable checks, and unavailable data. Page-level observations are rolled up into check-level and root-cause findings while raw evidence remains available in the interactive report. Value to fix prioritizes confirmed issues using severity, observed search exposure when available, and site-wide prevalence. Manual review and unavailable data do not receive defect scores.": "El informe separa las observaciones confirmadas, los elementos que requieren revisión, los controles no aplicables y los datos no disponibles. Las observaciones por página se agrupan en hallazgos por control y causa raíz, mientras la evidencia original permanece disponible en el informe interactivo. El beneficio de resolverlo prioriza los problemas confirmados según gravedad, exposición observada en búsquedas cuando está disponible y prevalencia en el sitio. La revisión manual y los datos no disponibles no reciben puntuación de defecto.",
    "The report separates confirmed observations, review-required items, not-applicable checks, and unavailable data. Only FAIL and PARTIAL count as confirmed issues. Page-level observations are rolled up into check-level and root-cause findings while raw evidence remains available in the interactive report. Value to fix prioritizes confirmed issues using severity, observed search exposure when available, and site-wide prevalence. Manual review and unavailable data do not receive defect scores.": "El informe separa las observaciones confirmadas, los elementos que requieren revisión, los controles no aplicables y los datos no disponibles. Solamente FAIL y PARTIAL cuentan como problemas confirmados. Las observaciones por página se agrupan en hallazgos por control y causa raíz, mientras la evidencia original permanece disponible en el informe interactivo. El beneficio de resolverlo prioriza los problemas confirmados según gravedad, exposición observada en búsquedas cuando está disponible y prevalencia en el sitio. La revisión manual y los datos no disponibles no reciben puntuación de defecto.",
    "Search visibility is not turning into search clicks": "La visibilidad en buscadores no se está convirtiendo en clics",
    "Communications · Content · Editorial": "Comunicaciones · Contenido · Editorial",
    "Communications / Brand": "Comunicaciones / Marca",
    "Communications / Editorial": "Comunicaciones / Editorial",
    "Content / Editorial": "Contenido / Editorial",
    "IR · Communications · Corporate Affairs · Marketing": "Relaciones con inversores · Comunicaciones · Asuntos corporativos · Marketing",
    "IR · Communications · Brand": "Relaciones con inversores · Comunicaciones · Marca",
    "IR · Communications · Editorial · Legal/Review": "Relaciones con inversores · Comunicaciones · Editorial · Revisión legal",
    "SEO · Content · Web": "SEO · Contenido · Web",
    "SEO · Growth · Marketing": "SEO · Crecimiento · Marketing",
    "SEO · Web · Engineering": "SEO · Web · Ingeniería",
    "Connect authoritative profiles with visible links and Organization/Person sameAs where appropriate.": "Conectá los perfiles oficiales mediante enlaces visibles y propiedades sameAs de Organization/Person cuando corresponda.",
    "Add a focused FAQ only when it helps users complete the page's task.": "Agregá preguntas frecuentes específicas solamente cuando ayuden a completar la tarea de la página.",
    "Add original examples, observations, tests, demonstrations, or case material when useful.": "Agregá ejemplos, observaciones, pruebas, demostraciones o casos propios cuando aporten valor.",
    "Use semantic lists for genuine sets, steps, requirements, or options.": "Usá listas semánticas para conjuntos, pasos, requisitos u opciones reales.",
    "Write a concise unique title; treat length as a review heuristic, not a ranking rule.": "Escribí un título único y conciso; usá la longitud como señal de revisión, no como regla de posicionamiento.",
    "Official profiles are not consistently connected": "Los perfiles oficiales no están conectados de manera consistente",
    "Lists do not consistently expose grouped facts or steps": "Las listas no muestran de manera consistente hechos o pasos agrupados",
    "Some page titles need refinement": "Algunos títulos de página necesitan ajustes",
    "Resolved": "Resuelto",
    "Improved": "Mejorado",
    "Worsened": "Empeoró",
    "Back to top ↑": "Volver arriba ↑",
    "Official profiles connected": "Perfiles oficiales conectados",
    "Comparisons are structured": "Las comparaciones están estructuradas",
    "Claims and evidence are not consistently substantiated": "Las afirmaciones y la evidencia no están justificadas de forma coherente",
    "Content is not consistently structured for answer retrieval": "El contenido no está estructurado de forma coherente para recuperar respuestas",
    "Lists expose grouped facts or steps": "Las listas muestran hechos o pasos agrupados",
    "No confirmed fail/partial findings currently require attention.": "No hay fallos ni hallazgos parciales confirmados que requieran atención ahora.",
    "Several related answer-readiness checks fail broadly across the site. Rather than a single FAQ or heading problem, the pattern indicates that much of the content is not consistently organized around clear questions, direct answers, and reusable answer blocks.": "Varios controles relacionados con la preparación para respuestas fallan en gran parte del sitio. No es un único problema de preguntas frecuentes o encabezados: buena parte del contenido no está organizada de manera coherente alrededor de preguntas claras, respuestas directas y bloques reutilizables.",
    "Official profiles connected is a repeated site-wide pattern: 11 of 11 tested pages are affected.": "La conexión con perfiles oficiales es un patrón repetido en todo el sitio: afecta 11 de 11 páginas analizadas.",
    "Recommended action:": "Acción recomendada:",
    "Explore current state and history": "Explorar el estado actual y el historial",
    "Each check carries its observation history and raw page evidence.": "Cada comprobación conserva su historial de observaciones y la evidencia original de la página.",
    "Manual review": "Revisión manual",
    "Comparing the latest completed check with its predecessor.": "Comparación de la última comprobación completada con la anterior.",
    "Partial coverage.": "Cobertura parcial.",
    "This is the complete URL decision inventory captured with this report: including deferred, excluded and duplicate URLs, not only pages that were audited.": "Este es el inventario completo de decisiones sobre URL capturado con el informe: incluye URL postergadas, excluidas y duplicadas, no solamente las páginas auditadas.",
    "How visible is the company in AI answers, and which sources are shaping those answers?": "¿Qué visibilidad tiene la empresa en las respuestas de IA y qué fuentes están influyendo en ellas?",
    "Can machines and external audiences clearly establish who the company is and why it is authoritative?": "¿Los sistemas y las audiencias externas pueden establecer claramente quién es la empresa y por qué tiene autoridad?",
    "AI RESPONSE SOURCE": "FUENTE DE RESPUESTAS DE IA",
    "Manual AI response evidence": "Evidencia de respuestas manuales de IA",
    "The AI response source is present but incomplete or partially unparsed. Missing or malformed responses are treated as unavailable evidence, never as entity absence.": "La fuente de respuestas de IA está presente, pero está incompleta o fue interpretada parcialmente. Las respuestas ausentes o malformadas se consideran evidencia no disponible, nunca ausencia de la entidad.",
    "These are not detected failures. A human determination is required before they can become confirmed findings.": "Estos no son fallos detectados. Se necesita una determinación humana antes de convertirlos en hallazgos confirmados.",
    "Pages awaiting review": "Páginas pendientes de revisión",
    "Current": "Actual",
    "Current state": "Estado actual",
    "Current scope": "Alcance actual",
    "Evidence type:": "Tipo de evidencia:",
    "Current page-level evidence": "Evidencia actual por página",
    "Evidence": "Evidencia",
    "No prior observation history is stored for this check yet.": "Todavía no hay historial de observaciones anteriores para esta comprobación.",
    "A single-page crawl cannot verify cross-channel naming and factual consistency.": "El rastreo de una sola página no permite verificar la coherencia de nombres y datos entre canales.",
    "Title is concise and descriptive": "El título es conciso y descriptivo",
    "FAQ content is visible": "El contenido de preguntas frecuentes es visible",
    "Question-led headings": "Encabezados formulados como preguntas",
    "Multiple relevant question forms": "Varias formas de preguntas relevantes",
    "Headed answer blocks": "Bloques de respuesta con encabezados",
    "Sections support fragment linking": "Las secciones permiten enlaces a fragmentos",
    "Common follow-up questions addressed": "Se responden preguntas de seguimiento frecuentes",
    "Examples or first-hand evidence": "Ejemplos o evidencia de primera mano",
    "Entity consistency across channels": "Coherencia de la entidad entre canales",
    "Editorial and correction standards": "Normas editoriales y de corrección",
    "Independent reputation confirmed": "Reputación independiente confirmada",
    "A qualitative explanation of the likely practical value of resolving a finding, based on scope, severity, confidence, exposure, and whether one change can improve multiple pages. It is not a forecast of traffic or revenue.": "Una explicación cualitativa del valor práctico probable de resolver un hallazgo, basada en su alcance, gravedad, confianza, exposición y en si un solo cambio puede mejorar varias páginas. No es una proyección de tráfico ni de ingresos.",
}

# Keep the detector catalog separate so completeness can be tested directly
# against the engine's declarations.
ES.update(DETECTOR_TITLES_ES)
ES.update(DETECTOR_RECOMMENDATIONS_ES)
ES.update(DETECTOR_EXPLANATIONS_ES)


EXCLUDED_TAGS = {"script", "style", "pre", "code"}
EXCLUDED_CLASSES = {"report-url", "llm-verbatim", "llm-headers", "data-block"}


def resolve_report_locale(query: str | None, cookie: str | None, accepted: str | None = None) -> str:
    for value in (query, cookie):
        normalized = str(value or "").strip().lower().split("-", 1)[0]
        if normalized in SUPPORTED_REPORT_LOCALES:
            return normalized
    if str(accepted or "").lower().startswith("es"):
        return "es"
    return "en"


def translate_text(value: str, locale: str) -> str:
    if locale != "es" or not value:
        return value
    leading = value[: len(value) - len(value.lstrip())]
    trailing = value[len(value.rstrip()) :]
    core = value.strip()
    if not core:
        return value
    if core.startswith("• "):
        return leading + "• " + translate_text(core[2:], locale).strip() + trailing
    translated = ES.get(core, core)
    if ": " in translated:
        label, detail = translated.split(": ", 1)
        if detail in ES:
            translated = f"{ES.get(label, label)}: {ES[detail]}"
    numbered_heading = re.fullmatch(r"(\d+(?:\.\d+)?)\s+(.+)", translated)
    if numbered_heading and numbered_heading.group(2) in ES:
        translated = f"{numbered_heading.group(1)} {ES[numbered_heading.group(2)]}"
    severity = {"low": "baja", "medium": "media", "high": "alta"}
    match = re.fullmatch(r"This is a (low|medium|high) finding affecting (\d+) of (\d+) tested pages\.", translated, re.I)
    if match:
        translated = f"Este es un hallazgo de gravedad {severity[match.group(1).lower()]} que afecta {match.group(2)} de {match.group(3)} páginas analizadas."
    match = re.fullmatch(r"Generated (.+)", translated)
    if match:
        translated = f"Generado el {match.group(1)}"
    match = re.fullmatch(r"Page (\d+)", translated)
    if match:
        translated = f"Página {match.group(1)}"
    match = re.fullmatch(r"Latest GEO/AEO audit run #(\d+) · status: ([^·]+) · (.+)", translated)
    if match:
        status = match.group(2).strip()
        translated = f"Última auditoría GEO/AEO #{match.group(1)} · estado: {ES.get(status, status)} · {match.group(3)}"
    match = re.fullmatch(r"Organic visibility: ([\d.]+) observed keywords across ([\d.]+) ranking pages, with ([\d.]+) impressions and ([\d.]+) clicks in the stored discovery period\.", translated)
    if match:
        translated = f"Visibilidad orgánica: {match.group(1)} palabras clave observadas en {match.group(2)} páginas posicionadas, con {match.group(3)} impresiones y {match.group(4)} clics durante el período almacenado."
    match = re.fullmatch(r"Observed GSC discovery period: (.+) to (.+)\. CTR: (.+)\. Observed position range: (.+)\.", translated)
    if match:
        translated = f"Período de descubrimiento observado en GSC: {match.group(1)} a {match.group(2)}. CTR: {match.group(3)}. Rango de posiciones observado: {match.group(4)}."
    match = re.fullmatch(r"Technical crawl: (\d+) pages crawled, (\d+) failed, latest crawl status (.+)\.", translated)
    if match:
        status = match.group(3)
        translated = f"Rastreo técnico: {match.group(1)} páginas rastreadas, {match.group(2)} fallidas; estado del rastreo más reciente: {ES.get(status, status)}."
    match = re.fullmatch(r"GEO/AEO readiness: GEO (.+), AEO (.+), combined (.+) across (\d+) audited pages\.", translated)
    if match:
        translated = f"Preparación GEO/AEO: GEO {match.group(1)}, AEO {match.group(2)}, combinado {match.group(3)} en {match.group(4)} páginas auditadas."
    match = re.fullmatch(r"GEO (.+) · AEO (.+) · Combined (.+)", translated)
    if match:
        translated = f"GEO {match.group(1)} · AEO {match.group(2)} · Combinado {match.group(3)}"
    match = re.fullmatch(r"(.+) is a repeated site-wide pattern: (\d+) of (\d+) tested pages are affected\.", translated)
    if match:
        translated = f"{ES.get(match.group(1), match.group(1))} es un patrón repetido en todo el sitio: afecta {match.group(2)} de {match.group(3)} páginas analizadas."
    match = re.fullmatch(r"One underlying pattern is supported by (\d+) related checks and affects (\d+) page\(s\)\. The detailed checks remain available as supporting evidence\.", translated)
    if match:
        translated = f"Un patrón subyacente está respaldado por {match.group(1)} controles relacionados y afecta {match.group(2)} páginas. Los controles detallados siguen disponibles como evidencia de respaldo."
    match = re.fullmatch(r"(.+)'s Living Pulse", translated)
    if match:
        translated = f"Pulso del dominio {match.group(1)}"
    match = re.fullmatch(r"During (.+), the site generated ([\d,]+) Google search impressions but only ([\d,]+) search clicks\. This is search-console evidence, not a measure of visits\.", translated)
    if match:
        translated = f"Durante {match.group(1)}, el sitio generó {match.group(2)} impresiones en Google pero solamente {match.group(3)} clics desde búsquedas. Es evidencia de Search Console, no una medición de visitas."
    match = re.fullmatch(r"Rerun '(.+)' and confirm the affected scope is reduced or the status becomes PASS\.", translated)
    if match:
        translated = f"Volvé a ejecutar «{ES.get(match.group(1), match.group(1))}» y confirmá que disminuya el alcance afectado o que el estado pase a APROBADO."
    match = re.fullmatch(r"(\d+) of (\d+) tested pages", translated)
    if match:
        translated = f"{match.group(1)} de {match.group(2)} páginas analizadas"
    match = re.fullmatch(r"(\d+) affected page(?:s)?", translated)
    if match:
        translated = f"{match.group(1)} página" + ("s afectadas" if match.group(1) != "1" else " afectada")
    match = re.fullmatch(r"(\d+) of (\d+)", translated)
    if match:
        translated = f"{match.group(1)} de {match.group(2)}"
    match = re.fullmatch(r"(\d+)/(\d+) affected", translated)
    if match:
        translated = f"{match.group(1)}/{match.group(2)} afectadas"
    match = re.fullmatch(r"(\d+) review", translated)
    if match:
        translated = f"{match.group(1)} para revisar"
    match = re.fullmatch(r"(Eligible|Crawled|Unchanged|Failed|Deferred|Excluded|Duplicate) (\d+)", translated)
    if match:
        labels = {
            "Eligible": "Elegibles", "Crawled": "Rastreadas", "Unchanged": "Sin cambios",
            "Failed": "Fallidas", "Deferred": "Postergadas", "Excluded": "Excluidas",
            "Duplicate": "Duplicadas",
        }
        translated = f"{labels[match.group(1)]} {match.group(2)}"
    match = re.fullmatch(r"(\d+) pages were successfully audited against an initial target of (\d+)\. The report remains usable, but conclusions apply only to the audited cohort\.", translated)
    if match:
        translated = f"Se auditaron correctamente {match.group(1)} páginas de un objetivo inicial de {match.group(2)}. El informe sigue siendo útil, pero sus conclusiones se aplican solamente al conjunto auditado."
    if " · " in translated:
        translated = " · ".join(ES.get(part, {"FAIL": "NO APROBADO", "PASS": "APROBADO", "PARTIAL": "PARCIAL", "New Issue": "Problema nuevo"}.get(part, part)) for part in translated.split(" · "))
    translated = re.sub(r"\b(\d+) affected pages\b", r"\1 páginas afectadas", translated, flags=re.I)
    translated = re.sub(r"\b(\d+) supporting checks\b", r"\1 comprobaciones relacionadas", translated, flags=re.I)
    translated = re.sub(r"\b(\d+) events?\b", lambda m: f"{m.group(1)} evento" + ("s" if m.group(1) != "1" else ""), translated, flags=re.I)
    translated = re.sub(r"\b(\d+)/(\d+) pages\b", r"\1/\2 páginas", translated, flags=re.I)
    translated = re.sub(r"\bFound (\d+) internal link\(s\)\.", r"Se encontraron \1 enlaces internos.", translated, flags=re.I)
    translated = re.sub(r"\bhigh confidence\b", "confianza alta", translated, flags=re.I)
    translated = re.sub(r"\bmedium confidence\b", "confianza media", translated, flags=re.I)
    translated = re.sub(
        r"\b(low|medium|high|critical):",
        lambda match: f"{ES.get(match.group(1).lower(), match.group(1))}:",
        translated,
        flags=re.I,
    )
    translated = translated.replace("Recommendation: open", "Recomendación: pendiente")
    translated = translated.replace("pages affected by the highest-priority observed pattern", "páginas afectadas por el patrón observado de mayor prioridad")
    return leading + translated + trailing


def _excluded(node: NavigableString) -> bool:
    parent = node.parent
    while parent is not None:
        if getattr(parent, "name", None) in EXCLUDED_TAGS:
            return True
        classes = set(parent.get("class") or []) if hasattr(parent, "get") else set()
        if classes & EXCLUDED_CLASSES or (hasattr(parent, "has_attr") and parent.has_attr("data-analysis-markdown")):
            return True
        parent = getattr(parent, "parent", None)
    return False


def localize_report_html(html: str, locale: str) -> str:
    """Localize rendered presentation text while preserving source evidence."""
    if locale != "es":
        return html
    soup = BeautifulSoup(html, "html.parser")
    if soup.html:
        soup.html["lang"] = locale
    for node in list(soup.find_all(string=True)):
        if isinstance(node, NavigableString) and not _excluded(node):
            translated = translate_text(str(node), locale)
            if translated != str(node):
                node.replace_with(translated)
    for element in soup.find_all(True):
        for attribute in ("aria-label", "placeholder", "title"):
            if element.has_attr(attribute):
                element[attribute] = translate_text(str(element[attribute]), locale).strip()
    return str(soup)
