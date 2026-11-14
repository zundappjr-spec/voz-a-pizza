# Tomando pedidos de voz por WhatsApp

Skill para interpretar pedidos enviados mediante audios de WhatsApp, convertirlos en datos estructurados, validarlos contra el catalogo del comercio, detectar ambiguedades y generar una confirmacion clara antes de registrar el pedido.

## Objetivo

Convertir audios informales enviados por clientes mediante WhatsApp en pedidos estructurados, validarlos contra el catalogo vigente y solicitar confirmacion antes de registrarlos.

La skill no debe confirmar compras, cobrar ni generar pedidos definitivos por su cuenta. Su responsabilidad termina al producir un pedido validado y confirmado por el cliente. El backend ejecuta el registro definitivo.

## Flujo

1. Recibir el evento de WhatsApp y verificar su identificador.
2. Descargar el audio mediante el componente autorizado.
3. Transcribir el audio.
4. Interpretar la transcripcion y extraer los elementos del pedido.
5. Validar productos, variantes, precios y disponibilidad contra el catalogo.
6. Detectar ambiguedades o datos faltantes.
7. Generar una pregunta concreta o un resumen de confirmacion.
8. Esperar la respuesta del cliente.
9. Aplicar correcciones si las hubiera y volver a validar.
10. Entregar el pedido confirmado al backend para su registro.
11. Registrar la trazabilidad sin almacenar el audio mas tiempo del necesario.

## Estados permitidos

`received -> transcribed -> interpreted -> requires_clarification -> requires_confirmation -> confirmed -> registered`

Estados alternativos: `cancelled`, `rejected`, `expired`, `manual_review`.

No se puede pasar de `interpreted` a `registered` sin atravesar `requires_confirmation` y `confirmed`.

## Estructura

```text
tomando-pedidos-voz-whatsapp/
├── SKILL.md
├── README.md
├── references/
├── scripts/
├── assets/plantillas/
└── evals/
```

## Scripts

- `scripts/validar_evento.py`: valida esquema, tipo de mensaje e idempotencia inicial.
- `scripts/validar_pedido.py`: valida cantidades, SKU, variantes y campos obligatorios.
- `scripts/calcular_total.py`: calcula importes con aritmetica decimal.
- `scripts/anonimizar.py`: elimina o enmascara datos personales antes de logs o evaluaciones.
- `scripts/registrar_pedido.py`: opera en modo simulacion por defecto y requiere un indicador explicito para registrar.

## Criterios de aceptacion

- Ningun producto inexistente se registra como valido.
- Ningun pedido se registra sin confirmacion.
- Un webhook duplicado no genera pedidos duplicados.
- Los totales coinciden con el catalogo y la aritmetica del backend.
- Los mensajes distinguen claramente borrador, confirmado y registrado.
- No se almacenan credenciales ni datos de pago.
- Todos los errores relevantes producen una accion concreta y segura.
- Existen al menos tres evaluaciones automatizadas con resultado esperado.

## Variables de entorno

Configurar todas las credenciales mediante variables de entorno o un gestor de secretos. Nunca almacenar credenciales ni datos de pago.

- `WHATSAPP_ACCESS_TOKEN`: token de WhatsApp Business Platform.
- `WHATSAPP_VERIFY_TOKEN`: token de verificacion del webhook.
- `WHATSAPP_PHONE_NUMBER_ID`: identificador del numero de telefono.
- `TRANSCRIPCION_API_URL`: endpoint del servicio de transcripcion (Azure AI Speech o Whisper).
- `TRANSCRIPCION_API_KEY`: clave del servicio de transcripcion.
- `CATALOGO_API_URL`: endpoint del catalogo del comercio.
- `CATALOGO_API_KEY`: clave del catalogo.
- `BACKEND_PEDIDOS_URL`: endpoint del backend para registrar pedidos.
- `BACKEND_PEDIDOS_KEY`: clave del backend.
- `AUDIO_STORAGE_URL`: endpoint de almacenamiento temporal de audio.
- `AUDIO_STORAGE_KEY`: clave de almacenamiento temporal.
- `COMMERCE_ID`: identificador del comercio para claves de idempotencia.

## Licencia

MIT
