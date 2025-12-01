# ================================
# Código FINAL - QGIS 3.40
# Gera gráfico + tabela + salva em PNG e PDF
# Digite: run()
# ================================

import os
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

        if caminho == "":
            print("Selecione um shapefile primeiro!")
            return

        # Pasta para salvar
        pasta = os.path.dirname(caminho)
        caminho_png = os.path.join(pasta, "grafico_erros.png")
        caminho_pdf = os.path.join(pasta, "grafico_erros.pdf")

        df_init = gpd.read_file(caminho)

        # Confere colunas
        colunas = df_init.columns
        if not all(col in colunas for col in ["IPHONE_X", "GEO_X", "IPHONE_Y", "GEO_Y"]):
            print("ERRO: O shapefile precisa ter as colunas: IPHONE_X, GEO_X, IPHONE_Y, GEO_Y")
            print("Colunas encontradas:", list(colunas))
            return

        # Calcula os erros
        df_init['erro_X'] = df_init['IPHONE_X'] - df_init['GEO_X']
        df_init['erro_Y'] = df_init['IPHONE_Y'] - df_init['GEO_Y']
        df_init['erro_lin'] = np.sqrt(df_init['erro_X']**2 + df_init['erro_Y']**2)

        # Valores médios
        mean_erro_X = df_init['erro_X'].mean()
        mean_erro_Y = df_init['erro_Y'].mean()
        mean_erro_lin = df_init['erro_lin'].mean()

        # Maior erro absoluto
        XY_max_error = df_init[['erro_X', 'erro_Y']].abs().max().max()
        lim = XY_max_error * 1.2

        print("\n==== RESULTADOS ====")
        print(f"Erro médio em X: {mean_erro_X:.3f} m")
        print(f"Erro médio em Y: {mean_erro_Y:.3f} m")
        print(f"Erro médio linear: {mean_erro_lin:.3f} m")

        # ======================= GRÁFICO =======================

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.set_aspect('equal')

        # Círculo do erro médio
        circle = plt.Circle((0, 0), mean_erro_lin,
                            fill=False,
                            edgecolor='gray',
                            linestyle='dashed',
                            linewidth=2)
        ax.add_patch(circle)

        # Pontos
        ax.scatter(0, 0, s=200, color='black', marker='+', label='Referência (0,0)')
        ax.scatter(df_init['erro_X'], df_init['erro_Y'],
                   s=15, alpha=0.6, label='Erros individuais')

        # ================= SETAS (QUIVER) =================

        ax.quiver(0, 0, mean_erro_X, 0,
                  angles='xy', scale_units='xy', scale=1,
                  color='red', width=0.005)

        ax.quiver(0, 0, 0, mean_erro_Y,
                  angles='xy', scale_units='xy', scale=1,
                  color='blue', width=0.005)

        ax.quiver(0, 0, mean_erro_X, mean_erro_Y,
                  angles='xy', scale_units='xy', scale=1,
                  color='green', width=0.005)

        # ================== TABELA NO CANTO SUPERIOR ESQUERDO ==================

        texto_tabela = (
            f"LEGENDA / EXPLICAÇÃO\n\n"
            f"+   = Referência (0,0)\n"
            f"•   = Erros individuais\n"
            f"→ Vermelho = Média em X\n"
            f"↑ Azul = Média em Y\n"
            f"↗ Verde = Média vetorial\n"
            f"Círculo = Erro linear médio\n\n"
            f"VALORES\n"
            f"Média X = {mean_erro_X:.3f} m\n"
            f"Média Y = {mean_erro_Y:.3f} m\n"
            f"Erro médio = {mean_erro_lin:.3f} m"
        )

        ax.text(
            0.02, 0.98,
            texto_tabela,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment='top',
            horizontalalignment='left',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.85)
        )

        # Limites e aparência
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)

        ax.grid(True, linestyle='--', alpha=0.5)
        ax.set_xlabel("Erro em X (m)")
        ax.set_ylabel("Erro em Y (m)")
        ax.set_title("Dispersão dos Erros GNSS")
        ax.legend()

        # ================== SALVAR AUTOMÁTICO ==================

        plt.savefig(caminho_png, dpi=300, bbox_inches='tight')
        plt.savefig(caminho_pdf, bbox_inches='tight')

        print("\n✅ Gráfico salvo com sucesso em:")
        print(f"PNG: {caminho_png}")
        print(f"PDF: {caminho_pdf}")

        plt.show()


# ===================== Função para rodar no QGIS =====================

def run():
    global janela
    janela = ErroPlotDialog()
    janela.show()
    return janela
