"""Construye y ejecuta el cuaderno con el intérprete del proyecto."""
from pathlib import Path
import os,sys,json
import nbformat as nbf
from nbclient import NotebookClient
from nbconvert import HTMLExporter

ROOT=Path(__file__).resolve().parents[1]
cells=[]
def md(s):cells.append(nbf.v4.new_markdown_cell(s))
def code(s):cells.append(nbf.v4.new_code_cell(s))

md('''# Educación e ingresos en México
## ¿Estudiar más se relaciona con ganar más?

**Análisis exploratorio con datos abiertos de México**  
**Autores:** Luis David Gonzalez Romero y Diego Alberto Ortega Carreto  
**Fuente:** ENIGH 2024, Nueva Serie, INEGI. **Elaboración:** 25 de octubre de 2026.

Este proyecto estudia la asociación entre escolaridad e ingreso monetario corriente del
trabajo principal. Compara un modelo con escolaridad sola y modelos con otros factores,
estima intervalos de confianza y evalúa predicción en grupos reservados.

**La población de estudio no incluye a todos los mexicanos:** se delimita a integrantes
del hogar de 25 a 64 años con un solo trabajo subordinado remunerado en México,
ingreso positivo y jornada válida. El resultado es asociativo, no causal.''')
md('''## 1. Pregunta, objetivo e hipótesis

**Pregunta:** dentro de la población delimitada, ¿se mantienen diferencias de ingreso por
escolaridad al considerar edad, jornada, sexo, ámbito rural y entidad federativa?

**Objetivo:** cuantificar esas diferencias mediante regresión ponderada e intervalos de
confianza, para describir brechas educativas y laborales con datos oficiales mexicanos.

**Hipótesis conjunta:** $H_0$: todos los contrastes de escolaridad frente a secundaria son
cero; $H_1$: al menos uno difiere. Se adopta $\\alpha=0.05$.

La comparación de referencia es **secundaria**. No se interpretan categorías escolares
como si fueran años numéricos equivalentes.''')
code('''from pathlib import Path
import sys, json
ROOT = Path.cwd().resolve()
if ROOT.name == "notebooks":
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
from IPython.display import display, Image, Markdown
import pandas as pd
import numpy as np
from src import analysis as a
pd.set_option("display.max_columns", 12)
pd.set_option("display.float_format", lambda x: f"{x:,.4f}")
print("Raíz del proyecto:", ROOT.name)''')
md('''## 2. Fuente y descarga reproducible

Se utilizan las tablas **Población**, **Trabajos** e **Ingresos**. Los ZIP originales
permanecen intactos; el manifiesto conserva enlaces, tamaños y huellas SHA-256.
Las uniones usan `folioviv`, `foliohog` y `numren` como texto.

Si los datos aún no existen, ejecutar `python scripts/download_data.py` desde la raíz.
La descarga requiere conexión a Internet; el análisis posterior es local.

- [Programa y microdatos](https://www.inegi.org.mx/programas/enigh/nc/2024/)
- [Descripción de la base](https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/microdatos/889463924494.pdf)
- [Diseño muestral](https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/doc/889463924517.pdf)''')
code('''from scripts.download_data import download
if not all((ROOT/f"data/raw/{t}.csv").exists() for t in ["poblacion", "trabajos", "ingresos"]):
    download()
display(pd.DataFrame(json.loads((ROOT/"data/source_manifest.json").read_text(encoding="utf-8")))[["file", "bytes", "sha256"]])''')
md('''## 3. Definición de variables y muestra

| Variable | Construcción y significado |
|---|---|
| Ingreso mensual | Suma de `ing_tri` para P001–P007, dividida entre 3; ingreso monetario corriente del trabajo principal, MXN |
| Log ingreso | Logaritmo natural del ingreso positivo; respuesta de las regresiones |
| Escolaridad | Nivel máximo con grados aprobados; puede estar incompleto |
| Edad | Edad menos 40 y su cuadrado; permite una relación curva con el log ingreso |
| Jornada | Logaritmo de horas semanales del trabajo principal; se admiten 1–168 |
| Mujer | `sexo=2`, según codificación del cuestionario; referencia `sexo=1` |
| Rural | Tercer dígito de `folioviv=6`, según el diccionario del INEGI |
| Entidad | Indicadores de entidad federativa |
| Ocupación | Gran división: primer dígito de SINCO; solo en modelo de sensibilidad |
| Peso, estrato y UPM | `factor`, `entidad + est_dis` y `entidad + upm` |

P001–P007 incluyen sueldo/destajo, comisiones, horas extra, incentivos, bonos y primas.
Se excluyen aguinaldo/utilidades del ejercicio 2023, trabajos secundarios, negocios y
transferencias. No se confunde esta medida con el ingreso total del hogar.

Los niveles técnicos y normales se conservan en una categoría separada por sus
antecedentes diversos. No se supone que una licenciatura reportada esté terminada.
Se usan observaciones completas, sin imputar el objetivo ni eliminar extremos por IQR.''')
code('''df, descriptivos, modelos, coeficientes, validacion, resultados = a.run()
display(pd.read_csv(a.TABLES/"calidad_fuentes.csv"))
display(pd.read_csv(a.TABLES/"auditoria_muestra.csv"))''')
md('''## 4. Auditoría de la muestra y del diseño

Los faltantes de variables que no aplican en el cuestionario no se tratan como errores
automáticos. La auditoría registra el número excluido en cada filtro. Cada persona
debe tener un único trabajo principal y una sola fila final.

Los factores de expansión se usan como **pesos de encuesta**, no como inversas de
la varianza. WLS resuelve el ajuste ponderado; su covarianza clásica no se utiliza
para la inferencia principal. La covarianza de Taylor agrega scores por UPM y los
centra dentro de cada estrato. Se conserva el marco completo con scores cero para
UPM sin personas del dominio. No se aplica corrección de población finita.''')
code('''assert not df.duplicated(a.KEY).any()
assert df.ingreso_mensual.gt(0).all()
assert df.htrab.between(1, 168).all()
assert df.edad.between(25, 64).all()
display(pd.Series(resultados["diseno"], name="Diseño"))
print("Personas observadas en el dominio:", f"{len(df):,}")
print("Población expandida del dominio:", f"{df.factor.sum():,.0f}")''')
md('''## 5. Distribución del ingreso

La media y la mediana son ponderadas. La transformación logarítmica permite expresar
las diferencias escolares como razones de ingreso y reduce la influencia de la escala
en pesos. No garantiza normalidad ni varianza constante. La primera gráfica se limita
a P99 para facilitar la lectura; **el modelo principal conserva toda la cola superior**.''')
code('''display(pd.Series({"Media mensual (MXN)": resultados["media_mensual_ponderada"],
                   "Mediana mensual (MXN)": resultados["mediana_mensual_ponderada"]}))
display(Image(filename=str(a.FIGURES/"01_distribucion.png")))''')
md('''## 6. Ingreso observado según escolaridad

Las barras muestran medias ponderadas con IC del 95% de Taylor para la media.
Son diferencias descriptivas entre grupos que también pueden diferir en edad,
ocupación, jornada y ubicación. Los cuartiles son cuantiles ponderados y no intervalos
de confianza.''')
code('''display(descriptivos)
display(Image(filename=str(a.FIGURES/"02_ingreso_escolaridad.png")))''')
md(r'''## 7. Especificación de la regresión

Modelo principal:

$$\log(Y_i)=\beta_0+\sum_g\beta_g I(E_i=g)+\beta_1(A_i-40)
+\beta_2(A_i-40)^2+\beta_3\log(H_i)+\beta_4 M_i+\beta_5 R_i
+\sum_s\gamma_s I(S_i=s)+\varepsilon_i.$$

El ajuste minimiza $\sum_i w_i(y_i-X_i\beta)^2$. Para un nivel escolar,
$100[\exp(\beta_g)-1]$ es la diferencia porcentual de la media geométrica condicional
frente a secundaria; no es directamente una diferencia de medias aritméticas en pesos.
Se transforman también ambos límites del intervalo.

El tercer modelo agrega ocupación como sensibilidad. La ocupación podría formar parte
del mecanismo que vincula educación e ingreso; incluirla cambia la comparación y no
"elimina" por sí sola el sesgo de confusión.''')
code('''display(pd.DataFrame({"Modelo": list(a.FORMULAS), "Fórmula": list(a.FORMULAS.values())}))
display(pd.read_csv(a.TABLES/"comparacion_ajuste.csv"))
display(coeficientes["Modelo ajustado"])
display(pd.read_csv(a.TABLES/"efectos_ajustados.csv")[["educacion","diferencia_pct","pct_inf","pct_sup","p"]])''')
md('''## 8. Intervalos y prueba conjunta

La covarianza de Taylor permite que la dispersión de los errores sea distinta y contempla
la agrupación de la muestra por UPM. Los IC se construyen con t y grados de libertad
UPM menos estratos. Si hay estratos con una UPM, se registra el ajuste de centrado global.
La prueba Wald conjunta examina todos los contrastes escolares a la vez.

Los valores p que aparecen como 0.0000 por redondeo o límites de precisión deben leerse
como p &lt; 0.0001; no como probabilidades exactamente nulas.

No rechazar una hipótesis no demuestra igualdad. Los IC del 95% se refieren al
procedimiento de estimación, no a una probabilidad posterior del parámetro.''')
code('''display(pd.DataFrame([resultados["prueba_escolaridad"]]))
display(Image(filename=str(a.FIGURES/"03_efectos_ajustados.png")))''')
md('''## 9. Diagnóstico y sensibilidad

Se agrega una salida OLS clásica como contraste exploratorio. Breusch–Pagan
y Jarque–Bera se reportan como diagnósticos exploratorios de ese ajuste; sus valores p
clásicos no incorporan el diseño de encuesta. La inferencia principal permanece en la
tabla con covarianza Taylor. El orden de filas no es temporal: Durbin–Watson no permite
concluir dependencia temporal en estos datos.

La sensibilidad sin el 1% superior se compara con el modelo completo y no reemplaza
silenciosamente la muestra principal.''')
code('''diagnosticos=json.loads((ROOT/"outputs/diagnosticos.json").read_text(encoding="utf-8"))
display(pd.Series(diagnosticos))
display(pd.read_csv(a.TABLES/"sensibilidad_extremos.csv"))
display(pd.read_csv(a.TABLES/"efectos_ocupacion.csv")[["educacion","diferencia_pct","pct_inf","pct_sup"]])
display(Image(filename=str(a.FIGURES/"04_diagnosticos.png")))''')
md('''## 10. Evaluación en observaciones reservadas

Se reserva aproximadamente 20% de las UPM con semilla 2026; una UPM completa pertenece
a entrenamiento o a prueba. Los coeficientes y la corrección de retrans­formación se
estiman exclusivamente en entrenamiento. Se compara con predecir la media ponderada
de entrenamiento para todas las personas.

Se reportan MAE, RMSE y R² ponderados en pesos, además de RMSE en log. La conversión
de log a pesos utiliza el factor global de Duan calculado con los residuos de entrenamiento;
es una aproximación y puede ser insuficiente si la dispersión depende de los predictores.
La evaluación es interna a esta encuesta; no acredita desempeño en otros años.''')
code('''display(pd.Series(resultados["validacion"]))
display(validacion)
display(Image(filename=str(a.FIGURES/"05_validacion.png")))''')
md('''## 11. Síntesis de resultados

La siguiente síntesis se forma con los resultados de esta ejecución. El resumen visual
utiliza las mismas tablas y gráficas de este cuaderno.''')
code('''lic=next(x for x in resultados["efectos_educacion"] if x["educacion"]=="Licenciatura")
display(Markdown(f"""En **{resultados['n']:,} personas observadas**, la categoría licenciatura presenta
una diferencia ajustada de **{lic['diferencia_pct']:+.1f}%** frente a secundaria,
con IC95% **[{lic['pct_inf']:.1f}%, {lic['pct_sup']:.1f}%]** en ingreso geométrico condicional.
El R² ponderado del modelo ajustado en escala logarítmica es **{resultados['r2_log_ajustado']:.3f}**.
Estos resultados describen a la población delimitada y no identifican el efecto causal de estudiar."""))''')
md('''## 12. Límites e interpretación

- Se observa solo a personas con un empleo subordinado remunerado e ingreso positivo.
  No se estima acceso al empleo, desempleo ni el beneficio total de una trayectoria escolar.
- Escolaridad indica el nivel con grados aprobados; puede estar incompleto. Técnica/normal
  reúne trayectorias distintas. No se atribuye una duración escolar inventada.
- Edad no equivale a experiencia laboral. No se observan todas las diferencias de habilidad,
  calidad educativa, historia familiar ni selección ocupacional.
- El ingreso trimestral mensualizado y las horas de la semana habitual tienen periodos
  de referencia distintos; la relación no es una contabilidad de salario por hora exacta.
- El diseño es transversal. Las diferencias ajustadas son asociaciones y no garantizan
  aumentos individuales de ingreso al obtener un grado.
- El ajuste de encuesta es una aproximación de Taylor con reemplazo. Los resultados son
  elaboración propia, no tabulados oficiales del INEGI.
- R² mide ajuste en una escala específica, no porcentaje de exactitud de un salario.

## Referencias

Instituto Nacional de Estadística y Geografía. (2025). *Encuesta Nacional de Ingresos y
Gastos de los Hogares 2024, Nueva Serie* [Microdatos]. https://www.inegi.org.mx/programas/enigh/nc/2024/

Instituto Nacional de Estadística y Geografía. (2025). *ENIGH 2024: Descripción de la base de datos*.
https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/microdatos/889463924494.pdf

Instituto Nacional de Estadística y Geografía. (2025). *ENIGH 2024: Diseño muestral*.
https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/doc/889463924517.pdf

statsmodels. (s. f.). *Weighted least squares and regression diagnostics*.
https://www.statsmodels.org/stable/regression.html

scikit-learn. (s. f.). *GroupShuffleSplit*.
https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupShuffleSplit.html''')
code('''display(pd.Series(json.loads((ROOT/"outputs/entorno.json").read_text(encoding="utf-8"))))
print("Tablas:", len(list(a.TABLES.glob("*.csv"))))
print("Gráficas PNG:", len(list(a.FIGURES.glob("*.png"))))''')

def main():
    notebooks=ROOT/'notebooks';notebooks.mkdir(exist_ok=True)
    nb=nbf.v4.new_notebook(cells=cells)
    nb.metadata.kernelspec={'display_name':'Python 3','language':'python','name':'python3'}
    nb.metadata.language_info={'name':'python','version':sys.version.split()[0]}
    target=notebooks/'01_educacion_ingresos_enigh2024.ipynb'
    nbf.write(nb,target)
    kernel=ROOT/'.jupyter/kernels/educacion-local';kernel.mkdir(parents=True,exist_ok=True)
    (kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
                      'display_name':'Educacion local','language':'python'}),encoding='utf-8')
    os.environ['JUPYTER_PATH']=str(ROOT/'.jupyter')
    os.environ['JUPYTER_RUNTIME_DIR']=str(ROOT/'.jupyter/runtime')
    Path(os.environ['JUPYTER_RUNTIME_DIR']).mkdir(exist_ok=True)
    client=NotebookClient(nb,timeout=1200,kernel_name='educacion-local',resources={'metadata':{'path':str(ROOT)}})
    client.execute()
    nb.metadata.kernelspec={'display_name':'Python 3','language':'python','name':'python3'}
    nbf.write(nb,target)
    html,_=HTMLExporter().from_notebook_node(nb)
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    (reports/'analisis_educacion_ingresos.html').write_text(html,encoding='utf-8')
    count=sum(c.cell_type=='code' for c in nb.cells)
    errors=sum(o.get('output_type')=='error' for c in nb.cells for o in c.get('outputs',[]))
    print(f'Cuaderno ejecutado: {count} celdas de código, {errors} errores',flush=True)

if __name__=='__main__':main()
