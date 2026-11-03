"""
Coleta os passos da memória de cálculo, no mesmo formato usado pelo módulo
de cabos (app/calculations.py): uma lista de passos com título, linhas de
texto (fórmula com os valores substituídos) e um resultado. Serializável
para JSON e para a exportação em Excel.
"""
import json


def fmt(v, casas=4):
    if v is None:
        return "-"
    if isinstance(v, str):
        return v
    return f"{v:,.{casas}g}" if abs(v) < 1e-3 and v != 0 else f"{v:,.{casas}f}"


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
