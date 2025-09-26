# ww_dashboard_streamlit.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import datetime
import json
import re
import os
import sys
from math import floor, ceil


def rerun_streamlit():
    try:
        if hasattr(st, "experimental_rerun") and callable(st.experimental_rerun):
            st.experimental_rerun()
        else:
            st.stop()
    except Exception:
        st.stop()


# -----------------------------
# CONFIGURAÇÃO INICIAL
# -----------------------------
st.set_page_config(page_title="Vigilantes do Peso Brasil", layout="wide")

DATA_FILE = "ww_data.json"
USERS_FILE = "ww_users.json"


# -----------------------------
# UTILITÁRIOS
# -----------------------------
def safe_parse_porçao(value):
    if value is None:
        raise ValueError("Porção ausente")
    try:
        return float(value)
    except Exception:
        pass
    s = str(value).strip()
    m = re.search(r"[\d,.]+", s)
    if not m:
        raise ValueError(f"Não foi possível interpretar a porção: {value}")
    num = m.group(0).replace(",", ".")
    try:
        return float(num)
    except Exception:
        raise ValueError(f"Não foi possível interpretar a porção: {value}")


def round_points(p):
    if p is None:
        return 0
    try:
        p = float(p)
    except Exception:
        return 0
    return int(p + 0.5)  # round half up


def load_data(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception:
            return {}
    return {}


def save_data(data, file_path):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str, indent=2)
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")


def persist_all():
    # salva todos os dados do usuário atual
    global data_store, activities
    save_data(data_store, USER_DATA_FILE)
    save_data(activities, ACTIVITY_FILE)


def iso_week_number(date_obj):
    return date_obj.isocalendar()[1]


def weekday_name_br(dt: datetime.date):
    days = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    return days[dt.weekday()]


# -----------------------------
# LOGIN / USUÁRIOS
# -----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""

# Carrega usuários globais
USERS_FILE = "ww_users.json"
users_store = load_data(USERS_FILE)
if not isinstance(users_store, dict):
    users_store = {}

def login_user(email, password):
    global users_store
    if email in users_store and users_store[email]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.current_user = email

        # Carregar dados privados do usuário assim que logar
        user_data_file = f"data_{email}.json"
        activity_file = f"activities_{email}.json"
        data_store = load_data(user_data_file) or {}
        activities = load_data(activity_file) or {}

        # Popular session_state imediatamente sem sobrescrever vazio
        st.session_state.peso = data_store.get("peso", st.session_state.get("peso", []))
        st.session_state.datas_peso = (
            [datetime.date.fromisoformat(d) for d in data_store.get("datas_peso", [])]
            if data_store.get("datas_peso")
            else st.session_state.get("datas_peso", [])
        )
        st.session_state.consumo_historico = data_store.get(
            "consumo_historico", st.session_state.get("consumo_historico", [])
        )
        st.session_state.pontos_semana = data_store.get(
            "pontos_semana", st.session_state.get("pontos_semana", [])
        )
        st.session_state.extras = float(
            data_store.get("extras", st.session_state.get("extras", 36.0))
        )
        st.session_state.consumo_diario = float(
            data_store.get("consumo_diario", st.session_state.get("consumo_diario", 0.0))
        )
        st.session_state.meta_diaria = data_store.get(
            "meta_diaria", st.session_state.get("meta_diaria", 29)
        )
        st.session_state.activities = activities or st.session_state.get("activities", {})

        st.success(f"Bem-vindo(a), {email}!")
        return True
    else:
        st.error("Email ou senha incorretos.")
        return False

def register_user(email, password):
    global users_store
    if email in users_store:
        st.error("Usuário já existe!")
        return False
    users_store[email] = {"password": password}
    save_data(users_store, USERS_FILE)
    st.session_state.logged_in = True
    st.session_state.current_user = email
    st.success(f"Cadastro realizado com sucesso! Bem-vindo(a), {email}!")
    return True

# -----------------------------
# INTERFACE DE LOGIN
# -----------------------------
if not st.session_state.logged_in:
    st.title("🔒 Login - Vigilantes do Peso Brasil")
    tab_login, tab_cadastro = st.tabs(["Login", "Cadastro"])

    with tab_login:
        email_login = st.text_input("Email", key="login_email")
        senha_login = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Login"):
            login_user(email_login.strip(), senha_login.strip())

    with tab_cadastro:
        email_cad = st.text_input("Email", key="cad_email")
        senha_cad = st.text_input("Senha", type="password", key="cad_pass")
        if st.button("Cadastrar"):
            register_user(email_cad.strip(), senha_cad.strip())

    st.stop()  # bloqueia acesso ao restante do app até logar

# -----------------------------
# ARQUIVOS GLOBAIS E PRIVADOS
# -----------------------------
USER_DATA_FILE = f"data_{st.session_state.current_user}.json"
ACTIVITY_FILE = f"activities_{st.session_state.current_user}.json"

# Carrega alimentos globais (disponíveis a todos)
if "alimentos" not in st.session_state:
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            global_data = json.load(f)
            if isinstance(global_data, list):
                st.session_state.alimentos = global_data
            elif isinstance(global_data, dict) and "alimentos" in global_data:
                st.session_state.alimentos = global_data["alimentos"]
            else:
                st.session_state.alimentos = []
    except FileNotFoundError:
        st.session_state.alimentos = []

# Carrega dados privados do usuário
data_store = load_data(USER_DATA_FILE) or {}
activities = load_data(ACTIVITY_FILE) or {}

st.session_state.peso = st.session_state.get("peso", data_store.get("peso", []))
st.session_state.datas_peso = st.session_state.get(
    "datas_peso",
    [datetime.date.fromisoformat(d) for d in data_store.get("datas_peso", [])] if data_store.get("datas_peso") else []
)
st.session_state.consumo_historico = st.session_state.get(
    "consumo_historico", data_store.get("consumo_historico", [])
)
st.session_state.pontos_semana = st.session_state.get(
    "pontos_semana", data_store.get("pontos_semana", [])
)
st.session_state.extras = st.session_state.get("extras", float(data_store.get("extras", 36.0)))
st.session_state.consumo_diario = st.session_state.get(
    "consumo_diario", float(data_store.get("consumo_diario", 0.0))
)
st.session_state.meta_diaria = st.session_state.get("meta_diaria", data_store.get("meta_diaria", 29))
st.session_state.activities = st.session_state.get("activities", activities)

# 🔹 Inicializar histórico acumulado (novo log unificado)
st.session_state.historico_acumulado = st.session_state.get(
    "historico_acumulado", data_store.get("historico_acumulado", [])
)

# Carregar perfil (mantém extras fora do formulário)
st.session_state.sexo = st.session_state.get("sexo", data_store.get("sexo", "Feminino"))
st.session_state.idade = st.session_state.get("idade", data_store.get("idade", 30))
st.session_state.altura = st.session_state.get("altura", data_store.get("altura", 1.70))
st.session_state.objetivo = st.session_state.get("objetivo", data_store.get("objetivo", "manutenção"))
st.session_state.nivel_atividade = st.session_state.get("nivel_atividade", data_store.get("nivel_atividade", "sedentário"))

if "menu" not in st.session_state:
    st.session_state.menu = "🏠 Dashboard"

# -----------------------------
# FUNÇÃO DE PERSISTÊNCIA
# -----------------------------
def persist_all():
    """Salva todos os dados privados do usuário, incluindo o novo histórico acumulado"""
    try:
        ds = {
            "peso": st.session_state.peso,
            "datas_peso": [
                d.isoformat() if isinstance(d, datetime.date) else str(d)
                for d in st.session_state.datas_peso
            ],
            "consumo_diario": float(st.session_state.consumo_diario),
            "meta_diaria": st.session_state.meta_diaria,
            "extras": float(st.session_state.extras),
            "consumo_historico": [
                {
                    "data": (
                        r["data"].isoformat()
                        if isinstance(r.get("data"), datetime.date)
                        else str(r.get("data"))
                    ),
                    "nome": r["nome"],
                    "quantidade": r["quantidade"],
                    "pontos": r["pontos"],
                    "usou_extras": r.get("usou_extras", 0.0),
                }
                for r in st.session_state.consumo_historico
            ],
            "pontos_semana": [
                {
                    "semana": w["semana"],
                    "pontos": [
                        {
                            "data": (
                                p["data"].isoformat()
                                if isinstance(p.get("data"), datetime.date)
                                else str(p.get("data"))
                            ),
                            "nome": p["nome"],
                            "quantidade": p["quantidade"],
                            "pontos": p["pontos"],
                            "usou_extras": p.get("usou_extras", 0.0),
                        }
                        for p in w.get("pontos", [])
                    ],
                    "extras": w.get("extras", 36.0),
                }
                for w in st.session_state.pontos_semana
            ],
            # 🔹 Novo bloco: salvar histórico acumulado
            "historico_acumulado": [
                {
                    **entry,
                    "data": (
                        entry["data"].isoformat()
                        if isinstance(entry.get("data"), datetime.date)
                        else str(entry.get("data"))
                    )
                }
                for entry in st.session_state.historico_acumulado
            ],
        }
        save_data(ds, USER_DATA_FILE)
        save_data(st.session_state.activities, ACTIVITY_FILE)
    except Exception as e:
        st.error(f"Erro ao persistir dados: {e}")

# -----------------------------
# FLAGS DE PRIMEIRO LOGIN E COMPLETAR PERFIL
# -----------------------------
if "primeiro_login" not in st.session_state:
    st.session_state.primeiro_login = False

def perfil_incompleto():
    """Checa se o perfil está incompleto (NÃO exige campo 'extras' no formulário)."""
    return (
        not st.session_state.get("peso")
        or not st.session_state.get("meta_diaria")
        # extras já faz parte do histórico/semana — não exigir aqui
        or not st.session_state.get("sexo")
        or not st.session_state.get("idade")
        or not st.session_state.get("altura")
        or not st.session_state.get("objetivo")
        or not st.session_state.get("nivel_atividade")
    )

# Função para completar perfil (SEM campo 'extras')
def completar_perfil():
    st.header("⚙️ Complete seu perfil")
    sexo = st.selectbox("Sexo:", ["Masculino", "Feminino"], key="perfil_sexo")
    idade = st.number_input("Idade:", min_value=10, max_value=120, step=1, key="perfil_idade")
    altura = st.number_input("Altura (m):", min_value=1.0, max_value=2.5, step=0.01, key="perfil_altura")
    objetivo = st.selectbox("Objetivo:", ["emagrecimento", "manutenção", "ganho"], key="perfil_objetivo")
    nivel_atividade = st.selectbox("Nível de Atividade:", ["sedentário", "moderado", "intenso"], key="perfil_nivel")

    peso_inicial = st.number_input("Peso inicial (kg):", min_value=0.0, step=0.1, key="perfil_peso")
    # NOTA: extras NÃO está no formulário conforme solicitado (mantém valor já existente em st.session_state.extras)

    if st.button("Salvar perfil", key="bot_salvar_perfil"):
        st.session_state.peso = [peso_inicial]
        st.session_state.datas_peso = [datetime.date.today()]
        st.session_state.sexo = sexo
        st.session_state.idade = idade
        st.session_state.altura = altura
        st.session_state.objetivo = objetivo
        st.session_state.nivel_atividade = nivel_atividade

        # Calcula meta automaticamente (usa sua função já existente)
        try:
            st.session_state.meta_diaria = calcular_meta_diaria(
                sexo=sexo,
                idade=idade,
                peso=peso_inicial,
                altura=altura,
                objetivo=objetivo,
                nivel_atividade=nivel_atividade
            )
        except Exception:
            # fallback seguro
            st.session_state.meta_diaria = st.session_state.get("meta_diaria", 29)

        st.session_state.primeiro_login = False
        persist_all()
        st.success("Perfil salvo com sucesso!")
        rerun_streamlit()

# -----------------------------
# FUNÇÃO RESET HISTÓRICO
# -----------------------------
def reset_historico():
    st.session_state.peso = []
    st.session_state.datas_peso = []
    st.session_state.consumo_historico = []
    st.session_state.pontos_semana = []
    st.session_state.extras = 36.0
    st.session_state.consumo_diario = 0.0
    persist_all()
    st.success("Histórico de peso e pontos zerado com sucesso!")

# -----------------------------
# GARANTIR SEMANA ATUAL
# -----------------------------
def ensure_current_week_exists():
    hoje = datetime.date.today()
    week = iso_week_number(hoje)
    if not st.session_state.pontos_semana or st.session_state.pontos_semana[-1].get("semana") != week:
        st.session_state.pontos_semana.append({"semana": week, "pontos": [], "extras": 36.0})
        st.session_state.extras = 36.0
        persist_all()

ensure_current_week_exists()

# -----------------------------
# RECONSTRUÇÃO E RECÁLCULO (EXTRAS / DIÁRIO) COM FATOR DE PONDERAÇÃO
# -----------------------------
def rebuild_pontos_semana_from_history():
    meta = float(st.session_state.meta_diaria or 29.0)
    fator_ponderacao = st.session_state.get("fator_ponderacao", 1.0)  # padrão 1.0
    weeks = {}

    for reg in st.session_state.consumo_historico:
        if not isinstance(reg.get("data"), datetime.date):
            try:
                reg["data"] = datetime.date.fromisoformat(reg["data"])
            except Exception:
                continue
        w = iso_week_number(reg["data"])
        if w not in weeks:
            weeks[w] = {"semana": w, "pontos": [], "extras": 36.0}
        # aplicar fator de ponderação
        reg["pontos"] = round_points(float(reg.get("pontos", 0.0)) * fator_ponderacao)
        weeks[w]["pontos"].append(reg)

    sorted_week_nums = sorted(weeks.keys())
    new_weeks = []
    for wnum in sorted_week_nums:
        week = weeks[wnum]
        extras_remaining = 36.0
        dates_in_order = []
        regs_by_date = {}
        for reg in week["pontos"]:
            d = reg["data"]
            if d not in regs_by_date:
                regs_by_date[d] = []
                dates_in_order.append(d)
            regs_by_date[d].append(reg)

        for d in sorted(dates_in_order):
            cumulative_day = 0.0
            for reg in regs_by_date[d]:
                p = float(reg.get("pontos", 0.0))
                before = cumulative_day
                after = cumulative_day + p
                if after <= meta:
                    used = 0.0
                else:
                    part_before_meta = max(0.0, meta - before)
                    extra_from_reg = p - part_before_meta
                    used = min(extra_from_reg, extras_remaining)
                    extras_remaining -= used
                    if extras_remaining < 0:
                        extras_remaining = 0.0
                reg["usou_extras"] = round_points(used)
                cumulative_day = after

        week["extras"] = round_points(extras_remaining)
        new_weeks.append(week)

    st.session_state.pontos_semana = new_weeks
    hoje = datetime.date.today()
    total_today = sum(float(r.get("pontos", 0.0)) for r in st.session_state.consumo_historico if r.get("data") == hoje)
    st.session_state.consumo_diario = total_today
    st.session_state.extras = st.session_state.pontos_semana[-1]["extras"] if st.session_state.pontos_semana else 36.0
    persist_all()


# -----------------------------
# NAVEGAÇÃO (botões laterais)
# -----------------------------
st.sidebar.title("📋 Menu")

menu_itens = [
    ("🏠 Dashboard", "🏠 Dashboard"),
    ("🍴 Registrar Consumo", "🍴 Registrar consumo"),
    ("⚖️ Registrar Peso", "⚖️ Registrar peso"),
    ("📂 Importar Alimentos", "📂 Importar planilha de alimentos"),
    ("➕ Cadastrar Alimento", "➕ Cadastrar novo alimento"),
    ("🔍 Consultar Alimento", "🔍 Consultar alimento"),
    ("🏃 Atividades Físicas", "🏃 Atividades Físicas"),
    ("📊 Históricos Acumulados", "📊 Históricos Acumulados"),  # nova opção adicionada
    ("🔄 Resetar Semana", "resetar_semana"),
    ("🚪 Sair", "🚪 Sair"),
]

for label, key in menu_itens:
    if st.sidebar.button(label, key=f"sidebtn_{label}", use_container_width=True):
        st.session_state.menu = key


        # -----------------------------
        # AÇÃO RESETAR SEMANA (dados do usuário)
        # -----------------------------
        if key == "resetar_semana":
            hoje = datetime.date.today()
            semana_atual = hoje.isocalendar()[1]

            st.session_state.pontos_semana = [
                w for w in st.session_state.pontos_semana if w.get("semana") != semana_atual
            ] if "pontos_semana" in st.session_state else []

            st.session_state.pontos_semana.append({
                "semana": semana_atual,
                "pontos": [],
                "extras": 36.0
            })

            st.session_state.extras = 36.0
            st.session_state.consumo_diario = 0.0

            if "consumo_historico" in st.session_state:
                st.session_state.consumo_historico = [
                    r for r in st.session_state.consumo_historico
                    if r.get("data").isocalendar()[1] != semana_atual
                ]

            if "persist_all" in globals():
                persist_all()

            st.sidebar.success(f"✅ Semana {semana_atual} resetada com sucesso!")

        # -----------------------------
        # AÇÃO SAIR (logout) - CORRIGIDA
        # -----------------------------
        elif key == "🚪 Sair":
            # Apenas desloga o usuário, sem apagar referência dele
            st.session_state.logged_in = False

            # ❌ NÃO apaga mais o current_user
            # st.session_state.current_user = ""

            # Remove apenas dados voláteis da sessão
            private_keys = [
                "peso", "datas_peso", "consumo_historico",
                "pontos_semana", "consumo_diario", "extras",
                "activities"
            ]
            for k in private_keys:
                if k in st.session_state:
                    del st.session_state[k]

            # Mantém alimentos globais intactos
            # st.session_state.alimentos continua disponível

            # Força recarregamento seguro
            try:
                st.experimental_rerun()
            except Exception:
                st.stop()  # fallback seguro

# -----------------------------
# CADASTRAR ALIMENTO AJUSTADO
# -----------------------------
def cadastrar_alimento():
    st.header("➕ Cadastrar Alimento")
    
    nome = st.text_input("Nome do alimento")
    porcao_in = st.text_input("Porção (g) — ex: 20 ou 20g ou 120", value="100")
    calorias = st.number_input("Calorias", min_value=0.0, step=0.1)
    carbo = st.number_input("Carboidratos (g)", min_value=0.0, step=0.1)
    gordura = st.number_input("Gordura (g)", min_value=0.0, step=0.1)
    saturada = st.number_input("Gordura Saturada (g)", min_value=0.0, step=0.1)
    fibra = st.number_input("Fibra (g)", min_value=0.0, step=0.1)
    acucar = st.number_input("Açúcar (g)", min_value=0.0, step=0.1)
    proteina = st.number_input("Proteína (g)", min_value=0.0, step=0.1)
    sodio_mg = st.number_input("Sódio (mg)", min_value=0.0, step=1.0)
    
    zero_pontos = st.checkbox("Este alimento tem 0 pontos?", key="cad_zero_points")
    
    if st.button("Cadastrar"):
        if not nome.strip():
            st.error("Informe o nome do alimento!")
            return
        
        try:
            porcao = safe_parse_porçao(porcao_in)
        except Exception as e:
            st.error(f"Erro ao interpretar a porção: {e}")
            return

        alimento = {
            "Nome": nome.strip(),
            "Porcao": porcao,
            "Calorias": round(calorias, 2),
            "Gordura": round(gordura, 2),
            "Saturada": round(saturada, 2),
            "Carbo": round(carbo, 2),
            "Fibra": round(fibra, 2),
            "Açúcar": round(acucar, 2),
            "Proteina": round(proteina, 2),
            "Sodio_mg": round(sodio_mg, 2),
            "ZeroPontos": zero_pontos
        }

        # Calcula pontos
        alimento["Pontos"] = calcular_pontos(alimento)

        # Adiciona ao session_state e salva no JSON global
        if "alimentos" not in st.session_state:
            st.session_state.alimentos = []
        st.session_state.alimentos.append(alimento)
        persist_all()  # salva globalmente

        st.success(f"Alimento '{nome}' cadastrado com sucesso! Pontos: {alimento['Pontos']}")

        # Atualiza UI imediatamente
        try:
            rerun_streamlit()
        except Exception:
            st.stop()


# -----------------------------
# IMPORTAR PLANILHA DE ALIMENTOS AJUSTADO
# -----------------------------
def importar_planilha():
    st.header("📂 Importar Alimentos")
    uploaded_file = st.file_uploader("Escolha sua planilha (.xlsx ou .csv)", type=["xlsx", "csv"], key="uploader_import")
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            alimentos_novos = []
            for _, row in df.iterrows():
                def g(col_options, default=0):
                    for c in col_options:
                        if c in row.index:
                            return row.get(c)
                    return default

                nome = g(["nome", "Nome", "NAME"], "Alimento sem nome")
                porc_val = g(["porcao", "Porcao", "Porção", "porção"], 100)
                calorias = float(g(["calorias", "Calorias"], 0) or 0)
                carbo = float(g(["carbo", "Carbo", "carboidratos", "Carboidratos"], 0) or 0)
                gordura = float(g(["gordura", "Gordura"], 0) or 0)
                saturada = float(g(["saturada", "Saturada"], 0) or 0)
                fibra = float(g(["fibra", "Fibra"], 0) or 0)
                acucar = float(g(["açúcar", "Acúcar", "Acucar", "acucar"], 0) or 0)
                proteina = float(g(["proteina", "Proteína", "Proteínas"], 0) or 0)
                sodio_mg = float(g(["sodio_mg", "Sodio_mg", "sódio_mg", "Sódio_mg"], 0) or 0)

                try:
                    porcao = safe_parse_porçao(porc_val)
                except Exception:
                    porcao = 100.0

                zero_ponto = str(g(["Zero Ponto", "ZeroPonto", "zeroponto"], "não")).strip().lower() == "sim"

                alimento = {
                    "Nome": str(nome),
                    "Porcao": porcao,
                    "Calorias": round(calorias, 2),
                    "Gordura": round(gordura, 2),
                    "Saturada": round(saturada, 2),
                    "Carbo": round(carbo, 2),
                    "Fibra": round(fibra, 2),
                    "Açúcar": round(acucar, 2),
                    "Proteina": round(proteina, 2),
                    "Sodio_mg": round(sodio_mg, 2),
                    "ZeroPontos": zero_ponto,
                    "Pontos": 0  # inicial, será calculado
                }

                alimento["Pontos"] = calcular_pontos(alimento)
                alimentos_novos.append(alimento)

            if "alimentos" not in st.session_state:
                st.session_state.alimentos = []

            st.session_state.alimentos.extend(alimentos_novos)
            persist_all()

            st.success(f"📂 Importadas {len(alimentos_novos)} linhas. Total agora: {len(st.session_state.alimentos)} alimentos.")
            try:
                rerun_streamlit()
            except Exception:
                st.stop()

        except Exception as e:
            st.error(f"Erro ao importar planilha: {e}\n(Se for .xlsx, instale openpyxl: pip install openpyxl)")

# -----------------------------
# FUNÇÃO REGISTRAR CONSUMO (REVISADA)
# -----------------------------
def registrar_consumo():
    st.header("🍴 Registrar Consumo")

    if not st.session_state.alimentos:
        st.warning("Nenhum alimento cadastrado ainda.")
        return

    # Seleção do alimento em ordem alfabética
    nomes = sorted([a["Nome"] for a in st.session_state.alimentos])
    escolha = st.selectbox("Escolha o alimento:", nomes, key="consumo_select")
    alimento = next((a for a in st.session_state.alimentos if a["Nome"] == escolha), None)
    if alimento is None:
        st.error("Alimento não encontrado.")
        return

    porcao_ref = float(alimento.get("Porcao", 100.0))
    pontos_por_porcao = round_points(alimento.get("Pontos", 0.0))
    st.markdown(f"**Porção referência:** {porcao_ref} g — Pontos (por porção): **{pontos_por_porcao}**")

    # Inicializa flags e listas
    if "mostrar_historico_consumo" not in st.session_state:
        st.session_state.mostrar_historico_consumo = False
    if "consumo_historico" not in st.session_state:
        st.session_state.consumo_historico = []

    # Formulário para registrar quantidade
    with st.form("form_reg_consumo", clear_on_submit=False):
        quantidade = st.number_input(
            f"Quantidade consumida em gramas (porção {porcao_ref} g):",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            key="reg_quant"
        )
        submitted = st.form_submit_button("Registrar consumo")

        if submitted:
            pontos_registrados = 0 if alimento.get("ZeroPontos", False) else round_points(
                float(alimento.get("Pontos", 0.0)) * (quantidade / porcao_ref if porcao_ref > 0 else 0.0)
            )

            registro = {
                "tipo": "consumo",
                "data": datetime.date.today(),
                "nome": escolha,
                "quantidade": float(quantidade),
                "pontos": pontos_registrados,
                "usou_extras": 0.0
            }
            st.session_state.consumo_historico.append(registro)

            # Recalcula pontos semanais e persiste
            rebuild_pontos_semana_from_history()
            persist_all()
            st.success(
                f"🍴 Registrado {quantidade:.2f}g de {escolha}. "
                f"Pontos: {pontos_registrados:.2f}. Total hoje: {st.session_state.consumo_diario:.2f}"
            )

            st.session_state.mostrar_historico_consumo = True
            try:
                rerun_streamlit()
            except Exception:
                st.stop()

    # Histórico com opções de editar/excluir
    with st.expander("### Histórico de Consumo (últimos registros)", expanded=st.session_state.mostrar_historico_consumo):
        if not st.session_state.consumo_historico:
            st.info("Nenhum consumo registrado ainda.")
        else:
            for idx in range(len(st.session_state.consumo_historico) - 1, -1, -1):
                reg = st.session_state.consumo_historico[idx]
                data = reg["data"]
                dia_sem = weekday_name_br(data) if isinstance(data, datetime.date) else ""
                display = f"{data.strftime('%d/%m/%Y')} ({dia_sem}): {reg['nome']} — {reg['quantidade']:.2f} g — {reg['pontos']:.2f} pts"
                if reg.get("usou_extras", 0.0):
                    display += f" — usou extras: {reg.get('usou_extras',0.0):.2f} pts"

                cols = st.columns([6, 1, 1])
                cols[0].write(display)

                # Editar registro
                if cols[1].button("Editar", key=f"edit_cons_{idx}"):
                    edit_key_q = f"edit_q_{idx}"
                    save_key = f"save_cons_{idx}"
                    with st.expander(f"Editar registro #{idx}", expanded=True):
                        new_q = st.number_input(
                            "Quantidade (g):", min_value=0.0, step=1.0,
                            value=reg["quantidade"], key=edit_key_q
                        )
                        alimento_ref = next((a for a in st.session_state.alimentos if a["Nome"] == reg["nome"]), None)
                        new_p = reg["pontos"]
                        if alimento_ref:
                            porc_ref = float(alimento_ref.get("Porcao", 100.0))
                            new_p = round_points(float(alimento_ref.get("Pontos", 0.0)) * (new_q / porc_ref if porc_ref > 0 else 0.0))

                        if st.button("Salvar alterações", key=save_key):
                            reg["quantidade"] = float(new_q)
                            reg["pontos"] = new_p
                            rebuild_pontos_semana_from_history()
                            persist_all()
                            st.success("Registro atualizado!")
                            rerun_streamlit()

                # Excluir registro
                if cols[2].button("Excluir", key=f"del_cons_{idx}"):
                    st.session_state.consumo_historico.pop(idx)
                    rebuild_pontos_semana_from_history()
                    persist_all()
                    st.success("Registro excluído.")
                    rerun_streamlit()

# -----------------------------
# FUNÇÃO CALCULAR META DIÁRIA
# -----------------------------
def calcular_meta_diaria(sexo, idade, peso, altura, objetivo, nivel_atividade):
    """
    Fórmula simplificada baseada em sexo, idade, peso, altura, objetivo e atividade.
    Essa fórmula pode ser adaptada de acordo com o modelo oficial do WW.
    """

    # Valores base por sexo
    if sexo.lower().startswith("m"):  # masculino
        base = 30
    else:  # feminino ou outros
        base = 27

    # Ajustes por idade
    if idade < 30:
        base += 2
    elif idade > 60:
        base -= 2

    # Ajustes por peso
    if peso < 60:
        base -= 1
    elif peso > 100:
        base += 2

    # Ajustes por altura
    if altura > 1.80:
        base += 1
    elif altura < 1.60:
        base -= 1

    # Ajustes por objetivo
    if objetivo == "emagrecimento":
        base -= 2
    elif objetivo == "manutenção":
        base += 0
    elif objetivo == "ganho":
        base += 2

    # Ajustes por nível de atividade
    if nivel_atividade == "sedentário":
        base -= 1
    elif nivel_atividade == "Moderado":
        base += 2
    elif nivel_atividade == "Intenso":
        base += 3

    return max(18, int(base))  # nunca abaixo de 18 pontos

# -----------------------------
# FUNÇÃO REGISTRAR PESO COMPLETA (AJUSTADA)
# -----------------------------
def registrar_peso():
    st.header("⚖️ Registrar Peso")

    # Inicializa flag
    if "mostrar_historico_peso" not in st.session_state:
        st.session_state.mostrar_historico_peso = False

    # Garante que campos do perfil existem no session_state
    for campo, valor in {
        "sexo": "feminino",
        "idade": 30,
        "altura": 1.70,
        "objetivo": "manutenção",
        "nivel_atividade": "sedentário"
    }.items():
        if campo not in st.session_state:
            st.session_state[campo] = valor

    # Formulário para registrar peso
    with st.form("form_peso"):
        peso_novo = st.number_input(
            "Informe seu peso (kg):",
            min_value=0.0,
            step=0.1,
            format="%.2f",
            key="input_peso_reg"
        )
        submitted = st.form_submit_button("Registrar peso")

        if submitted:
            # 🔹 Registra no histórico acumulado
            st.session_state.historico_acumulado.append({
                "tipo": "peso",
                "data": datetime.date.today().isoformat(),
                "valor": float(peso_novo)
            })

            # Calcula meta diária automaticamente
            st.session_state.meta_diaria = calcular_meta_diaria(
                sexo=st.session_state.sexo,
                idade=st.session_state.idade,
                peso=peso_novo,
                altura=st.session_state.altura,
                objetivo=st.session_state.objetivo,
                nivel_atividade=st.session_state.nivel_atividade
            )

            persist_all()
            st.success(f"Peso {peso_novo:.2f} kg registrado com sucesso! Meta diária: {st.session_state.meta_diaria} pts")
            st.session_state.mostrar_historico_peso = True
            rerun_streamlit()  # força atualização dinâmica do histórico

    # -----------------------------
    # Histórico de pesos
    # -----------------------------
    historico = st.session_state.get("historico_acumulado", [])
    pesos = [r for r in historico if r["tipo"] == "peso"]

    def parse_date(d):
        if isinstance(d, datetime.date):
            return d
        try:
            return datetime.date.fromisoformat(str(d))
        except:
            return None

    with st.expander("Histórico de Pesos", expanded=st.session_state.mostrar_historico_peso):
        if not pesos:
            st.info("Nenhum peso registrado ainda.")
        else:
            for idx in range(len(pesos) - 1, -1, -1):
                reg = pesos[idx]
                dia = parse_date(reg["data"])
                peso_reg = reg["valor"]

                # Tendência
                if idx == len(pesos) - 1:  # primeiro registro da lista invertida
                    tendencia = "➖"
                else:
                    peso_ant = pesos[idx + 1]["valor"]
                    if peso_reg < peso_ant:
                        tendencia = "⬇️"
                    elif peso_reg > peso_ant:
                        tendencia = "⬆️"
                    else:
                        tendencia = "➖"

                cols = st.columns([6, 1, 1])
                data_str = dia.strftime("%d/%m/%Y") if dia else str(reg["data"])
                cols[0].write(f"{data_str}: {peso_reg:.2f} kg {tendencia}")

                # Editar peso
                if cols[1].button("Editar", key=f"edit_peso_{idx}"):
                    edit_key = f"edit_peso_input_{idx}"
                    save_key = f"save_peso_{idx}"
                    with st.expander(f"Editar registro #{idx}", expanded=True):
                        new_peso = st.number_input(
                            "Novo peso (kg):",
                            min_value=0.0,
                            step=0.1,
                            value=peso_reg,
                            key=edit_key
                        )
                        if st.button("Salvar alterações", key=save_key):
                            reg["valor"] = float(new_peso)

                            # Atualiza meta diária automaticamente
                            st.session_state.meta_diaria = calcular_meta_diaria(
                                sexo=st.session_state.sexo,
                                idade=st.session_state.idade,
                                peso=new_peso,
                                altura=st.session_state.altura,
                                objetivo=st.session_state.objetivo,
                                nivel_atividade=st.session_state.nivel_atividade
                            )

                            persist_all()
                            st.success(f"Registro atualizado para {new_peso:.2f} kg. Meta diária: {st.session_state.meta_diaria} pts")
                            rerun_streamlit()

                # Excluir peso
                if cols[2].button("❌", key=f"del_peso_{idx}"):
                    pesos.remove(reg)
                    st.session_state.historico_acumulado = [r for r in historico if r not in pesos]
                    persist_all()
                    st.success("Registro excluído.")
                    rerun_streamlit()

    # -----------------------------
    # Relatório de variáveis do perfil
    # -----------------------------
    st.subheader("📋 Relatório do Perfil")
    st.write(f"**Sexo:** {st.session_state.sexo}")
    st.write(f"**Idade:** {st.session_state.idade} anos")
    st.write(f"**Altura:** {st.session_state.altura:.2f} m")
    st.write(f"**Objetivo:** {st.session_state.objetivo}")
    st.write(f"**Nível de atividade:** {st.session_state.nivel_atividade}")
    st.write(f"**Meta diária:** {st.session_state.meta_diaria} pontos")

    # Botão para editar perfil direto daqui
    with st.expander("✏️ Editar Perfil"):
        sexo = st.selectbox("Sexo", ["feminino", "masculino"], index=0 if st.session_state.sexo == "feminino" else 1)
        idade = st.number_input("Idade:", min_value=10, max_value=120, step=1, value=st.session_state.idade)
        altura = st.number_input("Altura (m):", min_value=1.0, max_value=2.5, step=0.01, value=st.session_state.altura)
        objetivo = st.selectbox("Objetivo", ["emagrecimento", "manutenção", "ganho"], index=["emagrecimento","manutenção","ganho"].index(st.session_state.objetivo))
        nivel_atividade = st.selectbox("Nível de atividade", ["sedentário", "moderado", "ativo"], index=["sedentário","moderado","ativo"].index(st.session_state.nivel_atividade))

        if st.button("Salvar Perfil", key="salvar_perfil_inline"):
            st.session_state.sexo = sexo
            st.session_state.idade = idade
            st.session_state.altura = altura
            st.session_state.objetivo = objetivo
            st.session_state.nivel_atividade = nivel_atividade

            # Recalcula meta
            if st.session_state.peso:
                st.session_state.meta_diaria = calcular_meta_diaria(
                    sexo=st.session_state.sexo,
                    idade=st.session_state.idade,
                    peso=st.session_state.peso[-1],
                    altura=st.session_state.altura,
                    objetivo=st.session_state.objetivo,
                    nivel_atividade=st.session_state.nivel_atividade
                )

            persist_all()
            st.success("Perfil atualizado com sucesso!")
            rerun_streamlit()

# -----------------------------
# Funções utilitárias e inicialização de alimentos
# -----------------------------
import streamlit as st
import json
import re
from math import floor

DATA_FILE = "ww_data.json"

def round_points(value):
    """Arredondamento padrão (round half up)."""
    try:
        return int(float(value) + 0.5)
    except:
        return 0

def safe_parse_porçao(porc):
    """Converte entrada de porção para float (remove 'g', etc)."""
    try:
        return float(re.sub("[^0-9.]", "", str(porc)))
    except:
        return 100.0

def persist_all():
    """Salva alimentos globais no JSON."""
    if "alimentos" in st.session_state:
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(st.session_state.alimentos, f, indent=4, ensure_ascii=False)
        except Exception as e:
            st.error(f"Erro ao salvar alimentos: {e}")

def load_alimentos():
    """Carrega alimentos do JSON global para session_state."""
    if "alimentos" not in st.session_state:
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data_store = json.load(f)
                # garante que sempre seja lista
                if isinstance(data_store, list):
                    st.session_state.alimentos = data_store
                elif isinstance(data_store, dict) and "alimentos" in data_store:
                    st.session_state.alimentos = data_store["alimentos"]
                else:
                    st.session_state.alimentos = []
        except FileNotFoundError:
            st.session_state.alimentos = []
        except Exception as e:
            st.session_state.alimentos = []
            st.error(f"Erro ao carregar alimentos: {e}")

def add_alimento_session(alimento):
    """Adiciona alimento ao session_state e persiste no JSON, forçando atualização da UI."""
    if "alimentos" not in st.session_state:
        st.session_state.alimentos = []
    st.session_state.alimentos.append(alimento)
    persist_all()
    # força atualização imediata para refletir o novo alimento
    try:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        else:
            st.stop()
    except Exception:
        st.stop()

# Inicializa lista de alimentos
load_alimentos()


# -----------------------------
# FUNÇÃO PARA CALCULAR PONTOS
# -----------------------------
def calcular_pontos(alimento):
    """
    Calcula os pontos de um alimento respeitando o campo 'Zero Ponto'.
    Retorna 0 se Zero Ponto = "sim", caso contrário aplica a fórmula.
    """
    # Normaliza o campo Zero Ponto
    zero_ponto = str(alimento.get("Zero Ponto", "não")).strip().lower()
    if zero_ponto == "sim":
        return 0

    # Extrai valores nutricionais, garantindo float
    calorias = float(alimento.get("Calorias", 0.0))
    carbo = float(alimento.get("Carbo", 0.0))
    gordura = float(alimento.get("Gordura", 0.0))
    proteina = float(alimento.get("Proteina", 0.0))
    sodio_mg = float(alimento.get("Sodio_mg", 0.0))

    # Calcula pontos bruto
    pontos_raw = (calorias / 50.0) + (carbo / 10.0) + (gordura / 5.0) + (proteina / 5.0) + (sodio_mg / 100.0)
    
    # Aplica arredondamento padrão
    pontos = round_points(pontos_raw)
    return pontos

# -----------------------------
# CONSULTAR + EDITAR/EXCLUIR ALIMENTO (AJUSTADO)
# -----------------------------
def consultar_alimento():
    st.header("🔍 Consultar Alimento")

    if not st.session_state.alimentos:
        st.warning("Nenhum alimento cadastrado ainda.")
        return

    # Lista de nomes em ordem alfabética e escolha
    nomes = sorted([a["Nome"] for a in st.session_state.alimentos])
    escolha = st.selectbox("Escolha o alimento:", nomes, key="consult_select")

    # Localizar índice e objeto
    idx = next((i for i, a in enumerate(st.session_state.alimentos) if a["Nome"] == escolha), None)
    if idx is None:
        st.error("Alimento não encontrado.")
        return
    alimento = st.session_state.alimentos[idx]

    # ----- Exibição -----
    st.subheader(alimento["Nome"])
    st.markdown(f"**Porção:** {alimento.get('Porcao', 0)} g")
    col1, col2, col3 = st.columns(3)
    comp1 = ["Calorias", "Carbo", "Fibra"]
    comp2 = ["Gordura", "Saturada", "Açúcar"]
    comp3 = ["Proteina", "Sodio_mg", "Pontos"]

    for c, comps in zip([col1, col2, col3], [comp1, comp2, comp3]):
        with c:
            for j, comp in enumerate(comps):
                valor = alimento.get(comp, 0)
                if comp == "Pontos":
                    valor_display = calcular_pontos(alimento)
                    st.markdown(f"**{comp}**")
                    st.markdown(
                        f"""
                        <div style="
                            background-color: #006400;
                            color: white;
                            font-size: 20px;
                            font-weight: 700;
                            text-align:center;
                            padding:10px;
                            border-radius:6px;">
                            {valor_display:.2f}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(f"**{comp}**")
                    st.button(f"**{valor}**", key=f"{alimento['Nome']}_{comp}_{j}", disabled=True, use_container_width=True)

    st.markdown(f"**Zero Ponto:** {alimento.get('ZeroPontos', 'não')}")
    st.markdown("---")

    # ----- Botões Editar / Excluir -----
    col_edit, col_delete = st.columns([1, 1])
    with col_edit:
        if st.button("✏️ Editar este alimento", key=f"edit_btn_{idx}"):
            st.session_state[f"edit_open_{idx}"] = True
            rerun_streamlit()
    with col_delete:
        if st.button("🗑️ Excluir este alimento", key=f"del_btn_{idx}"):
            st.session_state.alimentos.pop(idx)
            persist_all()
            st.success(f"Alimento '{escolha}' removido com sucesso!")
            rerun_streamlit()

    # ----- Painel de Edição -----
    flag_key = f"edit_open_{idx}"
    if st.session_state.get(flag_key, False):
        st.markdown("---")
        st.subheader(f"Editar '{alimento['Nome']}'")

        col_cancel, _ = st.columns([1, 3])
        with col_cancel:
            if st.button("✖️ Cancelar edição", key=f"cancel_edit_{idx}"):
                st.session_state[flag_key] = False
                rerun_streamlit()

        form_key = f"form_edit_{idx}"
        with st.form(form_key, clear_on_submit=False):
            nome_novo = st.text_input("Nome do alimento:", value=alimento.get("Nome", ""), key=f"edit_name_{idx}")
            porcao_novo = st.text_input("Porção (g):", value=str(alimento.get("Porcao", "")), key=f"edit_porc_{idx}")
            calorias_novo = st.number_input("Calorias (kcal):", min_value=0.0, value=float(alimento.get("Calorias", 0.0)), step=0.1, key=f"edit_cal_{idx}")
            carbo_novo = st.number_input("Carboidratos (g):", min_value=0.0, value=float(alimento.get("Carbo", 0.0)), step=0.1, key=f"edit_car_{idx}")
            gordura_novo = st.number_input("Gordura (g):", min_value=0.0, value=float(alimento.get("Gordura", 0.0)), step=0.1, key=f"edit_gor_{idx}")
            saturada_novo = st.number_input("Gordura Saturada (g):", min_value=0.0, value=float(alimento.get("Saturada", 0.0)), step=0.1, key=f"edit_sat_{idx}")
            fibra_novo = st.number_input("Fibra (g):", min_value=0.0, value=float(alimento.get("Fibra", 0.0)), step=0.1, key=f"edit_fib_{idx}")
            acucar_novo = st.number_input("Açúcar (g):", min_value=0.0, value=float(alimento.get("Açúcar", 0.0)), step=0.1, key=f"edit_acu_{idx}")
            proteina_novo = st.number_input("Proteína (g):", min_value=0.0, value=float(alimento.get("Proteina", 0.0)), step=0.1, key=f"edit_pro_{idx}")
            sodio_novo = st.number_input("Sódio (mg):", min_value=0.0, value=float(alimento.get("Sodio_mg", 0.0)), step=1.0, key=f"edit_sod_{idx}")
            zero_ponto_novo = st.selectbox(
                "Zero Ponto:", 
                options=["não", "sim"], 
                index=0 if str(alimento.get("ZeroPontos", "não")).strip().lower() == "não" else 1,
                key=f"edit_zero_{idx}"
            )

            salvar = st.form_submit_button("💾 Salvar alterações")
            if salvar:
                porcao_val = safe_parse_porçao(porcao_novo)
                # Atualiza alimento antes de recalcular pontos
                alimento.update({
                    "Nome": nome_novo.strip(),
                    "Porcao": porcao_val,
                    "Calorias": round(calorias_novo, 2),
                    "Carbo": round(carbo_novo, 2),
                    "Gordura": round(gordura_novo, 2),
                    "Saturada": round(saturada_novo, 2),
                    "Fibra": round(fibra_novo, 2),
                    "Açúcar": round(acucar_novo, 2),
                    "Proteina": round(proteina_novo, 2),
                    "Sodio_mg": round(sodio_novo, 2),
                    "ZeroPontos": zero_ponto_novo
                })

                # Recalcula pontos
                alimento["Pontos"] = calcular_pontos(alimento)
                persist_all()
                st.session_state[flag_key] = False
                st.success(f"Alimento '{nome_novo}' atualizado com sucesso! Pontos: {alimento['Pontos']}")
                rerun_streamlit()

# -----------------------------
# DASHBOARD PRINCIPAL COMPLETO COM HISTÓRICOS E GRÁFICOS
# -----------------------------
import datetime
import plotly.graph_objects as go
import numpy as np
import pandas as pd

if st.session_state.menu == "🏠 Dashboard":
    st.markdown("<h1 style='text-align: center; color: #2c3e50;'>🍏 Vigilantes do Peso Brasil</h1>", unsafe_allow_html=True)

    # Primeiro login ou perfil incompleto
    if st.session_state.get("primeiro_login", False) or perfil_incompleto():
        completar_perfil()
        st.stop()

    # -----------------------------
    # Recalcular métricas a partir do histórico acumulado
    # -----------------------------
    historico = st.session_state.get("historico_acumulado", [])

    def parse_date(d):
        if isinstance(d, datetime.date):
            return d
        try:
            return datetime.date.fromisoformat(str(d))
        except:
            return None

    hoje = datetime.date.today()
    semana_atual = iso_week_number(hoje)

    # Consumo diário
    consumo_hoje = sum(
        r.get("pontos", 0)
        for r in historico
        if r["tipo"] == "consumo" and parse_date(r["data"]) == hoje
    )

    # Extras semanais usados
    consumo_semana_extras = [
        r for r in historico
        if r["tipo"] == "consumo"
        and parse_date(r["data"])
        and iso_week_number(parse_date(r["data"])) == semana_atual
        and r.get("usou_extras", 0) > 0
    ]
    extras_usados = sum(r.get("usou_extras", 0) for r in consumo_semana_extras)

    # Atividades da semana
    atividades_semana = [
        r for r in historico
        if r["tipo"] == "atividade"
        and parse_date(r["data"])
        and iso_week_number(parse_date(r["data"])) == semana_atual
    ]
    pontos_atividade_semana = sum(r.get("pontos", 0) for r in atividades_semana)

    # Peso atual
    pesos = [r for r in historico if r["tipo"] == "peso"]
    peso_atual = pesos[-1]["valor"] if pesos else 0.0

    # Banco de extras disponível
    extras_base = 36.0
    extras_disponiveis = extras_base + pontos_atividade_semana - extras_usados

    st.markdown(
        f"<div style='background-color:#dff9fb;padding:15px;border-radius:10px;text-align:center;font-size:22px;'>"
        f"<b>Pontos consumidos hoje: {consumo_hoje:.2f} / {st.session_state.meta_diaria} | "
        f"Extras disponíveis (semana): {extras_disponiveis:.2f} | Peso atual: {peso_atual:.2f} kg</b>"
        f"</div>", unsafe_allow_html=True
    )

    # -----------------------------
    # Gráficos principais
    # -----------------------------
    col1, col2, col3 = st.columns(3, gap="large")
    graf_height = 430

    # Consumo Diário
    with col1:
        meta_diaria = st.session_state.meta_diaria
        fig1 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=consumo_hoje,
            number={'suffix': f" / {meta_diaria}"},
            gauge={'axis': {'range': [0, meta_diaria]},
                   'bar': {'color': "#e74c3c"},
                   'steps': [
                       {'range': [0, meta_diaria * 0.7], 'color': "#2ecc71"},
                       {'range': [meta_diaria * 0.7, meta_diaria], 'color': "#f1c40f"}
                   ]},
            title={'text': "Pontos Consumidos"}
        ))
        fig1.update_layout(height=graf_height)
        st.plotly_chart(fig1, use_container_width=True)

    # Pontos Extras
    with col2:
        excesso_diario = max(0, consumo_hoje - st.session_state.meta_diaria)
        total_banco = extras_base + pontos_atividade_semana
        fig2 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=excesso_diario,
            number={'suffix': f" / {total_banco:.0f}"},
            gauge={'axis': {'range': [0, total_banco]},
                   'bar': {'color': "#006400"},
                   'steps': [
                       {'range': [0, total_banco/3], 'color': "#e74c3c"},
                       {'range': [total_banco/3, 2*total_banco/3], 'color': "#f1c40f"},
                       {'range': [2*total_banco/3, total_banco], 'color': "#2ecc71"}
                   ]},
            title={'text': "⭐ Pontos Semanais Extras"}
        ))
        fig2.update_layout(height=graf_height)
        st.plotly_chart(fig2, use_container_width=True)

    # Peso Atual
    with col3:
        if len(pesos) <= 1:
            cor_gauge = "blue"
            tendencia = "➖"
        else:
            if pesos[-1]["valor"] < pesos[-2]["valor"]:
                cor_gauge = "green"
                tendencia = "⬇️"
            elif pesos[-1]["valor"] > pesos[-2]["valor"]:
                cor_gauge = "orange"
                tendencia = "⬆️"
            else:
                cor_gauge = "blue"
                tendencia = "➖"

        min_axis = min(r["valor"] for r in pesos) - 5 if pesos else 0
        max_axis = max(r["valor"] for r in pesos) + 5 if pesos else 100
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=peso_atual,
            gauge={'axis': {'range': [min_axis, max_axis]},
                   'bar': {'color': cor_gauge}},
            title={'text': f"Peso Atual {tendencia}"}
        ))
        fig_gauge.update_layout(height=graf_height)
        st.plotly_chart(fig_gauge, use_container_width=True)

# -----------------------------
# FUNÇÃO PARA EXIBIR HISTÓRICOS NO DASHBOARD
# -----------------------------
def exibir_historicos_dashboard():
    col_hist1, col_hist2, col_hist3 = st.columns(3)
    historico = st.session_state.get("historico_acumulado", [])

    def parse_date(d):
        if isinstance(d, datetime.date):
            return d
        try:
            return datetime.date.fromisoformat(str(d))
        except:
            return None

    # -----------------------------
    # Pontos Semanais / Histórico de Consumo
    # -----------------------------
    with col_hist1:
        st.markdown("### 📊 Pontos / Consumo Diário")
        
        # Pega todos os registros de consumo do histórico acumulado
        consumos = [r for r in historico if r["tipo"] == "consumo"]

        # Inclui também registros da semana atual (pontos_semana) sem duplicar
        for semana in st.session_state.pontos_semana:
            for reg in semana.get("pontos", []):
                reg_copy = reg.copy()
                reg_copy["tipo"] = "consumo"
                if not any(
                    r["data"] == reg_copy["data"] and r["nome"] == reg_copy["nome"] for r in consumos
                ):
                    consumos.append(reg_copy)

        if consumos:
            for reg in sorted(consumos, key=lambda x: parse_date(x["data"])):
                dia = parse_date(reg["data"])
                dia_str = dia.strftime("%d/%m/%Y") if dia else str(reg["data"])
                dia_sem = weekday_name_br(dia) if dia else ""
                st.markdown(
                    f"<div style='padding:10px; border:1px solid #f39c12; border-radius:5px; margin-bottom:5px;'>"
                    f"{dia_str} ({dia_sem}): {reg['nome']} {reg.get('quantidade',0):.2f} g "
                    f"<span style='color:#1f3c88'>({reg.get('pontos',0):.2f} pts)</span>"
                    f" — usou extras: ({reg.get('usou_extras',0):.2f} pts)"
                    f"</div>", unsafe_allow_html=True
                )
        else:
            st.write(" - (sem registros)")

    # -----------------------------
    # Histórico de Atividades
    # -----------------------------
    with col_hist2:
        st.markdown("### 🏃 Histórico de Atividades Físicas")
        acts = [r for r in historico if r["tipo"] == "atividade"]
        if acts:
            for reg in sorted(acts, key=lambda x: parse_date(x["data"])):
                dia = parse_date(reg["data"])
                dia_str = dia.strftime("%d/%m/%Y") if dia else str(reg["data"])
                dia_sem = weekday_name_br(dia) if dia else ""
                st.markdown(
                    f"<div style='padding:10px; border:1px solid #1abc9c; border-radius:5px; margin-bottom:5px;'>"
                    f"{dia_str} ({dia_sem}): {reg['tipo_atividade']} - {reg.get('minutos',0):.2f} min "
                    f"<span style='color:#1f3c88'>({reg.get('pontos',0):.2f} pts)</span>"
                    f"</div>", unsafe_allow_html=True
                )
        else:
            st.info("Nenhuma atividade registrada ainda.")

    # -----------------------------
    # Histórico de Peso
    # -----------------------------
    with col_hist3:
        st.markdown("### ⚖️ Histórico de Peso")
        pesos = [r for r in historico if r["tipo"] == "peso"]
        for i, reg in enumerate(pesos):
            dia = parse_date(reg["data"])
            tendencia = "➖"
            if i > 0:
                if reg["valor"] < pesos[i-1]["valor"]:
                    tendencia = "⬇️"
                elif reg["valor"] > pesos[i-1]["valor"]:
                    tendencia = "⬆️"
            dia_str = dia.strftime("%d/%m/%Y") if dia else str(reg["data"])
            dia_sem = weekday_name_br(dia) if dia else ""
            st.markdown(
                f"<div style='padding:10px; border:1px solid #3498db; border-radius:5px; margin-bottom:5px;'>"
                f"{dia_str} ({dia_sem}): {reg['valor']:.2f} kg {tendencia}</div>",
                unsafe_allow_html=True
            )

# -----------------------------
# Chamada somente no Dashboard
# -----------------------------
if st.session_state.menu == "🏠 Dashboard":
    exibir_historicos_dashboard()


    # -----------------------------
    # Tendência de Peso (linha)
    # -----------------------------
    if st.session_state.peso and st.session_state.datas_peso:
        if len(st.session_state.peso) == len(st.session_state.datas_peso):
            df_peso = pd.DataFrame({"Data": st.session_state.datas_peso, "Peso": st.session_state.peso})
            df_peso["Data_dt"] = pd.to_datetime(df_peso["Data"])
            if len(df_peso) >= 2:
                x_ord = np.array([d.toordinal() for d in df_peso["Data_dt"]])
                y = np.array(df_peso["Peso"])
                m, b = np.polyfit(x_ord, y, 1)
                y_trend = m*x_ord + b
                mode_plot = "lines+markers"
            else:
                y_trend = np.array(df_peso["Peso"])
                mode_plot = "markers"
            fig_line = go.Figure(go.Scatter(x=df_peso["Data_dt"].tolist(), y=y_trend.tolist(), mode=mode_plot, line=dict(color="#8e44ad", width=3)))
            fig_line.update_layout(yaxis_title="Peso (kg)", xaxis_title="Data", template="plotly_white", height=400)
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.warning("Erro: número de datas e pesos não coincidem.")
    else:
        st.info("Registre pelo menos um peso para ver a tendência.")

# -----------------------------
# FUNÇÃO DE ATIVIDADES FÍSICAS
# -----------------------------
def registrar_atividade_fisica():
    st.markdown("### 🏃 Registrar Atividade Física")
    
    # Inicializa flag
    if "mostrar_historico_atividade" not in st.session_state:
        st.session_state.mostrar_historico_atividade = False

    # Pontos base por atividade (para 15 min)
    pontos_base = {
        "Caminhada": 1,
        "Corrida": 2,
        "Bicicleta": 2,   # ajustado para 2 pontos a cada 15 min
        "Musculação": 2   # substitui "Academia" por "Musculação"
    }
    minutos_base = 15  # referência de 15 min

    # Formulário para registrar atividade
    with st.form("form_atividade", clear_on_submit=True):
        tipo = st.selectbox("Tipo de atividade", list(pontos_base.keys()))
        minutos = st.number_input("Duração (minutos)", min_value=1, max_value=300, value=15)
        data_atividade = st.date_input("Data da atividade", value=datetime.date.today())
        submitted = st.form_submit_button("Registrar Atividade")

        if submitted:
            # Calcula pontos automaticamente pela regra de 3 com arredondamento half-up
            pontos = round_points((minutos / minutos_base) * pontos_base.get(tipo, 1))

            # 🔹 Adiciona no histórico acumulado
            st.session_state.historico_acumulado.append({
                "tipo": "atividade",
                "data": data_atividade.isoformat(),
                "tipo_atividade": tipo,
                "minutos": minutos,
                "pontos": pontos
            })
            persist_all()
            st.success(f"✅ Atividade '{tipo}' registrada! ({pontos} pts)")
            st.session_state.mostrar_historico_atividade = True
            st.stop()

    # -----------------------------
    # Histórico de atividades
    # -----------------------------
    historico = st.session_state.get("historico_acumulado", [])

    def parse_date(d):
        if isinstance(d, datetime.date):
            return d
        try:
            return datetime.date.fromisoformat(str(d))
        except:
            return None

    atividades = [r for r in historico if r["tipo"] == "atividade"]

    with st.expander("Histórico de Atividades", expanded=st.session_state.mostrar_historico_atividade):
        if not atividades:
            st.info("Nenhuma atividade registrada ainda.")
        else:
            for idx, reg in enumerate(sorted(atividades, key=lambda x: parse_date(x["data"]), reverse=True)):
                dia = parse_date(reg["data"])
                dia_str = dia.strftime("%d/%m/%Y") if dia else str(reg["data"])
                dia_sem = weekday_name_br(dia) if dia else ""
                col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
                col1.write(f"{reg['tipo_atividade']} - {reg['minutos']} min")
                col2.write(f"{reg['pontos']} pts")

                # Botão Editar
                if col3.button("✏️", key=f"edit_{idx}"):
                    edit_key_tipo = f"edit_tipo_{idx}"
                    edit_key_min = f"edit_min_{idx}"
                    with st.expander(f"Editar atividade #{idx}", expanded=True):
                        novo_tipo = st.selectbox(
                            "Tipo de atividade",
                            list(pontos_base.keys()),
                            index=list(pontos_base.keys()).index(reg["tipo_atividade"]),
                            key=edit_key_tipo
                        )
                        novo_min = st.number_input(
                            "Duração (minutos)",
                            min_value=1,
                            max_value=300,
                            value=reg["minutos"],
                            key=edit_key_min
                        )
                        if st.button("Salvar alterações", key=f"save_{idx}"):
                            novo_pts = round_points((novo_min / minutos_base) * pontos_base.get(novo_tipo, 1))
                            reg.update({
                                "tipo_atividade": novo_tipo,
                                "minutos": novo_min,
                                "pontos": novo_pts
                            })
                            persist_all()
                            st.success("Atividade atualizada!")
                            st.stop()

                # Botão Excluir
                if col4.button("❌", key=f"del_{idx}"):
                    historico.remove(reg)
                    persist_all()
                    st.success("Atividade removida.")
                    st.stop()


# -----------------------------
# Função Históricos Acumulados (ajustada)
# -----------------------------
import streamlit as st
import datetime
import base64

# -----------------------------
# Função para gerar HTML do relatório (para download)
# -----------------------------
def gerar_html_relatorio(consumo_filtrado, atividades_filtrado, peso_filtrado, pontos_semana, data_inicio, data_fim, incluir_consumo=True, incluir_atividades=True):
    css = """
    <style>
        table {border-collapse: collapse; width: 100%;}
        th {background-color: #2ecc71; color: white; padding: 8px; text-align: left;}
        td {border: 1px solid #ddd; padding: 8px;}
        tr:nth-child(even){background-color: #f2f2f2;}
        h1, h2 {color: #2c3e50;}
    </style>
    """
    html = f"<html><head>{css}</head><body>"
    html += f"<h1>Histórico Acumulado - Vigilantes do Peso</h1>"
    html += f"<p>Período: {data_inicio} → {data_fim}</p>"

    # Pontos Semanais
    html += "<h2>Pontos Semanais</h2><table><tr><th>Semana</th><th>Data</th><th>Nome</th><th>Quantidade</th><th>Pontos</th><th>Extras usados</th></tr>"
    for w in pontos_semana:
        for r in w.get("pontos", []):
            if data_inicio <= r["data"] <= data_fim:
                html += f"<tr><td>{w['semana']}</td><td>{r['data'].strftime('%d/%m/%Y')}</td><td>{r['nome']}</td><td>{r['quantidade']}</td><td>{r['pontos']}</td><td>{r.get('usou_extras',0)}</td></tr>"
    html += "</table>"

    # Consumo Diário
    if incluir_consumo:
        html += "<h2>Consumo Diário</h2><table><tr><th>Data</th><th>Alimento</th><th>Quantidade (g)</th><th>Pontos</th><th>Extras usados</th></tr>"
        for r in consumo_filtrado:
            html += f"<tr><td>{r['data'].strftime('%d/%m/%Y')}</td><td>{r['nome']}</td><td>{r['quantidade']}</td><td>{r['pontos']}</td><td>{r.get('usou_extras',0)}</td></tr>"
        html += "</table>"

    # Atividades Físicas
    if incluir_atividades:
        html += "<h2>Atividades Físicas</h2><table><tr><th>Data</th><th>Tipo de Atividade</th><th>Duração (min)</th><th>Pontos</th></tr>"
        for d, lst in sorted(atividades_filtrado.items()):
            for a in lst:
                html += f"<tr><td>{d.strftime('%d/%m/%Y')}</td><td>{a['tipo']}</td><td>{a['minutos']}</td><td>{a['pontos']}</td></tr>"
        html += "</table>"

    # Peso
    html += "<h2>Peso</h2><table><tr><th>Data</th><th>Peso (kg)</th></tr>"
    for p,d in peso_filtrado:
        html += f"<tr><td>{d.strftime('%d/%m/%Y')}</td><td>{p:.2f}</td></tr>"
    html += "</table>"

    html += "</body></html>"
    return html

# -----------------------------
# Função para criar botão de download
# -----------------------------
def botao_download_html(html_content):
    b64 = base64.b64encode(html_content.encode()).decode()
    st.markdown(
        f'<a href="data:text/html;base64,{b64}" download="historico_acumulado.html">'
        f'<button style="padding:10px 20px; font-size:16px; background-color:#2ecc71; color:white; border:none; border-radius:5px; cursor:pointer;">Gerar Relatório</button>'
        f'</a>',
        unsafe_allow_html=True
    )

# -----------------------------
# Página Históricos Acumulados
# -----------------------------
def historico_acumulado_page():
    st.header("📅 Seleção de Período para Histórico Acumulado")
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        data_inicio = st.date_input(
            "Data Início", value=datetime.date.today() - datetime.timedelta(days=30)
        )
    with col2:
        data_fim = st.date_input(
            "Data Fim", value=datetime.date.today()
        )
    with col3:
        gerar = st.button("📄 Aplicar Filtro")

    incluir_atividades = st.checkbox("Incluir atividades físicas", value=True)
    incluir_consumo = st.checkbox("Incluir consumo diário", value=True)

    # -----------------------------
    # Só processa quando o botão for clicado
    # -----------------------------
    if gerar:
        historico = st.session_state.get("historico_acumulado", [])

        # Normalizar datas
        def parse_date(d):
            if isinstance(d, datetime.date):
                return d
            try:
                return datetime.date.fromisoformat(str(d))
            except:
                return None

        # Filtrar dados pelo período
        consumo_filtrado = [
            r for r in historico
            if r["tipo"] == "consumo" and (parse_date(r["data"]) and data_inicio <= parse_date(r["data"]) <= data_fim)
        ]
        atividades_filtrado = [
            r for r in historico
            if r["tipo"] == "atividade" and (parse_date(r["data"]) and data_inicio <= parse_date(r["data"]) <= data_fim)
        ]
        peso_filtrado = [
            r for r in historico
            if r["tipo"] == "peso" and (parse_date(r["data"]) and data_inicio <= parse_date(r["data"]) <= data_fim)
        ]

        # Exibir relatório completo
        exibir_relatorio(
            consumo_filtrado,
            atividades_filtrado,
            peso_filtrado,
            data_inicio,
            data_fim,
            incluir_consumo,
            incluir_atividades
        )

# -----------------------------
# Função para exibir relatório
# -----------------------------
def exibir_relatorio(consumo_filtrado, atividades_filtrado, peso_filtrado, data_inicio, data_fim,
                     incluir_consumo=True, incluir_atividades=True):
    """Exibe na tela o relatório completo de consumo, atividades, peso e pontos extras"""

    # Função local para normalizar datas
    def parse_date(d):
        if isinstance(d, datetime.date):
            return d
        try:
            return datetime.date.fromisoformat(str(d))
        except Exception:
            return None

    # 🔹 Reconstruir atividades filtradas por período
    atividades_filtrado_local = []
    if incluir_atividades:
        for semana in st.session_state.pontos_semana:
            for a in semana.get("atividades", []):
                try:
                    data_atividade = (
                        datetime.date.fromisoformat(a["horario"])
                        if isinstance(a["horario"], str)
                        else a["horario"]
                    )
                except Exception:
                    continue
                if data_inicio <= data_atividade <= data_fim:
                    a_display = a.copy()
                    a_display["tipo_atividade"] = a.get("tipo", "—")
                    a_display["data"] = data_atividade
                    atividades_filtrado_local.append(a_display)

    # -----------------------------
    # Consumo Diário
    # -----------------------------
    if incluir_consumo and consumo_filtrado:
        st.markdown("### Consumo Diário")
        st.table([
            {
                "Data": parse_date(r["data"]).strftime("%d/%m/%Y"),
                "Alimento": r["nome"],
                "Quantidade (g)": r["quantidade"],
                "Pontos": r["pontos"],
                "Extras usados": r.get("usou_extras", 0)
            }
            for r in consumo_filtrado
        ])

    # -----------------------------
    # Atividades Físicas
    # -----------------------------
    if incluir_atividades and atividades_filtrado_local:
        st.markdown("### Atividades Físicas")
        st.table([
            {
                "Data": r["data"].strftime("%d/%m/%Y"),
                "Atividade": r["tipo_atividade"],
                "Minutos": r.get("minutos", 0),
                "Pontos": r.get("pontos", 0)
            }
            for r in atividades_filtrado_local
        ])

    # -----------------------------
    # Peso
    # -----------------------------
    if peso_filtrado:
        st.markdown("### Peso")
        st.table([
            {
                "Data": parse_date(r["data"]).strftime("%d/%m/%Y"),
                "Peso (kg)": r["valor"]
            }
            for r in peso_filtrado
        ])

    # -----------------------------
    # Pontos Semanais Extras
    # -----------------------------
    pontos_semanais = [
        r for r in consumo_filtrado if r.get("usou_extras", 0) > 0
    ]
    if pontos_semanais:
        st.markdown("### Pontos Semanais Extras")
        st.table([
            {
                "Data": parse_date(r["data"]).strftime("%d/%m/%Y"),
                "Nome": r["nome"],
                "Quantidade": r["quantidade"],
                "Pontos": r["pontos"],
                "Extras usados": r.get("usou_extras", 0)
            }
            for r in pontos_semanais
        ])

    # -----------------------------
    # Botão verde para baixar HTML
    # -----------------------------
    html_relatorio = gerar_html_relatorio(
        consumo_filtrado,
        atividades_filtrado_local,
        peso_filtrado,
        pontos_semanais,
        data_inicio,
        data_fim,
        incluir_consumo,
        incluir_atividades
    )
    botao_download_html(html_relatorio)

# -----------------------------
# CÁLCULO META DIÁRIA WW
# -----------------------------
def calcular_meta_diaria(peso, altura, idade, sexo, objetivo, nivel_atividade):
    """
    Retorna a meta diária de pontos do usuário (aprox. WW SmartPoints).
    Ajuste baseado na idade, sexo, peso, altura, nível de atividade e objetivo.
    """
    # Fator de sexo
    if sexo.upper() == "M":
        sexo_factor = 5
    else:
        sexo_factor = -161

    # Taxa metabólica basal (Mifflin-St Jeor)
    tmb = (10 * peso) + (6.25 * altura) - (5 * idade) + sexo_factor

    # Fator de atividade
    fatores_atividade = {
        "sedentario": 1.2,
        "leve": 1.375,
        "moderado": 1.55,
        "alto": 1.725
    }
    tdee = tmb * fatores_atividade.get(nivel_atividade.lower(), 1.2)

    # Ajuste por objetivo
    if objetivo.lower() == "perder":
        tdee -= 500  # déficit calórico padrão
    elif objetivo.lower() == "ganhar":
        tdee += 500  # superávit calórico

    # Conversão aproximada calorias → pontos WW (aprox. 1 ponto ≈ 50 kcal)
    pontos = tdee / 50.0

    # Ajuste mínimo/máximo conforme WW real (~28-30)
    pontos = max(28, min(round_points(pontos), 30))

    return pontos


# -----------------------------
# ROTAS / PAGES
# -----------------------------
if st.session_state.menu == "🏠 Dashboard":
    st.write("🏠 Dashboard principal")  # substitua pelo seu código real do dashboard

elif st.session_state.menu == "📂 Importar planilha de alimentos":
    importar_planilha()

elif st.session_state.menu == "➕ Cadastrar novo alimento":
    cadastrar_alimento()

elif st.session_state.menu == "🍴 Registrar consumo":
    registrar_consumo()

elif st.session_state.menu == "⚖️ Registrar peso":
    registrar_peso()

elif st.session_state.menu == "🔍 Consultar alimento":
    consultar_alimento()

elif st.session_state.menu == "🏃 Atividades Físicas":
    registrar_atividade_fisica()

elif st.session_state.menu == "📊 Históricos Acumulados":
    historico_acumulado_page()  # nossa nova página de históricos

elif st.session_state.menu == "🚪 Sair":
    # logout já tratado no menu lateral
    pass
