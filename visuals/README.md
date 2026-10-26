# Resumen visual

Vista de una página de las diferencias de ingreso por escolaridad en la ENIGH 2024.
Incluye alcance, método, interpretación, validación, hallazgos y fuentes.

`scripts/build_visual_summary.py` utiliza las mismas tablas y figuras que el notebook.
Genera `resumen_educacion_ingresos.pdf` y `metadatos_resumen.json`; este último registra
las cifras y huellas SHA-256 de los archivos de origen. El PNG se exporta desde el PDF
con el comando de Poppler indicado en el README principal.

Las ecuaciones se componen con MathText y se conservan también en SVG. Los resultados
describen asociaciones dentro de la población delimitada, sin identificar causalidad.
