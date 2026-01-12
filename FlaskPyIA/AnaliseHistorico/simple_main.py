import json
from typing import Dict, Any, List
from datetime import datetime
import time
import AnaliseHistorico.LerHistorico as LerHistorico

class AnaliseHistorico:
    def __init__(self, payload):
        self.payload = payload
        self.gemini = LerHistorico.Gemini()

    def processar_historico(self):
       
        resultado = self.gemini.analisarDocumento(self.payload['historico'], self.payload['grade'])
        return {
            "status": "sucesso",
            "mensagem": "Histórico analisado com sucesso",
            "detalhes": resultado
        }


def main(payload):
    analise = AnaliseHistorico(payload)
    return analise.processar_historico()