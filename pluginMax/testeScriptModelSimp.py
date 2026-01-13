"""
Model exported as python.
Name : testeScriptSimp
Group : GEGAP
With QGIS : 33408
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterDefinition
import processing


class Testescriptsimp(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        param = QgsProcessingParameterVectorLayer('arquivo_c', 'Arquivo C', defaultValue=None)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        self.addParameter(QgsProcessingParameterVectorLayer('arquivo_ref', 'Arquivo Ref', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('arquivo_test', 'Arquivo Test', defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Out_simp', 'OUT_simp', optional=True, type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(1, model_feedback)
        results = {}
        outputs = {}

        # Unir atributos pelo mais próximo
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELDS_TO_COPY': [''],
            'INPUT': parameters['arquivo_ref'],
            'INPUT_2': parameters['arquivo_test'],
            'MAX_DISTANCE': None,
            'NEIGHBORS': 1,
            'PREFIX': '',
            'OUTPUT': parameters['Out_simp']
        }
        outputs['UnirAtributosPeloMaisPrximo'] = processing.run('native:joinbynearest', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Out_simp'] = outputs['UnirAtributosPeloMaisPrximo']['OUTPUT']
        return results

    def name(self):
        return 'testeScriptSimp'

    def displayName(self):
        return 'testeScriptSimp'

    def group(self):
        return 'GEGAP'

    def groupId(self):
        return 'GEGAP'

    def createInstance(self):
        return Testescriptsimp()
