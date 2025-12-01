# ======== codigo 100% ===========
# ================================
# Código Ajustado para QGIS 3.40
# Pronto para rodar no Console Python
# Digite: run()
# ================================

import sys
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QTabWidget, QWidget, QHBoxLayout
)


# ===================== JANELA PRINCIPAL =====================

class ErroPlotDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Análise de Erro - Carregar Shapefile")

        layout_principal = QVBoxLayout()

        # --- Campo para selecionar SHP ---
        self.label_shp = QLabel("Selecione o arquivo SHP contendo os pontos:")
        layout_principal.addWidget(self.label_shp)

        self.campo_shp = QLineEdit()
        layout_principal.addWidget(self.campo_shp)

        self.botao_procurar = QPushButton("Procurar Shapefile...")
        self.botao_procurar.clicked.connect(self.selecionar_shapefile)
        layout_principal.addWidget(self.botao_procurar)

        # --- Aba Final para Aceitar / Cancelar ---
        self.tabs = QTabWidget()
        layout_principal.addWidget(self.tabs)

        aba_final = QWidget()
        layout_botoes = QHBoxLayout()

        self.botao_aceitar = QPushButton("Aceitar")
        self.botao_aceitar.clicked.connect(self.processar_dados)
        layout_botoes.addWidget(self.botao_aceitar)

        self.botao_cancelar = QPushButton("Cancelar")
        self.botao_cancelar.clicked.connect(self.close)
        layout_botoes.addWidget(self.botao_cancelar)

        aba_final.setLayout(layout_botoes)
        self.tabs.addTab(aba_final, "Finalizar")

        self.setLayout(layout_principal)

    # ===================== Selecionar SHP =====================

    def selecionar_shapefile(self):
        arquivo, _ = QFileDialog.getOpenFileName(self, "Selecionar SHP", "", "Shapefile (*.shp)")
        if arquivo:
            self.campo_shp.setText(arquivo)

    # ===================== Processar Dados =====================

    def processar_dados(self):
        caminho = self.campo_shp.text()

        df_init = gpd.read_file(caminho)

        # Calcula os erros
        df_init['erro_X'] = df_init['IPHONE_X'] - df_init['GEO_X']
        df_init['erro_Y'] = df_init['IPHONE_Y'] - df_init['GEO_Y']
        df_init['erro_lin'] = np.sqrt(df_init['erro_X']**2 + df_init['erro_Y']**2)

        # Inicia figura
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.set_aspect('equal')

        # Círculo = erro médio
        mean_erro_lin = df_init['erro_lin'].mean()
        circle = plt.Circle((0, 0), mean_erro_lin, fill=False, edgecolor='gray', linestyle='dashed')
        ax.add_patch(circle)

        # Plot dos pontos
        plt.scatter(0, 0, s=500, color='black', marker='+')
        plt.scatter(df_init['erro_X'], df_init['erro_Y'], s=10)

        # Médias
        mean_erro_X = df_init['erro_X'].mean()
        mean_erro_Y = df_init['erro_Y'].mean()

        escala = XY_max_error * 0.03  # 3% da escala total

ax.arrow(0, 0, mean_erro_X, 0,
         head_width=escala, head_length=escala,
         fc='red', ec='red', length_includes_head=True)

ax.arrow(0, 0, 0, mean_erro_Y,
         head_width=escala, head_length=escala,
         fc='blue', ec='blue', length_includes_head=True)

ax.arrow(0, 0, mean_erro_X, mean_erro_Y,
         head_width=escala, head_length=escala,
         fc='green', ec='green', length_includes_head=True)

        # Definir limites
        XY_max_error = df_init[['erro_X', 'erro_Y']].abs().values.max()
        lim = XY_max_error * 1.1
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)

        ax.grid(True, linestyle='--', alpha=0.5)
        ax.set_xlabel("Erro em X (m)")
        ax.set_ylabel("Erro em Y (m)")
        plt.title("Dispersão dos Erros")

        plt.show()


# ===================== Função para rodar no QGIS =====================

def run():
    global janela
    janela = ErroPlotDialog()
    janela.show()
    return janela
