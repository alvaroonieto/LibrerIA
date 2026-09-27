"""
Dictado por voz: convierte lo que dice el usuario en texto.

Usa faster-whisper, que funciona en el propio ordenador/servidor
(sin enviar el audio a ninguna empresa). La primera vez descarga el modelo
(~150 MB con "base").

Si faster-whisper no está instalado, el botón del micrófono no aparece.
"""

import io

from libreria import config

_modelo = None


def disponible():
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def _cargar():
    global _modelo
    if _modelo is None:
        from faster_whisper import WhisperModel
        _modelo = WhisperModel(config.MODELO_VOZ, device="cpu", compute_type="int8")
    return _modelo


def transcribir(audio_bytes, idioma="es"):
    """audio_bytes: el WAV que da st.audio_input. Devuelve el texto (puede ser "")."""
    segmentos, _ = _cargar().transcribe(
        io.BytesIO(audio_bytes),
        language=idioma,
        beam_size=1,        # más rápido; para frases cortas es suficiente
        vad_filter=True,    # ignora silencios
    )
    return " ".join(s.text.strip() for s in segmentos).strip()
