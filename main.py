from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import List, Optional


DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="C.I.A. Backend")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# MODELOS
# =========================

class Progresso(BaseModel):
    codigo_acesso: str
    nome: str
    caso_id: str
    voto: Optional[str] = None
    teorias: List[str] = Field(default_factory=list)
    pistas_liberadas: int = 0
    revelacao_liberada: bool = False


class AceiteCaso(BaseModel):
    codigo_acesso: str
    nome: str
    caso_id: str


class NovoAcesso(BaseModel):
    codigo_acesso: str
    nome_cliente: str
    caso_id: str = "arquivo001"
    ativo: bool = True


# =========================
# CONEXÃO
# =========================

def conectar():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não foi configurada no Render.")

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )


# =========================
# ACESSOS INICIAIS
# =========================

def criar_acessos_iniciais(cursor, conn):
    acessos_iniciais = [
        ("CIA001-ANA2026", "Ana", "arquivo001"),
        ("CIA002-MARIA2026", "Maria", "arquivo001"),
        ("CIA003-JULIA2026", "Julia", "arquivo001"),
        ("CIA004-CARLA2026", "Carla", "arquivo001"),
        ("CIA005-AMANDA2026", "Amanda", "arquivo001"),
        ("CIA006-LUCAS2026", "Lucas", "arquivo001"),
        ("CIA007-PAULA2026", "Paula", "arquivo001"),
        ("CIA008-RAFA2026", "Rafa", "arquivo001"),
        ("CIA009-BIA2026", "Bia", "arquivo001"),
        ("CIA010-TESTE2026", "Teste", "arquivo001"),
    ]

    for codigo, nome, caso_id in acessos_iniciais:
        cursor.execute(
            """
            INSERT INTO acessos (
                codigo_acesso,
                nome_cliente,
                caso_id,
                ativo
            )
            VALUES (%s, %s, %s, TRUE)
            ON CONFLICT (codigo_acesso)
            DO NOTHING
            """,
            (codigo, nome, caso_id)
        )

    conn.commit()


# =========================
# CRIAR TABELAS
# =========================

def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS acessos (
            codigo_acesso TEXT PRIMARY KEY,
            nome_cliente TEXT NOT NULL,
            caso_id TEXT NOT NULL,
            ativo BOOLEAN DEFAULT TRUE,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_inicio TIMESTAMP,
            data_final TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS progresso (
            codigo_acesso TEXT NOT NULL,
            nome TEXT NOT NULL,
            caso_id TEXT NOT NULL,
            voto TEXT,
            teorias TEXT,
            pistas_liberadas INTEGER DEFAULT 0,
            revelacao_liberada BOOLEAN DEFAULT FALSE,
            data_inicio TIMESTAMP,
            data_final TIMESTAMP,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (codigo_acesso, caso_id)
        )
        """
    )

    conn.commit()

    criar_acessos_iniciais(cursor, conn)

    cursor.close()
    conn.close()


@app.on_event("startup")
def iniciar():
    criar_tabelas()


# =========================
# ROTAS BÁSICAS
# =========================

@app.get("/")
def home():
    return {
        "status": "Backend da C.I.A. funcionando no Render"
    }


@app.get("/teste")
def teste():
    return {
        "mensagem": "API online"
    }


# =========================
# POPULAR ACESSOS MANUALMENTE
# =========================

@app.get("/popular-acessos")
def popular_acessos():
    conn = conectar()
    cursor = conn.cursor()

    criar_acessos_iniciais(cursor, conn)

    cursor.execute(
        """
        SELECT
            codigo_acesso,
            nome_cliente,
            caso_id,
            ativo,
            data_criacao,
            data_inicio,
            data_final
        FROM acessos
        ORDER BY codigo_acesso ASC
        """
    )

    acessos = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "mensagem": "Acessos iniciais criados/verificados com sucesso.",
        "total": len(acessos),
        "acessos": acessos
    }


# =========================
# VALIDAR ACESSO
# =========================

@app.get("/validar-acesso/{codigo_acesso}/{caso_id}")
def validar_acesso(codigo_acesso: str, caso_id: str):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM acessos
        WHERE codigo_acesso = %s
        AND caso_id = %s
        AND ativo = TRUE
        """,
        (codigo_acesso, caso_id)
    )

    acesso = cursor.fetchone()

    cursor.close()
    conn.close()

    if not acesso:
        return {
            "valido": False,
            "mensagem": "Código inválido, inativo ou sem acesso a este caso."
        }

    return {
        "valido": True,
        "mensagem": "Acesso autorizado.",
        "codigo_acesso": acesso["codigo_acesso"],
        "nome_cliente": acesso["nome_cliente"],
        "caso_id": acesso["caso_id"],
        "ativo": acesso["ativo"],
        "data_inicio": acesso["data_inicio"],
        "data_final": acesso["data_final"]
    }


# =========================
# LISTAR ACESSOS
# =========================

@app.get("/acessos")
def listar_acessos():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            codigo_acesso,
            nome_cliente,
            caso_id,
            ativo,
            data_criacao,
            data_inicio,
            data_final
        FROM acessos
        ORDER BY codigo_acesso ASC
        """
    )

    acessos = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "total": len(acessos),
        "acessos": acessos
    }


# =========================
# CRIAR OU ATUALIZAR ACESSO
# =========================

@app.post("/criar-acesso")
def criar_acesso(dados: NovoAcesso):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO acessos (
            codigo_acesso,
            nome_cliente,
            caso_id,
            ativo
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (codigo_acesso)
        DO UPDATE SET
            nome_cliente = EXCLUDED.nome_cliente,
            caso_id = EXCLUDED.caso_id,
            ativo = EXCLUDED.ativo
        """,
        (
            dados.codigo_acesso,
            dados.nome_cliente,
            dados.caso_id,
            dados.ativo
        )
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "mensagem": "Acesso criado ou atualizado com sucesso.",
        "codigo_acesso": dados.codigo_acesso,
        "nome_cliente": dados.nome_cliente,
        "caso_id": dados.caso_id,
        "ativo": dados.ativo
    }


# =========================
# ACEITAR CASO
# =========================

@app.post("/aceitar-caso")
def aceitar_caso(dados: AceiteCaso):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM acessos
        WHERE codigo_acesso = %s
        AND caso_id = %s
        AND ativo = TRUE
        """,
        (dados.codigo_acesso, dados.caso_id)
    )

    acesso = cursor.fetchone()

    if not acesso:
        cursor.close()
        conn.close()

        return {
            "autorizado": False,
            "mensagem": "Código inválido, inativo ou sem acesso a este caso."
        }

    if acesso["data_inicio"]:
        cursor.execute(
            """
            SELECT *
            FROM progresso
            WHERE codigo_acesso = %s
            AND caso_id = %s
            """,
            (dados.codigo_acesso, dados.caso_id)
        )

        progresso_existente = cursor.fetchone()

        if not progresso_existente:
            cursor.execute(
                """
                INSERT INTO progresso (
                    codigo_acesso,
                    nome,
                    caso_id,
                    teorias,
                    pistas_liberadas,
                    revelacao_liberada,
                    data_inicio,
                    data_final
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (codigo_acesso, caso_id)
                DO NOTHING
                """,
                (
                    dados.codigo_acesso,
                    dados.nome,
                    dados.caso_id,
                    "",
                    0,
                    False,
                    acesso["data_inicio"],
                    acesso["data_final"]
                )
            )

            conn.commit()

        cursor.close()
        conn.close()

        return {
            "autorizado": True,
            "mensagem": "Caso já havia sido aceito.",
            "data_inicio": acesso["data_inicio"],
            "data_final": acesso["data_final"]
        }

    data_inicio = datetime.utcnow()
    data_final = data_inicio + timedelta(days=28)

    cursor.execute(
        """
        UPDATE acessos
        SET data_inicio = %s,
            data_final = %s
        WHERE codigo_acesso = %s
        AND caso_id = %s
        """,
        (
            data_inicio,
            data_final,
            dados.codigo_acesso,
            dados.caso_id
        )
    )

    cursor.execute(
        """
        INSERT INTO progresso (
            codigo_acesso,
            nome,
            caso_id,
            teorias,
            pistas_liberadas,
            revelacao_liberada,
            data_inicio,
            data_final
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (codigo_acesso, caso_id)
        DO NOTHING
        """,
        (
            dados.codigo_acesso,
            dados.nome,
            dados.caso_id,
            "",
            0,
            False,
            data_inicio,
            data_final
        )
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "autorizado": True,
        "mensagem": "Caso aceito com sucesso.",
        "data_inicio": data_inicio,
        "data_final": data_final
    }


# =========================
# SALVAR PROGRESSO
# =========================

@app.post("/progresso")
def salvar_progresso(dados: Progresso):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM acessos
        WHERE codigo_acesso = %s
        AND caso_id = %s
        AND ativo = TRUE
        """,
        (dados.codigo_acesso, dados.caso_id)
    )

    acesso = cursor.fetchone()

    if not acesso:
        cursor.close()
        conn.close()

        return {
            "autorizado": False,
            "mensagem": "Código inválido, inativo ou sem acesso a este caso."
        }

    teorias_texto = "||".join(dados.teorias)

    if acesso["data_inicio"]:
        data_inicio = acesso["data_inicio"]
        data_final = acesso["data_final"]
    else:
        data_inicio = datetime.utcnow()
        data_final = data_inicio + timedelta(days=28)

        cursor.execute(
            """
            UPDATE acessos
            SET data_inicio = %s,
                data_final = %s
            WHERE codigo_acesso = %s
            AND caso_id = %s
            """,
            (
                data_inicio,
                data_final,
                dados.codigo_acesso,
                dados.caso_id
            )
        )

    cursor.execute(
        """
        INSERT INTO progresso (
            codigo_acesso,
            nome,
            caso_id,
            voto,
            teorias,
            pistas_liberadas,
            revelacao_liberada,
            data_inicio,
            data_final,
            atualizado_em
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (codigo_acesso, caso_id)
        DO UPDATE SET
            nome = EXCLUDED.nome,
            voto = EXCLUDED.voto,
            teorias = EXCLUDED.teorias,
            pistas_liberadas = EXCLUDED.pistas_liberadas,
            revelacao_liberada = EXCLUDED.revelacao_liberada,
            data_inicio = EXCLUDED.data_inicio,
            data_final = EXCLUDED.data_final,
            atualizado_em = CURRENT_TIMESTAMP
        """,
        (
            dados.codigo_acesso,
            dados.nome,
            dados.caso_id,
            dados.voto,
            teorias_texto,
            dados.pistas_liberadas,
            dados.revelacao_liberada,
            data_inicio,
            data_final
        )
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "autorizado": True,
        "mensagem": "Progresso salvo com sucesso."
    }


# =========================
# BUSCAR PROGRESSO
# =========================

@app.get("/progresso/{codigo_acesso}/{caso_id}")
def buscar_progresso(codigo_acesso: str, caso_id: str):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM acessos
        WHERE codigo_acesso = %s
        AND caso_id = %s
        AND ativo = TRUE
        """,
        (codigo_acesso, caso_id)
    )

    acesso = cursor.fetchone()

    if not acesso:
        cursor.close()
        conn.close()

        return {
            "encontrado": False,
            "autorizado": False,
            "mensagem": "Código inválido, inativo ou sem acesso a este caso."
        }

    cursor.execute(
        """
        SELECT *
        FROM progresso
        WHERE codigo_acesso = %s
        AND caso_id = %s
        """,
        (codigo_acesso, caso_id)
    )

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if not row:
        return {
            "encontrado": False,
            "autorizado": True,
            "mensagem": "Acesso válido, mas nenhum progresso encontrado.",
            "codigo_acesso": acesso["codigo_acesso"],
            "nome": acesso["nome_cliente"],
            "caso_id": acesso["caso_id"],
            "data_inicio": acesso["data_inicio"],
            "data_final": acesso["data_final"]
        }

    teorias = []

    if row["teorias"]:
        teorias = row["teorias"].split("||")

    agora = datetime.utcnow()
    data_inicio = row["data_inicio"]
    data_final = row["data_final"]

    dias_passados = 0

    if data_inicio:
        dias_passados = (agora - data_inicio).days

    semana_atual = 1

    if dias_passados >= 22:
        semana_atual = 4
    elif dias_passados >= 15:
        semana_atual = 3
    elif dias_passados >= 8:
        semana_atual = 2

    revelacao_disponivel = False

    if data_final and agora >= data_final:
        revelacao_disponivel = True

    return {
        "encontrado": True,
        "autorizado": True,
        "codigo_acesso": row["codigo_acesso"],
        "nome": row["nome"],
        "caso_id": row["caso_id"],
        "voto": row["voto"],
        "teorias": teorias,
        "pistas_liberadas": row["pistas_liberadas"],
        "revelacao_liberada": row["revelacao_liberada"],
        "data_inicio": row["data_inicio"],
        "data_final": row["data_final"],
        "dias_passados": dias_passados,
        "semana_atual": semana_atual,
        "revelacao_disponivel": revelacao_disponivel
    }
