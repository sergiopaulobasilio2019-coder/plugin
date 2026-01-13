"""
Model exported as python.
Name : testeScript
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


class Testescript(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        param = QgsProcessingParameterVectorLayer('arquivo_c', 'Arquivo C', defaultValue=None)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        self.addParameter(QgsProcessingParameterVectorLayer('arquivo_ref', 'Arquivo Ref', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('arquivo_test', 'Arquivo Test', defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Out', 'OUT', optional=True, type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(5, model_feedback)
        results = {}
        outputs = {}

        # Calculando Campo X_Test
        alg_params = {
            'FIELD_LENGTH': 20,
            'FIELD_NAME': 'X_Test',
            'FIELD_PRECISION': 3,
            'FIELD_TYPE': 0,  # Decimal (double)
            'FORMULA': '$X',
            'INPUT': parameters['arquivo_test'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculandoCampoX_test'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Calculando Campo X_Ref
        alg_params = {
            'FIELD_LENGTH': 20,
            'FIELD_NAME': 'X_Ref',
            'FIELD_PRECISION': 3,
            'FIELD_TYPE': 0,  # Decimal (double)
            'FORMULA': '$X',
            'INPUT': parameters['arquivo_ref'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculandoCampoX_ref'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Calculando Campo Y_Test
        alg_params = {
            'FIELD_LENGTH': 20,
            'FIELD_NAME': 'Y_Test',
            'FIELD_PRECISION': 3,
            'FIELD_TYPE': 0,  # Decimal (double)
            'FORMULA': '$Y',
            'INPUT': outputs['CalculandoCampoX_test']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculandoCampoY_test'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Calculando Campo Y_Ref
        alg_params = {
            'FIELD_LENGTH': 20,
            'FIELD_NAME': 'Y_Ref',
            'FIELD_PRECISION': 3,
            'FIELD_TYPE': 0,  # Decimal (double)
            'FORMULA': '$Y',
            'INPUT': outputs['CalculandoCampoX_ref']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculandoCampoY_ref'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Unir atributos pelo mais próximo
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELDS_TO_COPY': ["'X_Test,Y_Test'"],
            'INPUT': outputs['CalculandoCampoY_ref']['OUTPUT'],
            'INPUT_2': outputs['CalculandoCampoY_test']['OUTPUT'],
            'MAX_DISTANCE': None,
            'NEIGHBORS': 1,
            'PREFIX': '',
            'OUTPUT': parameters['Out']
        }
        outputs['UnirAtributosPeloMaisPrximo'] = processing.run('native:joinbynearest', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Out'] = outputs['UnirAtributosPeloMaisPrximo']['OUTPUT']
        return results

    def name(self):
        return 'testeScript'

    def displayName(self):
        return 'testeScript'

    def group(self):
        return 'GEGAP'

    def groupId(self):
        return 'GEGAP'

    def createInstance(self):
        return Testescript()
