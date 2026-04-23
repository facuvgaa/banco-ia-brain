# Proyecto Moustro (Banco Moustro)

**Banco Moustro** es una demo de banca con **agente conversacional** de punta a punta: el usuario habla desde el navegador y, detrás, un **backend Java con Spring Boot** concentra la API de producto (préstamos, refinanciación, perfil inversor, reclamos) mientras la capa de IA —en **Python**, con **LangGraph** y orquestación por **Kafka**— encadena el razonamiento sin bloquear el hilo de negocio. La arquitectura es **orientada a eventos**: los mensajes viajan por streams, los servicios reaccionan de forma **asíncrona** y el sistema escala en ideas de *workers* y consumidores, no de un monolito gigante.

Sobre **AWS Bedrock** se apoya en **Anthropic Claude** con un reparto claro: **Claude Haiku** hace el trabajo **liviano y veloz** —triaje, clasificación de intención, ruteo hacia el módulo que corresponde—; **Claude Sonnet** se reserva para lo **exigente**: razonar con contexto, usar herramientas, armar explicaciones de préstamos o inversiones con la profundidad que el cliente merece. Así se optimizan **latencia y costo** sin sacrificar calidad cuando el trámite lo pide.

El diseño apuesta a **código asíncrono** y a **colas/streams** desacoplados: hoy levantás todo con **`docker compose`**, mañana el mismo desglose de procesos se mapea sin drama a **Kubernetes** (réplicas, autoscaling por servicio, service mesh si el equipo lo pide) porque el contrato son eventos y APIs, no acoplamiento fijo entre procesos.

---

## Arquitectura

![Arquitectura del sistema](images/arquitectura.png)

### Visión general

1. **Frontend** (`bank-front`): Vue 3 + Vite; el navegador llama a la API Java (p. ej. `http://localhost:8080/api`).
2. **Core** (`core-service-java/bank-ia`): Spring Boot, PostgreSQL (`banco-db`), publica y consume **eventos Kafka** (reclamos, respuestas de chat, etc.).
3. **Clasificador** (`ai-brain-python/services/classifier`): **consumidor** de Kafka; según el mensaje y el estado en **Redis**, enruta hacia el stream del master o del “brain” y workflows.
4. **Master** (`ai-brain-python/services/master`): grafo **LangGraph** (primera capella conversacional); usa checkpoints en **Redis**; puede marcar derivación al brain (p. ej. `[DERIVAR]`).
5. **Brain** (`ai-brain-python/services/brain`): lee `to-brain`, decide **workflow** (`workflow_loans` / `workflow_investment`) con caché y TTL en Redis, y reenvía al stream correcto.
6. **Workflows** (`workflows/loans`, `workflows/investment`): cada uno es un proceso **asíncrono** que consume su stream de Kafka, ejecuta un grafo LangGraph con **herramientas** que llaman al core vía `CORE_API_URL`, y persiste estado en Redis + conversaciones en `postgres_conversation` cuando aplica.

**Infraestructura compartida:** **Kafka** (tópicos/streams), **Redis** (sesión, `brain_workflow`, **checkpoints de LangGraph**, grupos de lectura de streams), **dos PostgreSQL** (negocio vs. historial guardado de conversación).

### Por eventos y código asíncrono

- Los servicios Python usan **asyncio** (clientes no bloqueantes, `async/await`) y se enganchan a Kafka con bucles de consumo adecuados a streaming.
- El **front no acopla** a un único monolito de IA: cada pieza reacciona a **eventos** (nuevo mensaje de usuario, mensaje hacia un workflow, salida hacia el front vía mecanismos del core).
- Ese desacoplamiento es lo que hace razonable un salto a **K8s**: colas o streams como contrato, servicios con procesos o workers horizontales, y Redis/Kafka/Postgres como backing services gestionados o operadores.

### Memoria en Redis (corto plazo) y PostgreSQL (persistencia)

En este proyecto **no hay un único “chip de memoria”**: se combina **Redis** para el **trabajo en curso** y **PostgreSQL** para cosas **duraderas** y consultables después.

**Redis — memoria operativa / corto plazo**

- **Checkpoints de LangGraph** (`AsyncRedisSaver`): el estado del grafo (mensajes del hilo, pasos) se guarda asociado al `thread_id` (típicamente el `customer_id`). Sirve para **seguir la misma conversación** en varios turnos sin reenviar todo el historial “a mano”. Es **rápido** y **volátil en la práctica**: depende de políticas de Redis, TTL de otras claves y limpieza; no está pensado como archivo legal de la charla.
- **`session:{customerId}`** (TTL ~30 min): indica a qué stream de Kafka debe ir el **siguiente** mensaje del usuario (p. ej. `to-brain` tras una derivación).
- **`brain_workflow:{customerId}`** (TTL alineado al clasificador, p. ej. 30 min): recuerda **qué workflow del brain** está activo (`workflow_loans` / `workflow_investment`) para no reclasificar en cada tecla.
- **`post_close:{customerId}`** (TTL ~15 min): flag tras un cierre tipo “¿algo más?” para que el clasificador pueda **resetear sesión** en el mensaje siguiente sin arrastrar el módulo anterior.

En conjunto, Redis actúa como **memoria de trabajo** del pipeline: barata en latencia, con **expiración** y orientada a **sesión activa**.

**PostgreSQL — memoria durable / largo plazo (tres lecturas útiles)**

1. **`conversation-db` (puerto 5433 en local)** — tabla `conversations` (`common/conversation_store.py`): tras un turno en **master** o en un **workflow**, se puede **insertar** un registro con `customer_id`, `service` (p. ej. `master`, `loans`, `investment`) y un **JSONB** de mensajes simplificados (rol + contenido). Es un **historial guardado** para auditoría, analítica o futuras integraciones; **no** reemplaza al checkpointer de LangGraph para reanudar el grafo en caliente (eso sigue en Redis mientras exista el checkpoint).
2. **`banco-db` (puerto 5432)** — datos de **negocio** del core Java: préstamos, ofertas, operaciones de refinanciación, **perfil inversor**, etc. Es la “memoria larga” del **cliente como entidad bancaria**, no del texto del chat.

**Resumen:** Redis = **contexto vivo** del flujo de IA y del enrutado (segundos/minutos, con TTL). PostgreSQL = **persistencia relacional**: historial de conversación en un esquema dedicado y **estado de producto** en el esquema del banco. *(Nota: “PostgREST” es otro producto; aquí se usa el cliente/servidor **PostgreSQL** estándar.)*

---

## Variables de entorno (`.env`)

Copiá **`.env.example`** a **`.env`** y completá los valores. **No subas `.env` al repositorio.**

| Variable | Uso |
|----------|-----|
| `VITE_API_URL` | Base URL de la API para el build del front (en Docker apunta al servicio; en local suele ser `http://localhost:8080/api`). |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Credenciales **IAM** de AWS. El runtime de `langchain_aws` + Bedrock invoca la API con **firma SigV4**; no es un “token Bearer” suelto como en algunos LLMs, sino clave/ secreto de IAM con permisos a **Amazon Bedrock** (InvokeModel / Converse) en la cuenta. |
| `AWS_REGION` | Región donde están habilitados los modelos Bedrock. Debe alinearse con el catálogo de modelos y con las políticas IAM. En el código, `get_bedrock_model_master` y `get_bedrock_model_brain` leen `AWS_REGION` (puedes unificar o usar perfiles/variables por entorno). |
| `AWS_PRIMARY_LLM` / `AWS_SECOND_LLM` | **IDs de modelo** en Bedrock (p. ej. Haiku para triaje, Sonnet para razonamiento con tools), no claves. Los tokens de la inferencia los gestiona **Bedrock** al invocar el modelo. |
| `REDIS_URL` | Conexión a Redis: sesión, caché de módulo del brain, **checkpoints de LangGraph** (estado de grafo por `thread`/`customer`), y auxiliares de streams. |
| `CORE_API_URL` | Base del core Java visto desde los workflows (rutas bajo `.../bank-ia`). |
| `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` | **Observabilidad (LangSmith)**: el “API key” es de **LangSmith** (trazas y depuración), no de Bedrock. Si no querés trazas, podés dejarlo desactivado o sin clave según tu configuración. |

### LangGraph y “estado” (a menudo confundido con “tokens”)

- **LangGraph** persiste el **estado del grafo** (pasos, mensajes, reanudación de diálogo) en **Redis** vía un checkpointer; eso no son “tokens de LLM”, sino **serialización de estado** + metadatos del run.
- Los **tokens de consumo** del modelo (entrada/salida) los cobra **AWS Bedrock** según el modelo y la llamada; se controlan con **límites de cuenta, presupuestos e IAM**, no con una variable de “token de LangGraph” en el `.env` salvo en sentido de **LangSmith** arriba.

---

## Estructura del repositorio

| Ruta | Rol |
|------|-----|
| `bank-front/` | SPA Vue: chat y consumo de API. |
| `core-service-java/bank-ia/` | API REST, dominio de préstamos, ofertas, refinanciación, perfil inversor. |
| `ai-brain-python/` | Classifier, master, brain, workflows (préstamos / inversión), `common/`. |
| `images/` | Recursos, p. ej. diagrama de arquitectura. |
| `docker-compose.yml` | Orquestación local (equivalente lógico a un stack de servicios en K8s). |
| `.env.example` | Plantilla de variables (copiar a `.env`). |

---

## Requisitos

- Docker y Docker Compose
- Cuenta **AWS** con **Amazon Bedrock** habilitado y credenciales IAM mínimas para invocar los modelos configurados
- Archivo **`.env`** a partir de **`.env.example`**

## Clonar el repositorio

Asegurate de tener [Git](https://git-scm.com/) instalado. En la terminal:

```bash
git clone https://github.com/facuvgaa/banco-ia-brain.git
cd banco-ia-brain
```

Si usás **SSH** (clave cargada en GitHub):

```bash
git clone git@github.com:facuvgaa/banco-ia-brain.git
cd banco-ia-brain
```

Para **actualizar** el código más adelante, desde la carpeta del proyecto:

```bash
git pull origin main
```

(El branch por defecto puede ser `main`; ajustá si tu remoto usa otro nombre.)

## Cómo levantar el entorno

Desde la **raíz del repositorio** (donde está `docker-compose.yml`):

```bash
cp .env.example .env
# Completar AWS_* y, si aplica, LANGCHAIN_API_KEY
docker compose up -d --build
```

Puertos habituales:

- **Frontend**: [http://localhost:5173](http://localhost:5173)
- **API Java**: [http://localhost:8080](http://localhost:8080) — prefijo `/api/v1/bank-ia/...`
- **Redis**: `localhost:6379`
- **PostgreSQL (core)**: `localhost:5432`
- **PostgreSQL (conversaciones)**: `localhost:5433`
- **Kafka**: `localhost:9092`

```bash
docker compose down
```

## Notas de producto

- **Préstamos / refinanciación**: reglas y datos en el core; los workflows consumen `CORE_API_URL`.
- **Inversión**: cuestionario y perfil inversor vía core; orquestado en el grafo correspondiente.
- **Cambio de módulo** (p. ej. de préstamos a inversión): suele requerir un mensaje explícito con intención (p. ej. “inversiones”); el clasificador y Redis actualizan el flujo.

## Licencia

[Código MIT](Licence) — Proyecto Moustro y colaboradores.
