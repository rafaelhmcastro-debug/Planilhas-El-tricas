import os
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models_auth import Usuario

SECRET_KEY = os.getenv("SECRET_KEY", "sua-chave-secreta-super-segura-mudeme-em-producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha_plana, senha_hash)


def criar_access_token(usuario_id: int, username: str) -> str:
    data = {
        "sub": str(usuario_id),
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: str = payload.get("sub")
        if usuario_id is None:
            return None
        return {"usuario_id": int(usuario_id), "username": payload.get("username")}
    except JWTError:
        return None


def obter_usuario_por_username(db: Session, username: str):
    return db.query(Usuario).filter(Usuario.username == username).first()


def obter_usuario_por_id(db: Session, usuario_id: int):
    return db.query(Usuario).filter(Usuario.id == usuario_id).first()


def obter_usuario_por_email(db: Session, email: str):
    return db.query(Usuario).filter(Usuario.email == email).first()


def criar_usuario(
    db: Session,
    username: str,
    email: str,
    empresa: str,
    senha: str,
    role: str = "user",
    ativo: bool = True,
    aprovado: bool = False
) -> Usuario:
    senha_hash = hash_senha(senha)
    usuario = Usuario(
        username=username,
        email=email,
        empresa=empresa,
        senha_hash=senha_hash,
        role=role,
        ativo=ativo,
        aprovado=aprovado,
        data_criacao=datetime.utcnow()
    )
    if aprovado:
        usuario.data_aprovacao = datetime.utcnow()
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def autenticar_usuario(db: Session, username: str, senha: str):
    usuario = obter_usuario_por_username(db, username)
    if not usuario:
        return None
    if not verificar_senha(senha, usuario.senha_hash):
        return None
    if not usuario.ativo or not usuario.aprovado:
        return None
    return usuario
