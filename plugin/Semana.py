"""
Plugin QGIS - Análise de Precisão Cartográfica (PEC / PEC-PCD)
v4 — Algoritmo nativo de Processing
  • QgsProcessingParameterVectorLayer para seleção unificada
    (camada do projeto OU arquivo — interface nativa do QGIS)
  • 4 gráficos: Freq+Acumulada, Boxplot, Dispersão, Comparativo
  • Curva de frequência encosta no eixo X
  • PEC + PEC-PCD, estatísticas completas
  • Saída: relatório HTML + camada de erros por ponto
"""

import os
import numpy as np
from datetime import datetime

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterFeatureSink,
    QgsProcessingOutputString,
    QgsFeatureSink,
    QgsFeature,
    QgsFields,
    QgsField,
    QgsWkbTypes,
    QgsProject,
    QgsSpatialIndex,
    QgsFeatureRequest,
    QgsDistanceArea,
)
from qgis.PyQt.QtCore import QVariant, QCoreApplication


# ─────────────────────────────────────────────────────────────
# Tabelas normativas
# ─────────────────────────────────────────────────────────────

LIMITES_PEC = {
    1_000:   (0.17,   0.30,   0.50),
    2_000:   (0.34,   0.60,   1.00),
    5_000:   (0.85,   1.50,   2.50),
    10_000:  (1.70,   3.00,   5.00),
    25_000:  (4.25,   7.50,  12.50),
    50_000:  (8.50,  15.00,  25.00),
    100_000: (17.00, 30.00,  50.00),
    250_000: (42.50, 75.00, 125.00),
}

LIMITES_PEC_PCD = {
    1_000:   (0.28,   0.50,   0.70),
    2_000:   (0.56,   1.00,   1.40),
    5_000:   (1.40,   2.50,   3.50),
    10_000:  (2.80,   5.00,   7.00),
    25_000:  (7.00,  12.50,  17.50),
    50_000:  (14.00, 25.00,  35.00),
    100_000: (28.00, 50.00,  70.00),
    250_000: (70.00, 125.00, 175.00),
}

ESCALAS_PADRAO = sorted(LIMITES_PEC.keys())


# ─────────────────────────────────────────────────────────────
# Algoritmo principal
# ─────────────────────────────────────────────────────────────

class AnalisePEC(QgsProcessingAlgorithm):

    PONTO_REF  = 'ponto_ref'
    PONTO_AVAL = 'ponto_aval'
    GEODESICA  = 'geodesica'
    CALCPCD    = 'calcpcd'
    SAIDA_HTML = 'saida_html'
    SAIDA_ERROS = 'saida_erros'

    # ── Metadados ────────────────────────────────────────────

    def name(self):
        return 'analise_pec'

    def displayName(self):
        return 'Análise de Precisão Cartográfica (PEC / PEC-PCD)'

    def group(self):
        return 'Cartografia'

    def groupId(self):
        return 'cartografia'

    def shortHelpString(self):
        return (
            'Calcula a precisão posicional entre dois conjuntos de pontos '
            'e classifica o produto cartográfico segundo o PEC '
            '(Decreto 89.817/1984) e o PEC-PCD (ET-ADGV/INDE).\n\n'
            'Ponto Ref = camada de referência (verdade de campo)\n'
            'Ponto Aval = camada avaliada (produto cartográfico)\n\n'
            'Saída: relatório HTML + camada vetorial com erro por ponto.'
        )

    def createInstance(self):
        return AnalisePEC()

    def tr(self, text):
        return QCoreApplication.translate('AnalisePEC', text)

    # ── Parâmetros — interface nativa do Processing ──────────

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.PONTO_REF,
                'Ponto de Referência (A)',
                types=[QgsProcessing.TypeVectorPoint],
                defaultValue=None
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.PONTO_AVAL,
                'Ponto Avaliado (B)',
                types=[QgsProcessing.TypeVectorPoint],
                defaultValue=None
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.GEODESICA,
                'Usar distância geodésica (elipsoidal)',
                defaultValue=True
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.CALCPCD,
                'Calcular também PEC-PCD (RMSE)',
                defaultValue=True
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.SAIDA_HTML,
                'Relatório HTML de saída',
                fileFilter='HTML (*.html)',
                optional=True,
                defaultValue=None
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.SAIDA_ERROS,
                'Camada de erros por ponto',
                type=QgsProcessing.TypeVectorPoint,
                optional=True,
                defaultValue=None
            )
        )

    # ── Execução ─────────────────────────────────────────────

    def processAlgorithm(self, parameters, context, feedback):

        layer_a  = self.parameterAsVectorLayer(parameters, self.PONTO_REF,  context)
        layer_b  = self.parameterAsVectorLayer(parameters, self.PONTO_AVAL, context)
        geodesica = self.parameterAsBoolean(parameters,   self.GEODESICA,   context)
        calc_pcd  = self.parameterAsBoolean(parameters,   self.CALCPCD,     context)

        # Validação
        if layer_a is None or not layer_a.isValid():
            raise Exception('Camada de referência inválida.')
        if layer_b is None or not layer_b.isValid():
            raise Exception('Camada avaliada inválida.')
        if layer_a.id() == layer_b.id():
            raise Exception('As duas camadas devem ser diferentes.')

        # Preparar sink de erros
        fields = QgsFields()
        fields.append(QgsField('id',     QVariant.Int))
        fields.append(QgsField('erro_m', QVariant.Double))

        saida_erros_path = self.parameterAsOutputLayer(
            parameters, self.SAIDA_ERROS, context
        )
        sink = None
        sink_id = None
        if saida_erros_path:
            sink, sink_id = self.parameterAsSink(
                parameters, self.SAIDA_ERROS, context,
                fields, QgsWkbTypes.Point, layer_a.crs()
            )

        # Cálculo
        index = QgsSpatialIndex(layer_b.getFeatures())
        area_calc = QgsDistanceArea()
        area_calc.setSourceCrs(layer_a.crs(),
                               QgsProject.instance().transformContext())
        area_calc.setEllipsoid(QgsProject.instance().ellipsoid())

        distancias = []
        coords_a   = []
        coords_b   = []
        total = layer_a.featureCount()

        for i, feat_a in enumerate(layer_a.getFeatures()):
            if feedback.isCanceled():
                break
            feedback.setProgress(int((i / max(total, 1)) * 100))

            geom_a = feat_a.geometry()
            if geom_a is None or geom_a.isEmpty():
                continue

            pt_a    = geom_a.asPoint()
            nearest = index.nearestNeighbor(pt_a, 1)
            if not nearest:
                continue

            feat_b = next(layer_b.getFeatures(
                QgsFeatureRequest().setFilterFid(nearest[0])
            ))
            geom_b = feat_b.geometry()
            pt_b   = geom_b.asPoint()

            dist = area_calc.measureLine(pt_a, pt_b) if geodesica \
                   else geom_a.distance(geom_b)

            distancias.append(dist)
            coords_a.append((pt_a.x(), pt_a.y()))
            coords_b.append((pt_b.x(), pt_b.y()))

            if sink:
                f = QgsFeature(fields)
                f.setGeometry(geom_a)
                f.setAttributes([i + 1, round(dist, 6)])
                sink.addFeature(f, QgsFeatureSink.FastInsert)

        if len(distancias) < 3:
            raise Exception('Pontos insuficientes (mínimo 3).')

        # Estatísticas
        r = calcular_estatisticas(distancias, coords_a, coords_b)

        # Log no Processing
        feedback.pushInfo('=' * 56)
        feedback.pushInfo('RELATÓRIO PEC / PEC-PCD')
        feedback.pushInfo('=' * 56)
        feedback.pushInfo(f"Total de pontos : {r['n']}")
        feedback.pushInfo(f"RMSE            : {r['rmse']:.4f} m")
        feedback.pushInfo(f"Percentil 90%   : {r['e90']:.4f} m")
        feedback.pushInfo(f"Escala          : 1:{r['escala_aj']:,}")
        feedback.pushInfo(f"Classificação PEC     : {r['classe_pec']}")
        feedback.pushInfo(f"Classificação PEC-PCD : {r['classe_pcd']}")
        feedback.pushInfo('=' * 56)

        # Relatório HTML
        html_path = self.parameterAsFileOutput(
            parameters, self.SAIDA_HTML, context
        )
        if html_path:
            _gerar_html(r, html_path, calc_pcd)
            feedback.pushInfo(f'Relatório salvo em: {html_path}')

        # Gráficos inline no Processing (matplotlib)
        try:
            _gerar_graficos(r, feedback)
        except Exception as e:
            feedback.pushWarning(f'Gráficos não gerados: {e}')

        resultado = {
            'classe_pec':  r['classe_pec'],
            'classe_pcd':  r['classe_pcd'],
            'escala':      f"1:{r['escala_aj']:,}",
            'rmse':        round(r['rmse'],  4),
            'percentil90': round(r['e90'],   4),
        }
        if sink_id:
            resultado[self.SAIDA_ERROS] = sink_id
        if html_path:
            resultado[self.SAIDA_HTML] = html_path

        return resultado


# ─────────────────────────────────────────────────────────────
# Estatísticas
# ─────────────────────────────────────────────────────────────

def calcular_estatisticas(distancias, coords_a, coords_b):
    dados = np.array(distancias)
    n     = len(dados)

    media   = float(np.mean(dados))
    mediana = float(np.median(dados))
    desvio  = float(np.std(dados, ddof=1))
    minimo  = float(np.min(dados))
    maximo  = float(np.max(dados))
    rmse    = float(np.sqrt(np.mean(dados ** 2)))
    e90     = float(np.percentile(dados, 90))
    e95     = float(np.percentile(dados, 95))

    escala_calc     = e90 / 0.17
    escalas_maiores = [e for e in ESCALAS_PADRAO if e >= escala_calc]
    escala_aj       = min(escalas_maiores) if escalas_maiores else ESCALAS_PADRAO[-1]

    lp   = LIMITES_PEC[escala_aj]
    lpcd = LIMITES_PEC_PCD[escala_aj]

    if   e90 <= lp[0]: classe_pec = 'Classe A'
    elif e90 <= lp[1]: classe_pec = 'Classe B'
    elif e90 <= lp[2]: classe_pec = 'Classe C'
    else:              classe_pec = 'Não enquadrado'

    if   rmse <= lpcd[0]: classe_pcd = 'Classe A'
    elif rmse <= lpcd[1]: classe_pcd = 'Classe B'
    elif rmse <= lpcd[2]: classe_pcd = 'Classe C'
    else:                 classe_pcd = 'Não enquadrado'

    bins_n = min(20, max(5, n // 5))
    count, bin_edges = np.histogram(dados, bins=bins_n)
    freq_pct   = (count / count.sum()) * 100
    acum_pct   = np.cumsum(freq_pct)
    bin_center = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    bin_ext    = np.concatenate([[bin_edges[0]],  bin_center, [bin_edges[-1]]])
    freq_ext   = np.concatenate([[0], freq_pct, [0]])

    return dict(
        erros=dados, coords_a=coords_a, coords_b=coords_b,
        n=n, media=media, mediana=mediana, desvio=desvio,
        minimo=minimo, maximo=maximo, rmse=rmse, e90=e90, e95=e95,
        escala_calc=escala_calc, escala_aj=escala_aj,
        classe_pec=classe_pec, classe_pcd=classe_pcd,
        lim_pec=lp, lim_pcd=lpcd,
        bin_center=bin_center, bin_ext=bin_ext,
        freq_ext=freq_ext, freq_pct=freq_pct, acum_pct=acum_pct,
        bin_edges=bin_edges,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    )


# ─────────────────────────────────────────────────────────────
# Gráficos (exibidos no painel de resultados do Processing)
# ─────────────────────────────────────────────────────────────

def _gerar_graficos(r, feedback):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    import tempfile, os

    fig = plt.figure(figsize=(14, 9))
    gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    CB = '#4A90D9'; CO = '#E07B39'; CG = '#27AE60'; CP = '#8E44AD'

    # 1) Freq + Acumulada
    ax1.fill_between(r['bin_ext'], r['freq_ext'], alpha=0.22, color=CB)
    ax1.plot(r['bin_ext'], r['freq_ext'], color=CB, linewidth=1.8,
             label='Frequência (%)')
    ax1r = ax1.twinx()
    ax1r.plot(r['bin_center'], r['acum_pct'], color=CO, linewidth=2.0,
              label='Freq. acumulada (%)')
    ax1r.set_ylim(0, 108)
    ax1r.set_ylabel('Freq. acumulada (%)', fontsize=8)
    ax1r.tick_params(labelsize=7)
    ax1.axvline(r['e90'], color=CG, linestyle='--', linewidth=1.4,
                label=f"Erro 90% = {r['e90']:.3f} m")
    ax1.set_xlabel('Erro (m)', fontsize=8)
    ax1.set_ylabel('Frequência (%)', fontsize=8)
    ax1.set_title('Distribuição de Frequência - PEC', fontsize=9)
    ax1.tick_params(labelsize=7)
    ax1.grid(True, linestyle=':', alpha=0.4)
    l1, lb1 = ax1.get_legend_handles_labels()
    l2, lb2 = ax1r.get_legend_handles_labels()
    ax1.legend(l1+l2, lb1+lb2, fontsize=7)

    # 2) Boxplot
    ax2.boxplot(r['erros'], vert=True, patch_artist=True,
                boxprops=dict(facecolor='#B3D4F5', color='#2C6BAA'),
                medianprops=dict(color=CO, linewidth=2),
                whiskerprops=dict(color='#2C6BAA'),
                capprops=dict(color='#2C6BAA'),
                flierprops=dict(marker='o', color=CO, alpha=0.5, markersize=3))
    ax2.axhline(r['e90'],  color=CG, linestyle='--', linewidth=1.2,
                label=f"P90 = {r['e90']:.3f} m")
    ax2.axhline(r['rmse'], color=CP, linestyle=':',  linewidth=1.2,
                label=f"RMSE = {r['rmse']:.3f} m")
    ax2.set_ylabel('Discrepância (m)', fontsize=8)
    ax2.set_title('Boxplot das Discrepâncias', fontsize=9)
    ax2.set_xticks([])
    ax2.legend(fontsize=7)
    ax2.tick_params(labelsize=7)
    ax2.grid(True, axis='y', linestyle=':', alpha=0.4)

    # 3) Dispersão
    if r['coords_a'] and r['coords_b']:
        xa = [c[0] for c in r['coords_a']]; ya = [c[1] for c in r['coords_a']]
        xb = [c[0] for c in r['coords_b']]; yb = [c[1] for c in r['coords_b']]
        for ax_, bx_, ay_, by_ in zip(xa, xb, ya, yb):
            ax3.plot([ax_, bx_], [ay_, by_], color='gray',
                     linewidth=0.5, alpha=0.35, zorder=1)
        ax3.scatter(xa, ya, s=18, color=CB, alpha=0.75,
                    label='Referência (A)', zorder=3)
        ax3.scatter(xb, yb, s=18, color=CO, alpha=0.75,
                    label='Avaliada (B)',   zorder=3)
        ax3.set_xlabel('X (m)', fontsize=8)
        ax3.set_ylabel('Y (m)', fontsize=8)
        ax3.set_title('Dispersão dos Pontos', fontsize=9)
        ax3.legend(fontsize=7)
        ax3.tick_params(labelsize=7)
        ax3.ticklabel_format(style='sci', axis='both',
                             scilimits=(0, 0), useOffset=True)
        ax3.grid(True, linestyle=':', alpha=0.4)

    # 4) Comparativo
    cats  = ['A\n(PEC)','B\n(PEC)','C\n(PEC)','A\n(PCD)','B\n(PCD)','C\n(PCD)']
    lims  = list(r['lim_pec']) + list(r['lim_pcd'])
    vals  = [r['e90']]*3 + [r['rmse']]*3
    cores = ['#2ECC71','#F39C12','#E74C3C']*2
    x     = np.arange(len(cats)); w = 0.35
    ax4.bar(x-w/2, lims, w, color=cores, alpha=0.55, label='Limite')
    ax4.bar(x+w/2, vals, w, color=CB,    alpha=0.85, label='Obtido')
    ax4.set_xticks(x); ax4.set_xticklabels(cats, fontsize=7)
    ax4.set_ylabel('Erro (m)', fontsize=8)
    ax4.set_title('Comparativo PEC / PEC-PCD', fontsize=9)
    ax4.legend(fontsize=7); ax4.tick_params(labelsize=7)
    ax4.grid(True, axis='y', linestyle=':', alpha=0.4)

    fig.suptitle(
        f"PEC — 1:{r['escala_aj']:,}  |  "
        f"PEC: {r['classe_pec']}  |  PEC-PCD: {r['classe_pcd']}",
        fontsize=11, fontweight='bold'
    )

    tmp = os.path.join(tempfile.gettempdir(), 'pec_graficos.png')
    fig.savefig(tmp, dpi=120, bbox_inches='tight')
    plt.close(fig)
    feedback.pushInfo(f'Gráficos salvos em: {tmp}')


# ─────────────────────────────────────────────────────────────
# Relatório HTML
# ─────────────────────────────────────────────────────────────

def _gerar_html(r, path, calc_pcd):
    def cls_cor(cls):
        return {'Classe A': '#27AE60', 'Classe B': '#F39C12',
                'Classe C': '#E67E22'}.get(cls, '#E74C3C')

    pcd_bloco = ''
    if calc_pcd:
        pcd_bloco = f"""
        <h2>PEC-PCD (ET-ADGV / INDE) — escala 1:{r['escala_aj']:,}</h2>
        <table>
          <tr><th>Classe</th><th>Limite RMSE (m)</th><th>RMSE obtido (m)</th></tr>
          <tr><td>A</td><td>{r['lim_pcd'][0]:.4f}</td>
              <td rowspan="3" style="color:{cls_cor(r['classe_pcd'])};font-size:1.3em;font-weight:bold">
              {r['rmse']:.4f}<br><small>{r['classe_pcd']}</small></td></tr>
          <tr><td>B</td><td>{r['lim_pcd'][1]:.4f}</td></tr>
          <tr><td>C</td><td>{r['lim_pcd'][2]:.4f}</td></tr>
        </table>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<title>Relatório PEC</title>
<style>
  body{{font-family:Arial,sans-serif;max-width:860px;margin:2rem auto;color:#222}}
  h1{{background:#2C3E50;color:#fff;padding:1rem;border-radius:4px}}
  h2{{border-left:4px solid #4A90D9;padding-left:.6rem;margin-top:1.5rem}}
  table{{border-collapse:collapse;width:100%;margin:.5rem 0}}
  th,td{{border:1px solid #ccc;padding:.4rem .7rem;text-align:center}}
  th{{background:#f0f0f0}}
  .stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem;margin:.5rem 0}}
  .card{{background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;
         padding:.6rem;text-align:center}}
  .card .val{{font-size:1.3em;font-weight:bold;color:#2C3E50}}
  .card .lbl{{font-size:.78em;color:#666}}
  footer{{margin-top:2rem;font-size:.8em;color:#999;text-align:center}}
</style></head><body>
<h1>Relatório de Precisão Cartográfica — PEC / PEC-PCD</h1>
<p>Gerado em: <strong>{r['timestamp']}</strong></p>

<h2>Estatísticas das Discrepâncias</h2>
<div class="stats">
  <div class="card"><div class="val">{r['n']}</div><div class="lbl">Pontos</div></div>
  <div class="card"><div class="val">{r['minimo']:.4f} m</div><div class="lbl">Mínimo</div></div>
  <div class="card"><div class="val">{r['maximo']:.4f} m</div><div class="lbl">Máximo</div></div>
  <div class="card"><div class="val">{r['media']:.4f} m</div><div class="lbl">Média</div></div>
  <div class="card"><div class="val">{r['desvio']:.4f} m</div><div class="lbl">Desvio padrão</div></div>
  <div class="card"><div class="val">{r['rmse']:.4f} m</div><div class="lbl">RMSE</div></div>
  <div class="card"><div class="val">{r['e90']:.4f} m</div><div class="lbl">Percentil 90%</div></div>
  <div class="card"><div class="val">{r['e95']:.4f} m</div><div class="lbl">Percentil 95%</div></div>
  <div class="card"><div class="val">1:{r['escala_aj']:,}</div><div class="lbl">Escala padronizada</div></div>
</div>

<h2>PEC (Decreto 89.817/1984) — escala 1:{r['escala_aj']:,}</h2>
<table>
  <tr><th>Classe</th><th>Limite P90 (m)</th><th>P90 obtido (m)</th></tr>
  <tr><td>A</td><td>{r['lim_pec'][0]:.4f}</td>
      <td rowspan="3" style="color:{cls_cor(r['classe_pec'])};font-size:1.3em;font-weight:bold">
      {r['e90']:.4f}<br><small>{r['classe_pec']}</small></td></tr>
  <tr><td>B</td><td>{r['lim_pec'][1]:.4f}</td></tr>
  <tr><td>C</td><td>{r['lim_pec'][2]:.4f}</td></tr>
</table>

{pcd_bloco}
<footer>Análise de Precisão Cartográfica — QGIS Processing</footer>
</body></html>"""

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)


# ─────────────────────────────────────────────────────────────
# Registro do algoritmo no Processing
# ─────────────────────────────────────────────────────────────

from qgis.core import QgsApplication

reg = QgsApplication.processingRegistry()

# Remove versão anterior se já registrada
for alg in reg.algorithms():
    if alg.id() == 'cartografia:analise_pec':
        try:
            from processing.core.Processing import Processing
            Processing.removeProvider(alg.provider())
        except Exception:
            pass
        break

from processing.core.ProcessingConfig import ProcessingConfig
from qgis.core import QgsProcessingProvider

class PecProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(AnalisePEC())
    def id(self):
        return 'pec_tools'
    def name(self):
        return 'Ferramentas PEC'
    def longName(self):
        return self.name()

_provider = PecProvider()
QgsApplication.processingRegistry().addProvider(_provider)

# Abre a caixa de diálogo nativa do Processing para o algoritmo
import processing
processing.execAlgorithmDialog('pec_tools:analise_pec')
