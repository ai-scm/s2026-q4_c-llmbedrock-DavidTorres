# src/app.py
import os
import streamlit as st
from dotenv import load_dotenv
from prompts import EXPERT_PROFILES
from bedrock_client import invoke_bedrock_chat

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Configuración general de la página
st.set_page_config(
    page_title="Tutor AWS Cloud Practitioner | Bedrock",
    page_icon="☁️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# --- Inicialización del Estado de Sesión ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "selected_profile" not in st.session_state:
    st.session_state.selected_profile = list(EXPERT_PROFILES.keys())[0]

if "session_tokens" not in st.session_state:
    st.session_state.session_tokens = {"input": 0, "output": 0, "total": 0}

# --- Barra Lateral: Configuración del Agente y Estado ---
with st.sidebar:
    st.title("☁️ AWS CLF-C02 Tutor")
    st.caption("Asistente especializado con Amazon Bedrock")
    st.divider()

    st.subheader("🎯 Perfil del Experto")
    profile_choice = st.selectbox(
        "Selecciona el enfoque de estudio:",
        options=list(EXPERT_PROFILES.keys()),
        index=list(EXPERT_PROFILES.keys()).index(st.session_state.selected_profile),
    )

    # Detectar cambio de perfil para reiniciar el contexto de conversación
    if profile_choice != st.session_state.selected_profile:
        st.session_state.selected_profile = profile_choice
        st.session_state.messages = []
        st.rerun()

    current_profile_data = EXPERT_PROFILES[st.session_state.selected_profile]
    st.info(current_profile_data["short_desc"])

    if st.button("🔄 Reiniciar conversación", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    # Información técnica del entorno
    st.subheader("⚙️ Entorno Bedrock")
    region = os.getenv("AWS_REGION", "us-east-1")
    model_id = os.getenv("MODEL_ID", "No configurado")
    auth_mode = (
        "API Key (Bearer)"
        if os.getenv("AWS_BEARER_TOKEN_BEDROCK") and not os.getenv("AWS_ACCESS_KEY_ID")
        else "IAM / SSO Credentials"
    )

    st.markdown(
        f"- **Región:** `{region}`\n"
        f"- **Modelo:** `{model_id}`\n"
        f"- **Auth:** `{auth_mode}`"
    )

    st.divider()

    # Métricas de consumo en la sesión
    st.subheader("📊 Consumo de Sesión")
    col1, col2 = st.columns(2)
    col1.metric("Tokens Entrada", st.session_state.session_tokens["input"])
    col2.metric("Tokens Salida", st.session_state.session_tokens["output"])

# --- Área Principal del Chat ---
st.header(st.session_state.selected_profile)
st.caption("Pregunta sobre conceptos, servicios, seguridad, costos o solicita preguntas tipo examen.")

# Mostrar mensaje inicial de bienvenida del perfil activo si no hay historial
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(current_profile_data["welcome_msg"])

# Renderizar todo el historial de mensajes guardado en la sesión
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Entrada conversacional del estudiante
if user_prompt := st.chat_input("Escribe tu consulta sobre AWS Cloud Practitioner..."):
    # 1. Agregar y mostrar el mensaje del estudiante
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # 2. Invocar a Amazon Bedrock enviando todo el historial de la sesión
    with st.chat_message("assistant"):
        with st.spinner("Analizando con Amazon Bedrock..."):
            response_text, metadata = invoke_bedrock_chat(
                messages=st.session_state.messages,
                system_prompt=current_profile_data["system_prompt"],
            )
            st.markdown(response_text)

            # Mostrar latencia discreta si la llamada fue exitosa
            if metadata:
                st.caption(
                    f"⚡ {metadata.get('latency_ms', 0)} ms | "
                    f"Tokens: {metadata.get('total_tokens', 0)}"
                )
                st.session_state.session_tokens["input"] += metadata.get("input_tokens", 0)
                st.session_state.session_tokens["output"] += metadata.get("output_tokens", 0)
                st.session_state.session_tokens["total"] += metadata.get("total_tokens", 0)

    # 3. Guardar la respuesta en el historial de sesión
    st.session_state.messages.append({"role": "assistant", "content": response_text})