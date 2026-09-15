// ==================== CONFIGURAÇÃO ====================

const API_BASE = '';
const TOKEN_KEY = 'auth_token';

// ==================== UTILITÁRIOS ====================

function obterToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function salvarToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

function removerToken() {
    localStorage.removeItem(TOKEN_KEY);
}

function limparErros() {
    document.querySelectorAll('.error-message').forEach(el => {
        el.textContent = '';
    });
    const formError = document.getElementById('formError');
    if (formError) formError.textContent = '';
}

function mostrarErro(elementId, mensagem) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = mensagem;
        el.style.display = 'block';
    }
}

function desabilitarFormulario(formulario, desabilitado) {
    formulario.querySelectorAll('input, button').forEach(el => {
        el.disabled = desabilitado;
    });
}

function mostrarCarregamento(mostrar) {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.classList.toggle('hidden', !mostrar);
    }

    const btnText = document.getElementById('btnText');
    const btnLoading = document.getElementById('btnLoading');
    if (btnText && btnLoading) {
        btnText.classList.toggle('hidden', mostrar);
        btnLoading.classList.toggle('hidden', !mostrar);
    }
}

// ==================== VALIDAÇÃO ====================

function validarUsername(username) {
    if (username.length < 3 || username.length > 50) {
        return 'Username deve ter entre 3 e 50 caracteres';
    }
    if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
        return 'Username deve conter apenas letras, números, - e _';
    }
    return null;
}

function validarEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        return 'Email inválido';
    }
    return null;
}

function validarSenha(senha) {
    if (senha.length < 8) {
        return 'Senha deve ter no mínimo 8 caracteres';
    }
    return null;
}

function validarConfirmacaoSenha(senha, confirmacao) {
    if (senha !== confirmacao) {
        return 'As senhas não conferem';
    }
    return null;
}

// ==================== LOGIN ====================

async function fazerLogin() {
    limparErros();
    const formulario = document.getElementById('loginForm');

    const username = document.getElementById('username').value.trim();
    const senha = document.getElementById('senha').value;

    // Validação básica
    if (!username) {
        mostrarErro('usernameError', 'Username é obrigatório');
        return;
    }

    if (!senha) {
        mostrarErro('senhaError', 'Senha é obrigatória');
        return;
    }

    desabilitarFormulario(formulario, true);
    mostrarCarregamento(true);

    try {
        const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                senha: senha
            })
        });

        const dados = await response.json();

        if (!response.ok) {
            if (response.status === 401) {
                mostrarErro('formError', 'Username ou senha incorretos');
            } else if (response.status === 403) {
                mostrarErro('formError', 'Sua conta não foi aprovada pelo administrador ou está desativada');
            } else {
                mostrarErro('formError', dados.detail || 'Erro ao fazer login');
            }
            return;
        }

        // Login bem-sucedido
        salvarToken(dados.access_token);

        // Guardar referência do usuário se lembrar foi marcado
        if (document.getElementById('lembrar').checked) {
            localStorage.setItem('lembrar_usuario', username);
        }

        // Redirecionar para dashboard
        window.location.href = '/index.html';

    } catch (erro) {
        console.error('Erro ao fazer login:', erro);
        mostrarErro('formError', 'Erro de conexão. Tente novamente.');
    } finally {
        desabilitarFormulario(formulario, false);
        mostrarCarregamento(false);
    }
}

// ==================== CADASTRO ====================

async function fazerCadastro() {
    limparErros();
    const formulario = document.getElementById('cadastroForm');

    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const empresa = document.getElementById('empresa').value.trim();
    const senha = document.getElementById('senha').value;
    const confirmarSenha = document.getElementById('confirmarSenha').value;
    const termos = document.getElementById('termos').checked;

    // Validações
    let temErro = false;

    const erroUsername = validarUsername(username);
    if (erroUsername) {
        mostrarErro('usernameError', erroUsername);
        temErro = true;
    }

    const erroEmail = validarEmail(email);
    if (erroEmail) {
        mostrarErro('emailError', erroEmail);
        temErro = true;
    }

    if (!empresa) {
        mostrarErro('empresaError', 'Empresa é obrigatória');
        temErro = true;
    }

    const erroSenha = validarSenha(senha);
    if (erroSenha) {
        mostrarErro('senhaError', erroSenha);
        temErro = true;
    }

    const erroConfirmacao = validarConfirmacaoSenha(senha, confirmarSenha);
    if (erroConfirmacao) {
        mostrarErro('confirmarSenhaError', erroConfirmacao);
        temErro = true;
    }

    if (!termos) {
        mostrarErro('termosError', 'Você deve concordar com os Termos de Uso');
        temErro = true;
    }

    if (temErro) {
        return;
    }

    desabilitarFormulario(formulario, true);
    mostrarCarregamento(true);

    try {
        const response = await fetch(`${API_BASE}/api/auth/cadastro`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                email: email,
                empresa: empresa,
                senha: senha,
                confirmar_senha: confirmarSenha
            })
        });

        const dados = await response.json();

        if (!response.ok) {
            if (dados.detail) {
                if (typeof dados.detail === 'string') {
                    mostrarErro('formError', dados.detail);
                } else if (Array.isArray(dados.detail)) {
                    const mensagens = dados.detail.map(err => err.msg).join(', ');
                    mostrarErro('formError', mensagens);
                }
            } else {
                mostrarErro('formError', 'Erro ao criar conta');
            }
            return;
        }

        // Cadastro bem-sucedido
        formulario.style.display = 'none';
        const successMsg = document.getElementById('successMessage');
        if (successMsg) {
            successMsg.classList.remove('hidden');
            successMsg.style.display = 'block';
        }

        // Redirecionar para login após 3 segundos
        setTimeout(() => {
            window.location.href = '/login.html';
        }, 3000);

    } catch (erro) {
        console.error('Erro ao fazer cadastro:', erro);
        mostrarErro('formError', 'Erro de conexão. Tente novamente.');
    } finally {
        desabilitarFormulario(formulario, false);
        mostrarCarregamento(false);
    }
}

// ==================== LOGOUT ====================

async function fazerLogout() {
    try {
        const token = obterToken();
        if (token) {
            await fetch(`${API_BASE}/api/auth/logout`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                }
            });
        }
    } catch (erro) {
        console.error('Erro ao fazer logout:', erro);
    } finally {
        removerToken();
        window.location.href = '/login.html';
    }
}

// ==================== INICIALIZAÇÃO ====================

document.addEventListener('DOMContentLoaded', () => {
    // Preencher username lembrado se aplicável
    const usuarioLembrado = localStorage.getItem('lembrar_usuario');
    if (usuarioLembrado) {
        const usernameInput = document.getElementById('username');
        if (usernameInput) {
            usernameInput.value = usuarioLembrado;
        }
        const lembrarCheckbox = document.getElementById('lembrar');
        if (lembrarCheckbox) {
            lembrarCheckbox.checked = true;
        }
    }

    // Verificar se usuário já está logado
    const token = obterToken();
    if (token && (window.location.pathname === '/login.html' || window.location.pathname === '/cadastro.html')) {
        // Redirecionar para dashboard se já tem token
        window.location.href = '/index.html';
    }
});
