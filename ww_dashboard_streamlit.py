# ww_dashboard_streamlit.py
# Versão integrada com suporte a múltiplos usuários (compartilha alimentos, dados restritos por usuário)
# Mantive suas funções originais; adicionei apenas o necessário para autenticação e persistência por usuário.

import streamlit as st
import json
import re
import os
import datetime
import hashlib
import plotly.graph_objects as go
import pandas as pd
from math import floor

# -----------------------------
# UTILITÁRIOS GERAIS
# -----------------------------
DATA_FILE = "ww_data.json"

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
    # round half up
    if p - int(p) < 0.5:
        return int(p)
    else:
        return int(p) + 1

def load_data():
    """Carrega o JSON. Se for lista (antigo), converte para dict com 'alimentos'."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Normalizar formato: lista antiga -> {'alimentos': [...], 'usuarios': {}}
            if isinstance(data, list):
                return {"alimentos": data, "usuarios": {}}
            if isinstance(data, dict):
                # garantir chaves
                if "alimentos" not in data:
                    data["alimentos"] = []
                if "usuarios" not in data:
                    data["usuarios"] = {}
                return data
            # fallback
            return {"alimentos": [], "usuarios": {}}
        except Exception:
            return {"alimentos": [], "usuarios": {}}
    return {"alimentos": [], "usuarios": {}}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str, indent=2)
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")

def iso_week_number(date_obj):
    return date_obj.isocalendar()[1]

def weekday_name_br(dt: datetime.date):
    days = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    return days[dt.weekday()]

# -----------------------------
# AUTENTICAÇÃO SIMPLES (hash de senha)
# -----------------------------
def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()

def cadastrar_usuario(usuario: str, senha: str):
    data = load_data()
    if not usuario:
        return False, "Nome de usuário vazio"
    if "usuarios" not in data:
        data["usuarios"] = {}
    if usuario in data["usuarios"]:
        return False, "Usuário já existe"
    data["usuarios"][usuario] = {
        "senha": hash_senha(senha),
        "peso": [],
        "datas_peso": [],
        "consumo_diario": 0.0,
        "meta_diaria": 29,
        "extras": 36.0,
        "consumo_historico": [],
        "pontos_semana": []
    }
    save_data(data)
    return True, "Usuário cadastrado com sucesso"

def login_usuario(usuario: str, senha: str):
    data = load_data()
    if "usuarios" not in data or usuario not in data["usuarios"]:
        return False
    if data["usuarios"][usuario]["senha"] != hash_senha(senha):
        return False
    st.session_state.usuario_logado = usuario
    return True

def logout_usuario():
    if "usuario_logado" in st.session_state:
        del st.session_state["usuario_logado"]

# -----------------------------
# RERUN COMPATÍVEL
# -----------------------------
def rerun_streamlit():
    """Tenta reiniciar o script de forma compatível com diferentes versões do Streamlit."""
    try:
        # Experimental rerun (padrão)
        if hasattr(st, "experimental_rerun") and callable(st.experimental_rerun):
            st.experimental_rerun()
            return
    except Exception:
        pass
    # fallback
    try:
        st.stop()
    except Exception:
        pass

# -----------------------------
# CONFIGURAÇÃO INICIAL STREAMLIT
# -----------------------------
st.set_page_config(page_title="Vigilantes do Peso Brasil", layout="wide")

# -----------------------------
# CARREGAR DADOS PERSISTIDOS (GLOBAIS)
# -----------------------------
data_store = load_data()

# -----------------------------
# INICIALIZAÇÃO DO SESSION_STATE
# -----------------------------
if "menu" not in st.session_state:
    st.session_state.menu = "🏠 Dashboard"

# garantir lista de alimentos global
if "alimentos" not in st.session_state:
    st.session_state.alimentos = data_store.get("alimentos", [])

# usuario logado: se já tiver em session, manter; senão, não carregar dados privados
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

# se houver usuário logado, inicializar os dados do usuário na sessão
def init_user_session(usuario):
    # carrega data_store atualizado
    global data_store
    data_store = load_data()
    users = data_store.get("usuarios", {})
    ud = users.get(usuario, None)
    if ud is None:
        # criar estrutura básica se não existir
        data_store.setdefault("usuarios", {})
        data_store["usuarios"].setdefault(usuario, {
            "senha": "",
            "peso": [],
            "datas_peso": [],
            "consumo_diario": 0.0,
            "meta_diaria": 29,
            "extras": 36.0,
            "consumo_historico": [],
            "pontos_semana": []
        })
        save_data(data_store)
        ud = data_store["usuarios"][usuario]

    # carregar no session_state (dados do usuário)
    st.session_state.peso = ud.get("peso", [])
    st.session_state.datas_peso = [datetime.date.fromisoformat(d) for d in ud.get("datas_peso", [])] if ud.get("datas_peso") else []
    st.session_state.consumo_diario = float(ud.get("consumo_diario", 0.0))
    st.session_state.meta_diaria = ud.get("meta_diaria", 29)
    st.session_state.extras = float(ud.get("extras", 36.0))
    # historico e pontos semanais já em objetos (datas podem ser isoformat strings)
    ch = ud.get("consumo_historico", [])
    # converter datas se necessário
    for r in ch:
        if isinstance(r.get("data"), str):
            try:
                r["data"] = datetime.date.fromisoformat(r["data"])
            except Exception:
                pass
    st.session_state.consumo_historico = ch

    ps = ud.get("pontos_semana", [])
    for w in ps:
        for reg in w.get("pontos", []):
            if isinstance(reg.get("data"), str):
                try:
                    reg["data"] = datetime.date.fromisoformat(reg["data"])
                except Exception:
                    pass
    st.session_state.pontos_semana = ps

    # alimentos unificados (garantir)
    st.session_state.alimentos = data_store.get("alimentos", [])

# persist_all -> agora salva dados do usuário + alimentos
def persist_all():
    """
    Persiste os dados em ww_data.json.
    Salva:
      - alimentos (unificados)
      - dados do usuário logado (peso, históricos, pontos_semana, etc.)
    """
    data = load_data()  # começa com formato normalizado
    # atualizar alimentos
    data["alimentos"] = st.session_state.alimentos

    usuario = st.session_state.get("usuario_logado", None)
    if usuario:
        data.setdefault("usuarios", {})
        # converter datas_peso para isoformat
        ds_peso_iso = [d.isoformat() for d in st.session_state.datas_peso]
        # converter consumo_historico datas
        ch_serial = []
        for r in st.session_state.consumo_historico:
            ch_serial.append({
                "data": r["data"].isoformat() if isinstance(r.get("data"), datetime.date) else str(r.get("data")),
                "nome": r["nome"],
                "quantidade": r["quantidade"],
                "pontos": r["pontos"],
                "usou_extras": r.get("usou_extras", 0.0)
            })
        ps_serial = []
        for w in st.session_state.pontos_semana:
            ps_serial.append({
                "semana": w.get("semana"),
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
            })
        # se usuário existir em data, preservamos a senha
        senha_hash = data.get("usuarios", {}).get(usuario, {}).get("senha", "")
        data["usuarios"][usuario] = {
            "senha": senha_hash,
            "peso": st.session_state.peso,
            "datas_peso": ds_peso_iso,
            "consumo_diario": float(st.session_state.consumo_diario),
            "meta_diaria": st.session_state.meta_diaria,
            "extras": float(st.session_state.extras),
            "consumo_historico": ch_serial,
            "pontos_semana": ps_serial
        }
    # salvar
    save_data(data)

# -----------------------------
# FUNÇÕES DE RECONSTRUÇÃO / RESET, iguais às suas mas adaptadas ao per-user
# -----------------------------
def reset_historico():
    """Zera histórico do usuário logado (peso, consumo, pontos)."""
    if not st.session_state.get("usuario_logado"):
        st.warning("Nenhum usuário logado para resetar histórico.")
        return
    st.session_state.peso = []
    st.session_state.datas_peso = []
    st.session_state.consumo_historico = []
    st.session_state.pontos_semana = []
    st.session_state.extras = 36.0
    st.session_state.consumo_diario = 0.0
    persist_all()
    st.success("Histórico de peso e pontos zerado com sucesso!")

def ensure_current_week_exists():
    hoje = datetime.date.today()
    week = iso_week_number(hoje)
    if not st.session_state.pontos_semana or st.session_state.pontos_semana[-1].get("semana") != week:
        st.session_state.pontos_semana.append({"semana": week, "pontos": [], "extras": 36.0})
        st.session_state.extras = 36.0
        persist_all()

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
# UI: LOGIN / CADASTRO (antes do menu)
# -----------------------------
# Se o usuário não estiver logado, mostramos tela de login/cadastro e paramos a execução principal.
if not st.session_state.get("usuario_logado"):
    st.sidebar.title("🔐 Autenticação")
    st.header("🔐 Login")
    usuario_input = st.text_input("Usuário", key="ui_user")
    senha_input = st.text_input("Senha", type="password", key="ui_pass")
    if st.button("Entrar", key="btn_login"):
        ok = login_usuario(usuario_input.strip(), senha_input or "")
        if ok:
            st.success(f"Bem-vindo(a), {usuario_input}!")
            # inicializa sessão do usuário com dados
            init_user_session(usuario_input.strip())
            # recarregar a página para aplicar menu/estado do usuário
            rerun_streamlit()
        else:
            st.error("Usuário ou senha incorretos")

    st.markdown("---")
    st.subheader("Cadastrar novo usuário")
    novo_usuario = st.text_input("Novo usuário", key="ui_new_user")
    nova_senha = st.text_input("Senha", type="password", key="ui_new_pass")
    if st.button("Cadastrar", key="btn_cad"):
        ok, msg = cadastrar_usuario(novo_usuario.strip(), nova_senha or "")
        if ok:
            st.success(msg + " — faça login agora.")
        else:
            st.error(msg)
    st.stop()  # para não renderizar o resto sem usuário

# Se chegou até aqui, há um usuário logado — assegure que sessão do usuário esteja inicializada
if st.session_state.get("usuario_logado"):
    # garante carregamento dos dados do usuário na sessão
    init_user_session(st.session_state.usuario_logado)

# -----------------------------
# NAVEGAÇÃO (botões laterais)
# -----------------------------
st.sidebar.title("📋 Menu")

menu_itens = [
    ("🏠 Dashboard", "dashboard"),
    ("🍴 Registrar Consumo", "consumo"),
    ("⚖️ Registrar Peso", "peso"),
    ("📂 Importar Alimentos", "importar"),
    ("➕ Cadastrar Alimento", "cadastrar"),
    ("🔍 Consultar Alimento", "consultar"),
    ("🔄 Resetar Semana", "resetar_semana"),
    ("🚪 Sair", "sair"),
]

# Inicializa menu se não existir
if "menu" not in st.session_state:
    st.session_state.menu = "dashboard"

# Botões laterais
for label, key in menu_itens:
    if st.sidebar.button(label, key=f"sidebtn_{key}", use_container_width=True):
        st.session_state.menu = key
        # força refresh simples
        rerun_streamlit()

# -----------------------------
# CARREGAR DADOS (variáveis locais para facilitar)
# -----------------------------
data = load_data()  # data global
usuario_atual = st.session_state.get("usuario_logado")

# -----------------------------
# AÇÃO: RESETAR SEMANA (apenas quando escolha no menu)
# -----------------------------
if st.session_state.menu == "resetar_semana":
    # ação: zera apenas os dados do usuário atual (conforme pedido)
    hoje = datetime.date.today()
    semana_atual = hoje.isocalendar()[1]

    # Zerar pontos da semana atual
    if "pontos_semana" in st.session_state:
        st.session_state.pontos_semana = [w for w in st.session_state.pontos_semana if w.get("semana") != semana_atual]
    else:
        st.session_state.pontos_semana = []

    # Adiciona semana vazia atual
    st.session_state.pontos_semana.append({
        "semana": semana_atual,
        "pontos": [],
        "extras": 36.0
    })

    # Zerar consumo diário e extras do usuário
    st.session_state.extras = 36.0
    st.session_state.consumo_diario = 0.0

    # Remove registros da semana atual do histórico do usuário
    if "consumo_historico" in st.session_state:
        # proteger caso datas sejam strings
        novo_hist = []
        for r in st.session_state.consumo_historico:
            d = r.get("data")
            if isinstance(d, str):
                try:
                    d = datetime.date.fromisoformat(d)
                except Exception:
                    # se não for parseable, manter (ou remover?) -> manter por segurança
                    novo_hist.append(r)
                    continue
            if iso_week_number(d) != semana_atual:
                novo_hist.append(r)
        st.session_state.consumo_historico = novo_hist

    # persistir
    persist_all()
    st.success(f"✅ Semana {semana_atual} resetada com sucesso para {usuario_atual}!")
    # voltar para dashboard
    st.session_state.menu = "dashboard"
    rerun_streamlit()

# -----------------------------
# FUNÇÕES PRINCIPAIS (importar, cadastrar, registrar consumo e peso)
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
            # adicionar sem duplicatas por nome (mantendo existente)
            nomes_exist = {a["Nome"] for a in st.session_state.alimentos}
            adicionados = 0
            for a in alimentos_novos:
                if a["Nome"] not in nomes_exist:
                    st.session_state.alimentos.append(a)
                    adicionados += 1
            persist_all()
            st.success(f"📂 Importadas {adicionados} linhas novas. Total agora: {len(st.session_state.alimentos)} alimentos.")
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
        # evitar duplicatas por nome
        nomes_exist = {a["Nome"] for a in st.session_state.alimentos}
        if nome in nomes_exist:
            st.error("Alimento com esse nome já existe.")
            return
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
            try:
                porcao_val = float(porcao_ref)
            except Exception:
                st.error("Erro ao interpretar porção do alimento selecionado.")
                return

            pontos_registrados_raw = float(alimento.get("Pontos", 0.0)) * (quantidade / porcao_val if porcao_val > 0 else 0.0)
            pontos_registrados = round_points(pontos_registrados_raw)

            registro = {"data": datetime.date.today(), "nome": escolha, "quantidade": float(quantidade), "pontos": pontos_registrados, "usou_extras": 0.0}
            st.session_state.consumo_historico.append(registro)

            rebuild_pontos_semana_from_history()
            persist_all()

            st.success(f"🍴 Registrado {quantidade:.2f}g de {escolha}. Pontos: {pontos_registrados:.2f}. Total hoje: {st.session_state.consumo_diario:.2f}")
            rerun_streamlit()

    # Histórico com opções de editar/excluir
    st.markdown("### Histórico de Consumo (últimos registros)")
    if not st.session_state.consumo_historico:
        st.info("Nenhum consumo registrado ainda.")
    else:
        # mostrar em ordem reversa (mais recente primeiro)
        for idx in range(len(st.session_state.consumo_historico) - 1, -1, -1):
            reg = st.session_state.consumo_historico[idx]
            data_r = reg["data"]
            dia_sem = weekday_name_br(data_r) if isinstance(data_r, datetime.date) else ""
            display = f"{data_r.strftime('%d/%m/%Y')} ({dia_sem}): {reg['nome']} — {reg['quantidade']:.2f} g — {reg['pontos']:.2f} pts"
            if reg.get("usou_extras", 0.0):
                display += f" — usou extras: {reg.get('usou_extras',0.0):.2f} pts"
            cols = st.columns([6, 1, 1])
            cols[0].write(display)

            # editar
            if cols[1].button("Editar", key=f"edit_cons_{idx}"):
                edit_key_q = f"edit_q_{idx}"
                save_key = f"save_cons_{idx}"
                with st.expander(f"Editar registro #{idx}", expanded=True):
                    new_q = st.number_input("Quantidade (g):", min_value=0.0, step=1.0, value=reg["quantidade"], key=edit_key_q)
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
                        rerun_streamlit()

            # excluir
            if cols[2].button("Excluir", key=f"del_cons_{idx}"):
                st.session_state.consumo_historico.pop(idx)
                rebuild_pontos_semana_from_history()
                persist_all()
                st.success("Registro excluído.")
                rerun_streamlit()

def registrar_peso():
    st.header("⚖️ Registrar Peso")
    with st.form("form_peso"):
        peso_novo = st.number_input("Informe seu peso (kg):", min_value=0.0, step=0.1, format="%.2f", key="input_peso_reg")
        submitted = st.form_submit_button("Registrar peso")
        if submitted:
            st.session_state.peso.append(float(peso_novo))
            st.session_state.datas_peso.append(datetime.date.today())
            persist_all()
            st.success(f"Peso {peso_novo:.2f} kg registrado com sucesso!")
            rerun_streamlit()

# -----------------------------
# FUNÇÕES AUXILIARES (de exibição/consulta)
# -----------------------------
def round_points_util(value):
    return floor(value + 0.5)

def calcular_pontos(alimento):
    cal = alimento.get("Calorias", 0)
    gord = alimento.get("Gordura", 0)
    sat = alimento.get("Saturada", 0)
    acucar = alimento.get("Açúcar", 0)
    prot = alimento.get("Proteina", 0)
    fibra = alimento.get("Fibra", 0)
    pontos = (cal / 33) + (gord / 9) + (sat / 4) + (acucar / 9) - (prot / 10) - (fibra / 12)
    return round_points(pontos)

def consultar_alimento():
    st.header("🔍 Consultar Alimento")
    if not st.session_state.alimentos:
        st.warning("Nenhum alimento cadastrado ainda.")
        return
    nomes = [a["Nome"] for a in st.session_state.alimentos]
    escolha = st.selectbox("Escolha o alimento:", nomes, key="consult_select")
    idx = next((i for i, a in enumerate(st.session_state.alimentos) if a["Nome"] == escolha), None)
    if idx is None:
        st.error("Alimento não encontrado.")
        return
    alimento = st.session_state.alimentos[idx]
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
            salvar = st.form_submit_button("💾 Salvar alterações")
            if salvar:
                porcao_val = safe_parse_porçao(porcao_novo)
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
                alimento["Pontos"] = calcular_pontos(alimento)
                persist_all()
                st.session_state[flag_key] = False
                st.success(f"Alimento '{nome_novo}' atualizado com sucesso! Pontos: {alimento['Pontos']}")
                rerun_streamlit()

# -----------------------------
# DASHBOARD PRINCIPAL
# -----------------------------
if st.session_state.menu == "dashboard":
    st.markdown("<h1 style='text-align: center; color: #2c3e50;'>🍏 Vigilantes do Peso Brasil</h1>", unsafe_allow_html=True)

    # Solicitar peso inicial se não houver
    if not st.session_state.peso:
        st.warning("⚖️ Por favor, registre seu peso inicial antes de usar o dashboard.")
        registrar_peso()
        st.stop()

    # Recalcular/exibir
    ensure_current_week_exists()
    rebuild_pontos_semana_from_history()

    peso_atual = st.session_state.peso[-1] if st.session_state.peso else None

    semana_atual = iso_week_number(datetime.date.today())
    semana_obj = next((w for w in st.session_state.pontos_semana if w.get("semana") == semana_atual), {"extras": 36.0})

    consumo_diario = st.session_state.consumo_diario if st.session_state.consumo_diario is not None else 0.0
    meta_diaria = st.session_state.meta_diaria if st.session_state.meta_diaria is not None else 29
    extras_semana = semana_obj.get("extras", 36.0)

    peso_text = f"{peso_atual:.2f} kg" if peso_atual is not None else "-"

    st.markdown(
        f"<div style='background-color:#dff9fb;padding:15px;border-radius:10px;text-align:center;font-size:22px;'>"
        f"<b>Pontos consumidos hoje: {consumo_diario:.2f} / {meta_diaria} | Extras disponíveis (semana): {extras_semana:.2f} | Peso atual: {peso_text}</b>"
        f"</div>", unsafe_allow_html=True)

    # GRÁFICOS COLORIDOS
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🍽️ Consumo Diário")
        fig1 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=float(consumo_diario),
            gauge={'axis': {'range': [0, meta_diaria]},
                   'bar': {'color': "#e74c3c"},
                   'steps': [
                       {'range': [0, meta_diaria * 0.7], 'color': "#2ecc71"},
                       {'range': [meta_diaria * 0.7, meta_diaria], 'color': "#f1c40f"}
                   ]},
            title={'text': "Pontos Consumidos"}))
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.markdown("### ⭐ Pontos Extras (semana)")
        extras_val = float(extras_semana)
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
        if not st.session_state.peso:
            cor_gauge = "blue"
            tendencia = "➖"
            valor_gauge = 0
            min_axis = 0
            max_axis = 100
        else:
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
            valor_gauge = st.session_state.peso[-1]
            min_axis = min(st.session_state.peso) - 5 if st.session_state.peso else 0
            max_axis = max(st.session_state.peso) + 5 if st.session_state.peso else 100

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=valor_gauge,
            gauge={'axis': {'range': [min_axis, max_axis]},
                   'bar': {'color': cor_gauge}},
            title={'text': f"Peso Atual {tendencia}"}))
        st.plotly_chart(fig_gauge, use_container_width=True)

    # HISTÓRICO PESO / PONTOS SEMANAIS lado a lado
    col_hist1, col_hist2 = st.columns(2)

    with col_hist1:
        st.markdown("### ⚖️ Histórico de Peso")
        if not st.session_state.peso:
            st.write(" - (sem registros)")
        else:
            for i, (p, d) in enumerate(zip(st.session_state.peso, st.session_state.datas_peso)):
                if i == 0:
                    tendencia = "➖"
                else:
                    if p < st.session_state.peso[i - 1]:
                        tendencia = "⬇️"
                    elif p > st.session_state.peso[i - 1]:
                        tendencia = "⬆️"
                    else:
                        tendência = "➖"
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

    # TENDÊNCIA DE PESO (gráfico)
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
# ROTAS / PAGES (menu)
# -----------------------------
elif st.session_state.menu == "importar":
    importar_planilha()
elif st.session_state.menu == "cadastrar":
    cadastrar_alimento()
elif st.session_state.menu == "consumo":
    registrar_consumo()
elif st.session_state.menu == "peso":
    registrar_peso()
elif st.session_state.menu == "consultar":
    consultar_alimento()
elif st.session_state.menu == "sair":
    # Efetuar logout e recarregar para tela de login
    logout_usuario()
    st.success("Logout efetuado.")
    rerun_streamlit()

# Persistir ao final (garante salvamento de mudanças feitas fora dos botões)
persist_all()










