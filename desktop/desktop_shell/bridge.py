"""
Ponte JS↔Python exposta à página via `window.pywebview.api` (requisito de
diálogo nativo de pasta — a web não tem como abrir um seletor de pasta do
sistema operacional; só o pywebview, rodando fora do sandbox do navegador,
consegue).

Mantido deliberadamente mínimo: a lógica de mover o banco/validar a pasta
fica no backend (`app/routers/sistema.py`), que a tela de Configurações já
chama por HTTP depois de receber o caminho escolhido aqui. Esta ponte só
abre o diálogo e devolve o caminho (ou `None` se o usuário cancelou).
"""
import webview


class Bridge:
    def escolher_pasta(self):
        resultado = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        if not resultado:
            return None
        return resultado[0] if isinstance(resultado, (list, tuple)) else resultado
