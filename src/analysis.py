"""Análisis reproducible de educación e ingresos, ENIGH 2024 Nueva Serie.

Los factores de expansión son pesos de encuesta, NO pesos de precisión.
Se usa WLS para resolver las ecuaciones ponderadas; la inferencia principal
usa una covarianza de Taylor por estrato y UPM, calculada explícitamente.
"""
from pathlib import Path
import json, platform, importlib.metadata
import numpy as np
import pandas as pd
import scipy.stats as st
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import jarque_bera, durbin_watson
from sklearn.model_selection import GroupShuffleSplit
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT=Path(__file__).resolve().parents[1]
TABLES=ROOT/'outputs/tables'
FIGURES=ROOT/'outputs/figures'
KEY=['folioviv','foliohog','numren']
LEVELS=['Sin primaria','Primaria','Secundaria','Media superior','Técnica o normal','Licenciatura','Posgrado']
EDU={0:LEVELS[0],1:LEVELS[0],2:LEVELS[1],3:LEVELS[2],4:LEVELS[3],5:LEVELS[4],6:LEVELS[4],7:LEVELS[5],8:LEVELS[6],9:LEVELS[6],10:LEVELS[6]}
EDU_TERM="C(educacion, Treatment(reference='Secundaria'))"
FORMULAS={
 'Escolaridad sola':f'log_ingreso ~ {EDU_TERM}',
 'Modelo ajustado':f'log_ingreso ~ {EDU_TERM} + edad_c + edad_c2 + log_horas + mujer + rural + C(entidad)',
 'Con ocupación':f'log_ingreso ~ {EDU_TERM} + edad_c + edad_c2 + log_horas + mujer + rural + C(entidad) + C(ocupacion)',
}
PURPLE='#74007c';BLUE='#146a97';ORANGE='#d57922';INK='#243346'

def save_table(df,name):
    TABLES.mkdir(parents=True,exist_ok=True)
    df.to_csv(TABLES/name,index=False,encoding='utf-8-sig',float_format='%.10g')

def load_data():
    """Lee claves como texto para conservar ceros y evitar uniones ambiguas."""
    dtypes={c:'string' for c in KEY+['entidad','est_dis','upm','sinco']}
    popcols=KEY+['parentesco','sexo','edad','nivelaprob','gradoaprob','antec_esc','num_trabaj','entidad','est_dis','upm','factor']
    jobcols=KEY+['id_trabajo','trapais','subor','pago','htrab','sinco']
    inccols=KEY+['clave','ing_tri']
    def read(table,cols):
        return pd.read_csv(ROOT/f'data/raw/{table}.csv',usecols=cols,
                           dtype={k:v for k,v in dtypes.items() if k in cols},
                           na_values=[' ',''],low_memory=False)
    return read('poblacion',popcols),read('trabajos',jobcols),read('ingresos',inccols)

def prepare(pop,jobs,incomes):
    if pop.duplicated(KEY).any():raise ValueError('Claves de persona duplicadas')
    primary=jobs.loc[jobs.id_trabajo.eq(1)].copy()
    if primary.duplicated(KEY).any():raise ValueError('Trabajo principal duplicado')
    # P001-P007: ingreso monetario corriente del trabajo principal subordinado.
    # Se excluyen aguinaldo/utilidades del ejercicio 2023 (P008/P009), ingresos
    # de trabajos secundarios, transferencias e ingresos de negocios.
    codes=[f'P{i:03d}' for i in range(1,8)]
    inc=incomes.loc[incomes.clave.isin(codes)].groupby(KEY,as_index=False).ing_tri.sum(min_count=1)
    merged=pop.merge(primary,on=KEY,how='left',validate='one_to_one').merge(inc,on=KEY,how='left',validate='one_to_one')
    merged['ingreso_mensual']=merged.ing_tri/3
    merged['educacion']=pd.Categorical(merged.nivelaprob.map(EDU),categories=LEVELS)
    merged['mujer']=merged.sexo.eq(2).astype(int)
    # Diccionario: tercer dígito de folioviv=6 identifica ámbito rural.
    merged['rural']=merged.folioviv.str[2].eq('6').astype(int)
    merged['edad_c']=merged.edad-40
    merged['edad_c2']=merged.edad_c**2
    merged['ocupacion']=merged.sinco.str[0].fillna('0')
    merged['estrato']=merged.entidad.str.zfill(2)+'_'+merged.est_dis
    merged['psu']=merged.entidad.str.zfill(2)+'_'+merged.upm
    design=merged[['estrato','psu']].drop_duplicates().dropna()
    if design.groupby('psu').estrato.nunique().max()!=1:raise ValueError('UPM en varios estratos')
    audit=[]
    current=merged
    filters=[
      ('Personas de la tabla Población',np.ones(len(merged),dtype=bool)),
      ('Edad entre 25 y 64 años',merged.edad.between(25,64)),
      ('Un solo trabajo declarado',merged.num_trabaj.eq(1)),
      ('Principal subordinado, remunerado y en México',merged.subor.eq(1)&merged.pago.eq(1)&merged.trapais.eq(1)),
      ('Ingreso principal monetario positivo (P001-P007)',merged.ingreso_mensual.gt(0)),
      ('Horas semanales válidas, entre 1 y 168',merged.htrab.between(1,168)),
      ('Escolaridad y diseño observados',merged.educacion.notna()&merged.factor.gt(0)&merged.estrato.notna()&merged.psu.notna()&merged.sexo.isin([1,2])),
      ('Integrantes del hogar (sin huéspedes ni servicio doméstico)',merged.parentesco.astype('string').str[0].isin(list('12356'))),
    ]
    keep=pd.Series(True,index=merged.index)
    for label,condition in filters:
        before=int(keep.sum());keep &= condition
        audit.append({'etapa':label,'n':int(keep.sum()),'excluidos_en_etapa':before-int(keep.sum())})
    df=merged.loc[keep].copy()
    df['log_ingreso']=np.log(df.ingreso_mensual)
    df['log_horas']=np.log(df.htrab)
    df['peso']=df.factor/df.factor.mean()
    if df.duplicated(KEY).any():raise ValueError('La unión multiplicó personas')
    quality=pd.DataFrame([{'tabla':name,'filas':len(t),'duplicados_exactos':int(t.duplicated().sum()),
                           'celdas_ausentes':int(t.isna().sum().sum())}
                          for name,t in [('poblacion_seleccion',pop),('trabajos_seleccion',jobs),('ingresos_seleccion',incomes)]])
    save_table(pd.DataFrame(audit),'auditoria_muestra.csv')
    save_table(quality,'calidad_fuentes.csv')
    return df.reset_index(drop=True),design,pd.DataFrame(audit)

def meat_by_design(scores,design):
    """Taylor con reemplazo, sin corrección de población finita.

    Conserva en el marco las UPM sin miembros del dominio, con score cero.
    Var(T)=sum_h m_h/(m_h-1) sum_j (T_hj-T_hmedia)(...)'.
    Estratos con una UPM usan centrado respecto al promedio global de UPM
    como ajuste conservador; su número se registra y se explica en el informe.
    """
    cols=[c for c in scores if c not in ['estrato','psu']]
    sums=scores.groupby(['estrato','psu'],observed=True)[cols].sum().reset_index()
    all_psu=design.merge(sums,on=['estrato','psu'],how='left').fillna({c:0.0 for c in cols})
    meat=np.zeros((len(cols),len(cols)))
    singleton=0
    center=all_psu[cols].mean().to_numpy()
    for _,g in all_psu.groupby('estrato',observed=True):
        a=g[cols].to_numpy();m=len(a)
        if m>1:
            dev=a-a.mean(axis=0);meat+=(m/(m-1))*(dev.T@dev)
        else:
            dev=a-center;meat+=dev.T@dev;singleton+=1
    info={'upm':len(all_psu),'estratos':all_psu.estrato.nunique(),
          'gl_diseno':int(len(all_psu)-all_psu.estrato.nunique()),'estratos_unitarios':singleton}
    return meat,info

def survey_covariance(model,df,design):
    x=np.asarray(model.model.exog);w=df.peso.to_numpy();r=np.asarray(model.resid)
    scores=pd.DataFrame(x*(w*r)[:,None],columns=[f's{i}' for i in range(x.shape[1])])
    scores[['estrato','psu']]=df[['estrato','psu']].to_numpy()
    meat,info=meat_by_design(scores,design)
    bread=np.linalg.inv((x.T*w)@x)
    cov=bread@meat@bread
    return (cov+cov.T)/2,info

def coef_table(model,cov,design_df):
    b=np.asarray(model.params);se=np.sqrt(np.maximum(np.diag(cov),0));t=b/se
    critical=st.t.ppf(.975,design_df)
    return pd.DataFrame({'termino':model.model.exog_names,'coef':b,'error_estandar':se,
                         't':t,'p':2*st.t.sf(abs(t),design_df),
                         'ic95_inf':b-critical*se,'ic95_sup':b+critical*se})

def education_effects(table):
    subset=table.loc[table.termino.str.startswith('C(educacion')].copy()
    subset['educacion']=subset.termino.str.extract(r'\[T\.(.*)\]')[0]
    for column in ['coef','ic95_inf','ic95_sup']:
        subset[column.replace('coef','diferencia_pct').replace('ic95_inf','pct_inf').replace('ic95_sup','pct_sup')]=100*np.expm1(subset[column])
    return subset

def weighted_quantile(x,w,q):
    order=np.argsort(x);x=np.asarray(x)[order];w=np.asarray(w)[order]
    return float(x[np.searchsorted(np.cumsum(w),q*w.sum(),side='left')])

def descriptive_by_education(df,design):
    rows=[]
    for level in LEVELS:
        mask=df.educacion.eq(level);g=df.loc[mask];w=g.factor.to_numpy();y=g.ingreso_mensual.to_numpy()
        mean=np.average(y,weights=w)
        scores=pd.DataFrame({'estrato':df.estrato,'psu':df.psu,
                             'score':np.where(mask,df.factor*(df.ingreso_mensual-mean)/w.sum(),0)})
        v,info=meat_by_design(scores,design);se=np.sqrt(v[0,0]);crit=st.t.ppf(.975,info['gl_diseno'])
        rows.append({'educacion':level,'n':len(g),'personas_expandidas':w.sum(),
                     'media_mensual':mean,'mediana_mensual':weighted_quantile(y,w,.5),
                     'q1_mensual':weighted_quantile(y,w,.25),'q3_mensual':weighted_quantile(y,w,.75),
                     'ic95_media_inf':mean-crit*se,'ic95_media_sup':mean+crit*se})
    return pd.DataFrame(rows)

def fit_models(df,design):
    models={};tables={};covs={};metrics=[]
    for name,formula in FORMULAS.items():
        m=smf.wls(formula,df,weights=df.peso).fit()
        cov,info=survey_covariance(m,df,design)
        tab=coef_table(m,cov,info['gl_diseno'])
        models[name]=m;tables[name]=tab;covs[name]=cov
        metrics.append({'modelo':name,'n':int(m.nobs),'parametros':len(m.params),
                        'r2_ponderada_log':m.rsquared,'r2_ajustada_log':m.rsquared_adj,
                        'condicion':m.condition_number})
        save_table(tab,{'Escolaridad sola':'coef_escolaridad.csv','Modelo ajustado':'coef_ajustado.csv','Con ocupación':'coef_ocupacion.csv'}[name])
    # Prueba Wald conjunta de todos los contrastes de escolaridad con covarianza Taylor.
    m=models['Modelo ajustado'];tab=tables['Modelo ajustado'];cov=covs['Modelo ajustado']
    ix=np.array([i for i,n in enumerate(m.model.exog_names) if n.startswith('C(educacion')])
    b=np.asarray(m.params)[ix];q=len(ix)
    f=float(b@np.linalg.solve(cov[np.ix_(ix,ix)],b)/q)
    wald={'F':f,'gl_num':q,'gl_den':info['gl_diseno'],'p':float(st.f.sf(f,q,info['gl_diseno']))}
    save_table(pd.DataFrame(metrics),'comparacion_ajuste.csv')
    save_table(pd.DataFrame([wald]),'wald_escolaridad.csv')
    for name,tab in tables.items():
        save_table(education_effects(tab),{'Escolaridad sola':'efectos_sin_ajustar.csv','Modelo ajustado':'efectos_ajustados.csv','Con ocupación':'efectos_ocupacion.csv'}[name])
    return models,tables,covs,info,wald

def validate_prediction(df):
    """Reserva UPM completas; ninguna persona de una UPM se reparte entre conjuntos."""
    split=GroupShuffleSplit(n_splits=1,test_size=.2,random_state=2026)
    train_idx,test_idx=next(split.split(df,groups=df.psu))
    train=df.iloc[train_idx].copy();test=df.iloc[test_idx].copy()
    if set(train.psu)&set(test.psu):raise AssertionError('Fuga de UPM')
    rows=[];prediction=None
    for name,formula in {'Media de entrenamiento':None,**FORMULAS}.items():
        if formula is None:
            prediction=np.full(len(test),np.average(train.ingreso_mensual,weights=train.factor))
            predlog=np.full(len(test),np.average(train.log_ingreso,weights=train.factor))
        else:
            m=smf.wls(formula,train,weights=train.peso).fit()
            predlog=m.predict(test).to_numpy()
            smear=np.average(np.exp(m.resid),weights=train.factor)
            prediction=np.exp(predlog)*smear
        w=test.factor.to_numpy();actual=test.ingreso_mensual.to_numpy()
        err=actual-prediction;logerr=test.log_ingreso.to_numpy()-predlog
        r2=1-np.average(err**2,weights=w)/np.average((actual-np.average(actual,weights=w))**2,weights=w)
        rows.append({'modelo':name,'n_entrenamiento':len(train),'n_prueba':len(test),
                     'mae_pesos':np.average(abs(err),weights=w),'rmse_pesos':np.sqrt(np.average(err**2,weights=w)),
                     'r2_prueba_pesos':r2,'rmse_log':np.sqrt(np.average(logerr**2,weights=w))})
    metrics=pd.DataFrame(rows);save_table(metrics,'validacion_upm.csv')
    split_info={'n_train':len(train),'n_test':len(test),'upm_train':train.psu.nunique(),'upm_test':test.psu.nunique(),'upm_compartidas':0,'semilla':2026}
    return metrics,split_info

def diagnostic_analysis(df):
    # Contraste OLS exploratorio separado de la inferencia principal de encuesta.
    m=smf.ols(FORMULAS['Modelo ajustado'],df).fit()
    bp=het_breuschpagan(m.resid,m.model.exog,robust=True)
    jb=jarque_bera(m.resid)
    diagnostics={'breusch_pagan_LM':bp[0],'breusch_pagan_p':bp[1],
                 'jarque_bera':jb[0],'jarque_bera_p':jb[1],
                 'asimetria':jb[2],'curtosis_Pearson':jb[3],
                 'durbin_watson':durbin_watson(m.resid),
                 'alcance':'Diagnósticos clásicos OLS exploratorios; sus p no incorporan el diseño de encuesta. DW no es temporal.'}
    (ROOT/'outputs/diagnosticos.json').write_text(json.dumps(diagnostics,indent=2,ensure_ascii=False),encoding='utf-8')
    (ROOT/'outputs/resumen_OLS_clasico.txt').write_text(m.summary().as_text(),encoding='utf-8')
    # Sensibilidad sin el 1% superior: no se modifica el análisis principal.
    cap=weighted_quantile(df.ingreso_mensual,df.factor,.99)
    subset=df.loc[df.ingreso_mensual.le(cap)].copy()
    trim=smf.wls(FORMULAS['Modelo ajustado'],subset,weights=subset.peso).fit()
    base=smf.wls(FORMULAS['Modelo ajustado'],df,weights=df.peso).fit()
    sensitivity=[]
    for term in base.params.index:
        if term.startswith('C(educacion'):
            sensitivity.append({'termino':term,'pct_completo':100*np.expm1(base.params[term]),
                                'pct_sin_1pct_superior':100*np.expm1(trim.params[term]),'umbral_p99':cap})
    save_table(pd.DataFrame(sensitivity),'sensibilidad_extremos.csv')
    return m,diagnostics

def style():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.titlesize':15,
                         'axes.labelcolor':INK,'text.color':INK,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.grid':True,'grid.alpha':.16,
                         'figure.facecolor':'white','savefig.facecolor':'white'})

def savefig(fig,name):
    FIGURES.mkdir(parents=True,exist_ok=True)
    fig.savefig(FIGURES/f'{name}.png',dpi=190,bbox_inches='tight')
    fig.savefig(FIGURES/f'{name}.svg',bbox_inches='tight')
    plt.close(fig)

def make_figures(df,descriptive,effects,validation,models,ols):
    style()
    fig,axes=plt.subplots(1,2,figsize=(11,4.1))
    w=df.factor/df.factor.sum();cap=weighted_quantile(df.ingreso_mensual,df.factor,.99)
    axes[0].hist(df.ingreso_mensual,bins=np.linspace(0,cap,60),weights=w,color=PURPLE)
    axes[0].set(xlabel='Ingreso mensual (MXN)',ylabel='Proporción ponderada',title='Ingreso en pesos (hasta P99)')
    axes[0].xaxis.set_major_formatter(FuncFormatter(lambda x,_:f'{x/1000:.0f} mil'))
    axes[1].hist(df.log_ingreso,bins=65,weights=w,color=BLUE)
    axes[1].set(xlabel='Logaritmo natural del ingreso',title='Escala utilizada en la regresión')
    fig.tight_layout();savefig(fig,'01_distribucion')
    fig,ax=plt.subplots(figsize=(10,5.5))
    d=descriptive.iloc[::-1];y=np.arange(len(d));mean=d.media_mensual.to_numpy()
    ax.barh(y,mean,color=[PURPLE if x in ['Licenciatura','Posgrado'] else BLUE for x in d.educacion],alpha=.88)
    ax.errorbar(mean,y,xerr=[mean-d.ic95_media_inf,d.ic95_media_sup-mean],fmt='none',ecolor=INK,capsize=4)
    for yi,v,upper in zip(y,mean,d.ic95_media_sup):ax.text(upper+350,yi,f'${v:,.0f}',va='center',fontsize=11)
    ax.set(yticks=y,yticklabels=d.educacion,xlabel='Ingreso mensual promedio (MXN)',title='Figura 1. Ingreso observado por escolaridad')
    ax.set_xlim(0,max(d.ic95_media_sup)*1.19)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x,_:f'{x/1000:.0f} mil'))
    fig.tight_layout();savefig(fig,'02_ingreso_escolaridad')
    e=effects.copy();e['orden']=e.educacion.map({v:i for i,v in enumerate(LEVELS)})
    e=e.sort_values('orden',ascending=False);y=np.arange(len(e))
    fig,ax=plt.subplots(figsize=(10,5.5))
    ax.errorbar(e.diferencia_pct,y,xerr=[e.diferencia_pct-e.pct_inf,e.pct_sup-e.diferencia_pct],fmt='o',color=PURPLE,capsize=4,markersize=7)
    ax.axvline(0,color=INK,lw=1)
    for yi,row in enumerate(e.itertuples()):ax.text(row.pct_sup+3,yi,f'{row.diferencia_pct:+.1f}%',va='center',fontsize=11)
    ax.set(yticks=y,yticklabels=e.educacion,xlabel='Diferencia porcentual ajustada frente a secundaria',title='Figura 2. Asociación al considerar otros factores')
    ax.set_xlim(min(-65,e.pct_inf.min()-12),e.pct_sup.max()+40)
    fig.tight_layout();savefig(fig,'03_efectos_ajustados')
    fig,axes=plt.subplots(1,2,figsize=(11,4.2))
    sample=df.sample(min(7000,len(df)),random_state=2026)
    positions=sample.index.to_numpy()
    fitted=models['Modelo ajustado'].fittedvalues.to_numpy();res=models['Modelo ajustado'].resid.to_numpy()
    axes[0].scatter(fitted[positions],res[positions],s=5,alpha=.15,color=BLUE)
    axes[0].axhline(0,color=PURPLE);axes[0].set(xlabel='Log ingreso ajustado',ylabel='Residuo en log',title='Figura 3a. Residuos del modelo ponderado')
    sm.qqplot(np.asarray(ols.resid),line='s',ax=axes[1],marker='.',markersize=2,alpha=.3)
    axes[1].set(title='Figura 3b. Q-Q de residuos OLS',xlabel='Cuantiles normales',ylabel='Cuantiles observados')
    fig.tight_layout();savefig(fig,'04_diagnosticos')
    fig,ax=plt.subplots(figsize=(10,4.5))
    v=validation.iloc[::-1]
    ax.barh(v.modelo,v.mae_pesos,color=[ORANGE,PURPLE,BLUE,'#8b94a1'])
    for yi,value in enumerate(v.mae_pesos):ax.text(value+80,yi,f'${value:,.0f}',va='center')
    ax.set(xlabel='Error absoluto medio ponderado (MXN)',title='Figura 4. Predicción en UPM reservadas')
    ax.set_xlim(0,v.mae_pesos.max()*1.2);fig.tight_layout();savefig(fig,'05_validacion')
    # Correlaciones descriptivas, sin convertir códigos nominales en cantidades.
    cols=['ingreso_mensual','log_ingreso','edad','htrab']
    save_table(df[cols].corr().reset_index(names='variable'),'correlaciones_no_ponderadas.csv')

def run():
    TABLES.mkdir(parents=True,exist_ok=True);FIGURES.mkdir(parents=True,exist_ok=True)
    pop,jobs,incomes=load_data();df,design,audit=prepare(pop,jobs,incomes)
    print('Muestra analítica:',len(df),flush=True)
    descriptive=descriptive_by_education(df,design);save_table(descriptive,'ingreso_por_escolaridad.csv')
    models,tables,covs,info,wald=fit_models(df,design)
    validation,split=validate_prediction(df)
    ols,diagnostics=diagnostic_analysis(df)
    effects=education_effects(tables['Modelo ajustado'])
    make_figures(df,descriptive,effects,validation,models,ols)
    all_mean=np.average(df.ingreso_mensual,weights=df.factor)
    summary={'pregunta':'¿Estudiar más se relaciona con ganar más en México?',
             'fuente':'ENIGH 2024 Nueva Serie, INEGI', 'n':len(df),'n_poblacion_fuente':len(pop),
             'personas_expandidas_dominio':int(df.factor.sum()),
             'media_mensual_ponderada':all_mean,
             'mediana_mensual_ponderada':weighted_quantile(df.ingreso_mensual,df.factor,.5),
             'r2_log_ajustado':models['Modelo ajustado'].rsquared,
             'diseno':info,'prueba_escolaridad':wald,'validacion':split,
             'efectos_educacion':effects[['educacion','diferencia_pct','pct_inf','pct_sup','p']].to_dict('records'),
             'formulas':FORMULAS,'fecha_elaboracion':'2026-10-25',
             'alcance':'Personas de 25-64 años, integrantes del hogar, con un solo trabajo subordinado remunerado en México e ingreso monetario corriente principal positivo; horas 1-168. P001-P007, ing_tri/3.',
             'escolaridad':'Máximo nivel con grados aprobados; puede estar incompleto. Técnica y normal se agrupan por heterogeneidad de antecedentes. No se infieren años de escolaridad.',
             'inferencia':'Taylor por UPM dentro de estratos, marco completo de Población con scores cero fuera del dominio. Aproximación con reemplazo sin corrección finita.',
             'causalidad':'Asociación condicionada; no identifica el efecto causal de estudiar ni representa a personas sin ingreso o sin empleo.'}
    (ROOT/'outputs/resultados.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    (ROOT/'outputs/entorno.json').write_text(json.dumps({'python':platform.python_version(),**{n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','statsmodels','matplotlib','scikit-learn','nbformat']}},indent=2),encoding='utf-8')
    processed=ROOT/'data/processed';processed.mkdir(exist_ok=True)
    # No exporta folios de personas: solo muestra analítica anonimizada para uso local.
    df.drop(columns=KEY+['sinco','upm','est_dis','psu','estrato']).to_csv(processed/'muestra_analitica.csv',index=False,encoding='utf-8-sig')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    return df,descriptive,models,tables,validation,summary

if __name__=='__main__':run()
