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

#=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
#Novo codigo 
# ==============================================================
# Script adaptado para rodar dentro do QGIS
# Autor: [Seu Nome]
# Descrição: combina análise de dados (Excel) e análise de erro (Shapefile)
#             com interface gráfica via PyQt5, compatível com ambiente QGIS.
# ==============================================================

# ------------------------
# BIBLIOTECAS DO PYTHON
# ------------------------
import sys
import os
import pandas as pd
import numpy as np

# Bibliotecas estatísticas e gráficas
try:
    from scipy.stats import shapiro
    HAS_SHAPIRO = True
except:
    HAS_SHAPIRO = False

import matplotlib.pyplot as plt

try:
    import seaborn as sns
    HAS_SEABORN = True
except:
    HAS_SEABORN = False

# Importações específicas do QGIS
# (essas só existem dentro do ambiente QGIS)
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QTabWidget, QWidget, QHBoxLayout
)
import geopandas as gpd   # leitura de shapefiles

# ==============================================================
# ===================== FUNÇÕES DE ANÁLISE =====================
# ==============================================================

def load_data(path):
    """
    Carrega o arquivo Excel e valida colunas esperadas:
    PONTO, X, Y, DISTANCIA
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    df = pd.read_excel(path)
    expected = ["PONTO", "X", "Y", "DISTANCIA"]

    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise KeyError(f"Colunas faltando: {missing} - esperado: {expected}")

    df = df.copy()
    df["X"] = pd.to_numeric(df["X"], errors="coerce")
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
    df["DISTANCIA"] = pd.to_numeric(df["DISTANCIA"], errors="coerce")
    df = df.dropna(subset=["X", "Y", "DISTANCIA"]).reset_index(drop=True)

    return df


def descriptive_stats(df):
    """ Calcula estatísticas descritivas para X, Y e DISTANCIA. """
    stats = df[["X", "Y", "DISTANCIA"]].describe().T
    stats["%_positivos"] = (df[["X", "Y", "DISTANCIA"]] > 0).sum() / len(df) * 100
    stats["%_negativos"] = (df[["X", "Y", "DISTANCIA"]] < 0).sum() / len(df) * 100
    return stats


def normality(df):
    """ Testa normalidade da coluna DISTANCIA (Shapiro-Wilk) """
    if not HAS_SHAPIRO:
        return None, None
    vals = df["DISTANCIA"].dropna().values
    if len(vals) < 3:
        return None, None
    return shapiro(vals)


# ==============================================================
# ===================== GRÁFICOS (Excel) ========================
# ==============================================================

def plot_scatter(df):
    """ Dispersão X vs Y colorida pela distância """
    x = df["X"].values
    y = df["Y"].values
    dist = df["DISTANCIA"].values
    plt.scatter(x, y, c=dist, cmap="viridis")
    plt.colorbar(label="DISTANCIA")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.title("Dispersão X vs Y (cor = DISTANCIA)")
    plt.show()


def plot_hist(df):
    """ Histograma da distância """
    plt.hist(df["DISTANCIA"].dropna().values, bins=30)
    plt.title("Histograma - DISTANCIA")
    plt.xlabel("DISTANCIA")
    plt.ylabel("Frequência")
    plt.show()


def plot_cdf(df):
    """ Função de distribuição acumulada """
    vals = np.sort(df["DISTANCIA"].dropna().values)
    cdf = np.arange(1, len(vals) + 1) / len(vals)
    plt.plot(vals, cdf)
    plt.grid(True)
    plt.title("Distribuição Acumulada (CDF) - DISTANCIA")
    plt.xlabel("DISTANCIA")
    plt.ylabel("Fração acumulada")
    plt.show()


def plot_box_violin(df):
    """ Boxplot ou Violin Plot dependendo da disponibilidade do Seaborn """
    vals = df["DISTANCIA"].dropna().values
    plt.figure(figsize=(8,4))
    if HAS_SEABORN:
        sns.boxplot(x=vals)
        sns.violinplot(x=vals, inner="quartile", color="lightgray")
        plt.title("Box + Violin - DISTANCIA")
    else:
        plt.boxplot(vals, vert=False)
        plt.title("BoxPlot - DISTANCIA")
    plt.xlabel("DISTANCIA")
    plt.show()


# ==============================================================
# ===================== INTERFACE PyQt (QGIS) ===================
# ==============================================================

class ErroPlotDialog(QDialog):
    """ Janela gráfica integrada ao QGIS para análise de shapefiles """
    def _init_(self, parent=None):
        super()._init_(parent)

        self.setWindowTitle("Análise de Erro - Shapefile (QGIS)")
        layout_principal = QVBoxLayout()

        # --- Campo de seleção do arquivo SHP ---
        self.label_shp = QLabel("Selecione o arquivo SHP contendo os pontos:")
        layout_principal.addWidget(self.label_shp)

        self.campo_shp = QLineEdit()
        layout_principal.addWidget(self.campo_shp)

        self.botao_procurar = QPushButton("Procurar Shapefile...")
        self.botao_procurar.clicked.connect(self.selecionar_shapefile)
        layout_principal.addWidget(self.botao_procurar)

        # --- Botões de ação ---
        layout_botoes = QHBoxLayout()
        self.botao_aceitar = QPushButton("Gerar gráfico")
        self.botao_aceitar.clicked.connect(self.processar_dados)
        layout_botoes.addWidget(self.botao_aceitar)

        self.botao_cancelar = QPushButton("Cancelar")
        self.botao_cancelar.clicked.connect(self.close)
        layout_botoes.addWidget(self.botao_cancelar)

        layout_principal.addLayout(layout_botoes)
        self.setLayout(layout_principal)

    def selecionar_shapefile(self):
        """ Abre seletor de arquivos dentro do ambiente QGIS """
        arquivo, _ = QFileDialog.getOpenFileName(self, "Selecionar SHP", "", "Shapefile (*.shp)")
        if arquivo:
            self.campo_shp.setText(arquivo)

    def processar_dados(self):
        """ Lê shapefile, calcula erros e gera gráfico de dispersão """
        caminho = self.campo_shp.text()
        if not caminho:
            self.label_shp.setText("⚠️ Selecione um shapefile primeiro!")
            return

        df = gpd.read_file(caminho)

        # Validação das colunas esperadas
        for col in ['IPHONE_X', 'IPHONE_Y', 'GEO_X', 'GEO_Y']:
            if col not in df.columns:
                self.label_shp.setText(f"⚠️ Coluna faltando: {col}")
                return

        # Cálculo dos erros
        df['erro_X'] = df['IPHONE_X'] - df['GEO_X']
        df['erro_Y'] = df['IPHONE_Y'] - df['GEO_Y']
        df['erro_lin'] = np.sqrt(df['erro_X']*2 + df['erro_Y']*2)

        # Plot de dispersão dos erros
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.set_aspect('equal')

        mean_erro_lin = df['erro_lin'].mean()
        circle = plt.Circle((0, 0), mean_erro_lin, fill=False, edgecolor='gray', linestyle='dashed')
        ax.add_patch(circle)

        plt.scatter(0, 0, s=500, color='black', marker='+')
        plt.scatter(df['erro_X'], df['erro_Y'], s=10)

        mean_erro_X = df['erro_X'].mean()
        mean_erro_Y = df['erro_Y'].mean()

        ax.arrow(0, 0, mean_erro_X, 0, head_width=0.5, color='red')
        ax.arrow(0, 0, 0, mean_erro_Y, head_width=0.5, color='blue')
        ax.arrow(0, 0, mean_erro_X, mean_erro_Y, head_width=0.5, color='green')

        lim = max(abs(df['erro_X']).max(), abs(df['erro_Y']).max()) * 1.1
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)

        ax.grid(True, linestyle='--', alpha=0.5)
        ax.set_xlabel("Erro em X (m)")
        ax.set_ylabel("Erro em Y (m)")
        plt.title("Dispersão dos Erros (QGIS)")

        plt.show()


# ==============================================================
# ===================== EXECUÇÃO (QGIS) =========================
# ==============================================================

# ⚠️ Importante:
# Dentro do QGIS NÃO se cria uma nova QApplication,
# pois o QGIS já está com o ambiente Qt rodando.
# Basta instanciar e exibir o diálogo diretamente.

# Rode no Console Python do QGIS:
# >>> exec(open('C:/caminho/para/analise_erro_qgis.py').read())

janela = ErroPlotDialog()
janela.show()
