"""
Utilitários de Autenticação
"""
from datetime import datetime, timedelta
from typing import Optional
import os

from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .models_auth import Usuario


# ==================== CONFIGURAÇÕES ====================

# Usar variáveis de ambiente com fallbacks
SECRET_KEY = os.getenv("SECRET_KEY", "sua-chave-super-secreta-mude-em-producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Contexto de criptografia
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==================== HASHING DE SENHA ====================

def hash_senha(senha: str) -> str:
    """Cria hash bcrypt da senha"""
    return pwd_context.hash(senha)


def verificar_senha(senha_plain: str, senha_hash: str) -> bool:
    """Verifica se a senha em plain text corresponde ao hash"""
    return pwd_context.verify(senha_plain, senha_hash)


# ==================== JWT ====================

def criar_access_token(usuario_id: int, username: str, expira_em: Optional[timedelta] = None) -> str:
    """Cria JWT token"""
    if expira_em:
        expire = datetime.utcnow() + expira_em
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    to_encode = {
        "sub": username,
        "usuario_id": usuario_id,
        "exp": expire
    }

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decodificar_token(token: str) -> Optional[dict]:
    """Decodifica e valida JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        usuario_id: int = payload.get("usuario_id")

        if username is None or usuario_id is None:
            return None

        return {"username": username, "usuario_id": usuario_id}
    except JWTError:
        return None


# ==================== USUARIO ====================

def obter_usuario_por_username(db: Session, username: str) -> Optional[Usuario]:
    """Busca usuário por username"""
    return db.query(Usuario).filter(Usuario.username == username).first()


def obter_usuario_por_id(db: Session, usuario_id: int) -> Optional[Usuario]:
    """Busca usuário por ID"""
    return db.query(Usuario).filter(Usuario.id == usuario_id).first()


def obter_usuario_por_email(db: Session, email: str) -> Optional[Usuario]:
    """Busca usuário por email"""
    return db.query(Usuario).filter(Usuario.email == email).first()


def criar_usuario(
    db: Session,
    username: str,
    email: str,
    empresa: str,
    senha: str,
    role: str = "user",
    ativo: bool = False,
    aprovado: bool = False
) -> Usuario:
    """Cria novo usuário"""
    usuario = Usuario(
        username=username,
        email=email,
        empresa=empresa,
        senha_hash=hash_senha(senha),
        role=role,
        ativo=ativo,
        aprovado=aprovado
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def autenticar_usuario(db: Session, username: str, senha: str) -> Optional[Usuario]:
    """Autentica usuário (retorna None se falhar)"""
    usuario = obter_usuario_por_username(db, username)

    if not usuario:
        return None

    if not usuario.ativo or not usuario.aprovado:
        return None

    if not verificar_senha(senha, usuario.senha_hash):
        return None

    return usuario
