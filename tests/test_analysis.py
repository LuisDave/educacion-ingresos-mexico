"""Comprobaciones del cálculo de encuesta y de la integridad del análisis."""
import unittest,json
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from src.analysis import meat_by_design,survey_covariance,coef_table,ROOT

class SurveyChecks(unittest.TestCase):
    def test_stratified_variance_and_zero_domain_psu(self):
        design=pd.DataFrame({'estrato':['a','a','b','b'],'psu':['1','2','3','4']})
        # UPM 4 no tiene miembros del dominio: se debe conservar con score cero.
        scores=pd.DataFrame({'estrato':['a','a','b'],'psu':['1','2','3'],'s':[1.,3.,2.]})
        result,info=meat_by_design(scores,design)
        # Estrato a: 2*((1-2)^2+(3-2)^2)=4; estrato b: 2*((2-1)^2+(0-1)^2)=4.
        np.testing.assert_allclose(result,[[8.]])
        self.assertEqual(info['gl_diseno'],2)

    def test_weight_scaling_does_not_change_estimates_or_variance(self):
        x=sm.add_constant(np.array([0.,1.,2.,3.,4.,5.]))
        y=np.array([2.,4.,3.,7.,6.,10.]);w=np.array([1.,2.,1.,3.,2.,1.])
        df=pd.DataFrame({'peso':w,'estrato':['a']*6,'psu':list('123456')})
        design=df[['estrato','psu']]
        one=sm.WLS(y,x,weights=w).fit();c1,_=survey_covariance(one,df,design)
        two=sm.WLS(y,x,weights=w*37).fit()
        df2=df.copy();df2.peso*=37;c2,_=survey_covariance(two,df2,design)
        np.testing.assert_allclose(one.params,two.params,rtol=1e-10,atol=1e-10)
        np.testing.assert_allclose(c1,c2,rtol=1e-10,atol=1e-10)
        # Contraste independiente de la solución mediante mínimos cuadrados blanqueados.
        reference=np.linalg.lstsq(x*np.sqrt(w)[:,None],y*np.sqrt(w),rcond=None)[0]
        np.testing.assert_allclose(one.params,reference,atol=1e-10)

    def test_outputs_have_consistent_counts_and_intervals(self):
        s=json.loads((ROOT/'outputs/resultados.json').read_text(encoding='utf-8'))
        d=pd.read_csv(ROOT/'outputs/tables/ingreso_por_escolaridad.csv')
        self.assertEqual(d.n.sum(),s['n'])
        self.assertEqual(s['validacion']['n_train']+s['validacion']['n_test'],s['n'])
        self.assertEqual(s['validacion']['upm_compartidas'],0)
        for e in s['efectos_educacion']:
            self.assertLess(e['pct_inf'],e['diferencia_pct'])
            self.assertGreater(e['pct_sup'],e['diferencia_pct'])
        c=pd.read_csv(ROOT/'outputs/tables/coef_ajustado.csv')
        np.testing.assert_allclose(c.coef/c.error_estandar,c.t,rtol=1e-8)

if __name__=='__main__':unittest.main()
