# ww_dashboard_ajustado_completo.py
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
    return int(p + 0.5)


def load_data(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_data(data, file_path):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str, indent=2)
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")

# -----------------------------
# LOGIN / USUÁRIOS AJUSTADO
# -----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""

users_store = load_data(USERS_FILE)
if not isinstance(users_store, dict):
    users_store = {}


def login_user(email, password):
    global users_store
    if email in users_store and users_store[email]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.current_user = email

        USER_DATA_FILE = f"data_{email}.json"
        ACTIVITY_FILE = f"activities_{email}.json"
        data_store = load_data(USER_DATA_FILE) or {}
        activities_store = load_data(ACTIVITY_FILE) or {}

        # Garantir chaves no session_state
        for key, default in {
            "peso": [],
            "datas_peso": [],
            "consumo_historico": [],
            "pontos_semana": [],
            "extras": 36.0,
            "consumo_diario": 0.0,
            "activities": {}
        }.items():
            if key not in st.session_state:
                st.session_state[key] = default

        # Carregar dados do JSON
        st.session_state.peso = data_store.get("peso", st.session_state.peso)
        st.session_state.datas_peso = [datetime.date.fromisoformat(d) for d in data_store.get("datas_peso", [])] if data_store.get("datas_peso") else st.session_state.datas_peso
        st.session_state.consumo_historico = data_store.get("consumo_historico", st.session_state.consumo_historico)
        st.session_state.pontos_semana = data_store.get("pontos_semana", st.session_state.pontos_semana)
        st.session_state.extras = float(data_store.get("extras", st.session_state.extras))
        st.session_state.consumo_diario = float(data_store.get("consumo_diario", st.session_state.consumo_diario))

        # Garantir atividades em cada semana
        for w in st.session_state.pontos_semana:
            if "atividades" not in w:
                w["atividades"] = []

        # Migrar activities soltas
        for dia_str, lst in activities_store.items():
            dia_obj = datetime.datetime.strptime(dia_str, "%Y-%m-%d").date() if isinstance(dia_str, str) else dia_str
            semana_num = dia_obj.isocalendar()[1]
            semana_obj = next((w for w in st.session_state.pontos_semana if w.get("semana") == semana_num), None)
            if semana_obj is None:
                semana_obj = {"semana": semana_num, "pontos": [], "extras": 36.0, "atividades": []}
                st.session_state.pontos_semana.append(semana_obj)
            for a in lst:
                atividade = {"tipo": a.get("tipo"), "minutos": a.get("minutos", 0), "pontos": a.get("pontos", 0), "horario": a.get("horario", dia_obj.isoformat())}
                semana_obj["atividades"].append(atividade)
        st.session_state.activities = {}

        # Perfil
        st.session_state.sexo = data_store.get("sexo", "Feminino")
        st.session_state.idade = data_store.get("idade", 30)
        st.session_state.altura = data_store.get("altura", 1.70)
        st.session_state.objetivo = data_store.get("objetivo", "manutenção")
        st.session_state.nivel_atividade = data_store.get("nivel_atividade", "sedentário")

        rebuild_pontos_semana_from_history()
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
# INTERFACE LOGIN / CADASTRO
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

    st.stop()

# -----------------------------
# GARANTIR HISTÓRICO PARA DASHBOARD
# -----------------------------
if "peso" not in st.session_state:
    st.session_state.peso = []
if "datas_peso" not in st.session_state:
    st.session_state.datas_peso = []
if "consumo_historico" not in st.session_state:
    st.session_state.consumo_historico = []
if "pontos_semana" not in st.session_state:
    st.session_state.pontos_semana = []
for w in st.session_state.pontos_semana:
    if "atividades" not in w:
        w["atividades"] = []
if "activities" not in st.session_state:
    st.session_state.activities = {}

# -----------------------------
# DASHBOARD + FUNÇÕES
# -----------------------------
def exibir_consumo():
    st.header("🍴 Histórico de Consumo")
    for r in st.session_state.consumo_historico:
        data = r.get("data")
        data_str = data.isoformat() if isinstance(data, datetime.date) else str(data)
        st.write(f"{data_str} — {r.get('nome')} — {r.get('quantidade')} — {r.get('pontos')} pts")

def exibir_pontos_atividades():
    st.header("🏃 Pontos Semanais e Atividades")
    for semana in st.session_state.pontos_semana:
        st.subheader(f"Semana {semana['semana']} — Extras: {semana.get('extras', 36)} pts")
        for p in semana.get("pontos", []):
            st.write(f"{p.get('data')} — {p.get('nome')} — {p.get('pontos')} pts")
        st.write("Atividades físicas:")
        for a in semana.get("atividades", []):
            st.write(f"{a.get('horario')} — {a.get('tipo')} — {a.get('minutos')} min — {a.get('pontos')} pts")

def exibir_peso():
    st.header("⚖️ Histórico de Peso")
    if st.session_state.peso and st.session_state.datas_peso:
        peso_df = pd.DataFrame({"Data": st.session_state.datas_peso, "Peso": st.session_state.peso})
        st.line_chart(peso_df.set_index("Data"))
    else:
        st.info("Nenhum registro de peso disponível.")

# -----------------------------
# Chamadas das funções por menu
# -----------------------------
if st.session_state.menu == "🏠 Dashboard":
    exibir_peso()
    consumo_hoje = sum(r.get("pontos", 0) for r in st.session_state.consumo_historico if r.get("data") == datetime.date.today())
    st.write(f"Consumo de hoje: {consumo_hoje} pts | Extras: {st.session_state.extras} pts")

elif st.session_state.menu == "🍴 Registrar Consumo":
    exibir_consumo()

elif st.session_state.menu == "⚖️ Registrar Peso":
    exibir_peso()

elif st.session_state.menu == "🏃 Atividades Físicas":
    exibir_pontos_atividades()

elif st.session_state.menu == "📊 Históricos Acumulados":
    exibir_consumo()
    exibir_pontos_atividades()
    exibir_peso()
