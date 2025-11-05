import sys
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
    QTabWidget, QWidget, QHBoxLayout
)

class ErroPlotDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Análise de Erro - Carregar Shapefile")

        # Layout principal da janela
        layout_principal = QVBoxLayout()

        # -------------------------------
        # CAMPO PARA SELECIONAR SHAPEFILE
        # -------------------------------
        self.label_shp = QLabel("Selecione o arquivo SHP contendo os pontos:")
        layout_principal.addWidget(self.label_shp)

        self.campo_shp = QLineEdit()
        layout_principal.addWidget(self.campo_shp)

        self.botao_procurar = QPushButton("Procurar Shapefile...")
        self.botao_procurar.clicked.connect(self.selecionar_shapefile)
        layout_principal.addWidget(self.botao_procurar)

        # -------------------------------
        # ABA COM BOTÕES ACEITAR/CANCELAR
        # -------------------------------
        self.tabs = QTabWidget()
        layout_principal.addWidget(self.tabs)

        aba_final = QWidget()
        layout_botoes = QHBoxLayout()

        self.botao_aceitar = QPushButton("Aceitar")
        self.botao_aceitar.clicked.connect(self.processar_dados)  # Quando clicado → roda o gráfico
        layout_botoes.addWidget(self.botao_aceitar)

        self.botao_cancelar = QPushButton("Cancelar")
        self.botao_cancelar.clicked.connect(self.close)  # Fecha janela
        layout_botoes.addWidget(self.botao_cancelar)

        aba_final.setLayout(layout_botoes)
        self.tabs.addTab(aba_final, "Finalizar")

        self.setLayout(layout_principal)

    # Função para abrir a janela de seleção de arquivo
    def selecionar_shapefile(self):
        arquivo, _ = QFileDialog.getOpenFileName(self, "Selecionar SHP", "", "Shapefile (*.shp)")
        if arquivo:
            self.campo_shp.setText(arquivo)

    # Função principal → onde seu código original é executado
    def processar_dados(self):
        caminho = self.campo_shp.text()

        # Lê o shapefile
        df_init = gpd.read_file(caminho)

        # Calcula erros (mesmo que no seu código original)
        df_init['erro_X'] = df_init['IPHONE_X'] - df_init['GEO_X']
        df_init['erro_Y'] = df_init['IPHONE_Y'] - df_init['GEO_Y']
        df_init['erro_lin'] = np.sqrt(df_init['erro_X']**2 + df_init['erro_Y']**2)

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.set_aspect('equal')

        mean_erro_lin = df_init['erro_lin'].mean()
        circle = plt.Circle((0, 0), mean_erro_lin, fill=False, edgecolor='gray', linestyle='dashed')
        ax.add_patch(circle)

        plt.scatter(0, 0, s=500, color='black', marker='+')
        plt.scatter(df_init['erro_X'], df_init['erro_Y'], s=10)

        mean_erro_X = df_init['erro_X'].mean()
        mean_erro_Y = df_init['erro_Y'].mean()

        ax.arrow(0, 0, mean_erro_X, 0, head_width=0.5, color='red')
        ax.arrow(0, 0, 0, mean_erro_Y, head_width=0.5, color='blue')
        ax.arrow(0, 0, mean_erro_X, mean_erro_Y, head_width=0.5, color='green')

        XY_max_error = df_init[['erro_X', 'erro_Y']].abs().values.max()
        lim = XY_max_error * 1.1
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)

        ax.grid(True, linestyle='--', alpha=0.5)
        ax.set_xlabel("Erro em X (m)")
        ax.set_ylabel("Erro em Y (m)")
        plt.title("Dispersão dos Erros")

        plt.show()


# Executa o aplicativo
if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela = ErroPlotDialog()
    janela.show()
    sys.exit(app.exec_())