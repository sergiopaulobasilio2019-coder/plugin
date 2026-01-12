import os
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton,
    QLabel, QComboBox, QLineEdit, QPushButton, QFileDialog,
    QMessageBox
)

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsMapLayerType
)


class TwoShapefilesDialog(QDialog):
    """
    Diálogo que permite escolher 2 camadas:
    - via layers existentes no projeto, OU
    - via seleção de arquivo shapefile (.shp)
    """

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.setWindowTitle("Two Shapefiles Loader")
        self.setMinimumWidth(520)

        # Armazenar referências finais
        self.layer_a = None
        self.layer_b = None

        self._build_ui()
        self._wire_events()

    # ---------------- UI ----------------

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Modo de seleção
        gb_mode = QGroupBox("Fonte dos dados")
        mode_layout = QHBoxLayout(gb_mode)
        self.rb_project = QRadioButton("Usar layers do projeto")
        self.rb_files = QRadioButton("Selecionar arquivos (Shapefile)")
        self.rb_project.setChecked(True)

        mode_layout.addWidget(self.rb_project)
        mode_layout.addWidget(self.rb_files)
        layout.addWidget(gb_mode)

        # Grupo: projeto
        self.gb_project = QGroupBox("Selecionar 2 layers vetoriais do projeto")
        gp_layout = QVBoxLayout(self.gb_project)

        row_a = QHBoxLayout()
        row_a.addWidget(QLabel("Layer A:"))
        self.cmb_a = QComboBox()
        row_a.addWidget(self.cmb_a)

        row_b = QHBoxLayout()
        row_b.addWidget(QLabel("Layer B:"))
        self.cmb_b = QComboBox()
        row_b.addWidget(self.cmb_b)

        gp_layout.addLayout(row_a)
        gp_layout.addLayout(row_b)
        layout.addWidget(self.gb_project)

        # Grupo: arquivos
        self.gb_files = QGroupBox("Selecionar 2 arquivos .shp")
        gf_layout = QVBoxLayout(self.gb_files)

        file_a = QHBoxLayout()
        file_a.addWidget(QLabel("Shapefile A:"))
        self.txt_a = QLineEdit()
        self.txt_a.setPlaceholderText("Caminho do arquivo .shp")
        self.btn_browse_a = QPushButton("Procurar...")
        file_a.addWidget(self.txt_a)
        file_a.addWidget(self.btn_browse_a)

        file_b = QHBoxLayout()
        file_b.addWidget(QLabel("Shapefile B:"))
        self.txt_b = QLineEdit()
        self.txt_b.setPlaceholderText("Caminho do arquivo .shp")
        self.btn_browse_b = QPushButton("Procurar...")
        file_b.addWidget(self.txt_b)
        file_b.addWidget(self.btn_browse_b)

        gf_layout.addLayout(file_a)
        gf_layout.addLayout(file_b)
        layout.addWidget(self.gb_files)

        # Botões
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.btn_load = QPushButton("Carregar")
        self.btn_close = QPushButton("Fechar")
        buttons.addWidget(self.btn_load)
        buttons.addWidget(self.btn_close)
        layout.addLayout(buttons)

        self._toggle_mode_ui()

    def _wire_events(self):
        self.rb_project.toggled.connect(self._toggle_mode_ui)
        self.rb_files.toggled.connect(self._toggle_mode_ui)

        self.btn_browse_a.clicked.connect(lambda: self._browse_shp(self.txt_a))
        self.btn_browse_b.clicked.connect(lambda: self._browse_shp(self.txt_b))

        self.btn_load.clicked.connect(self._on_load_clicked)
        self.btn_close.clicked.connect(self.close)

    # ---------------- Helpers ----------------

    def refresh_layers(self):
        """
        Recarrega a lista de layers vetoriais do projeto.
        """
        self.cmb_a.clear()
        self.cmb_b.clear()

        layers = [
            lyr for lyr in QgsProject.instance().mapLayers().values()
            if lyr.type() == QgsMapLayerType.VectorLayer
        ]

        # Armazenar layerId no userData do item
        for lyr in layers:
            self.cmb_a.addItem(lyr.name(), lyr.id())
            self.cmb_b.addItem(lyr.name(), lyr.id())

    def _toggle_mode_ui(self):
        use_project = self.rb_project.isChecked()
        self.gb_project.setEnabled(use_project)
        self.gb_files.setEnabled(not use_project)

    def _browse_shp(self, target_line_edit):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Shapefile",
            "",
            "Shapefile (*.shp)"
        )
        if path:
            target_line_edit.setText(path)

    # ---------------- Load logic ----------------

    def _on_load_clicked(self):
        try:
            if self.rb_project.isChecked():
                self.layer_a, self.layer_b = self._get_layers_from_project()
            else:
                self.layer_a, self.layer_b = self._get_layers_from_files()

            # Exemplo: zoom para o layer A após carregar
            if self.layer_a:
                self.iface.setActiveLayer(self.layer_a)

            QMessageBox.information(
                self,
                "Sucesso",
                f"Layers definidos:\nA: {self.layer_a.name()}\nB: {self.layer_b.name()}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

    def _get_layers_from_project(self):
        id_a = self.cmb_a.currentData()
        id_b = self.cmb_b.currentData()

        if not id_a or not id_b:
            raise ValueError("Selecione Layer A e Layer B.")

        if id_a == id_b:
            raise ValueError("Layer A e Layer B devem ser diferentes.")

        lyr_a = QgsProject.instance().mapLayer(id_a)
        lyr_b = QgsProject.instance().mapLayer(id_b)

        if lyr_a is None or lyr_b is None:
            raise ValueError("Não foi possível obter um ou ambos os layers do projeto.")

        return self._validate_vector_layer(lyr_a, "Layer A"), self._validate_vector_layer(lyr_b, "Layer B")

    def _get_layers_from_files(self):
        path_a = self.txt_a.text().strip()
        path_b = self.txt_b.text().strip()

        if not path_a or not path_b:
            raise ValueError("Informe os dois caminhos de shapefile (.shp).")

        if os.path.abspath(path_a) == os.path.abspath(path_b):
            raise ValueError("Shapefile A e Shapefile B devem ser diferentes.")

        lyr_a = self._load_vector_layer(path_a, "Shapefile A")
        lyr_b = self._load_vector_layer(path_b, "Shapefile B")
        return lyr_a, lyr_b

    def _load_vector_layer(self, path, label):
        if not os.path.exists(path):
            raise ValueError(f"{label}: arquivo não encontrado:\n{path}")

        # Nome amigável no painel: usa o nome do arquivo
        name = os.path.splitext(os.path.basename(path))[0]
        layer = QgsVectorLayer(path, name, "ogr")

        self._validate_vector_layer(layer, label)

        # Adiciona ao projeto (e retorna o objeto efetivo)
        QgsProject.instance().addMapLayer(layer)
        return layer

    def _validate_vector_layer(self, layer, label):
        if layer is None:
            raise ValueError(f"{label}: layer inválido (None).")
        if not isinstance(layer, QgsVectorLayer):
            raise ValueError(f"{label}: não é uma camada vetorial.")
        if not layer.isValid():
            raise ValueError(f"{label}: camada não é válida (verifique o arquivo/dados).")
        return layer
