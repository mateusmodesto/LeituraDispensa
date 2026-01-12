from flask import Flask, request, jsonify
#from FlaskPyIA.tasks import validar_documento
#from celery.result import AsyncResult
#from FlaskPyIA.celery_app import celery

app = Flask(__name__)

def err(msg, code=400, extra=None):
    payload = {"status": "erro", "msg": msg}

    if extra:
        safe_extra = {}
        for k, v in extra.items():
            if isinstance(v, (dict, list, str, int, float, bool)) or v is None:
                safe_extra[k] = v
            else:
                safe_extra[k] = str(v)  # 🔒 conversão forçada
        payload.update(safe_extra)

    return jsonify(payload), code




@app.route("/analiseHistorico", methods=["POST"])
def analiseHistorico():
    # Simulação de leitura de histórico
    import AnaliseHistorico.simple_main as ah
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return err("JSON inválido ou ausente", 400)
        payload = {            
            "aluno": data.get("aluno"),
            "historico": data.get("historico"),
            "grade": data.get("grade"),
            "id_analise": data.get("id_analise"),
        }
        # Validações (400)
        if not payload['historico']:
            return err("Campo 'historico' é obrigatório", 400)
        if not payload['aluno']:
            return err("Campo 'aluno' é obrigatório", 400)
        if not payload['grade']:
            return err("Campo 'grade' é obrigatório", 400)
        
        payload = convert_sets(payload)

        result = convert_sets(ah.main(payload))

        
        if result['status'] == 'sucesso':
            return jsonify({
                    "status": "processado",
                    "resultado": result
                }), 200
        elif result['status'] == 'error':
            return jsonify({'status': "nao processado", "resultado": result, "payload": payload}), 200

        return err("Erro ao processar histórico", 200, {
            "detail": convert_sets(result)
        })

    except Exception as e:
        return err("Erro interno", 500, {"detail": str(e)})
    

def convert_sets(obj):
    if isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, dict):
        return {k: convert_sets(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_sets(i) for i in obj]
    else:
        return obj

if __name__ == "__main__":
    app.run(host="10.200.23.13", port=5000, debug=False)
