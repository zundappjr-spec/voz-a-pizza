# Agentes especializados — Tomador de pedidos de voz por WhatsApp

Siete agentes ejecutables que procesan pedidos de clientes recibidos mediante
mensajes de voz de WhatsApp. Reutilizan los contratos existentes de
`tomando-pedidos-voz-whatsapp/scripts/` y `orquestador-pedidos-whatsapp/`
sin modificar codigo operativo.

## Flujo de estados (del SKILL.md existente)

`received -> transcribed -> interpreted -> requires_clarification ->
requires_confirmation -> confirmed -> registered`

## Agentes

| # | Agente | Archivo | Responsabilidad | Contratos reutilizados |
|---|--------|---------|-----------------|------------------------|
| 1 | RECEPTOR | `agente_receptor.py` | Recibe el webhook, valida el evento, identifica al cliente, obtiene el message_id, detecta duplicados e identifica audios. | `validar_evento.validate_event`, `compute_idempotency_key` |
| 2 | TRANSCRIPCION | `agente_transcripcion.py` | Descarga el audio (componente autorizado), transcribe y borra el audio temporal. | `orchestrator.descargar_audio`, `transcribir_audio` |
| 3 | INTERPRETACION | `agente_interpretacion.py` | Extrae productos, cantidades, confianza y datos faltantes de la transcripcion. | `orchestrator.interpretar_pedido` |
| 4 | VALIDACION | `agente_validacion.py` | Valida SKU, cantidades, variantes y disponibilidad contra el catalogo. | `validar_pedido.validate_pedido` |
| 5 | CALCULO | `agente_calculo.py` | Calcula subtotal y total con aritmetica decimal determinista. | `calcular_total.calcular_total` |
| 6 | CONFIRMACION | `agente_confirmacion.py` | Genera el resumen de confirmacion o la pregunta de aclaracion y envia el mensaje por WhatsApp. | `orchestrator.enviar_mensaje_whatsapp`, `anonimizar.anonimizar_texto` |
| 7 | REGISTRO | `agente_registro.py` | Registra el pedido confirmado mediante el componente autorizado (simulacion por defecto) y anonimiza para loguear. | `registrar_pedido.registrar_pedido`, `generar_clave_pedido`, `anonimizar.anonimizar_para_log` |

## Ejecucion

Pipeline completo (modo simulacion, sin registrar):

```bash
python agentes/pipeline.py <commerce_id> <evento.json>
```

Con numero de cliente y confirmacion explicita:

```bash
python agentes/pipeline.py <commerce_id> <evento.json> <numero_cliente> --confirmar
```

Habilitar registro real:

```bash
REGISTRAR_PEDIDOS=1 python agentes/pipeline.py <commerce_id> <evento.json> --registrar
```

Cada agente también es ejecutable de forma independiente recibiendo un JSON de contexto.

## Politicas respetadas

- Ningun pedido se registra sin confirmacion explicita del cliente.
- Un webhook duplicado devuelve el resultado ya obtenido (idempotencia por message_id).
- Modo simulacion por defecto: no hay llamadas de registro reales salvo `REGISTRAR_PEDIDOS=1`.
- Credenciales y datos de pago nunca se loguean ni almacenan en texto plano (anonimizacion).
- El audio temporal se borra despues de transcribir (politica de datos).
