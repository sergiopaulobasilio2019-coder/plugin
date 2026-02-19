from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingException,
    QgsSpatialIndex,
    QgsFeatureRequest
)

import numpy as np
import matplotlib.pyplot as plt


class PECAlgorithm(QgsProcessingAlgorithm):

    REF = 'REF'
    TEST = 'TEST'

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.REF,
                'Camada de Referência',
                [QgsProcessing.TypeVectorPoint]
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.TEST,
                'Camada de Teste',
                [QgsProcessing.TypeVectorPoint]
            )
        )

    def processAlgorithm(self, parameters, context, feedback):

        ref = self.parameterAsVectorLayer(parameters, self.REF, context)
        test = self.parameterAsVectorLayer(parameters, self.TEST, context)

        if not ref or not test:
            raise QgsProcessingException('Erro ao carregar camadas.')

        # 🔥 REMOVIDA QUALQUER EXIGÊNCIA DE MESMO NÚMERO DE PONTOS

        # Criar índice espacial da camada de teste
        index = QgsSpatialIndex(test.getFeatures())

        distancias = []

        for feat_ref in ref.getFeatures():

            geom_ref = feat_ref.geometry()

            if geom_ref is None or geom_ref.isEmpty():
                continue

            # Busca vizinho mais próximo
            nearest_ids = index.nearestNeighbor(geom_ref.asPoint(), 1)

            if not nearest_ids:
                continue

            request = QgsFeatureRequest().setFilterFid(nearest_ids[0])
            feat_test = next(test.getFeatures(request))

            dist = geom_ref.distance(feat_test.geometry())
            distancias.append(dist)

        if len(distancias) == 0:
            raise QgsProcessingException("Nenhuma distância foi calculada.")

        dados = np.array(distancias)

        # ==============================
        # Cálculo PEC
        # ==============================

        erro_90 = np.percentile(dados, 90)

        escala_calc = erro_90 / 0.17

        escalas_padrao = [1000, 2000, 5000, 10000, 25000, 50000, 100000]

        escala_ajustada = None
        for e in escalas_padrao:
            if e >= escala_calc:
                escala_ajustada = e
                break

        if escala_ajustada is None:
            escala_ajustada = escalas_padrao[-1]

        if erro_90 <= 0.17 * escala_ajustada:
            classe = "Classe A"
        elif erro_90 <= 0.30 * escala_ajustada:
            classe = "Classe B"
        else:
            classe = "Classe C ou inferior"

        feedback.pushInfo(f"Erro 90%: {erro_90:.3f} m")
        feedback.pushInfo(f"Escala Calculada: 1:{escala_calc:.0f}")
        fee
