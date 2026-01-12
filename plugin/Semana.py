# ================================
# Código FINAL - QGIS 3.40
# Gera gráfico + tabela + salva em PNG e PDF
# ================================

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QTabWidget, QWidget, QHBoxLayout
)

print("\n===== SCRIPT GNSS - CARREGANDO =====")

# ===================== JANELA PRINCIPAL =====================

class ErroPlotDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Análise de Erro - Carregar Shapefile")

        layout_principal = QVBoxLayout()

        self.label_shp = QLabel("Selecione o arquivo SHP contendo os pontos:")
        layout_principal.addWidget(self.label_shp)

        self.campo_shp = QLineEdit()
        layout_principal.addWidget(self.campo_shp)

        self.botao_procurar = QPushButton("Procurar Shapefile...")
        self.botao_procurar.clicked.connect(self.selecionar_shapefile)
        layout_principal.addWidget(self.botao_procurar)

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

    def selecionar_shapefile(self):
        arquivo, _ = QFileDialog.getOpenFileName(self, "Selecionar SHP", "", "Shapefile (*.shp)")
        if arquivo:
            self.campo_shp.setText(arquivo)

    def processar_dados(self):
        caminho = self.campo_shp.text()

        if caminho == "":
            print("❌ Selecione um shapefile primeiro!")
            return

        pasta = os.path.dirname(caminho)
        caminho_png = os.path.join(pasta, "grafico_erros.png")
        caminho_pdf = os.path.join(pasta, "grafico_erros.pdf")

        print(">>> Lendo SHP:", caminho)
        df_init = gpd.read_file(caminho)

        colunas = df_init.columns
        if not all(col in colunas for col in ["IPHONE_X", "GEO_X", "IPHONE_Y", "GEO_Y"]):
            print("❌ ERRO: O shapefile precisa ter as colunas: IPHONE_X, GEO_X, IPHONE_Y, GEO_Y")
            print("Colunas encontradas:", list(colunas))
            return

        df_init['erro_X'] = df_init['IPHONE_X'] - df_init['GEO_X']
        df_init['erro_Y'] = df_init['IPHONE_Y'] - df_init['GEO_Y']
        df_init['erro_lin'] = np.sqrt(df_init['erro_X']**2 + df_init['erro_Y']**2)

        mean_erro_X = df_init['erro_X'].mean()
        mean_erro_Y = df_init['erro_Y'].mean()
        mean_erro_lin = df_init['erro_lin'].mean()

        XY_max_error = df_init[['erro_X', 'erro_Y']].abs().max().max()
        lim = XY_max_error * 1.2

        print("\n==== RESULTADOS ====")
        print(f"Erro médio em X: {mean_erro_X:.3f} m")
        print(f"Erro médio em Y: {mean_erro_Y:.3f} m")
        print(f"Erro médio linear: {mean_erro_lin:.3f} m")

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.set_aspect('equal')

        circle = plt.Circle((0, 0), mean_erro_lin,
                            fill=False, edgecolor='gray',
                            linestyle='dashed', linewidth=2)
        ax.add_patch(circle)

        ax.scatter(0, 0, s=200, color='black', marker='+', label='Referência (0,0)')
        ax.scatter(df_init['erro_X'], df_init['erro_Y'], s=15, alpha=0.6, label='Erros')

        ax.quiver(0, 0, mean_erro_X, 0, color='red', scale_units='xy', scale=1)
        ax.quiver(0, 0, 0, mean_erro_Y, color='blue', scale_units='xy', scale=1)
        ax.quiver(0, 0, mean_erro_X, mean_erro_Y, color='green', scale_units='xy', scale=1)

        texto = (
            f"Média X = {mean_erro_X:.3f} m\n"
            f"Média Y = {mean_erro_Y:.3f} m\n"
            f"Erro médio = {mean_erro_lin:.3f} m"
        )

        ax.text(0.02, 0.98, texto, transform=ax.transAxes,
                verticalalignment='top',
                bbox=dict(facecolor='white', alpha=0.85))

        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.set_xlabel("Erro em X (m)")
        ax.set_ylabel("Erro em Y (m)")
        ax.set_title("Dispersão dos Erros GNSS")
        ax.legend()

        plt.savefig(caminho_png, dpi=300, bbox_inches='tight')
        plt.savefig(caminho_pdf, bbox_inches='tight')

        print("\n✅ Gráfico salvo:")
        print("PNG:", caminho_png)
        print("PDF:", caminho_pdf)

        plt.show()


# ===================== Função RUN =====================

def run():
    global janela
    janela = ErroPlotDialog()
    janela.show()
    print(">>> JANELA ABERTA COM SUCESSO")
    return janela


print(">>> Função run registrada:", "run" in globals())
