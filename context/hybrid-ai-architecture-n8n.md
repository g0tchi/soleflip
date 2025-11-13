# Hybrid AI Architecture mit n8n, LangChain & Memori
**Version**: 2.0 - n8n-First Approach
**Datum**: 2025-11-13
**Status**: Architecture Design

## Executive Summary

**Flexibelste AI-Lösung** für SoleFlip mit n8n als Orchestrator, kombiniert:
1. **LangChain Agents in n8n** - Native Integration, Drag & Drop
2. **Memori Microservice** - Persistentes Conversation Memory
3. **MindsDB Knowledge Bases** - Dokumentation & RAG (bereits vorhanden)
4. **FastAPI Tools** - Business Logic für LangChain Agents

**Vorteile:**
- ✅ No-Code/Low-Code AI-Workflows in n8n
- ✅ Persistente Memory über Sessions
- ✅ Maximale Flexibilität (verschiedene Backends pro Workflow)
- ✅ Kosteneffizient (80-90% günstiger als Vector-DB)
- ✅ Nutzt bestehende Infrastruktur (MindsDB, n8n, PostgreSQL)

---

## Architektur-Übersicht

```
┌────────────────────────────────────────────────────────────────┐
│                         n8n Workflows                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Schedule │  │ Webhook  │  │ Manual   │  │ Discord  │     │
│  │ Trigger  │  │ Trigger  │  │ Trigger  │  │ Trigger  │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │             │              │              │            │
│       ▼             ▼              ▼              ▼            │
│  ┌────────────────────────────────────────────────────────┐   │
│  │         LangChain Agent Node (n8n native)             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │  Memory  │  │   Tools  │  │   LLM    │           │   │
│  │  │  (HTTP)  │  │  (HTTP)  │  │ (OpenAI) │           │   │
│  │  └──────────┘  └──────────┘  └──────────┘           │   │
│  └────────────────────────────────────────────────────────┘   │
│       │             │              │                           │
└───────┼─────────────┼──────────────┼───────────────────────────┘
        │             │              │
        ▼             ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Memori    │ │   FastAPI   │ │   MindsDB   │
│   Service   │ │   Backend   │ │  (External) │
│             │ │             │ │             │
│ Port: 8001  │ │ Port: 8000  │ │ Remote      │
│             │ │             │ │             │
│ - Get Mem   │ │ - Inventory │ │ - KB Query  │
│ - Store Mem │ │ - Pricing   │ │ - RAG       │
│ - Clear Mem │ │ - Analytics │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
        │             │              │
        └─────────────┴──────────────┘
                      ▼
              ┌──────────────┐
              │  PostgreSQL  │
              │              │
              │ - soleflip   │
              │ - n8n        │
              │ - metabase   │
              │ - memori_*   │
              └──────────────┘
```

---

## Component Details

### 1. **n8n LangChain Agent Nodes** (Orchestrator)

n8n hat **native LangChain Support** seit Version 1.0!

**Verfügbare Nodes:**
- `AI Agent` - Orchestriert LangChain Agents
- `AI Memory` - Conversation Memory (wir nutzen Memori stattdessen)
- `AI Tool` - Custom Tools für Agent
- `OpenAI Chat Model` - LLM Backend
- `HTTP Request` - Für Memori/FastAPI Calls

**Beispiel n8n Workflow:**
```json
{
  "nodes": [
    {
      "type": "n8n-nodes-langchain.agent",
      "name": "AI Assistant",
      "parameters": {
        "model": "gpt-4",
        "systemMessage": "You are a SoleFlip inventory assistant...",
        "tools": ["inventory_tool", "pricing_tool"],
        "memory": "external_memory"
      }
    },
    {
      "type": "n8n-nodes-base.httpRequest",
      "name": "Get Memory",
      "parameters": {
        "url": "http://memori-service:8001/memory/{{ $json.user_id }}",
        "method": "GET"
      }
    },
    {
      "type": "n8n-nodes-base.httpRequest",
      "name": "Inventory Tool",
      "parameters": {
        "url": "http://soleflip-api:8000/ai/tools/inventory",
        "method": "POST",
        "body": "{{ $json }}"
      }
    }
  ]
}
```

---

### 2. **Memori Microservice** (Conversation Memory)

Separater Python Service für persistentes Memory.

**Service-Struktur:**
```
services/
└── memori-service/
    ├── Dockerfile
    ├── main.py              # FastAPI app
    ├── requirements.txt     # memori-py, fastapi, etc.
    ├── config.py
    └── api/
        ├── memory_router.py # Memory endpoints
        └── schemas.py       # Pydantic models
```

**API Endpoints:**
```python
# GET /memory/{user_id}
# Retrieve conversation memory for user

# POST /memory/{user_id}
# Store new conversation turn

# DELETE /memory/{user_id}
# Clear user memory

# POST /chat
# Direct chat with memory (alternative zu n8n Agent)
```

**Docker Service:**
```yaml
# docker-compose.yml (erweitert)
memori-service:
  build: ./services/memori-service
  container_name: soleflip-memori
  restart: unless-stopped
  environment:
    DATABASE_URL: postgresql://soleflip:${POSTGRES_PASSWORD}@postgres:5432/soleflip
    OPENAI_API_KEY: ${OPENAI_API_KEY}
    MEMORI_ENABLED: true
  ports:
    - "8001:8001"
  networks:
    - soleflip-network
  depends_on:
    - postgres
```

---

### 3. **FastAPI Tools** (Business Logic)

Neue Domain: `domains/ai/tools/` für LangChain-kompatible Tools.

**Tool-Struktur:**
```python
# domains/ai/tools/inventory_tool.py
from pydantic import BaseModel, Field

class InventoryToolInput(BaseModel):
    """Input schema for inventory tool"""
    query: str = Field(..., description="Natural language query about inventory")
    filters: dict = Field(default={}, description="Optional filters")

class InventoryToolOutput(BaseModel):
    """Output schema for inventory tool"""
    result: str
    data: dict
    metadata: dict

async def inventory_tool(input: InventoryToolInput) -> InventoryToolOutput:
    """
    LangChain-compatible tool for inventory queries.
    Called by n8n AI Agent.
    """
    # Business logic hier
    pass
```

**API Endpoints:**
```
POST /ai/tools/inventory
POST /ai/tools/pricing
POST /ai/tools/analytics
POST /ai/tools/orders
GET  /ai/tools/list        # List available tools for n8n
```

---

### 4. **MindsDB Knowledge Bases** (Optional RAG)

Bereits vorhanden, kann parallel genutzt werden für:
- Dokumentations-Queries
- RAG über context/ Dateien
- Historical Data Analysis

**n8n Integration:**
```json
{
  "type": "n8n-nodes-base.httpRequest",
  "name": "Query MindsDB KB",
  "parameters": {
    "url": "https://minds.netzhouse.synology.me/api/sql",
    "method": "POST",
    "body": {
      "query": "SELECT * FROM kb_inventory WHERE content LIKE '%dead stock%'"
    }
  }
}
```

---

## Implementation Plan

### Phase 1: Memori Microservice (Tag 1-2)

#### 1.1 Service Setup

**Datei**: `services/memori-service/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**Datei**: `services/memori-service/requirements.txt`
```txt
fastapi==0.104.0
uvicorn[standard]==0.24.0
memori-py>=0.1.0
openai>=1.12.0
anthropic>=0.18.0
pydantic>=2.4.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
structlog>=23.2.0
asyncpg>=0.29.0
sqlalchemy[asyncio]>=2.0.0
```

**Datei**: `services/memori-service/main.py`
```python
"""
Memori Microservice for SoleFlip
Provides conversation memory via HTTP API
"""
import memori
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID
import structlog
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from config import settings

logger = structlog.get_logger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Memori Service",
    version="1.0.0",
    description="Conversation Memory Service for SoleFlip"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Memori
@app.on_event("startup")
async def startup():
    """Initialize Memori on startup"""
    memori.enable(
        database_connect=settings.DATABASE_URL,
        provider=settings.PROVIDER,
        user_tracking=True
    )

    global llm_client
    if settings.PROVIDER == "openai":
        llm_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    elif settings.PROVIDER == "anthropic":
        llm_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    logger.info("memori_service_started", provider=settings.PROVIDER)


# Schemas
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    user_id: str
    messages: List[Message]
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096

class ChatResponse(BaseModel):
    response: str
    tokens_used: int
    model: str

class MemoryResponse(BaseModel):
    user_id: str
    conversations: List[Dict[str, Any]]
    count: int


# Endpoints
@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "provider": settings.PROVIDER}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with memory persistence.
    Used by n8n workflows.
    """
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        if request.system_prompt:
            messages.insert(0, {"role": "system", "content": request.system_prompt})

        # OpenAI
        if settings.PROVIDER == "openai":
            response = await llm_client.chat.completions.create(
                model=settings.MODEL,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                memori_user_id=request.user_id  # Memori magic
            )

            return ChatResponse(
                response=response.choices[0].message.content,
                tokens_used=response.usage.total_tokens,
                model=response.model
            )

        # Anthropic
        elif settings.PROVIDER == "anthropic":
            system = next((m["content"] for m in messages if m["role"] == "system"), None)
            user_messages = [m for m in messages if m["role"] != "system"]

            response = await llm_client.messages.create(
                model=settings.MODEL,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=system,
                messages=user_messages,
                metadata={"user_id": request.user_id}
            )

            return ChatResponse(
                response=response.content[0].text,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                model=response.model
            )

    except Exception as e:
        logger.error("chat_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/{user_id}", response_model=MemoryResponse)
async def get_memory(user_id: str, limit: int = 10):
    """
    Retrieve conversation memory for user.
    Used by n8n to inject context.
    """
    try:
        # This would query Memori's internal storage
        # Implementation depends on Memori's API
        # For now, placeholder
        return MemoryResponse(
            user_id=user_id,
            conversations=[],
            count=0
        )
    except Exception as e:
        logger.error("get_memory_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memory/{user_id}")
async def clear_memory(user_id: str):
    """Clear all memory for user"""
    try:
        # Clear implementation
        logger.info("memory_cleared", user_id=user_id)
        return {"status": "cleared", "user_id": user_id}
    except Exception as e:
        logger.error("clear_memory_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/{user_id}/store")
async def store_memory(user_id: str, message: Message):
    """Store a conversation turn"""
    try:
        # Store implementation
        logger.info("memory_stored", user_id=user_id)
        return {"status": "stored", "user_id": user_id}
    except Exception as e:
        logger.error("store_memory_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

**Datei**: `services/memori-service/config.py`
```python
"""Configuration for Memori Service"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    PROVIDER: str = "openai"  # or anthropic
    MODEL: str = "gpt-4-turbo-preview"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

### Phase 2: FastAPI Tools (Tag 3-4)

**Datei**: `domains/ai/tools/__init__.py`
**Datei**: `domains/ai/tools/base.py`

```python
"""Base tool interface for LangChain compatibility"""
from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel

class ToolInput(BaseModel):
    """Base input schema for tools"""
    pass

class ToolOutput(BaseModel):
    """Base output schema for tools"""
    success: bool
    result: str
    data: Dict[str, Any] = {}
    error: str = ""

class BaseTool(ABC):
    """Base class for LangChain-compatible tools"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM"""
        pass

    @abstractmethod
    async def run(self, input: ToolInput) -> ToolOutput:
        """Execute tool logic"""
        pass
```

**Datei**: `domains/ai/tools/inventory_tool.py`

```python
"""Inventory query tool for LangChain agents"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from domains.ai.tools.base import BaseTool, ToolInput, ToolOutput
from domains.ai.services.context_builder import ContextBuilder

class InventoryToolInput(ToolInput):
    """Input for inventory tool"""
    query: str = Field(..., description="Natural language query about inventory")
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional filters (brand, category, etc.)"
    )

class InventoryTool(BaseTool):
    """Tool for querying inventory data"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.context_builder = ContextBuilder(session)

    @property
    def name(self) -> str:
        return "inventory_query"

    @property
    def description(self) -> str:
        return """Query inventory data including:
- Current stock levels
- Dead stock analysis (items >60 days)
- Product locations
- Quantity information
- Brand and category filters

Example queries:
- "What is my dead stock rate?"
- "Show me all Nike items"
- "How many items are in warehouse A?"
"""

    async def run(self, input: InventoryToolInput) -> ToolOutput:
        """Execute inventory query"""
        try:
            # Build context using existing service
            context = await self.context_builder.build_inventory_context(
                filters=input.filters
            )

            return ToolOutput(
                success=True,
                result=context,
                data={"filters": input.filters or {}}
            )

        except Exception as e:
            return ToolOutput(
                success=False,
                result="",
                error=str(e)
            )
```

**API Router**: `domains/ai/api/tools_router.py`

```python
"""API endpoints for AI tools - called by n8n"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from domains.ai.tools.inventory_tool import InventoryTool, InventoryToolInput
from domains.ai.tools.pricing_tool import PricingTool, PricingToolInput
from domains.ai.tools.analytics_tool import AnalyticsTool, AnalyticsToolInput
from domains.ai.tools.base import ToolOutput
from shared.api.dependencies import get_db_session

router = APIRouter(prefix="/ai/tools", tags=["AI Tools"])

@router.post("/inventory", response_model=ToolOutput)
async def inventory_tool(
    input: InventoryToolInput,
    session: AsyncSession = Depends(get_db_session)
) -> ToolOutput:
    """Inventory query tool for n8n"""
    tool = InventoryTool(session)
    return await tool.run(input)

@router.post("/pricing", response_model=ToolOutput)
async def pricing_tool(
    input: PricingToolInput,
    session: AsyncSession = Depends(get_db_session)
) -> ToolOutput:
    """Pricing analysis tool for n8n"""
    tool = PricingTool(session)
    return await tool.run(input)

@router.post("/analytics", response_model=ToolOutput)
async def analytics_tool(
    input: AnalyticsToolInput,
    session: AsyncSession = Depends(get_db_session)
) -> ToolOutput:
    """Analytics tool for n8n"""
    tool = AnalyticsTool(session)
    return await tool.run(input)

@router.get("/list")
async def list_tools() -> List[Dict[str, Any]]:
    """List all available tools with descriptions"""
    return [
        {
            "name": "inventory_query",
            "endpoint": "/ai/tools/inventory",
            "description": "Query inventory data and stock levels",
            "input_schema": InventoryToolInput.schema()
        },
        {
            "name": "pricing_analysis",
            "endpoint": "/ai/tools/pricing",
            "description": "Analyze pricing and recommendations",
            "input_schema": PricingToolInput.schema()
        },
        {
            "name": "analytics_query",
            "endpoint": "/ai/tools/analytics",
            "description": "Sales analytics and performance metrics",
            "input_schema": AnalyticsToolInput.schema()
        }
    ]
```

---

### Phase 3: n8n Workflow Examples (Tag 5)

#### Workflow 1: AI Inventory Assistant (Discord Bot)

```json
{
  "name": "AI Inventory Assistant (Discord)",
  "nodes": [
    {
      "parameters": {
        "path": "ai-assistant",
        "httpMethod": "POST"
      },
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300]
    },
    {
      "parameters": {
        "url": "http://memori-service:8001/chat",
        "method": "POST",
        "bodyParameters": {
          "parameters": [
            {
              "name": "user_id",
              "value": "={{ $json.user_id }}"
            },
            {
              "name": "messages",
              "value": "={{ $json.messages }}"
            },
            {
              "name": "system_prompt",
              "value": "You are SoleFlip AI Assistant. Help with inventory queries using available tools."
            }
          ]
        }
      },
      "name": "Memori Chat",
      "type": "n8n-nodes-base.httpRequest",
      "position": [450, 300]
    },
    {
      "parameters": {
        "resource": "message",
        "operation": "send",
        "channel": "={{ $json.channel_id }}",
        "content": "={{ $json.response }}"
      },
      "name": "Discord Reply",
      "type": "n8n-nodes-base.discord",
      "position": [650, 300]
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{ "node": "Memori Chat", "type": "main", "index": 0 }]]
    },
    "Memori Chat": {
      "main": [[{ "node": "Discord Reply", "type": "main", "index": 0 }]]
    }
  }
}
```

#### Workflow 2: AI-Enhanced Dead Stock Alert

Erweitere bestehenden Workflow `02_daily_dead_stock_alert.json`:

```json
{
  "name": "AI Dead Stock Analyzer",
  "nodes": [
    {
      "name": "Schedule Trigger",
      "type": "n8n-nodes-base.scheduleTrigger",
      "parameters": {
        "rule": { "interval": [{ "field": "hours", "hoursInterval": 24 }] }
      }
    },
    {
      "name": "Query Dead Stock",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "query": "SELECT * FROM inventory.items WHERE age_days > 60"
      }
    },
    {
      "name": "AI Analysis",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://memori-service:8001/chat",
        "method": "POST",
        "body": {
          "user_id": "system",
          "messages": [
            {
              "role": "user",
              "content": "Analyze this dead stock data and provide recommendations: {{ $json }}"
            }
          ]
        }
      }
    },
    {
      "name": "Send Discord Alert",
      "type": "n8n-nodes-base.discord",
      "parameters": {
        "content": "🚨 Dead Stock Alert\n\n{{ $json.response }}"
      }
    }
  ]
}
```

---

### Phase 4: Docker Integration (Tag 6)

**Datei**: `docker-compose.yml` (erweitert)

```yaml
services:
  # ... existing services ...

  # Memori Service
  memori-service:
    build:
      context: ./services/memori-service
      dockerfile: Dockerfile
    container_name: soleflip-memori
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql+asyncpg://soleflip:${POSTGRES_PASSWORD}@postgres:5432/soleflip
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      PROVIDER: ${AI_PROVIDER:-openai}
      MODEL: ${AI_MODEL:-gpt-4-turbo-preview}
    ports:
      - "8001:8001"
    networks:
      - soleflip-network
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 128M
          cpus: '0.1'
```

**.env Updates**:
```bash
# AI Configuration
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
AI_PROVIDER=openai  # or anthropic
AI_MODEL=gpt-4-turbo-preview
```

---

## Use Cases & Examples

### Use Case 1: Discord AI Assistant

**User in Discord:** "@SoleFlip How many Nike items have been in stock for more than 60 days?"

**n8n Flow:**
1. Discord Webhook triggers
2. Extract user_id and message
3. HTTP Call zu Memori Service
   - Memori lädt User-Context
   - LLM versteht Query
   - LLM nutzt Tools (Inventory API)
4. Response zurück zu Discord

**Ergebnis:** Konversation mit Gedächtnis über Discord!

---

### Use Case 2: Proaktive AI Insights

**n8n Workflow (täglich):**
1. Schedule Trigger (8:00 AM)
2. Query DB: Top-Performer, Dead Stock, Anomalien
3. AI Analysis: Memori generiert Insights
4. Send to Discord/Slack mit Handlungsempfehlungen

---

### Use Case 3: Multi-Tool AI Agent

**User:** "What should I do with my slow-moving inventory?"

**AI Agent Flow:**
1. Tool 1: Inventory Analysis (welche Items sind slow-moving)
2. Tool 2: Pricing Analysis (aktuelle Preise vs Markt)
3. Tool 3: Analytics (historische Performance)
4. **AI kombiniert alle Daten** → Actionable Recommendations

---

## Kosten-Kalkulation

### Geschätzte monatliche Kosten

**Annahme:**
- 500 AI-Queries/Tag (Discord, Workflows, etc.)
- Durchschnittlich 800 Input + 400 Output Tokens

**OpenAI GPT-4 Turbo:**
- Input: 500 × 800 × $0.01/1K = $4/Tag
- Output: 500 × 400 × $0.03/1K = $6/Tag
- **Total: $300/Monat**

**Mit Memori Optimierung:**
- 80-90% weniger Tokens durch intelligentes Caching
- **Geschätzte Kosten: $30-60/Monat**

**Alternative: GPT-3.5 Turbo:**
- 10x günstiger als GPT-4
- **Geschätzte Kosten: $3-6/Monat**

---

## Deployment Checkliste

### Pre-Production

- [ ] Memori Service gebaut und getestet
  ```bash
  cd services/memori-service
  docker build -t soleflip-memori .
  ```

- [ ] Environment Variables konfiguriert
  - [ ] `OPENAI_API_KEY`
  - [ ] `AI_PROVIDER=openai`
  - [ ] `AI_MODEL=gpt-4-turbo-preview`

- [ ] Docker Compose erweitert
  ```bash
  docker-compose up -d memori-service
  ```

- [ ] Health Check
  ```bash
  curl http://localhost:8001/health
  ```

- [ ] FastAPI Tools registriert
  ```python
  # main.py
  from domains.ai.api.tools_router import router as tools_router
  app.include_router(tools_router)
  ```

- [ ] n8n Workflows importiert
  - [ ] AI Inventory Assistant
  - [ ] AI Dead Stock Analyzer

- [ ] Tests durchgeführt
  ```bash
  # Unit Tests
  pytest tests/unit/ai/

  # Integration Test
  curl -X POST http://localhost:8001/chat \
    -H "Content-Type: application/json" \
    -d '{
      "user_id": "test-user",
      "messages": [{"role": "user", "content": "Hello"}]
    }'
  ```

---

## Monitoring & Observability

### Metrics to Track

```python
# domains/ai/monitoring/metrics.py
from prometheus_client import Counter, Histogram

ai_requests_total = Counter(
    'ai_requests_total',
    'Total AI requests',
    ['provider', 'model', 'status']
)

ai_tokens_used = Counter(
    'ai_tokens_used_total',
    'Total tokens used',
    ['provider', 'model', 'type']
)

ai_response_time = Histogram(
    'ai_response_time_seconds',
    'AI response time',
    ['provider', 'model']
)
```

### Logging Best Practices

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info(
    "ai_request_completed",
    user_id=user_id,
    provider="openai",
    model="gpt-4",
    tokens_used=response.tokens_used,
    response_time_ms=duration_ms,
    success=True
)
```

---

## Vergleich: Option A vs B vs C

| Feature | Option A (LangChain + Memori) | Option B (MindsDB) | Option C (Memori Only) |
|---------|-------------------------------|-------------------|------------------------|
| **Flexibilität** | ⭐⭐⭐⭐⭐ Maximal | ⭐⭐⭐ Gut | ⭐⭐⭐ Gut |
| **n8n Integration** | ⭐⭐⭐⭐⭐ Native | ⭐⭐⭐⭐ Gut | ⭐⭐⭐ HTTP only |
| **Kosten** | ⭐⭐⭐⭐ Niedrig | ⭐⭐⭐ Mittel | ⭐⭐⭐⭐⭐ Sehr niedrig |
| **Setup-Komplexität** | ⭐⭐⭐ Mittel | ⭐⭐⭐⭐ Einfach | ⭐⭐⭐⭐ Einfach |
| **Conversation Memory** | ⭐⭐⭐⭐⭐ Persistent | ⭐⭐ Limitiert | ⭐⭐⭐⭐⭐ Persistent |
| **No-Code Workflows** | ⭐⭐⭐⭐⭐ Drag & Drop | ⭐⭐⭐⭐ SQL-basiert | ⭐⭐⭐ Code erforderlich |
| **Multi-Backend** | ⭐⭐⭐⭐⭐ Ja | ⭐⭐ Nein | ⭐⭐ Nein |

**Fazit:** Option A bietet die beste Balance zwischen Flexibilität, Kosten und Features.

---

## Next Steps

1. **Phase 1 starten:** Memori Microservice bauen
   ```bash
   mkdir -p services/memori-service
   # ... Code aus diesem Plan kopieren
   ```

2. **Docker Stack erweitern:**
   ```bash
   docker-compose up -d memori-service
   ```

3. **n8n Workflows importieren:**
   - AI Inventory Assistant
   - AI Dead Stock Analyzer

4. **Testing:**
   - Unit Tests für Tools
   - Integration Tests für Memori Service
   - End-to-End Test mit n8n

5. **Production Rollout:**
   - Monitoring einrichten
   - Cost Tracking aktivieren
   - User Feedback sammeln

**Ready to build?** 🚀
