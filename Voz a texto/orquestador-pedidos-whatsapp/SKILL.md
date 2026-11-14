---
name: orquestador-pedidos-whatsapp
description: Orquestador que recibe webhooks de WhatsApp, coordina descarga de audio, transcripcion, interpretacion, validacion, confirmacion y registro de pedidos de voz. Usar con la skill tomando-pedidos-voz-whatsapp.
license: MIT
compatibility: Requiere WhatsApp Business Platform, servicio de transcripcion, catalogo del comercio y backend de pedidos. Credenciales mediante variables de entorno.
metadata:
  author: equipo-tfi
  version: "1.0.0"
---

# Orquestador de pedidos de voz por WhatsApp

## Objetivo

Orquestar el flujo de extremo a extremo de un pedido de voz: recibir el webhook de WhatsApp, descargar y transcribir el audio, interpretar el pedido con la skill, validar contra el catalogo, calcular el total, solicitar confirmacion al cliente y registrar el pedido confirmado en el backend.

El orquestador no confirma compras ni cobra por su cuenta. Su responsabilidad termina al entregar el pedido validado y confirmado al componente autorizado de registro.

## Flujo del orquestador

1. Recibir el evento de WhatsApp (webhook HTTPS) y verificar su identificador.
2. Validar el evento con `scripts/validar_evento.py` (esquema, tipo de mensaje, idempotencia inicial).
3. Descargar el audio mediante el componente autorizado (WhatsApp Business Platform).
4. Transcribir el audio mediante el servicio autorizado (Azure AI Speech o Whisper).
5. Invocar la skill `tomando-pedidos-voz-whatsapp` para interpretar la transcripcion y extraer el pedido.
6. Validar productos, cantidades y disponibilidad con `scripts/validar_pedido.py`.
7. Calcular importes con `scripts/calcular_total.py` (aritmetica decimal).
8. Generar el resumen de confirmacion o la pregunta de aclaracion.
9. Enviar el mensaje al cliente por WhatsApp y esperar su respuesta.
10. Si hay aclaraciones, repetir la interpretacion con la respuesta del cliente.
11. Al recibir confirmacion explicita, registrar el pedido con `scripts/registrar_pedido.py`.
12. Anonimizar datos antes de loguear con `scripts/anonimizar.py`.
13. Registrar trazabilidad sin almacenar el audio mas tiempo del necesario.

## Estados del pedido

`received -> transcribed -> interpreted -> requires_clarification -> requires_confirmation -> confirmed -> registered`

Estados alternativos: `cancelled`, `rejected`, `expired`, `manual_review`.

No se pasa de `interpreted` a `registered` sin atravesar `requires_confirmation` y `confirmed`.

## Politica de acciones

Todas las acciones con efecto real (envio de WhatsApp, registro de pedido) aplican las compuertas del orquestador:

1. Preparar borrador.
2. Validar datos, precios, disponibilidad e idempotencia.
3. Mostrar resumen al cliente.
4. Esperar confirmacion explicita.
5. Registrar mediante el unico componente autorizado.
6. Guardar resultado e identificador de operacion.

## Variables de entorno

- `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`
- `TRANSCRIPCION_API_URL`, `TRANSCRIPCION_API_KEY`
- `CATALOGO_API_URL`, `CATALOGO_API_KEY`
- `BACKEND_PEDIDOS_URL`, `BACKEND_PEDIDOS_KEY`
- `AUDIO_STORAGE_URL`, `AUDIO_STORAGE_KEY`
- `COMMERCE_ID`: identificador del comercio para claves de idempotencia.
- `REGISTRAR_PEDIDOS`: `1` para habilitar registro real (por defecto simulacion).

## Estructura

```text
orquestador-pedidos-whatsapp/
├── SKILL.md
├── README.md
├── orchestrator.py
├── requirements.txt
└── references/
```

## Criterios de aceptacion del orquestador

- Ningun pedido se registra sin confirmacion explicita del cliente.
- Un webhook duplicado devuelve el resultado ya obtenido (sin duplicar pedidos).
- Los totales coinciden con el catalogo y la aritmetica del backend.
- En modo simulacion (por defecto) no se realizan llamadas de registro reales.
- Los credenciales nunca se loguean ni se almacenan en texto plano.
