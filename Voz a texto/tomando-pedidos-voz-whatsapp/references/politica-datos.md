# Politica de datos

Régimen de muestra, almacenamiento y transmision de informacion del cliente. Leer este archivo antes de mostrar, almacenar o transmitir informacion del cliente.

## Datos verdes (seguros de mostrar y almacenar)

- Productos y cantidades.
- SKU.
- Precios y moneda.
- Estado del pedido.
- Identificadores internos sin significado personal.

## Datos amarillos (minimizar, proteger, retener solo el tiempo necesario)

- Numero de telefono.
- Nombre del cliente.
- Direccion de entrega.
- Audio y transcripcion.
- Observaciones que puedan contener informacion personal.

Los datos amarillos deben minimizarse, protegerse y retenerse solo durante el tiempo necesario. El audio y la transcripcion se borran una vez completado el flujo o al expirar el plazo de retencion.

## Datos rojos (nunca entran al contexto del modelo, logs, memoria ni archivos compartidos)

- Tokens y credenciales.
- Datos de tarjetas.
- Codigos de verificacion.
- Contrasenas.
- Informacion financiera no necesaria para el pedido.

Ningun dato rojo se envia al modelo de interpretacion ni se registra en logs.

## Retencion

El audio original no se almacena mas tiempo del necesario. Una vez transcrito y validado el pedido, se programa su borrado del almacenamiento temporal.
