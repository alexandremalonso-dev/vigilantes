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

users_store = load_data(USERS_FILE) or {}

def login_user(email, password):
    if email in users_store and users_store[email]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.current_user = email

        # Carregar dados privados do usuário assim que logar
        user_data_file = f"data_{email}.json"
        activity_file = f"activities_{email}.json"
        data_store = load_data(user_data_file) or {}
        activities = load_data(activity_file) or {}

        # Popular session_state imediatamente
        st.session_state.peso = data_store.get("peso", [])
        st.session_state.datas_peso = [
            datetime.date.fromisoformat(d) for d in data_store.get("datas_peso", [])
        ] if data_store.get("datas_peso") else []
        st.session_state.consumo_historico = data_store.get("consumo_historico", [])
        st.session_state.pontos_semana = data_store.get("pontos_semana", [])
        st.session_state.extras = float(data_store.get("extras", 36.0))
        st.session_state.consumo_diario = float(data_store.get("consumo_diario", 0.0))
        st.session_state.meta_diaria = data_store.get("meta_diaria", 29)
        st.session_state.activities = activities

        st.success(f"Bem-vindo(a), {email}!")
        return True
    else:
        st.error("Email ou senha incorretos.")
        return False

def register_user(email, password):
    if email in users_store:
        st.error("Usuário já existe!")
        return False
    users_store[email] = {"password": password}
    save_data(users_store, USERS_FILE)
    st.session_state.logged_in = True
    st.session_state.current_user = email

    # Cria arquivos de dados vazios ao registrar
    save_data({}, f"data_{email}.json")
    save_data({}, f"activities_{email}.json")

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

if "menu" not in st.session_state:
    st.session_state.menu = "🏠 Dashboard"

# -----------------------------
# FUNÇÃO DE PERSISTÊNCIA
# -----------------------------
def persist_all():
    """Salva apenas os dados privados do usuário"""
    try:
        ds = {
            "peso": st.session_state.peso,
            "datas_peso": [d.isoformat() for d in st.session_state.datas_peso],
            "consumo_diario": float(st.session_state.consumo_diario),
            "meta_diaria": st.session_state.meta_diaria,
            "extras": float(st.session_state.extras),
            "consumo_historico": [
                {
                    "data": r["data"].isoformat() if isinstance(r.get("data"), datetime.date) else str(r.get("data")),
                    "nome": r["nome"],
                    "quantidade": r["quantidade"],
                    "pontos": r["pontos"],
                    "usou_extras": r.get("usou_extras", 0.0)
                } for r in st.session_state.consumo_historico
            ],
            "pontos_semana": [
                {
                    "semana": w["semana"],
                    "pontos": [
                        {
                            "data": p["data"].isoformat() if isinstance(p.get("data"), datetime.date) else str(p.get("data")),
                            "nome": p["nome"],
                            "quantidade": p["quantidade"],
                            "pontos": p["pontos"],
                            "usou_extras": p.get("usou_extras", 0.0)
                        } for p in w.get("pontos", [])
                    ],
                    "extras": w.get("extras", 36.0)
                } for w in st.session_state.pontos_semana
            ]
        }
        save_data(ds, USER_DATA_FILE)
        save_data(st.session_state.activities, ACTIVITY_FILE)
    except Exception as e:
        st.error(f"Erro ao persistir dados: {e}")


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
# RECONSTRUÇÃO E RECÁLCULO (EXTRAS / DIÁRIO)
# -----------------------------
def rebuild_pontos_semana_from_history():
    meta = float(st.session_state.meta_diaria or 29.0)
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
# FUNÇÃO REGISTRAR CONSUMO (AJUSTADO)
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

    # Inicializa flag para histórico expandido
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
            if alimento.get("ZeroPontos", False):
                pontos_registrados = 0
            else:
                pontos_raw = float(alimento.get("Pontos", 0.0)) * (quantidade / porcao_ref if porcao_ref > 0 else 0.0)
                pontos_registrados = round_points(pontos_raw)

            registro = {
                "data": datetime.date.today(),
                "nome": escolha,
                "quantidade": float(quantidade),
                "pontos": pontos_registrados,
                "usou_extras": 0.0
            }
            st.session_state.consumo_historico.append(registro)

            rebuild_pontos_semana_from_history()
            persist_all()
            st.success(
                f"🍴 Registrado {quantidade:.2f}g de {escolha}. "
                f"Pontos: {pontos_registrados:.2f}. Total hoje: {st.session_state.consumo_diario:.2f}"
            )

            # ativa flag para exibir histórico
            st.session_state.mostrar_historico_consumo = True

            # ⚡ Força atualização imediata da interface
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
                        if alimento_ref:
                            porc_ref = float(alimento_ref.get("Porcao", 100.0))
                            new_p_raw = float(alimento_ref.get("Pontos", 0.0)) * (new_q / porc_ref if porc_ref > 0 else 0.0)
                            new_p = round_points(new_p_raw)
                        else:
                            new_p = reg["pontos"]

                        if st.button("Salvar alterações", key=save_key):
                            reg["quantidade"] = float(new_q)
                            reg["pontos"] = new_p
                            rebuild_pontos_semana_from_history()
                            persist_all()
                            st.success("Registro atualizado!")
                            rerun_streamlit()  # atualização imediata

                # Excluir registro
                if cols[2].button("Excluir", key=f"del_cons_{idx}"):
                    st.session_state.consumo_historico.pop(idx)
                    rebuild_pontos_semana_from_history()
                    persist_all()
                    st.success("Registro excluído.")
                    rerun_streamlit()  # atualização imediata

# -----------------------------
# FUNÇÃO REGISTRAR PESO
# -----------------------------
def registrar_peso():
    st.header("⚖️ Registrar Peso")

    # Inicializa flags e listas
    if "mostrar_historico_peso" not in st.session_state:
        st.session_state.mostrar_historico_peso = False
    if "peso" not in st.session_state:
        st.session_state.peso = []
    if "datas_peso" not in st.session_state:
        st.session_state.datas_peso = []

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
            st.session_state.peso.append(float(peso_novo))
            st.session_state.datas_peso.append(datetime.date.today())
            persist_all()
            st.success(f"Peso {peso_novo:.2f} kg registrado com sucesso!")
            # ativa flag para exibir histórico
            st.session_state.mostrar_historico_peso = True
            st.stop()  # força atualização dinâmica do histórico

    # Histórico de pesos
    with st.expander("Histórico de Pesos", expanded=st.session_state.mostrar_historico_peso):
        if not st.session_state.peso:
            st.info("Nenhum peso registrado ainda.")
        else:
            for idx in range(len(st.session_state.peso) - 1, -1, -1):
                data_reg = st.session_state.datas_peso[idx]
                peso_reg = st.session_state.peso[idx]
                cols = st.columns([6, 1, 1])
                cols[0].write(f"{data_reg.strftime('%d/%m/%Y')}: {peso_reg:.2f} kg")
                
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
                            st.session_state.peso[idx] = float(new_peso)
                            persist_all()
                            st.success(f"Registro atualizado para {new_peso:.2f} kg")
                            st.stop()  # força atualização dinâmica do histórico

                # Excluir peso
                if cols[2].button("❌", key=f"del_peso_{idx}"):
                    st.session_state.peso.pop(idx)
                    st.session_state.datas_peso.pop(idx)
                    persist_all()
                    st.success("Registro excluído.")
                    st.stop()  # força atualização dinâmica do histórico

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
# DASHBOARD PRINCIPAL
# -----------------------------
if st.session_state.menu == "🏠 Dashboard":
    st.markdown("<h1 style='text-align: center; color: #2c3e50;'>🍏 Vigilantes do Peso Brasil</h1>", unsafe_allow_html=True)

    # Solicitar peso inicial se não houver
    if not st.session_state.peso:
        st.warning("⚖️ Por favor, registre seu peso inicial antes de usar o dashboard.")
        registrar_peso()
        st.stop()

    # Garantir semana atual e recalcular a partir do histórico
    ensure_current_week_exists()
    rebuild_pontos_semana_from_history()

    peso_atual = st.session_state.peso[-1] if st.session_state.peso else 0.0
    semana_atual = iso_week_number(datetime.date.today())
    semana_obj = next((w for w in st.session_state.pontos_semana if w["semana"] == semana_atual), None)
    if not semana_obj:
        semana_obj = {"semana": semana_atual, "extras": 36.0, "pontos": []}
        st.session_state.pontos_semana.append(semana_obj)

    # -----------------------------
    # Indicadores principais (gráficos)
    # -----------------------------
    col1, col2, col3 = st.columns(3)

    # Consumo Diário
    with col1:
        meta_diaria = st.session_state.meta_diaria
        consumo_diario = float(st.session_state.consumo_diario)
        fig1 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=consumo_diario,
            number={'suffix': f" / {meta_diaria}"},
            gauge={'axis': {'range': [0, meta_diaria]},
                   'bar': {'color': "#e74c3c"},
                   'steps': [
                       {'range': [0, meta_diaria * 0.7], 'color': "#2ecc71"},
                       {'range': [meta_diaria * 0.7, meta_diaria], 'color': "#f1c40f"}
                   ]},
            title={'text': "Pontos Consumidos"}))
        st.plotly_chart(fig1, use_container_width=True)

    # Banco de Pontos Extras
    with col2:
        pontos_atividade_semana = sum(
            a.get('pontos', 0.0)
            for dia_str, lst in st.session_state.activities.items()
            for a in lst
            if iso_week_number(datetime.datetime.strptime(dia_str, "%Y-%m-%d").date() if isinstance(dia_str, str) else dia_str) == semana_atual
        )
        total_banco = 36.0 + pontos_atividade_semana
        usados = total_banco - float(semana_obj.get("extras", 36.0))
        fig2 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=usados,
            number={'suffix': f" / {total_banco:.0f}"},
            gauge={'axis': {'range': [0, total_banco]},
                   'bar': {'color': "#006400"},
                   'steps': [
                       {'range': [0, total_banco/3], 'color': "#e74c3c"},
                       {'range': [total_banco/3, 2*total_banco/3], 'color': "#f1c40f"},
                       {'range': [2*total_banco/3, total_banco], 'color': "#2ecc71"}
                   ]},
            title={'text': "Usado / Total (Pontos Extras)"}
        ))
        st.plotly_chart(fig2, use_container_width=True)

    # Peso Atual
    with col3:
        if len(st.session_state.peso) <= 1:
            cor_gauge = "blue"
            tendencia = "➖"
        else:
            if st.session_state.peso[-1] < st.session_state.peso[-2]:
                cor_gauge = "green"
                tendencia = "⬇️"
            elif st.session_state.peso[-1] > st.session_state.peso[-2]:
                cor_gauge = "orange"
                tendencia = "⬆️"
            else:
                cor_gauge = "blue"
                tendencia = "➖"

        min_axis = min(st.session_state.peso) - 5 if st.session_state.peso else 0
        max_axis = max(st.session_state.peso) + 5 if st.session_state.peso else 100
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=peso_atual,
            gauge={'axis': {'range': [min_axis, max_axis]},
                   'bar': {'color': cor_gauge}} ,
            title={'text': f"Peso Atual {tendencia}"}
        ))
        st.plotly_chart(fig_gauge, use_container_width=True)

    # -----------------------------
    # Históricos (SOMENTE no dashboard)
    # Ordem: Pontos Semanais, Atividades, Peso
    # -----------------------------
    col_hist1, col_hist2, col_hist3 = st.columns(3)

    # Pontos Semanais
    with col_hist1:
        st.markdown("### 📊 Pontos Semanais")
        all_pontos = [reg for w in st.session_state.pontos_semana for reg in w.get("pontos", [])]
        if not all_pontos:
            st.write(" - (sem registros)")
        else:
            for reg in sorted(all_pontos, key=lambda x: x["data"]):
                dia = reg["data"].strftime("%d/%m/%Y") if isinstance(reg["data"], datetime.date) else str(reg["data"])
                dia_sem = weekday_name_br(reg["data"]) if isinstance(reg["data"], datetime.date) else ""
                usados = f" - usou extras: {reg.get('usou_extras',0.0):.2f} pts" if reg.get("usou_extras", 0.0) else ""
                st.markdown(
                    f"<div style='padding:10px; border:1px solid #f39c12; border-radius:5px; margin-bottom:5px;'>{dia} ({dia_sem}): {reg['nome']} {reg['quantidade']:.2f} min ({reg['pontos']:.2f} pts){usados}</div>",
                    unsafe_allow_html=True
                )

    # Histórico de Atividades Físicas
    with col_hist2:
        st.markdown("### 🏃 Histórico de Atividades Físicas")
        if st.session_state.activities:
            acts_list = [(d, a['tipo'], a['minutos'], a['pontos']) 
                         for d, lst in st.session_state.activities.items() for a in lst]
            if acts_list:
                acts_list_sorted = sorted(acts_list, key=lambda x: x[0])
                for d, tipo, minutos, pontos in acts_list_sorted:
                    st.markdown(
                        f"<div style='padding:10px; border:1px solid #1abc9c; border-radius:5px; margin-bottom:5px;'>{d}: {tipo} - {minutos:.2f} min ({pontos:.2f} pts)</div>",
                        unsafe_allow_html=True
                    )
        else:
            st.info("Nenhuma atividade registrada ainda.")

    # Histórico de Peso
    with col_hist3:
        st.markdown("### ⚖️ Histórico de Peso")
        for i, (p, d) in enumerate(zip(st.session_state.peso, st.session_state.datas_peso)):
            if i == 0:
                tendencia = "➖"
            else:
                if p < st.session_state.peso[i - 1]:
                    tendencia = "⬇️"
                elif p > st.session_state.peso[i - 1]:
                    tendencia = "⬆️"
                else:
                    tendencia = "➖"
            st.markdown(
                f"<div style='padding:10px; border:1px solid #3498db; border-radius:5px; margin-bottom:5px;'>{d.strftime('%d/%m/%Y')}: {p:.2f} kg {tendencia}</div>",
                unsafe_allow_html=True
            )

    # -----------------------------
    # Tendência de Peso (linha de tendência)
    # -----------------------------
    import numpy as np
    import pandas as pd

    if st.session_state.peso and st.session_state.datas_peso:
        if len(st.session_state.peso) == len(st.session_state.datas_peso):
            df_peso = pd.DataFrame({
                "Data": st.session_state.datas_peso,
                "Peso": st.session_state.peso
            })
            df_peso["Data_dt"] = pd.to_datetime(df_peso["Data"])

            if len(df_peso) >= 2:
                x_ord = np.array([d.toordinal() for d in df_peso["Data_dt"]])
                y = np.array(df_peso["Peso"])
                m, b = np.polyfit(x_ord, y, 1)
                y_trend = m * x_ord + b
                mode_plot = "lines+markers"
            else:
                y_trend = np.array(df_peso["Peso"])
                mode_plot = "markers"

            fig_line = go.Figure(
                go.Scatter(
                    x=df_peso["Data_dt"].tolist(),
                    y=y_trend.tolist(),
                    mode=mode_plot,
                    line=dict(color="#8e44ad", width=3)
                )
            )
            fig_line.update_layout(
                yaxis_title="Peso (kg)",
                xaxis_title="Data",
                template="plotly_white"
            )
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
    
    # Inicializa flags e estruturas
    if "mostrar_historico_atividade" not in st.session_state:
        st.session_state.mostrar_historico_atividade = False
    if "activities" not in st.session_state:
        st.session_state.activities = {}
    if "pontos_semana" not in st.session_state:
        st.session_state.pontos_semana = []

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

            # Adiciona atividade ao dia
            if data_atividade not in st.session_state.activities:
                st.session_state.activities[data_atividade] = []
            st.session_state.activities[data_atividade].append({
                "tipo": tipo,
                "minutos": minutos,
                "pontos": pontos
            })

            # Atualiza pontos extras da semana
            semana_atual = iso_week_number(data_atividade)
            semana_obj = next((w for w in st.session_state.pontos_semana if w["semana"] == semana_atual), None)
            if not semana_obj:
                semana_obj = {"semana": semana_atual, "extras": 36.0, "pontos": []}
                st.session_state.pontos_semana.append(semana_obj)

            semana_obj["extras"] = semana_obj.get("extras", 36.0) + pontos
            semana_obj["pontos"].append({
                "data": data_atividade,
                "nome": tipo,
                "quantidade": minutos,
                "pontos": pontos,
                "usou_extras": 0.0
            })

            persist_all()
            st.success(f"✅ Atividade '{tipo}' registrada! Pontos extras atualizados: {semana_obj['extras']:.2f}")

            # ativa flag para exibir histórico
            st.session_state.mostrar_historico_atividade = True
            st.stop()  # força atualização dinâmica do histórico

    # Histórico de atividades
    activities = st.session_state.get("activities", {})
    with st.expander("Histórico de Atividades", expanded=st.session_state.mostrar_historico_atividade):
        if not activities:
            st.info("Nenhuma atividade registrada ainda.")
        else:
            for dia in sorted(activities.keys(), reverse=True):
                atos = activities[dia]
                st.markdown(f"**{dia.strftime('%d/%m/%Y')}**")
                for idx, ato in enumerate(list(atos)):
                    col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
                    col1.write(f"{ato['tipo']} - {ato['minutos']} min")
                    col2.write(f"{ato['pontos']} pts")

                    # Botão Editar: permite alterar apenas os minutos, recalculando os pontos
                    if col3.button("✏️", key=f"edit_{dia}_{idx}"):
                        edit_key_tipo = f"edit_tipo_{dia}_{idx}"
                        edit_key_min = f"edit_min_{dia}_{idx}"
                        with st.expander(f"Editar atividade #{idx}", expanded=True):
                            novo_tipo = st.selectbox(
                                "Tipo de atividade",
                                list(pontos_base.keys()),
                                index=list(pontos_base.keys()).index(ato["tipo"]),
                                key=edit_key_tipo
                            )
                            novo_min = st.number_input(
                                "Duração (minutos)",
                                min_value=1,
                                max_value=300,
                                value=ato["minutos"],
                                key=edit_key_min
                            )
                            if st.button("Salvar alterações", key=f"save_{dia}_{idx}"):
                                # Recalcula pontos automaticamente com arredondamento half-up
                                novo_pts = round_points((novo_min / minutos_base) * pontos_base.get(novo_tipo, 1))
                                
                                # Atualiza extras da semana
                                semana = iso_week_number(dia)
                                ws = next((w for w in st.session_state.pontos_semana if w.get('semana') == semana), None)
                                if ws:
                                    ws['extras'] = max(0.0, ws.get('extras', 36.0) - float(ato['pontos']) + float(novo_pts))
                                
                                # Atualiza atividade
                                st.session_state.activities[dia][idx] = {
                                    "tipo": novo_tipo,
                                    "minutos": novo_min,
                                    "pontos": novo_pts
                                }
                                persist_all()
                                st.success("Atividade atualizada!")
                                st.stop()  # força atualização dinâmica do histórico

                    # Botão Excluir
                    if col4.button("❌", key=f"del_{dia}_{idx}"):
                        removed = st.session_state.activities[dia].pop(idx)
                        # Ajusta extras da semana
                        semana = iso_week_number(dia)
                        ws = next((w for w in st.session_state.pontos_semana if w.get('semana') == semana), None)
                        if ws:
                            ws['extras'] = max(0.0, ws.get('extras', 36.0) - float(removed.get('pontos', 0)))
                        if not st.session_state.activities[dia]:
                            del st.session_state.activities[dia]
                        persist_all()
                        st.success("Atividade removida.")
                        st.stop()  # força atualização dinâmica do histórico

import streamlit as st
import datetime
import pdfkit
import tempfile
import pandas as pd
import plotly.graph_objects as go

# -----------------------------
# BLOCO 1: Filtros de Período e Botões
# -----------------------------
def blocos_filtros_report():
    st.header("📅 Seleção de Período para Histórico Acumulado")
    
    col1, col2, col3 = st.columns([2,2,1])
    with col1:
        data_inicio = st.date_input("Data Início", value=datetime.date.today() - datetime.timedelta(days=30))
    with col2:
        data_fim = st.date_input("Data Fim", value=datetime.date.today())
    with col3:
        gerar = st.button("📄 Gerar Report")
    
    incluir_atividades = st.checkbox("Incluir atividades físicas", value=True)
    incluir_consumo = st.checkbox("Incluir consumo diário", value=True)
    
    return gerar, data_inicio, data_fim, incluir_atividades, incluir_consumo

# -----------------------------
# BLOCO 2: Indicadores Resumidos
# -----------------------------
def blocos_indicadores_acumulados(consumo_historico, pontos_semana, peso_list, datas_peso, atividades, data_inicio, data_fim):
    st.markdown("### 📊 Indicadores Resumidos do Período")
    
    # Filtra dados
    peso_filtrado = [(p,d) for p,d in zip(peso_list,datas_peso) if data_inicio <= d <= data_fim]
    consumo_filtrado = [r for r in consumo_historico if data_inicio <= r["data"] <= data_fim]
    atividades_filtrado = {d: lst for d,lst in atividades.items() if data_inicio <= d <= data_fim}
    
    pontos_consumidos = sum(float(r.get("pontos",0)) for r in consumo_filtrado)
    pontos_extras_acumulados = sum(w.get("extras",36) for w in pontos_semana if any(data_inicio <= r.get("data") <= data_fim for r in w.get("pontos", [])))
    
    if peso_filtrado:
        peso_inicial = peso_filtrado[0][0]
        peso_final = peso_filtrado[-1][0]
        if peso_final < peso_inicial:
            tendencia = "⬇️"
        elif peso_final > peso_inicial:
            tendencia = "⬆️"
        else:
            tendencia = "➖"
    else:
        peso_inicial = peso_final = 0.0
        tendencia = "➖"
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pontos Extras Acumulados", f"{pontos_extras_acumulados:.0f}")
    col2.metric("Pontos Consumidos", f"{pontos_consumidos:.0f}")
    col3.metric("Peso Inicial x Final", f"{peso_inicial:.1f}kg → {peso_final:.1f}kg")
    col4.metric("Tendência Geral Peso", tendencia)

# -----------------------------
# BLOCO 3: Tabelas de Histórico Detalhado
# -----------------------------
def blocos_tabelas_historico(consumo_historico, pontos_semana, peso_list, datas_peso, atividades, data_inicio, data_fim, incluir_atividades=True, incluir_consumo=True):
    st.markdown("### 🗂 Histórico Detalhado")

    # Pontos Semanais
    st.subheader("📌 Pontos Semanais")
    for w in pontos_semana:
        week_points = [r for r in w.get("pontos",[]) if data_inicio <= r["data"] <= data_fim]
        if week_points:
            st.markdown(f"**Semana {w['semana']}** — Extras Restantes: {w['extras']}")
            for r in week_points:
                st.write(f"{r['data'].strftime('%d/%m/%Y')}: {r['nome']} — {r['quantidade']} min — {r['pontos']} pts (usou extras: {r.get('usou_extras',0)})")
    
    # Consumo Diário
    if incluir_consumo:
        st.subheader("🍴 Consumo Diário")
        consumo_filtrado = [r for r in consumo_historico if data_inicio <= r["data"] <= data_fim]
        for r in consumo_filtrado:
            st.write(f"{r['data'].strftime('%d/%m/%Y')}: {r['nome']} — {r['quantidade']} g — {r['pontos']} pts (usou extras: {r.get('usou_extras',0)})")
    
    # Peso
    st.subheader("⚖️ Peso")
    peso_filtrado = [(p,d) for p,d in zip(peso_list,datas_peso) if data_inicio <= d <= data_fim]
    for p,d in peso_filtrado:
        st.write(f"{d.strftime('%d/%m/%Y')}: {p:.2f} kg")
    
    # Atividades Físicas
    if incluir_atividades:
        st.subheader("🏃 Atividades Físicas")
        atividades_filtrado = {d: lst for d,lst in atividades.items() if data_inicio <= d <= data_fim}
        for d, lst in sorted(atividades_filtrado.items()):
            for a in lst:
                st.write(f"{d.strftime('%d/%m/%Y')}: {a['tipo']} — {a['minutos']} min — {a['pontos']} pts")

# -----------------------------
# BLOCO 4: Exportar PDF
# -----------------------------
def blocos_exportar_pdf(html_content, filename="historico_acumulado.pdf"):
    st.markdown("### 📤 Exportar Report")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        tmp.write(html_content.encode('utf-8'))
        tmp_path = tmp.name
    
    if st.button("🖨️ Exportar PDF"):
        try:
            pdfkit.from_file(tmp_path, filename)
            st.success(f"PDF gerado com sucesso: {filename}")
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

# -----------------------------
# FUNÇÃO PRINCIPAL: Página Históricos Acumulados
# -----------------------------
def historico_acumulado_page():
    gerar, data_inicio, data_fim, incluir_atividades, incluir_consumo = blocos_filtros_report()
    
    if gerar:
        # Assumindo que você já tenha estas variáveis do session_state
        consumo_historico = st.session_state.get("consumo_historico", [])
        pontos_semana = st.session_state.get("pontos_semana", [])
        peso_list = st.session_state.get("peso", [])
        datas_peso = st.session_state.get("datas_peso", [])
        atividades = st.session_state.get("activities", {})
        
        blocos_indicadores_acumulados(consumo_historico, pontos_semana, peso_list, datas_peso, atividades, data_inicio, data_fim)
        blocos_tabelas_historico(consumo_historico, pontos_semana, peso_list, datas_peso, atividades, data_inicio, data_fim, incluir_atividades, incluir_consumo)
        
        # Montar HTML simples para exportar PDF (exemplo)
        html_content = "<h1>Histórico Acumulado Vigilantes do Peso</h1>"
        html_content += f"<p>Período: {data_inicio} → {data_fim}</p>"
        html_content += "<ul>"
        for r in consumo_historico:
            if data_inicio <= r["data"] <= data_fim:
                html_content += f"<li>{r['data']}: {r['nome']} — {r['quantidade']} g — {r['pontos']} pts</li>"
        html_content += "</ul>"
        blocos_exportar_pdf(html_content)


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
