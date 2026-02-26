import os
import numpy as np

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton,
    QLabel, QComboBox, QLineEdit, QPushButton, QFileDialog,
    QMessageBox, QTextEdit, QWidget, QTabWidget
)

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsMapLayerType,
    QgsSpatialIndex, QgsFeatureRequest
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class TwoShapefilesDialog(QDialog):

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.setWindowTitle("Análise de Precisão Cartográfica - PEC")
        self.setMinimumWidth(900)
        self.setMinimumHeight(650)

        self.layer_a = None
        self.layer_b = None

        self._build_ui()
        self._wire_events()
        self.refresh_layers()

    # Interface

    def _build_ui(self):

        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Aba Seleção
        self.tab_select = QWidget()
        layout1 = QVBoxLayout(self.tab_select)

        gb_mode = QGroupBox("Fonte dos Dados")
        mode_layout = QHBoxLayout(gb_mode)

        self.rb_project = QRadioButton("Utilizar camadas do projeto")
        self.rb_files = QRadioButton("Selecionar arquivos Shapefile (.shp)")
        self.rb_project.setChecked(True)

        mode_layout.addWidget(self.rb_project)
        mode_layout.addWidget(self.rb_files)
        layout1.addWidget(gb_mode)

        self.gb_project = QGroupBox("Camadas do Projeto")
        gp_layout = QVBoxLayout(self.gb_project)

        row_a = QHBoxLayout()
        row_a.addWidget(QLabel("Camada A:"))
        self.cmb_a = QComboBox()
        row_a.addWidget(self.cmb_a)

        row_b = QHBoxLayout()
        row_b.addWidget(QLabel("Camada B:"))
        self.cmb_b = QComboBox()
        row_b.addWidget(self.cmb_b)

        gp_layout.addLayout(row_a)
        gp_layout.addLayout(row_b)
        layout1.addWidget(self.gb_project)

        self.gb_files = QGroupBox("Arquivos Shapefile")
        gf_layout = QVBoxLayout(self.gb_files)

        file_a = QHBoxLayout()
        file_a.addWidget(QLabel("Shapefile A:"))
        self.txt_a = QLineEdit()
        self.btn_browse_a = QPushButton("Selecionar")
        file_a.addWidget(self.txt_a)
        file_a.addWidget(self.btn_browse_a)

        file_b = QHBoxLayout()
        file_b.addWidget(QLabel("Shapefile B:"))
        self.txt_b = QLineEdit()
        self.btn_browse_b = QPushButton("Selecionar")
        file_b.addWidget(self.txt_b)
        file_b.addWidget(self.btn_browse_b)

        gf_layout.addLayout(file_a)
        gf_layout.addLayout(file_b)
        layout1.addWidget(self.gb_files)

        self.btn_execute = QPushButton("Executar Análise")
        layout1.addWidget(self.btn_execute)

        self.tabs.addTab(self.tab_select, "Seleção")

        # Aba Relatório
        self.tab_report = QWidget()
        layout2 = QVBoxLayout(self.tab_report)

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        layout2.addWidget(self.report_text)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout2.addWidget(self.canvas)

        self.tabs.addTab(self.tab_report, "Relatório e Gráficos")

        self._toggle_mode_ui()

    # Eventos

    def _wire_events(self):
        self.rb_project.toggled.connect(self._toggle_mode_ui)
        self.rb_files.toggled.connect(self._toggle_mode_ui)
        self.btn_browse_a.clicked.connect(lambda: self._browse(self.txt_a))
        self.btn_browse_b.clicked.connect(lambda: self._browse(self.txt_b))
        self.btn_execute.clicked.connect(self._executar)

    # Funções auxiliares

    def refresh_layers(self):
        self.cmb_a.clear()
        self.cmb_b.clear()

        layers = [
            lyr for lyr in QgsProject.instance().mapLayers().values()
            if lyr.type() == QgsMapLayerType.VectorLayer
        ]

        for lyr in layers:
            self.cmb_a.addItem(lyr.name(), lyr.id())
            self.cmb_b.addItem(lyr.name(), lyr.id())

    def _toggle_mode_ui(self):
        use_project = self.rb_project.isChecked()
        self.gb_project.setEnabled(use_project)
        self.gb_files.setEnabled(not use_project)

    def _browse(self, target):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Shapefile", "", "Shapefile (*.shp)"
        )
        if path:
            target.setText(path)

    # Execução principal

    def _executar(self):
        try:
            if self.rb_project.isChecked():
                self.layer_a, self.layer_b = self._get_layers_from_project()
            else:
                self.layer_a, self.layer_b = self._get_layers_from_files()

            resultados = self.calcular(self.layer_a, self.layer_b)
            self.mostrar_relatorio(resultados)
            self.gerar_grafico(resultados)

            self.tabs.setCurrentIndex(1)

        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

    # Cálculo PEC

    def calcular(self, layer_a, layer_b):

        index = QgsSpatialIndex(layer_b.getFeatures())
        distancias = []

        for feat_a in layer_a.getFeatures():

            geom_a = feat_a.geometry()
            if geom_a is None or geom_a.isEmpty():
                continue

            nearest_ids = index.nearestNeighbor(geom_a.asPoint(), 1)
            if not nearest_ids:
                continue

            request = QgsFeatureRequest().setFilterFid(nearest_ids[0])
            feat_b = next(layer_b.getFeatures(request))

            dist = geom_a.distance(feat_b.geometry())
            distancias.append(dist)

        if len(distancias) == 0:
            raise Exception("Nenhuma distância calculada.")

        dados = np.array(distancias)

        erro_90 = np.percentile(dados, 90)
        escala_calc = erro_90 / 0.17

        escalas_padrao = [1000, 2000, 5000, 10000, 25000, 50000, 100000]
        escala_ajustada = min([e for e in escalas_padrao if e >= escala_calc])

        if erro_90 <= 0.17 * escala_ajustada:
            classe = "Classe A"
        elif erro_90 <= 0.30 * escala_ajustada:
            classe = "Classe B"
        else:
            classe = "Classe C ou inferior"

        bins = 10
        count, bins_values = np.histogram(dados, bins=bins)
        percent = (count / sum(count)) * 100
        bins_center = 0.5 * (bins_values[:-1] + bins_values[1:])
        freq_acum = np.cumsum(percent)

        return {
            "erros": dados,
            "erro_90": erro_90,
            "escala_calc": escala_calc,
            "escala_ajustada": escala_ajustada,
            "classe": classe,
            "bins_center": bins_center,
            "freq": percent,
            "freq_acum": freq_acum
        }

    # Relatório

    def mostrar_relatorio(self, resultados):

        texto = (
            "RELATÓRIO PEC\n\n"
            f"Total de pontos analisados: {len(resultados['erros'])}\n\n"
            f"Erro 90%: {resultados['erro_90']:.4f} m\n"
            f"Escala calculada: 1:{resultados['escala_calc']:.0f}\n"
            f"Escala ajustada: 1:{resultados['escala_ajustada']}\n\n"
            f"Classificação PEC: {resultados['classe']}\n"
        )

        self.report_text.setText(texto)

    # Gráfico

    def gerar_grafico(self, resultados):

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        ax.plot(resultados["bins_center"],
                resultados["freq"],
                label="Frequência (%)")

        ax.plot(resultados["bins_center"],
                resultados["freq_acum"],
                label="Frequência acumulada (%)")

        ax.axvline(resultados["erro_90"],
                   linestyle='--',
                   label="Erro 90%")

        ax.set_xlabel("Erro (m)")
        ax.set_ylabel("Frequência (%)")
        ax.set_title("Distribuição de Frequência - PEC")
        ax.grid(True, linestyle=":")
        ax.legend()

        self.canvas.draw()

    # Obtenção das camadas

    def _get_layers_from_project(self):
        id_a = self.cmb_a.currentData()
        id_b = self.cmb_b.currentData()

        if id_a == id_b:
            raise Exception("As camadas devem ser diferentes.")

        return (QgsProject.instance().mapLayer(id_a),
                QgsProject.instance().mapLayer(id_b))

    def _get_layers_from_files(self):
        lyr_a = QgsVectorLayer(self.txt_a.text(), "Camada_A", "ogr")
        lyr_b = QgsVectorLayer(self.txt_b.text(), "Camada_B", "ogr")

        QgsProject.instance().addMapLayer(lyr_a)
        QgsProject.instance().addMapLayer(lyr_b)

        return lyr_a, lyr_b


dlg = TwoShapefilesDialog(iface)
dlg.exec_()
