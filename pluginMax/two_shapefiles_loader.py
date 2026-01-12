from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .gui.dialog import TwoShapefilesDialog


class TwoShapefilesLoaderPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dlg = None

    def tr(self, message):
        return QCoreApplication.translate("TwoShapefilesLoaderPlugin", message)

    def initGui(self):
        icon = QIcon(":/")  # fallback
        # Se você tiver icon.png em resources sem compilar .qrc, use caminho relativo:
        icon = QIcon(self._plugin_icon_path())

        self.action = QAction(icon, self.tr("Two Shapefiles Loader"), self.iface.mainWindow())
        self.action.triggered.connect(self.run)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.tr("&Two Shapefiles Loader"), self.action)

    def unload(self):
        if self.action:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu(self.tr("&Two Shapefiles Loader"), self.action)

    def run(self):
        if self.dlg is None:
            self.dlg = TwoShapefilesDialog(self.iface)
        self.dlg.refresh_layers()
        self.dlg.show()

    def _plugin_icon_path(self):
        # caminho relativo ao arquivo do plugin
        import os
        return os.path.join(os.path.dirname(__file__), "resources", "icon.png")
