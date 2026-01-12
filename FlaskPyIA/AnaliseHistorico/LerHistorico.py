from datetime import datetime
import subprocess
from google import genai
from google.genai import types
import httpx
import requests
import os
import json

class Gemini():
    def __init__(self):
        self.client = genai.Client(api_key="")
        
        self.prompt = """
            Você é um sistema especializado em leitura, interpretação e estruturação de documentos acadêmicos brasileiros (histórico escolar de ensino superior). Você recebe um documento em PDF ou imagem (escaneado) e um JSON com novas disciplinas. Sua tarefa é:
            1) extrair dados do histórico escolar;
            2) estruturar tudo no JSON solicitado;
            3) comparar disciplinas já cursadas com as novas disciplinas e indicar possível dispensa com porcentagem baseada em carga horária.

            ENTRADAS
            A) DOCUMENTO (PDF ou IMAGEM)
            - Histórico escolar de uma instituição de ensino superior brasileira.
            - Pode conter ruídos de digitalização/OCR, tabelas, carimbos, assinaturas, abreviações e variações de layout.

            B) JSON DE NOVAS DISCIPLINAS
            Você receberá um JSON contendo as novas disciplinas que o aluno irá cursar. Exemplo (pode variar):
            {
            "novas_disciplinas": [
                {"codigo": "ABC123", "nome": "Algoritmos", "carga_horaria": 60},
                {"codigo": "DEF456", "nome": "Banco de Dados", "carga_horaria": 80}
            ]
            }

            OBJETIVOS DE EXTRAÇÃO (DO HISTÓRICO)
            Extraia e identifique com precisão:

            1) DADOS DO ALUNO
            - Nome do Aluno
            - Número de Matrícula
            - Curso
            - Período de Ingresso (ex.: 2021.1, 1º semestre de 2020, 2020/2 etc.)

            2) DISCIPLINAS CURSADAS
            Para cada disciplina cursada no histórico, extraia:
            - codigo (se existir no documento; se não, use "")
            - nome
            - carga_horaria (em horas; se não constar, use 0)
            - creditos (se não constar, use 0)
            - nota (como texto; ex.: "8,5", "7.0", "A", "MB", "AP", "—")
            - situacao (padronize para um destes valores quando possível):
            "APROVADO", "REPROVADO", "CURSANDO", "TRANCADO", "DISPENSADO", "EQUIVALENCIA", "INDEFINIDO"

            REGRAS IMPORTANTES (EXTRAÇÃO)
            - Seja tolerante a erros de OCR e variações (ex.: “Matricula”, “Matrícula”, “RA”, “Registro Acadêmico”).
            - Não invente informações.
            - Se um campo não for encontrado, use "" (string vazia) para texto e 0 para números.
            - Se a situação não estiver explícita:
            - Se houver indicação clara de aprovação (“AP”, “Aprovado”, “Apto”, “Dispensado”, “Deferido”), use "APROVADO" ou "DISPENSADO" conforme o termo.
            - Se houver indicação clara de reprovação (“RP”, “Reprovado”, “Reprov.”), use "REPROVADO".
            - Se estiver em andamento (“Cursando”, “Em curso”), use "CURSANDO".
            - Caso não seja possível inferir, use "INDEFINIDO".
            - Se créditos ou carga horária estiverem em formato não padrão, converta para inteiro quando possível.
            - Se houver nota na disciplina, então deve haver situação correspondente.
            - Considere variações comuns de termos e abreviações.

            COMPARAÇÃO COM AS NOVAS DISCIPLINAS (DISPENSA / APROVEITAMENTO)
            Você deve comparar as disciplinas do histórico (disciplinas_cursadas) com as novas disciplinas recebidas no JSON.

            COMO ENCONTRAR EQUIVALÊNCIA
            Considere como “equivalente” quando:
            - O código for igual (match exato), OU
            - O nome for semelhante (variações de acento, abreviações, ordem de palavras)

            REGRA DE PORCENTAGEM POR CARGA HORÁRIA
            Quando você encontrar uma disciplina cursada equivalente a uma nova disciplina, calcule:

            porcentagem_aproveitamento = (carga_horaria_cursada / carga_horaria_nova) * 100

            - Arredonde a porcentagem para inteiro ou para 1 casa decimal (escolha uma e mantenha consistente).
            - Se carga_horaria_nova for 0, defina porcentagem_aproveitamento como 0 e explique na observacao.

            POSSÍVEL DISPENSA
            - Defina possivel_dispensa = true quando:
            - a disciplina cursada equivalente tiver situacao "APROVADO" ou "DISPENSADO" ou suas variantes como já foi decretado acima, E
            - Caso contrário, possivel_dispensa = false, e descreva o motivo na observacao (ex.: “situação reprovado”, “não encontrada equivalente” etc.)

            SAÍDA (OBRIGATÓRIA)
            Retorne EXCLUSIVAMENTE um JSON válido, sem texto fora do JSON, seguindo exatamente esta estrutura:

            {
            "aluno": {
                "nome": "",
                "matricula": "",
                "curso": "",
                "periodo_ingresso": ""
            },
            "comparacao_disciplinas": [
                {
                "nova_disciplina": {
                    "codigo": "",
                    "nome": "",
                    "carga_horaria": 0
                },
                "disciplina_cursada_equivalente": {
                    "codigo": "",
                    "nome": "",
                    "carga_horaria": 0,
                    "creditos": 0,
                    "nota": "",
                    "situacao": ""
                },
                "porcentagem_aproveitamento": 0,
                "possivel_dispensa": true,
                "observacao": ""
                }
            ]
            }

            ORIENTAÇÕES FINAIS
            - Não inclua comentários, markdown, explicações ou qualquer texto fora do JSON.
            - Preencha comparacao_disciplinas com um item para CADA nova disciplina:
            - Se não encontrar equivalente no histórico, deixe disciplina_cursada_equivalente com campos vazios/0 e possivel_dispensa=false, explicando na observacao.
            - Priorize matches por código. Se não houver, use similaridade de nome e evidências textuais.
            """
    
    def analisarDocumento(self, url, grade):
        ext = url.lower().split(".")[-1]
        if ext in ["jpg", "jpeg", "png", "tiff"]:
            return self.leituraImage(url, grade)
        elif ext == "pdf":
            return self.leituraPDF(url, grade)
        elif ext == 'docx':
            return self.docx_to_pdf_from_url_word(url, grade)
        else:
            return {"Erro": True, "Motivo": "Tipo de arquivo não suportado"}

    def leituraImage(self, url, grade):
        try:
            image_bytes = requests.get(url).content
            conteudo = self.prompt + "\n\nJSON DE DISCIPLINAS:\n" + json.dumps(
                grade,
                ensure_ascii=False,
                indent=2
            )
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type='image/jpeg',
                    ),
                    conteudo
                ]
            )
        except Exception as e:
            return {"Erro": True, "Motivo": str(e)}

        return json.loads(response.text.strip().removeprefix("```json").removesuffix("```").strip())

    def leituraPDF(self, url, grade):
        try:
            doc_data = httpx.get(url).content
            conteudo = self.prompt + "\n\nJSON DE DISCIPLINAS:\n" + json.dumps(
                grade,
                ensure_ascii=False,
                indent=2
            )
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    types.Part.from_bytes(
                        data=doc_data,
                        mime_type='application/pdf',
                    ),
                    conteudo
                ]
            )

            return json.loads(response.text.strip().removeprefix("```json").removesuffix("```").strip())
        except Exception as e:
            return {"Erro": True, "Motivo": str(e)}


    def docx_to_pdf_from_url_word(self, url, grade, pdf_name='DocumentoTransformado.pdf'):
        project_dir = os.getcwd()
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        file_id = f"historico_{timestamp}"

        if pdf_name is None:
            pdf_name = f"historico_{timestamp}.pdf"

        docx_path = os.path.join(project_dir, f"{file_id}.docx")
        pdf_path = os.path.join(project_dir, pdf_name)

        # baixar DOCX
        r = requests.get(url)
        r.raise_for_status()
        with open(docx_path, "wb") as f:
            f.write(r.content)

        try:
            libreoffice_path = "C:\\Program Files\\LibreOffice\\program\\soffice.exe"

            # converter via LibreOffice headless
            subprocess.run(
                [
                    libreoffice_path,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", project_dir,
                    docx_path
                ],
                check=True
            )

            # LibreOffice gera PDF com o mesmo nome base
            generated_pdf = docx_path.replace(".docx", ".pdf")
            os.rename(generated_pdf, pdf_path)

            with open(pdf_path, "rb") as pf:
                pdf_bytes = pf.read()
            conteudo = self.prompt + "\n\nJSON DE DISCIPLINAS:\n" + json.dumps(
                grade,
                ensure_ascii=False,
                indent=2
            )
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(
                        data=pdf_bytes,
                        mime_type="application/pdf",
                    ),
                    conteudo
                ]
            )

            result = json.loads(
                response.text.strip()
                .removeprefix("```json")
                .removesuffix("```")
                .strip()
            )


        except Exception as e:
            return {"Erro": True, "Motivo": str(e)}


        finally:
            for path in (docx_path, pdf_path):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass

        return result