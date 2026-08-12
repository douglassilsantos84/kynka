# Kynka Backend 6.0

Overlay final para o repositório Kynka existente. Preserva o core e adiciona API HTTP e sessões isoladas.

## Instalar
Extraia este ZIP na raiz do projeto Kynka, mantendo a estrutura de pastas.

```powershell
.\FINALIZAR_BACKEND.ps1
python run_api.py
```

Abra `http://127.0.0.1:8000/docs`.

## Endpoints
- GET `/api/v1/health`
- GET `/api/v1/status`
- POST `/api/v1/sessions`
- DELETE `/api/v1/sessions/{session_id}`
- POST `/api/v1/chat`
- GET `/api/v1/sessions/{session_id}/memory`
- DELETE `/api/v1/sessions/{session_id}/memory`
- GET `/api/v1/sessions/{session_id}/variables`
- GET `/api/v1/capabilities`

O `session_id` retornado por `/chat` deve ser enviado nas mensagens seguintes para preservar memória e contexto.

## Backend pronto quando
1. `python -m kynka` continua funcionando.
2. `python -m pytest tests\api -q` passa.
3. `python run_api.py` inicia sem traceback.
4. `/api/v1/health` retorna `{"status":"ok"}`.
5. `/api/v1/chat` calcula 10 + 5 = 15.
6. O mesmo `session_id` resolve "esse resultado".
7. Um objetivo composto retorna `mode="plan"` e suas etapas.
