"""
Núcleo de cálculo elétrico — Fase 1 do porte para desktop (ADR 0001).

Pacote Python puro: nenhum módulo aqui importa SQLAlchemy, FastAPI ou qualquer
coisa de UI. Toda função recebe dados já resolvidos (dataclasses/dicts/listas)
e devolve dados já resolvidos — quem busca no banco e monta esses dados é a
camada `app/` (fora deste pacote). Isso permite testar o núcleo inteiro sem
banco nem interface, conforme pedido na Fase 1.

Portado de `cabos-app/app/calculations.py`, mantendo as mesmas fórmulas e
regras (ver `decisions-and-spec-corrections.md` na raiz do repositório para o
histórico de toda decisão/correção em relação à especificação original).
"""
