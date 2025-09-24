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
    if "alimentos" in st.session_state:
        with open(DATA_FILE, "w") as f:
            json.dump(st.session_state.alimentos, f, indent=4)

# -----------------------------
# Inicialização da sessão
# -----------------------------
if "alimentos" not in st.session_state:
    try:
        with open(DATA_FILE, "r") as f:
            data_store = json.load(f)
            # sempre garantir lista
            if isinstance(data_store, list):
                st.session_state.alimentos = data_store
            elif isinstance(data_store, dict) and "alimentos" in data_store:
                st.session_state.alimentos = data_store["alimentos"]
            else:
                st.session_state.alimentos = []
    except FileNotFoundError:
        st.session_state.alimentos = []
