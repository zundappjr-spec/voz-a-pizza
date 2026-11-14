# Formato de catalogo

Reglas para interpretar el catalogo del comercio.

## Estructura de un producto

```json
{
  "sku": "PIZ-G-MUZ",
  "name": "Pizza grande de muzzarella",
  "price": 14500,
  "currency": "ARS",
  "available": true
}
```

## Reglas de interpretacion

- Usar exclusivamente productos existentes en el catalogo recibido.
- No inventar SKU, precio, promocion, variante ni disponibilidad.
- Ante nombres similares, pedir una aclaracion con opciones concretas.
- Si un producto no existe, informar alternativas reales del catalogo sin seleccionar ninguna automaticamente.
- Obtener precios unicamente del catalogo o de la API autorizada.
- Informar moneda y version del catalogo utilizados.

## Disponibilidad

Solo se pueden incluir en el pedido productos con `available: true`. Un producto sin stock se rechaza y se notifica al cliente.
