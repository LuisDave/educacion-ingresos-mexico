"""Resumen visual de una página. Usa exclusivamente resultados del análisis."""
from pathlib import Path
import json
import hashlib
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor,white
from reportlab.lib.utils import ImageReader
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'visuals';OUT.mkdir(exist_ok=True)
PURPLE='#74007c';INK='#243346';BLUE='#146a97';PALE='#f5f0f7'
W=900/25.4*72;H=675/25.4*72
FONT_DIR=Path('C:/Windows/Fonts')
if FONT_DIR.exists():
    regular=FONT_DIR/'arial.ttf';bold=FONT_DIR/'arialbd.ttf'
    italic=FONT_DIR/'ariali.ttf';bold_italic=FONT_DIR/'arialbi.ttf'
else:
    from matplotlib import font_manager
    regular=Path(font_manager.findfont('DejaVu Sans'))
    bold=Path(font_manager.findfont(matplotlib.font_manager.FontProperties(family='DejaVu Sans',weight='bold')))
    italic=Path(font_manager.findfont(matplotlib.font_manager.FontProperties(family='DejaVu Sans',style='italic')))
    bold_italic=Path(font_manager.findfont(matplotlib.font_manager.FontProperties(family='DejaVu Sans',weight='bold',style='italic')))
pdfmetrics.registerFont(TTFont('Body',str(regular)))
pdfmetrics.registerFont(TTFont('Bold',str(bold)))
pdfmetrics.registerFont(TTFont('Italic',str(italic)))
pdfmetrics.registerFont(TTFont('BoldItalic',str(bold_italic)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold',italic='Italic',boldItalic='BoldItalic')

def build():
    s=json.loads((ROOT/'outputs/resultados.json').read_text(encoding='utf-8'))
    validation=pd.read_csv(ROOT/'outputs/tables/validacion_upm.csv')
    sensitivity=pd.read_csv(ROOT/'outputs/tables/sensibilidad_extremos.csv')
    lic_trim=sensitivity.loc[sensitivity.termino.str.contains('T.Licenciatura',regex=False),'pct_sin_1pct_superior'].iloc[0]
    lic=next(x for x in s['efectos_educacion'] if x['educacion']=='Licenciatura')
    coefficients=pd.read_csv(ROOT/'outputs/tables/coef_ajustado.csv')
    blic=coefficients.loc[coefficients.termino.str.contains('T.Licenciatura',regex=False)].iloc[0]
    fit=pd.read_csv(ROOT/'outputs/tables/comparacion_ajuste.csv')
    school_r2=fit.loc[fit.modelo.eq('Escolaridad sola'),'r2_ponderada_log'].iloc[0]
    wald=s['prueba_escolaridad']
    secondary=float(pd.read_csv(ROOT/'outputs/tables/ingreso_por_escolaridad.csv').query("educacion == 'Secundaria'").media_mensual.iloc[0])
    mae=float(validation.loc[validation.modelo.eq('Modelo ajustado'),'mae_pesos'].iloc[0])
    baseline=float(validation.loc[validation.modelo.eq('Media de entrenamiento'),'mae_pesos'].iloc[0])
    pct_improvement=100*(1-mae/baseline)
    c=canvas.Canvas(str(OUT/'resumen_educacion_ingresos.pdf'),pagesize=(W,H))
    c.setTitle('Educación e ingresos en México | ENIGH 2024')
    c.setAuthor('Luis David Gonzalez Romero y Diego Alberto Ortega Carreto')
    boxes=[]
    def line(text,x,y,size=26,bold=False,color=INK):
        c.setFillColor(HexColor(color));c.setFont('Bold' if bold else 'Body',size)
        c.drawString(x,H-y-size*.82,text)
    def centered(text,x,y,size=26,bold=False,color=INK):
        c.setFillColor(HexColor(color));c.setFont('Bold' if bold else 'Body',size)
        c.drawCentredString(x,H-y-size*.82,text)
    def paragraph(text,x,y,width,size=26,leading=None,color=INK,hanging=0,align=0):
        style=ParagraphStyle('body',fontName='Body',fontSize=size,leading=leading or size*1.24,textColor=HexColor(color),spaceAfter=0,leftIndent=hanging,firstLineIndent=-hanging,alignment=align)
        p=Paragraph(text,style);pw,ph=p.wrap(width,H)
        p.drawOn(c,x,H-y-ph);boxes.append({'x':x,'y':y,'w':pw,'h':ph,'text':text[:50]})
        return y+ph
    def section(title,x,y,width):
        c.setFillColor(HexColor(PURPLE));c.roundRect(x,H-y-47,width,47,7,fill=1,stroke=0)
        centered(title,x+width/2,y+7,31,True,'#ffffff')
        return y+62
    def picture(name,x,y,width):
        p=ROOT/f'outputs/figures/{name}.png'
        im=Image.open(p);height=width*im.height/im.width
        c.drawImage(ImageReader(im),x,H-y-height,width,height,mask='auto')
        return y+height
    c.setFillColor(white);c.rect(0,0,W,H,fill=1,stroke=0)
    c.setStrokeColor(HexColor(PURPLE));c.setLineWidth(8);c.rect(4,4,W-8,H-8,fill=0,stroke=1)
    # Encabezado del resumen visual.
    c.setFillColor(HexColor('#ebebeb'));c.rect(8,H-250,W-16,242,fill=1,stroke=0)
    centered('ENIGH',230,45,63,True,PURPLE)
    centered('2024',230,113,67,True,PURPLE)
    centered('DATOS ABIERTOS · MÉXICO',230,199,21,color=BLUE)
    c.setStrokeColor(HexColor('#cfbfd1'));c.setLineWidth(1.4)
    c.line(445,H-30,445,H-225);c.line(W-445,H-30,W-445,H-225)
    centered('¿Estudiar más se relaciona',W/2,24,63,True,PURPLE)
    centered('con ganar más en México?',W/2,94,63,True,PURPLE)
    centered('Escolaridad e ingreso del trabajo principal · ENIGH 2024',W/2,168,28,color=BLUE)
    centered('Luis David Gonzalez Romero  ·  Diego Alberto Ortega Carreto',W/2,215,27,True,PURPLE)
    paragraph('<b>Análisis exploratorio</b><br/>Regresión e inferencia<br/>Datos abiertos del INEGI<br/>Python · ENIGH 2024<br/>25 de octubre de 2026',W-427,50,394,23,31,align=1)
    margin=34;gap=24;col=(W-2*margin-2*gap)/3
    x1=margin;x2=x1+col+gap;x3=x2+col+gap
    # Primera columna: contexto, objetivo, muestra y matemáticas aplicadas.
    y=section('1. Contexto',x1,267,col)
    y=paragraph('La escolaridad y el ingreso pueden variar con la edad, la jornada y la ubicación. Se analiza su asociación en una población laboral definida de México (INEGI, 2025c).',x1+12,y,col-24)+24
    y=section('2. Pregunta de análisis',x1,y,col)
    y=paragraph('¿Cómo difiere el ingreso por escolaridad al considerar edad, jornada, sexo y ubicación? Se comparan las brechas mediante regresión e intervalos de confianza del 95% (IC95%).',x1+12,y,col-24)+24
    y=section('3. Datos y población de estudio',x1,y,col)
    y=paragraph('<b>Tabla 1.</b> Delimitación de la muestra y la respuesta.',x1+12,y,col-24,23,align=1)+10
    rows=[('Fuente','ENIGH 2024 · INEGI'),('Muestra analítica',f"{s['n']:,} personas"),('Edad','25 a 64 años'),('Empleo','Uno, subordinado, pagado, en México'),('Ingreso mensual (MXN)','Ingreso trimestral principal / 3')]
    for i,(label,value) in enumerate(rows):
        if i%2==0:c.setFillColor(HexColor(PALE));c.rect(x1+9,H-y-39,col-18,39,fill=1,stroke=0)
        line(label,x1+17,y+8,23,True);line(value,x1+305,y+8,22);y+=39
    y+=13
    y=paragraph('La Tabla 1 considera ingreso principal positivo y jornadas de 1 a 168 h/semana. Escolaridad: nivel con grados aprobados; puede estar incompleto.',x1+12,y,col-24,23)+20
    y=section('4. Metodología y modelo',x1,y,col)
    y=paragraph('Regresión lineal múltiple ponderada con factores de expansión. Controles: edad, edad², log horas, sexo, ruralidad y entidad. IC95% de Taylor por estrato y unidad primaria de muestreo (UPM) (INEGI, 2025b).',x1+12,y,col-24,23)+9
    fig=plt.figure(figsize=(12,2.5))
    fig.text(.01,.77,r'$\log(Y_i)=\beta_0+\sum_{g=1}^{6}\beta_g I(E_i=g)+\mathbf{z}_i^T\gamma+\varepsilon_i$',fontsize=23)
    fig.text(.01,.43,r'$\widehat{\theta}=\arg\min_{\theta}\sum_i w_i[\log(Y_i)-\mathbf{x}_i^T\theta]^2$',fontsize=23)
    fig.text(.01,.10,r'$\Delta_g(\%)=100[\exp(\beta_g)-1]$',fontsize=23)
    formula=OUT/'modelo.png';fig.savefig(formula,dpi=300,bbox_inches='tight',facecolor='white')
    fig.savefig(OUT/'modelo.svg',bbox_inches='tight',facecolor='white');plt.close(fig)
    im=Image.open(formula);formula_width=col-135;height=formula_width*im.height/im.width
    c.drawImage(ImageReader(im),x1+(col-formula_width)/2,H-y-height,formula_width,height);y+=height+7
    y=paragraph('<i>Y</i>: ingreso; <i>E</i>: escolaridad; <i>I</i>: indicador; β<sub>0</sub>: intercepto; β<sub>g</sub>: contrastes escolares; <b>z</b>: controles y γ: sus coeficientes; <b>x</b>: predictores; θ: coeficientes del modelo; <i>w</i>: factor; ε: error.',x1+12,y,col-24,22)+9
    end1=paragraph('Referencia: secundaria. Δ compara ingreso geométrico condicional.<br/><b>H<sub>0</sub></b>: β<sub>1</sub> = ... = β<sub>6</sub> = 0; <b>H<sub>1</sub></b>: alguno difiere; α = 0.05.',x1+12,y,col-24,22)
    # Segunda columna: evidencia principal y tamaños de asociación.
    y2=section('5. Resultados e interpretación',x2,267,col)
    y2=picture('02_ingreso_escolaridad',x2+25,y2,col-50)
    y2=paragraph('Figura 1. Medias ponderadas e IC95% para la media. En secundaria, el promedio observado es '+f'${secondary:,.0f} MXN mensuales. Los grupos también difieren en otros factores.',x2+12,y2+8,col-24,23,align=1)+24
    y2=picture('03_efectos_ajustados',x2+25,y2,col-50)
    y2=paragraph('Figura 2. Diferencias ajustadas frente a secundaria e IC95%. Se rechaza H<sub>0</sub>: hay asociación al considerar edad, jornada, sexo, ámbito y entidad. Los intervalos contemplan el diseño de encuesta.',x2+12,y2+7,col-24,23,align=1)+12
    c.setFillColor(HexColor(PALE));c.roundRect(x2+10,H-y2-58,col-20,68,9,fill=1,stroke=0)
    centered(f"Licenciatura: {lic['diferencia_pct']:+.1f}%",x2+col/2,y2,49,True,PURPLE)
    y2+=65
    y2=paragraph(f"β<sub>Lic</sub> = {blic.coef:.3f}; IC95% β: [{blic.ic95_inf:.3f}, {blic.ic95_sup:.3f}].<br/>IC95% Δ: <b>[{lic['pct_inf']:.1f}%, {lic['pct_sup']:.1f}%]</b> vs. secundaria.<br/>R² ponderado en log: <b>{s['r2_log_ajustado']:.3f}</b>; escolaridad sola: {school_r2:.3f}.<br/>Wald F({wald['gl_num']}, {wald['gl_den']:,}) = {wald['F']:.2f}; <b>p &lt; 0.001</b>.",x2+15,y2,col-30,24,align=1)+12
    end2=paragraph(f"Lectura: ingreso típico ≈ {1+lic['diferencia_pct']/100:.2f} veces el de secundaria con iguales factores del modelo (media geométrica). No implica causalidad.",x2+15,y2,col-30,23,color=BLUE,align=1)
    # Tercera columna: comprobación predictiva y límites.
    y3=section('6. Validación y límites',x3,267,col)
    y3=picture('04_diagnosticos',x3,y3,col)
    y3=paragraph('Figura 3. Residuos y Q-Q: persisten colas y dispersión desigual. Los diagnósticos clásicos son exploratorios; la inferencia principal usa la covarianza del diseño de encuesta.',x3+12,y3+8,col-24,24)+24
    y3=picture('05_validacion',x3,y3,col)
    y3=paragraph(f"Figura 4. Prueba en {s['validacion']['n_test']:,} personas de UPM completas reservadas. MAE (error absoluto medio) ponderado del modelo ajustado: <b>${mae:,.0f} MXN</b>; mide cuánto se aleja en promedio la predicción del ingreso observado. Frente a predecir la media (${baseline:,.0f}), el error baja <b>{pct_improvement:.1f}%</b>. Retransformación de Duan (1983), estimada en entrenamiento.",x3+12,y3+8,col-24,23)+18
    end3=paragraph('<b>Límites.</b> Asociación, sin identificación causal. Solo personas empleadas con ingreso positivo; edad no equivale a experiencia. Validación interna, sin garantía para otros años.',x3+12,y3,col-24,23)
    # Pie: conclusión aplicada y bibliografía.
    bottom=1660
    if max(end1,end2)>bottom-15:
        raise ValueError(f'Columnas invaden el pie: {end1=:.1f}, {end2=:.1f}')
    yb=section('7. Hallazgos y conclusiones',x1,bottom,col*2+gap)
    paragraph(f"<b>1. Brechas cuantificadas.</b> Licenciatura: {lic['diferencia_pct']:+.1f}% frente a secundaria; sin el 1% superior, solo como sensibilidad: {lic_trim:+.1f}%.<br/><b>2. Explicación parcial.</b> El modelo describe el {100*s['r2_log_ajustado']:.1f}% de la variación ponderada del log ingreso; quedan factores fuera.<br/><b>3. Predicción con límites.</b> El error baja {pct_improvement:.1f}% frente a predecir la media. Las brechas no identifican el efecto causal de estudiar.",x1+15,yb,col*2+gap-30,25)
    ref_top=max(1380,end3+20)
    yr=section('8. Dataset y referencias',x3,ref_top,col)
    c.setFillColor(HexColor(PALE));c.roundRect(x3+10,H-yr-61,col-20,61,8,fill=1,stroke=0)
    dataset_links=' · '.join(f'<link href="https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/microdatos/enigh2024_ns_{key}_csv.zip" color="#146a97">{label}</link>' for key,label in [('poblacion','Población'),('ingresos','Ingresos'),('trabajos','Trabajos')])
    yr=paragraph('<b>Dataset oficial: INEGI · ENIGH 2024</b><br/>Tablas descargables: '+dataset_links,x3+12,yr+5,col-24,20,24,align=1)+18
    refs=[
      'Duan, N. (1983). Smearing estimate: A nonparametric retransformation method. <i>Journal of the American Statistical Association, 78</i>(383), 605-610. <link href="https://doi.org/10.1080/01621459.1983.10478017" color="#146a97">https://doi.org/10.1080/01621459.1983.10478017</link>',
      'Instituto Nacional de Estadística y Geografía. (2025a). <i>Encuesta Nacional de Ingresos y Gastos de los Hogares 2024: Descripción de la base de datos</i>. <link href="https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/microdatos/889463924494.pdf" color="#146a97">https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/microdatos/889463924494.pdf</link>',
      'Instituto Nacional de Estadística y Geografía. (2025b). <i>Encuesta Nacional de Ingresos y Gastos de los Hogares 2024: Diseño muestral</i>. <link href="https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/doc/889463924517.pdf" color="#146a97">https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/doc/889463924517.pdf</link>',
      'Instituto Nacional de Estadística y Geografía. (2025c). <i>Encuesta Nacional de Ingresos y Gastos de los Hogares 2024, Nueva Serie</i> [Microdatos]. <link href="https://www.inegi.org.mx/programas/enigh/nc/2024/" color="#146a97">https://www.inegi.org.mx/programas/enigh/nc/2024/</link>'
    ]
    for ref in refs:yr=paragraph(ref,x3+12,yr,col-24,18,21.5,hanging=18)+8
    paragraph('<b>Proyecto:</b> educacion-ingresos-mexico · Código y notebook incluidos.',x3+12,yr,col-24,18,22,align=1)
    centered('Tabla 1 y figuras 1-4: elaboración propia con ENIGH 2024; no es un tabulado oficial.  ·  90 × 67.5 cm  ·  Análisis reproducible en Python',W/2,H-48,20,color=PURPLE)
    for b in boxes:
        if b['y']+b['h']>H-58:raise ValueError(f'Texto fuera de página: {b}')
    c.showPage();c.save()
    graph_names=['02_ingreso_escolaridad.png','03_efectos_ajustados.png','04_diagnosticos.png','05_validacion.png']
    evidence=['outputs/resultados.json','outputs/tables/coef_ajustado.csv','outputs/tables/ingreso_por_escolaridad.csv','outputs/tables/validacion_upm.csv','outputs/tables/sensibilidad_extremos.csv','notebooks/01_educacion_ingresos_enigh2024.ipynb']+[f'outputs/figures/{f}' for f in graph_names]
    (OUT/'metadatos_resumen.json').write_text(json.dumps({'n':s['n'],'licenciatura_pct':lic['diferencia_pct'],'licenciatura_ic':[lic['pct_inf'],lic['pct_sup']],
       'coef_licenciatura':float(blic.coef),'prueba_escolaridad':wald,'r2_log':s['r2_log_ajustado'],'mae_prueba':mae,'fuentes_graficas':graph_names,
       'editor_ecuaciones':'Matplotlib MathText; PNG de 300 dpi y fuente SVG',
       'sha256_fuentes':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in evidence},
       'revision_distribucion':{'fin_columna_1':end1,'fin_columna_2':end2,'inicio_conclusion':bottom,'fin_validacion':end3,'inicio_referencias':ref_top}},indent=2,ensure_ascii=False),encoding='utf-8')
    print(OUT/'resumen_educacion_ingresos.pdf')

if __name__=='__main__':build()
