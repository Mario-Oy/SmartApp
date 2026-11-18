"""SmartEdu AI: backend Python, API compatible con el frontend Angular original."""
import os
import re
from dotenv import load_dotenv
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parent / ".env")

app = FastAPI(title="SmartEdu AI", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
PROMPTS = Path(__file__).resolve().parent / "prompts"

class StudyRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=300)
    sourceText: str = Field(default="", max_length=12000)
    workType: Literal["summary", "assignment"] = "summary"
    mode: Literal["simple", "context"] = "simple"
    activity: str = "resumen"
    customInstructions: str = Field(default="", max_length=4000)

class GradeRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=300)
    studentText: str = Field(min_length=1, max_length=12000)
    instructions: str = Field(default="", max_length=3000)
    mode: Literal["simple", "context"] = "simple"
    activity: str = "evaluacion-resumen"
    customInstructions: str = Field(default="", max_length=4000)

class AIResponse(BaseModel):
    mode: str
    provider: str
    result: str
    promptUsed: str

def render(template: str, **fields: str) -> str:
    text = (PROMPTS / template).read_text(encoding="utf-8")
    for key, value in fields.items():
        text = text.replace("{{" + key + "}}", value)
    return text

CONTEXTS = Path(__file__).resolve().parent / "contexts"
ACTIVITY_NAMES = {
    "alumno": {"resumen": "Resumen", "ensayo": "Ensayo", "cuestionario": "Cuestionario", "guia-estudio": "Guía de estudio", "personalizada": "Tarea personalizada"},
    "docente": {"evaluacion-resumen": "Evaluar resumen", "rubrica": "Evaluación con rúbrica", "retroalimentacion": "Retroalimentación", "personalizada": "Tarea personalizada"},
}

def list_activities(module: str):
    if module not in ACTIVITY_NAMES:
        raise HTTPException(404, detail="Módulo desconocido")
    return [{"id": key, "name": name} for key, name in ACTIVITY_NAMES[module].items() if (CONTEXTS / module / f"{key}.md").is_file()]

def context_from_md(module: str, activity: str, fields: dict[str, str]) -> str:
    if module not in ACTIVITY_NAMES or activity not in ACTIVITY_NAMES[module]:
        raise HTTPException(400, detail="Actividad no permitida")
    file = CONTEXTS / module / f"{activity}.md"
    if not file.is_file():
        raise HTTPException(404, detail="No existe la plantilla Markdown")
    template = file.read_text(encoding="utf-8")
    def replace(match):
        return fields.get(match.group(1), "")
    return re.sub(r"\{\{([A-Z_]+)\}\}", replace, template)

@app.get("/api/activities/{module}")
def activities(module: str):
    return list_activities(module)

async def generate(prompt: str, max_tokens: int) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DEMO")
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").removeprefix("models/")
    if not model.replace("-", "").replace("_", "").replace(".", "").isalnum():
        raise HTTPException(400, detail="Nombre de modelo no válido")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2, "maxOutputTokens": max_tokens}}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, headers={"x-goog-api-key": api_key}, json=payload)
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Gemini devolvió HTTP {response.status_code}. Verifica modelo, acceso y cuota.")
        parts = response.json()["candidates"][0]["content"]["parts"]
        result = "\n".join(part["text"] for part in parts if "text" in part).strip()
        if not result:
            raise ValueError("Respuesta vacía")
        return result
    except httpx.HTTPError:
        raise HTTPException(502, detail="No fue posible contactar con Gemini") from None
    except (KeyError, IndexError, ValueError, TypeError):
        raise HTTPException(502, detail="Gemini devolvió una respuesta inesperada") from None

@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "real" if os.getenv("GEMINI_API_KEY", "").strip() else "demo"}

@app.post("/api/study/generate", response_model=AIResponse)
async def study(input: StudyRequest):
    prompt = render("with-context.txt" if input.mode == "context" else "without-context.txt", TOPIC=input.topic, SOURCE=input.sourceText or "No se proporcionó material fuente.", TYPE="trabajo escolar" if input.workType == "assignment" else "resumen")
    if input.mode == "context":
        prompt = context_from_md("alumno", input.activity, {"TOPIC": input.topic, "SOURCE": input.sourceText or "Sin material de apoyo", "CUSTOM": input.customInstructions or "Sin instrucciones adicionales"})
    else:
        prompt = f"Elabora una actividad académica sobre: {input.topic}."
    if not os.getenv("GEMINI_API_KEY", "").strip():
        result = (f"SIMULACIÓN SIN IA REAL — {input.topic}\n\nIdea principal: define el concepto y explica sus aplicaciones.\nConceptos clave: identifica tres conceptos relevantes.\nEjemplo: añade un caso cotidiano.\nConclusión: relaciona el tema con la asignatura.\n\nEsta respuesta es una plantilla ilustrativa, NO un resumen verificado del tema." if input.mode == "context" else f"SIMULACIÓN SIN IA REAL — {input.topic} es un tema importante. Tiene aplicaciones en distintas áreas y resulta útil conocerlo.\n\nTexto genérico ilustrativo; no se generó mediante IA.")
        return AIResponse(mode=input.mode, provider="demo", result=result, promptUsed=prompt)
    return AIResponse(mode=input.mode, provider="gemini", result=await generate(prompt, 1100), promptUsed=prompt)

@app.post("/api/grade/evaluate", response_model=AIResponse)
async def grade(input: GradeRequest):
    prompt = render("grade-with-context.txt" if input.mode == "context" else "grade-without-context.txt", TOPIC=input.topic, STUDENT_TEXT=input.studentText, INSTRUCTIONS=input.instructions or "No se proporcionaron instrucciones adicionales.")
    if input.mode == "context":
        prompt = context_from_md("docente", input.activity, {"TOPIC": input.topic, "STUDENT_TEXT": input.studentText, "INSTRUCTIONS": input.instructions or "Sin instrucciones originales", "CUSTOM": input.customInstructions or "Sin instrucciones adicionales"})
    else:
        prompt = f"Evalúa de forma general el siguiente trabajo sobre {input.topic}:\n{input.studentText}"
    if not os.getenv("GEMINI_API_KEY", "").strip():
        result = ("SIMULACIÓN SIN IA REAL — EVALUACIÓN CON RÚBRICA\nComprensión: pendiente /30\nConceptos: pendiente /30\nOrganización: pendiente /20\nEjemplos: pendiente /20\nCalificación: no disponible.\nEl docente debe revisar el texto y justificar cada criterio." if input.mode == "context" else "SIMULACIÓN SIN IA REAL — EVALUACIÓN GENERAL\nNo se asigna calificación: faltan criterios explícitos y no hay IA conectada.")
        return AIResponse(mode=input.mode, provider="demo", result=result, promptUsed=prompt)
    return AIResponse(mode=input.mode, provider="gemini", result=await generate(prompt, 1600), promptUsed=prompt)


# SmartApps: clasificador de incidentes. Resultados de IA son sugerencias, no acciones automáticas.
class IncidentRequest(BaseModel):
    description: str = Field(min_length=5, max_length=6000)
    mode: Literal["simple", "context"] = "simple"

INCIDENT_RULES = {
    "seguridad": ["phishing", "contraseña robada", "acceso no autorizado", "malware", "virus", "ransomware", "cuenta comprometida"],
    "red": ["wifi", "wi-fi", "internet", "vpn", "conexión", "red", "latencia"],
    "hardware": ["impresora", "pantalla", "teclado", "disco duro", "batería", "monitor", "laptop"],
    "software": ["aplicación", "sistema", "error", "login", "inicio de sesión", "software", "actualización"],
}

def demo_incident(description: str, mode: str) -> str:
    import unicodedata
    def normalize(value: str) -> str:
        return ''.join(ch for ch in unicodedata.normalize('NFD', value.lower()) if unicodedata.category(ch) != 'Mn')
    text = normalize(description)
    matches = {category: sum(normalize(word) in text for word in words) for category, words in INCIDENT_RULES.items()}
    category = max(matches, key=matches.get) if any(matches.values()) else 'sin clasificar'
    urgent = any(normalize(term) in text for term in ['caida total', 'todos los usuarios', 'datos filtrados', 'ransomware', 'no funciona ningun'])
    priority = 'alta (orientativa)' if urgent else 'pendiente de confirmar'
    if mode == 'simple':
        return f'SIMULACIÓN LOCAL (reglas, no IA)\nCategoría probable: {category}\nNo se realizó análisis de impacto ni urgencia.'
    return (f'SIMULACIÓN LOCAL (reglas, no IA)\nCategoría probable: {category}\nPrioridad orientativa: {priority}\n'
            'Impacto: no determinado; requiere número de usuarios afectados y servicio.\n'
            'Urgencia: no determinada; requiere tiempo límite y alternativa disponible.\n'
            'Acción sugerida: registrar ticket, confirmar alcance y escalar a soporte según procedimiento.\n'
            'Confianza: no calculada. Revisar clasificación manualmente.')

@app.post("/api/incidents/classify", response_model=AIResponse)
async def classify_incident(input: IncidentRequest):
    prompt = render("incident-with-context.txt" if input.mode == "context" else "incident-without-context.txt", DESCRIPTION=input.description)
    if not os.getenv("GEMINI_API_KEY", "").strip():
        return AIResponse(mode=input.mode, provider="demo-reglas", result=demo_incident(input.description, input.mode), promptUsed=prompt)
    return AIResponse(mode=input.mode, provider="gemini", result=await generate(prompt, 1100), promptUsed=prompt)
