def classFactory(iface):
    from .two_shapefiles_loader import TwoShapefilesLoaderPlugin
    return TwoShapefilesLoaderPlugin(iface)