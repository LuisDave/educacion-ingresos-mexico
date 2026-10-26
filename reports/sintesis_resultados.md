# Educación e ingresos: síntesis del análisis

**Pregunta:** ¿estudiar más se relaciona con ganar más en México?

Se analizaron los microdatos oficiales de la ENIGH 2024 del INEGI. La muestra contiene
76,407 integrantes del hogar de 25 a 64 años con un solo trabajo subordinado remunerado
en México, ingreso positivo y jornada válida. La respuesta es el ingreso monetario
corriente mensualizado del trabajo principal, calculado con las claves P001–P007.

Se comparó un modelo con escolaridad sola con otro ajustado por edad, edad al cuadrado,
horas semanales, sexo, ámbito rural y entidad federativa. El análisis incorpora los
factores de expansión y estima intervalos mediante una aproximación de Taylor que
considera estratos y unidades primarias de muestreo (UPM).

## Resultados principales

La media mensual ponderada del dominio es $11,892 MXN; la mediana, $9,783 MXN.
El ingreso observado promedio es $8,900 para secundaria, $16,686 para licenciatura
y $26,305 para posgrado. Estos promedios no consideran las diferencias en otros factores.

Al considerar los controles, licenciatura presenta una diferencia de **+94.1%**
frente a secundaria en ingreso geométrico condicional, con **IC95% de 90.2% a 98.1%**.
La prueba conjunta rechaza que todos los contrastes escolares sean cero (p < 0.001).
El R² ponderado del modelo ajustado, en escala logarítmica, es **0.392**.

La validación reservó UPM completas: 60,765 personas en entrenamiento y 15,642 en
prueba, sin UPM compartidas. El error absoluto medio del modelo ajustado fue
**$5,181 MXN**, frente a $6,431 al predecir la media de entrenamiento: 19.4% menos error.
Este desempeño corresponde a validación interna, no a otro año ni a datos futuros.

Al excluir el 1% superior solamente como sensibilidad, la diferencia de licenciatura
cambia de +94.1% a +87.8%. El modelo principal conserva todos los ingresos positivos.

## Cómo explicar la conclusión

En la población estudiada, mayor escolaridad se asocia con mayor ingreso y la relación
permanece al considerar otros factores. La educación aporta información, pero no basta
para explicar las diferencias individuales ni para predecir con precisión cada ingreso.

La diferencia porcentual no garantiza que una persona aumentaría su ingreso en esa
proporción al estudiar una licenciatura. No se identifica causalidad: intervienen
selección al empleo, calidad educativa, historia familiar y otros factores no medidos.
El nivel escolar reportado puede estar incompleto; edad no equivale a experiencia.

## Fuente y trazabilidad

INEGI. (2025). *Encuesta Nacional de Ingresos y Gastos de los Hogares 2024, Nueva Serie*
[Microdatos]. https://www.inegi.org.mx/programas/enigh/nc/2024/

Las tablas completas, la auditoría de filtros, los coeficientes, los intervalos, las
pruebas y los diagnósticos están en el notebook y en `outputs/tables/`.
El resumen visual utiliza esas mismas salidas. Elaboración propia;
estos resultados no constituyen un tabulado oficial del INEGI.
