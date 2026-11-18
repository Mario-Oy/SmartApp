# SmartEdu AI — Angular + Python (FastAPI)

Migración del proyecto original **SmartEdu AI Angular + .NET**: se mantiene Angular 20, las rutas `/alumno` y `/docente`, los cuatro archivos de prompts y los contratos HTTP. Se sustituye únicamente el backend .NET por Python + FastAPI.

**Python es un lenguaje de programación, no un sistema operativo.** Este proyecto puede ejecutarse en Windows, Linux o macOS con Python 3.10+ y Node.js compatible con Angular 20.

## Backend Python

En terminal, desde `backend/`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 5050
```

En Linux/macOS, activar con `source .venv/bin/activate`; según el sistema usar `python3` en lugar de `python`.

Verifica `http://localhost:5050/docs` y `http://localhost:5050/api/health`.

## Frontend Angular

Desde `frontend/`, en otra terminal:

```powershell
npm install
npm start
```

Abre `http://localhost:4200/alumno` o `http://localhost:4200/docente`. El proxy de Angular apunta a `http://localhost:5050`.

## Sin conexión a Gemini (modo demo)

Si **no** defines `GEMINI_API_KEY`, el backend devuelve respuestas didácticas SIMULADAS; no son resúmenes ni calificaciones reales. La instalación inicial de Python/Node y paquetes sí requiere conexión o caché previa.

## Con Gemini real

En PowerShell, **antes de iniciar el backend**:

```powershell
$env:GEMINI_API_KEY="TU_CLAVE_PRIVADA"
$env:GEMINI_MODEL="MODELO_HABILITADO_EN_TU_CUENTA"
python -m uvicorn main:app --reload --port 5050
```

En Linux/macOS: `export GEMINI_API_KEY=...` y `export GEMINI_MODEL=...`.

El backend usa la API REST `generateContent`. Verifica en Google AI Studio qué modelo admite tu clave y la operación; no todos los modelos listados garantizan acceso efectivo. No publiques la clave ni la coloques en Angular.

## Endpoints

- `GET /api/health`
- `POST /api/study/generate`: `{ "topic": "El ciclo del agua", "sourceText": "", "workType": "summary", "mode": "context" }`
- `POST /api/grade/evaluate`: `{ "topic": "El ciclo del agua", "studentText": "...", "instructions": "", "mode": "context" }`

Ambos POST responden `{ "mode": "context", "provider": "demo|gemini", "result": "...", "promptUsed": "..." }`.

## Consideraciones educativas

Usa trabajos ficticios o anonimizados. La evaluación de IA es **sugerida** y debe ser revisada por el docente; no se debe usar como calificación automática definitiva.


## SmartApps — Clasificador de incidentes

Ruta Angular: `http://localhost:4200/incidentes`
Endpoint Python: `POST /api/incidents/classify`

Ejemplo de petición:
```json
{"description":"La VPN no funciona para 20 personas desde las 8:00", "mode":"context"}
```

Modos: `simple` (instrucción genérica) y `context` (categorías, impacto, urgencia, evidencias y escalamiento).

Sin `GEMINI_API_KEY`, el clasificador usa reglas locales basadas en palabras clave; **no es IA** y no asigna una prioridad definitiva. Con una API Key configurada, consulta Gemini con el modelo definido en `GEMINI_MODEL`. No almacena tickets ni datos y no sustituye a una mesa de ayuda.

### Actividad sugerida
1. Abrir `/incidentes` y describir una falla de VPN, una impresora o un posible phishing.
2. Comparar los resultados sin contexto y con contexto.
3. Identificar información faltante (usuarios afectados, tiempo, servicio crítico).
4. Debatir cómo cambiaría la clasificación al contar con esos datos.


## Configuración .env y actividades Markdown

1. En `backend`, copia `.env.example` como `.env`. Escribe `GEMINI_API_KEY` y `GEMINI_MODEL` (modelo que soporte `generateContent` para tu cuenta). Nunca compartas `.env`.
2. Instala dependencias: `pip install -r requirements.txt`. Inicia: `python -m uvicorn main:app --reload --port 5050`.
3. En `frontend`: `npm install` y `npm start`.
4. Visita `/alumno` y `/docente`. Cada uno muestra un selector de tareas que lee `GET /api/activities/{module}`.
5. Las plantillas están en `backend/contexts/alumno` y `backend/contexts/docente`. Variables admitidas: `{{TOPIC}}`, `{{SOURCE}}`, `{{CUSTOM}}`, `{{STUDENT_TEXT}}`, `{{INSTRUCTIONS}}` según plantilla.
6. La tarea **personalizada** habilita un campo de texto. El modo **sin contexto** conserva un prompt general; el modo **con contexto** carga el Markdown elegido.
7. Para agregar una actividad nueva hay que registrar su ID y nombre en `ACTIVITY_NAMES` de `backend/main.py`, además de crear el `.md`. No se permite cargar rutas arbitrarias.
8. Sin clave, el sistema devuelve **simulaciones**. Las llamadas reales requieren conexión y un modelo válido.
