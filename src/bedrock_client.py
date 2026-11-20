# src/bedrock_client.py
import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError


def get_bedrock_client():
    """
    Inicializa y retorna el cliente de Amazon Bedrock Runtime.
    Soporta autenticación mediante variables estándar de AWS IAM/SSO
    (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
    o mediante AWS_BEARER_TOKEN_BEDROCK (API Key de Bedrock en SDKs recientes).
    """
    region = os.getenv("AWS_REGION", "us-east-1")

    # Configuración de reintentos y timeouts para mayor resiliencia
    retry_config = Config(
        region_name=region,
        retries={"max_attempts": 3, "mode": "standard"},
        read_timeout=60,
    )

    # Si se usa API Key de Bedrock (AWS_BEARER_TOKEN_BEDROCK), boto3 la detecta
    # automáticamente desde el entorno si no se pasan credenciales explícitas.
    if os.getenv("AWS_BEARER_TOKEN_BEDROCK") and not os.getenv("AWS_ACCESS_KEY_ID"):
        return boto3.client(
            service_name="bedrock-runtime",
            region_name=region,
            config=retry_config,
        )

    # Flujo estándar con credenciales IAM / SSO
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=region,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN") or None,
        config=retry_config,
    )


def invoke_bedrock_chat(messages: list[dict], system_prompt: str) -> tuple[str, dict]:
    """
    Envía el historial de conversación y el system prompt a Amazon Bedrock
    utilizando la Converse API.

    Args:
        messages: Lista de diccionarios con formato [{"role": "user"|"assistant", "content": "..."}]
        system_prompt: Instrucciones del perfil de experto seleccionado.

    Returns:
        Tupla (respuesta_texto, metadata_uso)
    """
    model_id = os.getenv("MODEL_ID", "us.amazon.nova-2-lite-v1:0")

    # Formatear el historial al esquema exigido por Bedrock Converse API
    formatted_messages = [
        {
            "role": msg["role"],
            "content": [{"text": msg["content"]}],
        }
        for msg in messages
    ]

    try:
        client = get_bedrock_client()

        response = client.converse(
            modelId=model_id,
            messages=formatted_messages,
            system=[{"text": system_prompt}],
            inferenceConfig={
                "maxTokens": 1200,
                "temperature": 0.4,  # Equilibrio entre precisión técnica y naturalidad
                "topP": 0.9,
            },
        )

        # Extraer texto de la respuesta
        output_message = response["output"]["message"]
        response_text = output_message["content"][0]["text"]

        # Extraer métricas de tokens (útil para transparencia y monitoreo FinOps)
        usage = response.get("usage", {})
        metadata = {
            "input_tokens": usage.get("inputTokens", 0),
            "output_tokens": usage.get("outputTokens", 0),
            "total_tokens": usage.get("totalTokens", 0),
            "latency_ms": response.get("metrics", {}).get("latencyMs", 0),
        }

        return response_text, metadata

    except (NoCredentialsError, PartialCredentialsError):
        return (
            "⚠️ **Error de autenticación:** No se detectaron credenciales válidas de AWS. "
            "Verifica tu archivo `.env` o las variables de entorno del contenedor.",
            {},
        )
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_msg = e.response["Error"]["Message"]

        if error_code == "ExpiredTokenException":
            return (
                "⚠️ **Credenciales expiradas:** Tu `AWS_SESSION_TOKEN` temporal caducó. "
                "Obtén nuevas llaves en el portal de AWS SSO, actualiza tu `.env` y reinicia la aplicación.",
                {},
            )
        if error_code == "AccessDeniedException":
            return (
                f"⚠️ **Acceso denegado ({error_code}):** Tu rol no tiene permiso para invocar `{model_id}` "
                f"en la región `{os.getenv('AWS_REGION', 'us-east-1')}`. Detalle: {error_msg}",
                {},
            )
        return f"⚠️ **Error de Amazon Bedrock ({error_code}):** {error_msg}", {}

    except Exception as e:
        return f"⚠️ **Error inesperado al conectar con Bedrock:** {str(e)}", {}