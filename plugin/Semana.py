import numpy as np
import geopandas as gpd
import os
from datetime import datetime

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QTabWidget, QWidget, QHBoxLayout, QMessageBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class ErroPlotDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Análise de Distorção GNSS Pro (Corrigido)")
        self.resize(1000, 700)
        
        self.dados_calculados = None 
        self.current_fig = None

        layout_principal = QVBoxLayout()
        self.tabs = QTabWidget()

        # --- ABA 1: ENTRADA ---
        aba_dados = QWidget()
        layout_dados = QVBoxLayout()

        # Campos de arquivo
        self.ref_edit = QLineEdit()
        self.test_edit = QLineEdit()
        
        for label, edit, method in [
            ("Referência (Base):", self.ref_edit, self.selecionar_ref),
            ("Teste (GNSS):", self.test_edit, self.selecionar_test)
        ]:
            lay = QHBoxLayout()
            edit.setReadOnly(True)
            btn = QPushButton("...")
            btn.setFixedWidth(40)
            btn.clicked.connect(method)
            lay.addWidget(QLabel(label))
            lay.addWidget(edit)
            lay.addWidget(btn)
            layout_dados.addLayout(lay)

        self.btn_calc = QPushButton("🚀 CALCULAR E GERAR RELATÓRIO")
        self.btn_calc.setFixedHeight(45)
        self.btn_calc.setStyleSheet("font-weight: bold; background-color: #27ae60; color: white;")
        self.btn_calc.clicked.connect(self.processar_dados)
        
        layout_dados.addSpacing(10)
        layout_dados.addWidget(self.btn_calc)
        layout_dados.addStretch()
        aba_dados.setLayout(layout_dados)
        self.tabs.addTab(aba_dados, "1. Entrada")

        # --- ABA 2: RESULTADOS ---
        self.aba_resultados = QWidget()
        self.layout_res = QVBoxLayout()
        
        self.btn_exportar = QPushButton("📄 Salvar Relatório em PDF")
        self.btn_exportar.setFixedHeight(35)
        self.btn_exportar.setStyleSheet("background-color: #2980b9; color: white;")
        self.btn_exportar.clicked.connect(self.exportar_pdf)
        self.btn_exportar.hide()
        
        self.aba_resultados.setLayout(self.layout_res)
        self.tabs.addTab(self.aba_resultados, "2. Resultados")

        layout_principal.addWidget(self.tabs)
        self.setLayout(layout_principal)

    def selecionar_ref(self):
        arq, _ = QFileDialog.getOpenFileName(self, "Referência", "", "Shapefile (*.shp)")
        if arq: self.ref_edit.setText(arq)

    def selecionar_test(self):
        arq, _ = QFileDialog.getOpenFileName(self, "Teste", "", "Shapefile (*.shp)")
        if arq: self.test_edit.setText(arq)

    def limpar_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def processar_dados(self):
        if not self.ref_edit.text() or not self.test_edit.text():
            QMessageBox.warning(self, "Aviso", "Selecione os arquivos.")
            return

        try:
            # 1. Carregar
            ref = gpd.read_file(self.ref_edit.text())
            test = gpd.read_file(self.test_edit.text())
            
            # 2. Harmonizar CRS
            if ref.crs != test.crs: 
                ref = ref.to_crs(test.crs)

            # 3. EXTRAÇÃO MANUAL (Resolve o erro do geometry_right)
            ref['ref_x'] = ref.geometry.x
            ref['ref_y'] = ref.geometry.y

            # 4. Join Proximidade
            joined = gpd.sjoin_nearest(test, ref, how="left", distance_col="dist_oficial")

            # 5. Cálculos
            joined["eX"] = joined.geometry.x - joined["ref_x"]
            joined["eY"] = joined.geometry.y - joined["ref_y"]
            joined["eLin"] = np.sqrt(joined["eX"]**2 + joined["eY"]**2)

            stats = {
                'mx': joined["eX"].mean(), 
                'my': joined["eY"].mean(),
                'mlin': joined["eLin"].mean(), 
                'rmse': np.sqrt((joined["eLin"]**2).mean()),
                'total': len(joined), 
                'data': datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            self.dados_calculados = (joined, stats)

            # 6. Interface Gráfica
            self.limpar_layout(self.layout_res)
            
            resumo_txt = f"Pontos: {stats['total']} | RMSE: {stats['rmse']:.3f}m | Erro Médio: {stats['mlin']:.3f}m"
            self.layout_res.addWidget(QLabel(f"<b>{resumo_txt}</b>"))

            fig = Figure(figsize=(10, 5), dpi=100)
            canvas = FigureCanvas(fig)
            
            ax1 = fig.add_subplot(121)
            ax1.scatter(joined["eX"], joined["eY"], alpha=0.6, color='#3498db', edgecolors='white')
            ax1.axhline(0, color='black', lw=1); ax1.axvline(0, color='black', lw=1)
            ax1.set_title("Dispersão dos Erros (m)")
            ax1.set_xlabel("Erro X"); ax1.set_ylabel("Erro Y")
            ax1.grid(True, linestyle='--', alpha=0.6)
            
            ax2 = fig.add_subplot(122)
            ax2.hist(joined["eLin"], bins=10, color='#2ecc71', edgecolor='white')
            ax2.set_title("Histograma de Erro Linear")
            ax2.set_xlabel("Distância (m)"); ax2.set_ylabel("Frequência")

            fig.tight_layout()
            self.layout_res.addWidget(canvas)
            self.layout_res.addWidget(self.btn_exportar)
            self.btn_exportar.show()
            self.current_fig = fig
            self.tabs.setCurrentIndex(1)

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Ocorreu um problema: {str(e)}")

    def exportar_pdf(self):
        if not self.current_fig: return
        
        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar Relatório", "Analise_GNSS.pdf", "PDF (*.pdf)")
        if caminho:
            try:
                # Adiciona cabeçalho no PDF
                _, s = self.dados_calculados
                info = f"Relatório GNSS - {s['data']}\nRMSE: {s['rmse']:.4f}m | Pontos: {s['total']}"
                self.current_fig.text(0.5, 0.02, info, ha='center', fontsize=8, color='gray')
                
                self.current_fig.savefig(caminho, bbox_inches='tight')
                QMessageBox.information(self, "Sucesso", "PDF salvo com sucesso!")
            except Exception as e:
                QMessageBox.critical(self, "Erro ao salvar", str(e))

def run():
    global dlg_gnss
    dlg_gnss = ErroPlotDialog()
    dlg_gnss.show()
    return dlg_gnss

run()
