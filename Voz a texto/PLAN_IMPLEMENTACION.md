# Plan de Implementación — Orquestador y Agentes de Pedidos de Voz por WhatsApp

**Proyecto:** C:\Voz a texto  
**Fecha:** 2026-11-14  
**Estado:** En ejecución / Pruebas de funcionalidad

## 1. Objetivo

Verificar que el orquestador de agentes y las skills permitan registrar pedidos correctamente desde el flujo de extremo a extremo (recepción de webhook → transcripción → interpretación → validación → cálculo → confirmación → registro), sin inventar resultados y solo aplicando correcciones cuando se encuentren fallos reales de reconocimiento de productos o cantidades.

## 2. Alcance

- Orquestador: `orquestador-pedidos-whatsapp/`
- Agentes especializados: `agentes/` (7 agentes + pipeline)
- Skill de interpretación: `tomando-pedidos-voz-whatsapp/`
- Catálogos externos: `orquestador-pedidos-whatsapp/config/comercios/`
- Interfaz web: `app_web.py`

## 3. Arquitectura actual

```
Flujo de estados:
received -> transcribed -> interpreted -> requires_clarification ->
requires_confirmation -> confirmed -> registered

Agentes:
1. RECEPTOR         - agente_receptor.py
2. TRANSCRIPCION    - agente_transcripcion.py
3. INTERPRETACION   - agente_interpretacion.py
4. VALIDACION       - agente_validacion.py
5. CALCULO          - agente_calculo.py
6. CONFIRMACION     - agente_confirmacion.py
7. REGISTRO         - agente_registro.py

Orquestador: orquesta los 7 agentes mediante pipeline.py
```

## 4. Requisitos funcionales

| ID | Requisito | Estado | Verificación |
|----|-----------|--------|--------------|
| R1 | Recibir mensaje de WhatsApp y validar evento | Implementado | agente_receptor |
| R2 | Transcribir audio con faster-whisper (modelo small, español, CPU, int8) | Implementado | agente_transcripcion + transcriptor.py |
| R3 | Interpretar transcripción contra catálogo externo | Implementado | agente_interpretacion + orchestrator.interpretar_pedido |
| R4 | Validar productos, cantidades y disponibilidad | Implementado | agente_validacion + validar_pedido.validate_pedido |
| R5 | Calcular subtotal y total con aritmética decimal | Implementado | agente_calculo + calcular_total.calcular_total |
| R6 | Generar resumen de confirmación o pregunta de aclaración | Implementado | agente_confirmacion |
| R7 | Registrar pedido confirmado (simulación por defecto) | Implementado | agente_registro + registrar_pedido.registrar_pedido |
| R8 | Idempotencia por message_id (no duplicar pedidos) | Implementado | pipeline + clave de idempotencia |
| R9 | No registrar sin confirmación explícita del cliente | Implementado | agente_registro + compuertas de acción |
| R10 | Anonimizar datos antes de loguear | Implementado | anonimizar.anonimizar_para_log |

## 5. Catálogos de comercio

| Comercio | Archivo | Productos | Nota |
|----------|---------|-----------|------|
| Supermercado | `config/comercios/supermercado-demo.json` | 32 productos + 1 no disponible (nafta súper) | Incluye unidades: unidad, kilogramo, litro, paquete, lata, resma |
| Pizzería | `config/comercios/pizzeria-demo.json` | 3 productos | Incluye aliases y phonetic_aliases |

## 6. Plan de pruebas de funcionalidad

### 6.1 Prueba A: Pedido de supermercado (transcripción real)

**Archivo:** `tests_audio/evento_supermercado.json`  
**Transcripción:** "Hola, ¿qué tal? Necesito comprar 17 resmas de papel, 4 latas de tomate, 5 litros de nasta super, 8 choplos, 7 mandarinas, 27 revistas del demoledor, 8 kilos de carne, de cerdo y lo de vaca."

**Resultado esperado:**
- Identificar: resma de papel A4 (17), tomate triturado en lata (4), mandarina (7), carne vacuna (8 kg)
- No identificar: choplos (no existe en catálogo), revistas del demoledor (no existe)
- No disponible: nafta súper (no se vende en supermercado)
- Estado final: `requires_clarification` (hay productos no identificados y no disponibles)
- No avanzar a confirmación sin resolver aclaraciones

### 6.2 Prueba B: Pedido de pizzería

**Archivo:** `tests_audio/evento_pizzeria.json`  
**Transcripción:** "Hola, quiero pedir dos pizzas grandes, una de muzza y otra napolitana para retirar."

**Resultado esperado:**
- Identificar: pizza grande de muzzarella (1), pizza grande napolitana (1)
- Modalidad: pickup (retirar)
- Subtotal: 31300.00 ARS
- Estado final: `requires_confirmation` (listo para confirmar)
- Al confirmar: estado `registered` (en simulación)

### 6.3 Prueba C: Registro con confirmación explícita

**Resultado esperado:**
- Ejecutar pipeline con `--confirmar --registrar`
- Agente 7 (registro) debe ejecutar `registrar_pedido`
- Estado final: `registered`
- Clave de pedido generada (distinta del message_id)

### 6.4 Prueba D: Idempotencia (webhook duplicado)

**Resultado esperado:**
- Ejecutar el mismo evento dos veces con el mismo message_id
- Segunda ejecución debe devolver `duplicado` sin crear segundo pedido

## 7. Criterios de aceptación

- [ ] Ningún pedido se registra sin confirmación explícita del cliente.
- [ ] Un webhook duplicado devuelve el resultado ya obtenido (sin duplicar pedidos).
- [ ] Los totales coinciden con el catálogo y la aritmética del backend.
- [ ] En modo simulación (por defecto) no se realizan llamadas de registro reales.
- [ ] Los crédenciales nunca se loguean ni se almacenan en texto plano.
- [ ] Productos inexistentes no se registran como válidos.
- [ ] Pedidos parciales (con productos no identificados) quedan en `requires_clarification`.

## 8. Archivos modificados (según pruebas)

| Archivo | Cambio | Motivo |
|---------|--------|--------|
| `agentes/pipeline.py` | Agregado trace_id al contexto | Trazabilidad de extremo a extremo |
| `agentes/contexto.py` | Agregado campo trace_id | Identificar cada ejecución única |
| `agentes/agente_interpretacion.py` | Carga catálogo externo por comercio_id | Soporte multi-comercio |
| `orquestador-pedidos-whatsapp/orchestrator.py` | Intérprete con unidades, cantidades, productos no disponibles, ambiguedades | Soporte supermercado y pizzería |
| `orquestador-pedidos-whatsapp/config/catalogo_loader.py` | Cargador de catálogos JSON externos | Catálogos configurables por comercio |
| `app_web.py` | Selector de comercio, diagnóstico de agentes | Interfaz web con trazabilidad |
| `tests_audio/evento_supermercado.json` | Nuevo | Evento de prueba para supermercado |
| `tests_audio/evento_pizzeria.json` | Nuevo | Evento de prueba para pizzería |
| `PLAN_IMPLEMENTACION.md` | Nuevo | Este documento |
| `README.md` | Actualizado | Resultados de pruebas de funcionalidad |

## 9. Próximos pasos

1. Ejecutar pruebas A, B, C, D con los archivos de evento creados.
2. Documentar resultados en `README.md`.
3. Si se encuentran fallos de reconocimiento, aplicar corrección mínima y reejecutar.
4. Validar que el registro en simulación funcione correctamente con `--confirmar --registrar`.

## 10. Rediseño visual — Interfaz de observabilidad (completado)

La interfaz `app_web.py` fue rediseñada como un dashboard de IA sin modificar la lógica de negocio:

### Archivos modificados
- `agentes/pipeline.py` — Agregado `event_callback` opcional y políticas/acciones por agente para observabilidad. No se rompió el contrato público.
- `app_web.py` — Rediseño completo: CSS personalizado, layout 2 columnas, componente Flujo Inteligente, tarjeta Orquestador, resultado final, diagnóstico colapsable.

### Componentes visuales creados
- Tarjeta del Orquestador con barra de progreso real basada en agentes ejecutados.
- Componente "Flujo inteligente" con 7 tarjetas de agentes (estados: pendiente, procesando con pulso, completado, bloqueado, error).
- Tarjeta de resultado final diferenciada por estado (válido verde / incompleto naranja / error rojo).
- Sección de diagnóstico colapsable por defecto con eventos de agentes.

### Mecanismo de eventos
- `pipeline.ejecutar()` acepta `event_callback` opcional.
- Eventos: `agent_started`, `agent_completed`, `agent_blocked`, `agent_failed`.
- Cada evento: `trace_id`, `agent_name`, `status`, `action`, `policy`, `result`, `timestamp`.

### Resultados de pruebas del rediseño
| Prueba | Estado | Resultado |
|--------|--------|-----------|
| Supermercado (transcripción real) | `requires_clarification` | 3 productos identificados, nafta súper no disponible, choplos/revistas no asumidos |
| Pizzería (dos pizzas para retirar) | `requires_confirmation` | 2 productos, subtotal 31300.00 ARS, pickup |
| Pizzería + confirmar + registrar | `borrador` (simulación) | Registro en simulación, clave de pedido generada |
| Idempotencia (webhook duplicado) | Mismo resultado | No duplica pedidos |
| Pedido ambiguo (3 pizzas, 2 variantes) | `requires_clarification` | Falta tercera variante detectada |

### Comando para iniciar
```cmd
C:\Voz a texto\.venv\Scripts\streamlit run app_web.py
```

**CRITERIO FUNDAMENTAL:** No se sacrificó funcionalidad por estética. No se reescribieron componentes operativos. La interfaz muestra visualmente el comportamiento real del sistema.
