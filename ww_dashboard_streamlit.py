# ww_dashboard_streamlit.py
import streamlit as st
import json, re, os, datetime
import plotly.graph_objects as go
import pandas as pd
from math import floor

def rerun_streamlit():
    try:
        if callable(st.experimental_rerun):
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

users_store = load_data(USERS_FILE)
if not isinstance(users_store, dict):
    users_store = {}

def login_user(email, password):
    if email in users_store and users_store[email]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.current_user = email
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
# A PARTIR DAQUI, APP PRINCIPAL
# -----------------------------
st.title(f"📊 Bem-vindo(a), {st.session_state.current_user}!")
# aqui continua o seu dashboard normalmente

# -----------------------------
# CARREGAR DADOS PERSISTIDOS
# -----------------------------
data_store = load_data(DATA_FILE)

# -----------------------------
# INICIALIZAÇÃO DO SESSION_STATE
# -----------------------------
if "menu" not in st.session_state:
    st.session_state.menu = "🏠 Dashboard"

if "alimentos" not in st.session_state:
    if isinstance(data_store, list):
        st.session_state.alimentos = data_store
    elif isinstance(data_store, dict) and "alimentos" in data_store:
        st.session_state.alimentos = data_store["alimentos"]
    else:
        st.session_state.alimentos = []

if isinstance(data_store, dict):  # só tenta .get se for dict
    if "peso" not in st.session_state:
        st.session_state.peso = data_store.get("peso", [])

    if "datas_peso" not in st.session_state:
        ds = data_store.get("datas_peso", [])
        st.session_state.datas_peso = [datetime.date.fromisoformat(d) for d in ds] if ds else []

    if "consumo_diario" not in st.session_state:
        st.session_state.consumo_diario = float(data_store.get("consumo_diario", 0.0))

    if "meta_diaria" not in st.session_state:
        st.session_state.meta_diaria = data_store.get("meta_diaria", 29)

    if "extras" not in st.session_state:
        st.session_state.extras = float(data_store.get("extras", 36.0))

    if "consumo_historico" not in st.session_state:
        ch = data_store.get("consumo_historico", [])
        for r in ch:
            if isinstance(r.get("data"), str):
                try:
                    r["data"] = datetime.date.fromisoformat(r["data"])
                except Exception:
                    pass
        st.session_state.consumo_historico = ch

    if "pontos_semana" not in st.session_state:
        ps = data_store.get("pontos_semana", [])
        for w in ps:
            for reg in w.get("pontos", []):
                if isinstance(reg.get("data"), str):
                    try:
                        reg["data"] = datetime.date.fromisoformat(reg["data"])
                    except Exception:
                        pass
        st.session_state.pontos_semana = ps
else:
    # caso data_store seja lista, inicializa os demais vazios
    if "peso" not in st.session_state:
        st.session_state.peso = []
    if "datas_peso" not in st.session_state:
        st.session_state.datas_peso = []
    if "consumo_diario" not in st.session_state:
        st.session_state.consumo_diario = 0.0
    if "meta_diaria" not in st.session_state:
        st.session_state.meta_diaria = 29
    if "extras" not in st.session_state:
        st.session_state.extras = 36.0
    if "consumo_historico" not in st.session_state:
        st.session_state.consumo_historico = []
    if "pontos_semana" not in st.session_state:
        st.session_state.pontos_semana = []

# -----------------------------
# PERSISTÊNCIA
# -----------------------------
def persist_all():
    try:
        ds = {
            "alimentos": st.session_state.alimentos,
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
                }
                for r in st.session_state.consumo_historico
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
        save_data(ds)
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
    ("🔄 Resetar Semana", "resetar_semana"),
    ("🚪 Sair", "🚪 Sair"),
]

for label, key in menu_itens:
    if st.sidebar.button(label, key=f"sidebtn_{label}", use_container_width=True):
        st.session_state.menu = key

        # -----------------------------
        # AÇÃO RESETAR SEMANA
        # -----------------------------
        if key == "resetar_semana":
            hoje = datetime.date.today()
            semana_atual = hoje.isocalendar()[1]

            # Zerar pontos da semana atual
            if "pontos_semana" in st.session_state:
                st.session_state.pontos_semana = [
                    w for w in st.session_state.pontos_semana if w.get("semana") != semana_atual
                ]
            else:
                st.session_state.pontos_semana = []

            # Cria nova semana zerada
            st.session_state.pontos_semana.append({
                "semana": semana_atual,
                "pontos": [],
                "extras": 36.0
            })

            # Zera consumo diário e extras
            st.session_state.extras = 36.0
            st.session_state.consumo_diario = 0.0

            # Remove registros da semana atual do histórico
            if "consumo_historico" in st.session_state:
                st.session_state.consumo_historico = [
                    r for r in st.session_state.consumo_historico
                    if r.get("data").isocalendar()[1] != semana_atual
                ]

            # Persistir alterações se houver função definida
            if "persist_all" in globals():
                persist_all()

            # Mensagem de sucesso
            st.sidebar.success(f"✅ Semana {semana_atual} resetada com sucesso!")

# -----------------------------
# FUNÇÕES PRINCIPAIS
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
            # tentar normalizar e mapear colunas
            alimentos_novos = []
            for _, row in df.iterrows():
                try:
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
                    pontos_calc = (calorias/50.0) + (carbo/10.0) + (gordura/5.0) + (proteina/5.0) + (sodio_mg/100.0)
                    pontos = round_points(pontos_calc)
                    try:
                        porcao = safe_parse_porçao(porc_val)
                    except Exception:
                        porcao = 100.0
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
                        "Pontos": pontos
                    }
                    alimentos_novos.append(alimento)
                except Exception:
                    continue
            st.session_state.alimentos.extend(alimentos_novos)
            persist_all()
            st.success(f"📂 Importadas {len(alimentos_novos)} linhas. Total agora: {len(st.session_state.alimentos)} alimentos.")
        except Exception as e:
            st.error(f"Erro ao importar planilha: {e}\n(Se for .xlsx, instale openpyxl: pip install openpyxl)")

def cadastrar_alimento():
    st.header("➕ Cadastrar Alimento")
    nome = st.text_input("Nome do alimento:", key="cad_nome")
    porcao_in = st.text_input("Porção (g) — ex: 20 ou 20g ou 120:", key="cad_porc")
    calorias = st.number_input("Calorias (kcal)", min_value=0.0, step=0.1, key="cad_cal")
    carbo = st.number_input("Carboidratos (g)", min_value=0.0, step=0.1, key="cad_car")
    gordura = st.number_input("Gordura (g)", min_value=0.0, step=0.1, key="cad_gor")
    saturada = st.number_input("Gordura Saturada (g)", min_value=0.0, step=0.1, key="cad_sat")
    fibra = st.number_input("Fibra (g)", min_value=0.0, step=0.1, key="cad_fib")
    acucar = st.number_input("Açúcar (g)", min_value=0.0, step=0.1, key="cad_acu")
    proteina = st.number_input("Proteína (g)", min_value=0.0, step=0.1, key="cad_pro")
    sodio_mg = st.number_input("Sódio (mg)", min_value=0.0, step=1.0, key="cad_sod")

    if st.button("Cadastrar alimento", key="bot_cad_alim"):
        if not nome:
            st.error("Informe o nome do alimento!")
            return
        try:
            porcao = safe_parse_porçao(porcao_in)
        except Exception as e:
            st.error(f"Erro ao interpretar a porção do alimento: {e}")
            return
        pontos_raw = (calorias / 50.0) + (carbo / 10.0) + (gordura / 5.0) + (proteina / 5.0) + (sodio_mg / 100.0)
        pontos = round_points(pontos_raw)
        alimento = {
            "Nome": nome,
            "Porcao": porcao,
            "Calorias": round(calorias, 2),
            "Gordura": round(gordura, 2),
            "Saturada": round(saturada, 2),
            "Carbo": round(carbo, 2),
            "Fibra": round(fibra, 2),
            "Açúcar": round(acucar, 2),
            "Proteina": round(proteina, 2),
            "Sodio_mg": round(sodio_mg, 2),
            "Pontos": pontos
        }
        st.session_state.alimentos.append(alimento)
        persist_all()
        st.success(f"Alimento '{nome}' cadastrado com sucesso! Pontos: {pontos}")

def registrar_consumo():
    st.header("🍴 Registrar Consumo")
    if not st.session_state.alimentos:
        st.warning("Nenhum alimento cadastrado ainda.")
        return

    nomes = [a["Nome"] for a in st.session_state.alimentos]
    escolha = st.selectbox("Escolha o alimento consumido:", nomes, key="reg_select_consumo")

    # localizar alimento
    alimento = next((a for a in st.session_state.alimentos if a["Nome"] == escolha), None)
    if alimento is None:
        st.error("Alimento não encontrado.")
        return

    # exibir porção referência
    porcao_ref = alimento.get("Porcao", 100.0)
    pontos_por_porcao = round_points(alimento.get("Pontos", 0.0))
    st.markdown(f"**Porção referência:** {porcao_ref} g — Pontos (por porção): **{pontos_por_porcao}**")

    # usar formulário para permitir submit com Enter
    with st.form("form_reg_consumo", clear_on_submit=False):
        quantidade = st.number_input(f"Quantidade consumida em gramas (porção {porcao_ref} g):", min_value=0.0, step=1.0, format="%.2f", key="reg_quant")
        submitted = st.form_submit_button("Registrar consumo")
        if submitted:
            # calcular pontos proporcionalmente (usar porção numérica)
            try:
                porcao_val = float(porcao_ref)
            except Exception:
                st.error("Erro ao interpretar porção do alimento selecionado.")
                return

            pontos_registrados_raw = float(alimento.get("Pontos", 0.0)) * (quantidade / porcao_val if porcao_val > 0 else 0.0)
            pontos_registrados = round_points(pontos_registrados_raw)

            # preparar registro
            registro = {"data": datetime.date.today(), "nome": escolha, "quantidade": float(quantidade), "pontos": pontos_registrados, "usou_extras": 0.0}
            st.session_state.consumo_historico.append(registro)

            # rebuild whole weeks/historico/extras from history (ensures consistent rules)
            rebuild_pontos_semana_from_history()

            persist_all()

            st.success(f"🍴 Registrado {quantidade:.2f}g de {escolha}. Pontos: {pontos_registrados:.2f}. Total hoje: {st.session_state.consumo_diario:.2f}")

            # refresh to update dashboards/graphs immediately
            if hasattr(st, "experimental_rerun"):
                rerun_streamlit()
            else:
                st.stop()

    # Histórico com opções de editar/excluir
    st.markdown("### Histórico de Consumo (últimos registros)")
    if not st.session_state.consumo_historico:
        st.info("Nenhum consumo registrado ainda.")
    else:
        # mostrar em ordem reversa (mais recente primeiro)
        for idx in range(len(st.session_state.consumo_historico) - 1, -1, -1):
            reg = st.session_state.consumo_historico[idx]
            data = reg["data"]
            dia_sem = weekday_name_br(data) if isinstance(data, datetime.date) else ""
            display = f"{data.strftime('%d/%m/%Y')} ({dia_sem}): {reg['nome']} — {reg['quantidade']:.2f} g — {reg['pontos']:.2f} pts"
            if reg.get("usou_extras", 0.0):
                display += f" — usou extras: {reg.get('usou_extras',0.0):.2f} pts"
            cols = st.columns([6, 1, 1])
            cols[0].write(display)

            # editar
            if cols[1].button("Editar", key=f"edit_cons_{idx}"):
                # abrir painel de edição inline (expander)
                edit_key_q = f"edit_q_{idx}"
                save_key = f"save_cons_{idx}"
                with st.expander(f"Editar registro #{idx}", expanded=True):
                    new_q = st.number_input("Quantidade (g):", min_value=0.0, step=1.0, value=reg["quantidade"], key=edit_key_q)
                    # recalcular pontos
                    alimento_ref = next((a for a in st.session_state.alimentos if a["Nome"] == reg["nome"]), None)
                    if alimento_ref:
                        porc_ref = float(alimento_ref.get("Porcao", 100.0))
                        new_p_raw = float(alimento_ref.get("Pontos", 0.0)) * (new_q / porc_ref if porc_ref > 0 else 0.0)
                        new_p = round_points(new_p_raw)
                    else:
                        new_p = reg["pontos"]
                    if st.button("Salvar alterações", key=save_key):
                        # atualizar registro
                        reg["quantidade"] = float(new_q)
                        reg["pontos"] = new_p
                        # rebuild para recalcular extras/diário corretamente
                        rebuild_pontos_semana_from_history()
                        persist_all()
                        if hasattr(st, "experimental_rerun"):
                            rerun_streamlit()
                        else:
                            st.stop()

            # excluir
            if cols[2].button("Excluir", key=f"del_cons_{idx}"):
                removed = st.session_state.consumo_historico.pop(idx)
                # rebuild para recalcular extras/diário corretamente
                rebuild_pontos_semana_from_history()
                persist_all()
                st.success("Registro excluído.")
                if hasattr(st, "experimental_rerun"):
                    rerun_streamlit()
                else:
                    st.stop()

def registrar_peso():
    st.header("⚖️ Registrar Peso")
    # usar form para permitir Enter
    with st.form("form_peso"):
        peso_novo = st.number_input("Informe seu peso (kg):", min_value=0.0, step=0.1, format="%.2f", key="input_peso_reg")
        submitted = st.form_submit_button("Registrar peso")
        if submitted:
            st.session_state.peso.append(float(peso_novo))
            st.session_state.datas_peso.append(datetime.date.today())
            persist_all()
            st.success(f"Peso {peso_novo:.2f} kg registrado com sucesso!")
            if hasattr(st, "experimental_rerun"):
                rerun_streamlit()
            else:
                st.stop()

# -----------------------------
# Funções utilitárias
# -----------------------------
import streamlit as st
import json
import re
from math import floor

DATA_FILE = "ww_data.json"

def round_points(value):
    """Arredondamento padrão (round half up)."""
    return floor(value + 0.5)

def safe_parse_porçao(porc):
    """Converte entrada de porção para float (remove 'g', etc)."""
    try:
        return float(re.sub("[^0-9.]", "", str(porc)))
    except:
        return 100.0

def persist_all():
    """Salva alimentos no JSON."""
    with open(DATA_FILE, "w") as f:
        json.dump(st.session_state.alimentos, f, indent=4)

# -----------------------------
# Inicialização da sessão
# -----------------------------
if "alimentos" not in st.session_state:
    try:
        with open(DATA_FILE, "r") as f:
            data_store = json.load(f)
            if isinstance(data_store, list):
                st.session_state.alimentos = data_store
            elif isinstance(data_store, dict) and "alimentos" in data_store:
                st.session_state.alimentos = data_store["alimentos"]
            else:
                st.session_state.alimentos = []
    except FileNotFoundError:
        st.session_state.alimentos = []

# -----------------------------
# Função de cadastro
# -----------------------------
def cadastrar_alimento():
    st.header("➕ Cadastrar Alimento")
    nome = st.text_input("Nome do alimento:", key="cad_nome")
    porcao_in = st.text_input("Porção (g):", key="cad_porc")
    calorias = st.number_input("Calorias (kcal)", min_value=0.0, step=0.1, key="cad_cal")
    carbo = st.number_input("Carboidratos (g)", min_value=0.0, step=0.1, key="cad_car")
    gordura = st.number_input("Gordura (g)", min_value=0.0, step=0.1, key="cad_gor")
    saturada = st.number_input("Gordura Saturada (g)", min_value=0.0, step=0.1, key="cad_sat")
    fibra = st.number_input("Fibra (g)", min_value=0.0, step=0.1, key="cad_fib")
    acucar = st.number_input("Açúcar (g)", min_value=0.0, step=0.1, key="cad_acu")
    proteina = st.number_input("Proteína (g)", min_value=0.0, step=0.1, key="cad_pro")
    sodio_mg = st.number_input("Sódio (mg)", min_value=0.0, step=1.0, key="cad_sod")

    if st.button("Cadastrar alimento", key="bot_cad_alim"):
        if not nome:
            st.error("Informe o nome do alimento!")
            return
        porcao = safe_parse_porçao(porcao_in)

        pontos_raw = (calorias / 50.0) + (carbo / 10.0) + (gordura / 5.0) + (proteina / 5.0) + (sodio_mg / 100.0)
        pontos = round_points(pontos_raw)

        alimento = {
            "Nome": nome,
            "Porcao": porcao,
            "Calorias": round(calorias, 2),
            "Gordura": round(gordura, 2),
            "Saturada": round(saturada, 2),
            "Carbo": round(carbo, 2),
            "Fibra": round(fibra, 2),
            "Açúcar": round(acucar, 2),
            "Proteina": round(proteina, 2),
            "Sodio_mg": round(sodio_mg, 2),
            "Pontos": pontos
        }
        st.session_state.alimentos.append(alimento)
        persist_all()
        st.success(f"Alimento '{nome}' cadastrado com sucesso! Pontos: {pontos}")

# -----------------------------
# FUNÇÃO PARA CALCULAR PONTOS
# -----------------------------
def calcular_pontos(alimento):
    """
    Calcula pontos no estilo WW usando arredondamento half-up.
    Fórmula adaptada (pode ajustar se já tiver a sua oficial).
    """
    cal = alimento.get("Calorias", 0)
    gord = alimento.get("Gordura", 0)
    sat = alimento.get("Saturada", 0)
    acucar = alimento.get("Açúcar", 0)
    prot = alimento.get("Proteina", 0)
    fibra = alimento.get("Fibra", 0)

    pontos = (cal / 33) + (gord / 9) + (sat / 4) + (acucar / 9) - (prot / 10) - (fibra / 12)
    return round_points(pontos)


# -----------------------------
# CONSULTAR + EDITAR/EXCLUIR ALIMENTO
# -----------------------------
def consultar_alimento():
    st.header("🔍 Consultar Alimento")

    if not st.session_state.alimentos:
        st.warning("Nenhum alimento cadastrado ainda.")
        return

    # lista de nomes e escolha
    nomes = [a["Nome"] for a in st.session_state.alimentos]
    escolha = st.selectbox("Escolha o alimento:", nomes, key="consult_select")

    # localizar índice e objeto
    idx = next((i for i, a in enumerate(st.session_state.alimentos) if a["Nome"] == escolha), None)
    if idx is None:
        st.error("Alimento não encontrado.")
        return
    alimento = st.session_state.alimentos[idx]

    # ----- Exibição (mantendo design original) -----
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
                    valor_display = round_points(valor)
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

    st.markdown("---")

    # ----- Botões lado a lado (Editar / Excluir) -----
    col_edit, col_delete = st.columns([1, 1])
    with col_edit:
        if st.button("✏️ Editar este alimento", key=f"edit_btn_{idx}"):
            st.session_state[f"edit_open_{idx}"] = True
    with col_delete:
        if st.button("🗑️ Excluir este alimento", key=f"del_btn_{idx}"):
            st.session_state.alimentos.pop(idx)
            persist_all()
            st.success(f"Alimento '{escolha}' removido com sucesso!")
            rerun_streamlit()

    # ----- Painel de edição (abre só se a flag estiver True) -----
    flag_key = f"edit_open_{idx}"
    if st.session_state.get(flag_key, False):
        st.markdown("---")
        st.subheader(f"Editar '{alimento['Nome']}'")

        # Botão Cancelar fora do formulário
        col_cancel, _ = st.columns([1, 3])
        with col_cancel:
            if st.button("✖️ Cancelar edição", key=f"cancel_edit_{idx}"):
                st.session_state[flag_key] = False
                rerun_streamlit()

        # Formulário de edição
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

            salvar = st.form_submit_button("💾 Salvar alterações")
            if salvar:
                porcao_val = safe_parse_porçao(porcao_novo)

                # Atualiza o alimento com os novos valores antes de recalcular pontos
                alimento.update({
                    "Nome": nome_novo,
                    "Porcao": porcao_val,
                    "Calorias": round(calorias_novo, 2),
                    "Gordura": round(gordura_novo, 2),
                    "Saturada": round(saturada_novo, 2),
                    "Carbo": round(carbo_novo, 2),
                    "Fibra": round(fibra_novo, 2),
                    "Açúcar": round(acucar_novo, 2),
                    "Proteina": round(proteina_novo, 2),
                    "Sodio_mg": round(sodio_novo, 2)
                })

                # Recalcula os pontos usando a função oficial
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

    # solicitar peso inicial se não houver
    if not st.session_state.peso:
        st.warning("⚖️ Por favor, registre seu peso inicial antes de usar o dashboard.")
        registrar_peso()
        st.stop()

    # garantir semana atual e recalcular a partir do histórico (garante gráficos consistentes)
    ensure_current_week_exists()
    rebuild_pontos_semana_from_history()

    peso_atual = st.session_state.peso[-1]

    semana_atual = iso_week_number(datetime.date.today())
    semana_obj = next((w for w in st.session_state.pontos_semana if w["semana"] == semana_atual), {"extras": 36.0})

    st.markdown(
        f"<div style='background-color:#dff9fb;padding:15px;border-radius:10px;text-align:center;font-size:22px;'>"
        f"<b>Pontos consumidos hoje: {st.session_state.consumo_diario:.2f} / {st.session_state.meta_diaria} | Extras disponíveis (semana): {semana_obj.get('extras', 36.0):.2f} | Peso atual: {peso_atual:.2f} kg</b>"
        f"</div>", unsafe_allow_html=True)

    # GRÁFICOS COLORIDOS
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🍽️ Consumo Diário")
        fig1 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=float(st.session_state.consumo_diario),
            gauge={'axis': {'range': [0, st.session_state.meta_diaria]},
                   'bar': {'color': "#e74c3c"},
                   'steps': [
                       {'range': [0, st.session_state.meta_diaria * 0.7], 'color': "#2ecc71"},
                       {'range': [st.session_state.meta_diaria * 0.7, st.session_state.meta_diaria], 'color': "#f1c40f"}
                   ]},
            title={'text': "Pontos Consumidos"}))
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.markdown("### ⭐ Pontos Extras (semana)")
        extras_val = float(semana_obj.get("extras", 36.0))
        fig2 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=extras_val,
            gauge={'axis': {'range': [0, 36]},
                   'bar': {'color': "#006400"},
                   'steps': [
                       {'range': [0, 12], 'color': "#e74c3c"},
                       {'range': [12, 24], 'color': "#f1c40f"},
                       {'range': [24, 36], 'color': "#2ecc71"}
                   ]},
            title={'text': "Pontos Extras Disponíveis (semana)"}))
        st.plotly_chart(fig2, use_container_width=True)

    with col3:
        st.markdown("### ⚖️ Peso Atual")
        if len(st.session_state.peso) == 1:
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

        # criar gauge para peso atual
        min_axis = min(st.session_state.peso) - 5 if st.session_state.peso else 0
        max_axis = max(st.session_state.peso) + 5 if st.session_state.peso else 100
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=st.session_state.peso[-1],
            gauge={'axis': {'range': [min_axis, max_axis]},
                   'bar': {'color': cor_gauge}},
            title={'text': f"Peso Atual {tendencia}"}))
        st.plotly_chart(fig_gauge, use_container_width=True)

    # HISTÓRICO PESO / PONTOS SEMANAIS lado a lado
    col_hist1, col_hist2 = st.columns(2)

    with col_hist1:
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
            st.write(f"{d.strftime('%d/%m/%Y')}: {p:.2f} kg {tendencia}")

    with col_hist2:
        st.markdown("### 📊 Pontos Semanais (últimas 4 semanas)")
        ensure_current_week_exists()
        semanas_a_mostrar = st.session_state.pontos_semana[-4:]
        if not semanas_a_mostrar:
            st.write(" - (sem registros)")
        for semana in semanas_a_mostrar:
            st.write(f"Semana {semana['semana']}:")
            if not semana.get("pontos"):
                st.write(" - (sem registros)")
            for reg in semana.get("pontos", []):
                dia = reg["data"].strftime("%d/%m/%Y") if isinstance(reg["data"], datetime.date) else str(reg["data"])
                dia_sem = weekday_name_br(reg["data"]) if isinstance(reg["data"], datetime.date) else ""
                usados = f" - usou extras: {reg.get('usou_extras',0.0):.2f} pts" if reg.get("usou_extras", 0.0) else ""
                st.write(f"- {dia} ({dia_sem}): {reg['nome']} {reg['quantidade']:.2f}g ({reg['pontos']:.2f} pts){usados}")

    # TENDÊNCIA DE PESO ABAIXO (gráfico full width)
    st.markdown("### 📈 Tendência de Peso")
    if st.session_state.peso:
        df_peso = pd.DataFrame({"Data": [d.isoformat() for d in st.session_state.datas_peso], "Peso": st.session_state.peso})
        df_peso["Data_dt"] = pd.to_datetime(df_peso["Data"])
        fig_line = go.Figure(go.Scatter(
            x=list(df_peso["Data_dt"]),
            y=list(df_peso["Peso"]),
            mode="lines+markers",
            line=dict(color="#8e44ad", width=3),
            marker=dict(size=8)
        ))
        fig_line.update_layout(yaxis_title="Peso (kg)", xaxis_title="Data", template="plotly_white")
        st.plotly_chart(fig_line, use_container_width=True)

# -----------------------------
# ROTAS / PAGES
# -----------------------------
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
elif st.session_state.menu == "🚪 Sair":
    st.stop()

# Persistir ao final (garante salvamento de mudanças feitas fora dos botões)
persist_all()
