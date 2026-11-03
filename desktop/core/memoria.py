"""
Memória de cálculo: registro estruturado de cada passo do dimensionamento
(título, linhas de texto com a fórmula e os valores substituídos, resultado),
na ordem em que os passos aconteceram. Mesmo padrão já usado em
`cabos-app/app/risco5419/memoria.py`, reaproveitado aqui para o núcleo de
cabos/equipamentos/painéis/infraestrutura.
"""
import json


class MemoriaCalculo:
    def __init__(self):
        self.passos = []

    def registrar(self, titulo: str, linhas: list[str], resultado=None, referencia: str | None = None):
        self.passos.append({
            "titulo": titulo,
            "linhas": linhas,
            "resultado": resultado,
            "referencia": referencia,
        })

    def to_dict(self) -> dict:
        return {"passos": self.passos}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
