# Politica de acciones

Régimen para acciones con efecto real (confirmar, enviar o registrar un pedido). Leer este archivo cuando se confirme, envíe o registre un pedido.

## Compuertas obligatorias

Registrar un pedido o enviar un mensaje por WhatsApp son acciones externas. Aplicar estas compuertas en orden:

1. Preparar el borrador del pedido.
2. Validar datos, precios, disponibilidad e idempotencia.
3. Mostrar el resumen al cliente.
4. Esperar confirmacion explicita.
5. Registrar el pedido mediante el unico componente autorizado.
6. Guardar el resultado y el identificador de la operacion.

La skill no debe utilizar metodos alternativos para saltear estas compuertas.

## Confirmacion humana

Antes de registrar el pedido, mostrar como minimo:

- Productos y cantidades.
- Variantes y observaciones.
- Precio unitario y total.
- Modalidad de entrega.
- Horario solicitado.
- Direccion, solo cuando corresponda.

Aceptar como confirmacion expresiones inequivocas, por ejemplo: `si, confirmo`, `confirmar pedido` o la accion equivalente definida en la interfaz.

Una respuesta ambigua como `dale` puede tomarse como confirmacion solo si el mensaje anterior contenia el resumen completo y no habia preguntas pendientes. Esta condicion debe estar implementada y auditada por el backend.

## Idempotencia

- Usar `message_id` como clave inicial de procesamiento.
- Usar una clave independiente para el pedido confirmado.
- Si el webhook se repite, devolver el resultado ya obtenido.
- No crear un segundo pedido por reintentos de red.
- Registrar la respuesta del sistema despues de una operacion exitosa.

Clave sugerida:

```text
commerce_id|message_id|operation|catalog_version