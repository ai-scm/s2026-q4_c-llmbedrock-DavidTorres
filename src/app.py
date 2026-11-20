# src/app.py
import os
import streamlit as st
from dotenv import load_dotenv
from prompts import EXPERT_PROFILES
from bedrock_client import invoke_bedrock_chat
from storage import (
    load_all_conversations,
    create_conversation,
    update_conversation,
    delete_conversation,
)

load_dotenv()

st.set_page_config(
    page_title="AWS CLF-C02 Tutor · Claude Style",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="expanded",
)

QUICK_PROMPTS = {
    "🏛️ Arquitecto Cloud (Conceptos y Well-Architected)": [
        "Explícame los 6 pilares del Well-Architected Framework con ejemplos",
        "¿Cuál es la diferencia entre CAPEX y OPEX en la nube?",
        "Resume las 6 perspectivas del AWS Cloud Adoption Framework (CAF)",
    ],
    "🛡️ Especialista en Seguridad (IAM, KMS y Cumplimiento)": [
        "¿Cómo funciona el Modelo de Responsabilidad Compartida en EC2 vs S3?",
        "Diferencia entre Usuario IAM, Grupo, Rol y Política",
        "¿Cuándo usar AWS WAF frente a AWS Shield?",
    ],
    "⚙️ Ingeniero de Servicios Core (Cómputo, Red y Datos)": [
        "Compara Amazon S3, EBS y EFS en una tabla",
        "Diferencia clave entre Security Groups y NACLs",
        "¿Cuándo elegir Amazon RDS frente a DynamoDB?",
    ],
    "💰 Consultor FinOps (Facturación, Precios y Soporte)": [
        "Compara On-Demand, Savings Plans, Reserved y Spot Instances",
        "Diferencia entre AWS Budgets, Cost Explorer y Pricing Calculator",
        "¿Qué incluye el plan Business Support frente a Developer?",
    ],
    "📝 Evaluador de Examen (Simulador CLF-C02)": [
        "Dame una pregunta tipo examen sobre Seguridad e IAM",
        "Dame una pregunta tipo examen sobre S3 y almacenamiento",
        "Dame una pregunta aleatoria difícil del examen CLF-C02",
    ],
}

# --- Estilos CSS inspirados en Claude ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap');

    .stApp {
        background-color: #FAF9F5;
        color: #141413;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    header[data-testid="stHeader"] {
        background-color: rgba(250, 249, 245, 0.85);
        backdrop-filter: blur(8px);
    }
    #MainMenu, footer, .stDeployButton {
        visibility: hidden;
    }

    /* Barra lateral estilo Claude */
    section[data-testid="stSidebar"] {
        background-color: #F0EEE6;
        border-right: 1px solid #E3E0D5;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background-color: transparent;
        color: #2C2B28;
        border: 1px solid transparent;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 400;
        text-align: left;
        justify-content: flex-start;
        padding: 0.45rem 0.65rem;
        transition: all 0.15s ease;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #E5E2D7;
        color: #141413;
    }

    /* Saludo editorial centrado */
    .claude-welcome-box {
        text-align: center;
        padding: 2.2rem 1rem 1.4rem 1rem;
    }
    .claude-sparkle {
        color: #D97757;
        font-size: 2.2rem;
        margin-bottom: 0.4rem;
    }
    .claude-title {
        font-family: 'Newsreader', Georgia, serif;
        font-size: 2.1rem;
        font-weight: 500;
        color: #141413;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
    }
    .claude-subtitle {
        font-size: 0.96rem;
        color: #5E5D59;
        max-width: 540px;
        margin: 0 auto 1.5rem auto;
        line-height: 1.55;
    }

    /* Tarjetas de sugerencias rápidas */
    .main div[data-testid="stHorizontalBlock"] .stButton > button {
        background-color: #F4F2EA;
        color: #2C2B28;
        border: 1px solid #E2DFD3;
        border-radius: 12px;
        padding: 0.75rem 0.9rem;
        font-size: 0.84rem;
        line-height: 1.4;
        text-align: left;
        height: 100%;
        transition: all 0.18s ease;
    }
    .main div[data-testid="stHorizontalBlock"] .stButton > button:hover {
        background-color: #FFFFFF;
        border-color: #D97757;
        box-shadow: 0 2px 8px rgba(20, 20, 19, 0.05);
    }

    /* Mensajes del chat */
    div[data-testid="stChatMessage"] {
        background-color: transparent;
        padding: 0.9rem 0.2rem;
        gap: 0.9rem;
    }
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
        background-color: #F0EEE6;
        border-radius: 16px;
        padding: 0.95rem 1.15rem;
        margin: 0.4rem 0;
        border: 1px solid #E5E2D7;
    }
    div[data-testid="stChatMessage"] p,
    div[data-testid="stChatMessage"] li {
        font-size: 0.98rem;
        line-height: 1.65;
        color: #1A1918;
    }

    /* Caja de entrada inferior */
    div[data-testid="stChatInput"] {
        background-color: #FAF9F5;
    }
    div[data-testid="stChatInput"] > div {
        background-color: #FFFFFF;
        border: 1px solid #DCD8CA;
        border-radius: 16px;
        box-shadow: 0 4px 16px rgba(20, 20, 19, 0.06);
    }
    div[data-testid="stChatInput"] > div:focus-within {
        border-color: #D97757;
        box-shadow: 0 4px 20px rgba(217, 119, 87, 0.14);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Cargar conversaciones persistentes ---
all_chats = load_all_conversations()
default_profile = list(EXPERT_PROFILES.keys())[0]

# Si no hay ninguna conversación guardada, creamos la primera automáticamente
if not all_chats:
    first_id = create_conversation(default_profile)
    all_chats = load_all_conversations()
    st.session_state.active_chat_id = first_id

if (
    "active_chat_id" not in st.session_state
    or st.session_state.active_chat_id not in all_chats
):
    # Seleccionar la conversación más reciente
    sorted_ids = sorted(
        all_chats.keys(),
        key=lambda cid: all_chats[cid].get("updated_at", ""),
        reverse=True,
    )
    st.session_state.active_chat_id = sorted_ids[0]

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

active_chat = all_chats[st.session_state.active_chat_id]
active_profile = active_chat.get("profile", default_profile)
if active_profile not in EXPERT_PROFILES:
    active_profile = default_profile

# --- Barra Lateral: Nueva conversación, Perfil e Historial ---
with st.sidebar:
    st.markdown("### ✦ AWS Cloud Tutor")
    st.caption("Preparación CLF-C02 · Amazon Bedrock")

    if st.button("＋  Nueva conversación", use_container_width=True, type="primary"):
        new_id = create_conversation(active_profile)
        st.session_state.active_chat_id = new_id
        st.session_state.pending_prompt = None
        st.rerun()

    st.markdown("---")
    st.markdown("**Especialidad del chat actual**")
    profile_choice = st.selectbox(
        "Perfil",
        options=list(EXPERT_PROFILES.keys()),
        index=list(EXPERT_PROFILES.keys()).index(active_profile),
        label_visibility="collapsed",
    )

    if profile_choice != active_profile:
        active_profile = profile_choice
        update_conversation(
            chat_id=st.session_state.active_chat_id,
            messages=active_chat["messages"],
            profile=active_profile,
            tokens=active_chat.get("tokens"),
        )
        st.rerun()

    current_profile_data = EXPERT_PROFILES[active_profile]
    st.caption(current_profile_data["short_desc"])

    st.markdown("---")
    st.markdown("**Recientes**")

    # Ordenar chats del más reciente al más antiguo
    sorted_chats = sorted(
        all_chats.values(),
        key=lambda c: c.get("updated_at", ""),
        reverse=True,
    )

    for chat in sorted_chats:
        cid = chat["id"]
        is_current = cid == st.session_state.active_chat_id
        role_icon = chat.get("profile", default_profile).split(" ")[0]
        prefix = "● " if is_current else ""
        label = f"{prefix}{role_icon} {chat['title']}"

        col_chat, col_del = st.columns([0.84, 0.16])
        with col_chat:
            if st.button(label, key=f"select_{cid}", use_container_width=True):
                st.session_state.active_chat_id = cid
                st.session_state.pending_prompt = None
                st.rerun()
        with col_del:
            if st.button("✕", key=f"del_{cid}", help="Eliminar conversación"):
                delete_conversation(cid)
                if is_current:
                    remaining = load_all_conversations()
                    if remaining:
                        st.session_state.active_chat_id = list(remaining.keys())[0]
                    else:
                        st.session_state.active_chat_id = create_conversation(active_profile)
                st.rerun()

    st.markdown("---")
    with st.expander("⚙️ Modelo y consumo del chat", expanded=False):
        region = os.getenv("AWS_REGION", "us-east-1")
        model_id = os.getenv("MODEL_ID", "No configurado")
        chat_tokens = active_chat.get("tokens", {"input": 0, "output": 0})
        st.markdown(f"**Región:** `{region}`")
        st.markdown(f"**Modelo:** `{model_id}`")
        col1, col2 = st.columns(2)
        col1.metric("Entrada", chat_tokens.get("input", 0))
        col2.metric("Salida", chat_tokens.get("output", 0))

# --- Área Principal ---
messages = active_chat.get("messages", [])

if not messages:
    clean_title = active_profile.split(" ", 1)[1]
    st.markdown(
        f"""
        <div class="claude-welcome-box">
            <div class="claude-sparkle">✦</div>
            <div class="claude-title">{clean_title}</div>
            <div class="claude-subtitle">{current_profile_data["short_desc"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    suggestions = QUICK_PROMPTS.get(active_profile, [])
    if suggestions:
        cols = st.columns(len(suggestions))
        for idx, suggestion in enumerate(suggestions):
            with cols[idx]:
                if st.button(suggestion, key=f"sug_{idx}", use_container_width=True):
                    st.session_state.pending_prompt = suggestion
                    st.rerun()

# Renderizar mensajes de la conversación activa
for msg in messages:
    avatar = "👤" if msg["role"] == "user" else "✨"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Entrada del estudiante
typed_prompt = st.chat_input("Escribe tu pregunta sobre AWS Cloud Practitioner...")
user_prompt = st.session_state.pending_prompt or typed_prompt
if st.session_state.pending_prompt:
    st.session_state.pending_prompt = None

if user_prompt:
    messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_prompt)

    with st.chat_message("assistant", avatar="✨"):
        with st.spinner("Pensando..."):
            response_text, metadata = invoke_bedrock_chat(
                messages=messages,
                system_prompt=current_profile_data["system_prompt"],
            )
            st.markdown(response_text)

            chat_tokens = active_chat.get("tokens", {"input": 0, "output": 0, "total": 0})
            if metadata:
                st.caption(
                    f"✦ {metadata.get('latency_ms', 0)} ms · "
                    f"{metadata.get('total_tokens', 0)} tokens"
                )
                chat_tokens["input"] = chat_tokens.get("input", 0) + metadata.get("input_tokens", 0)
                chat_tokens["output"] = chat_tokens.get("output", 0) + metadata.get("output_tokens", 0)
                chat_tokens["total"] = chat_tokens.get("total", 0) + metadata.get("total_tokens", 0)

    messages.append({"role": "assistant", "content": response_text})

    # Guardar conversación actualizada en disco
    update_conversation(
        chat_id=st.session_state.active_chat_id,
        messages=messages,
        profile=active_profile,
        tokens=chat_tokens,
    )
    st.rerun()