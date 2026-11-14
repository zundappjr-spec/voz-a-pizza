# Orquestador de pedidos de voz por WhatsApp

Orquestador que recibe webhooks de WhatsApp y coordina descarga de audio, transcripcion, interpretacion, validacion, confirmacion y registro de pedidos de voz. Usa la skill `tomando-pedidos-voz-whatsapp`.

## Como ejecutar

```bash
python orchestrator.py --webhook
```

O probar un flujo completo con un evento de ejemplo:

```bash
python orchestrator.py --test-evento eventos/ejemplo.json
```

## Modo simulacion

Por defecto el orquestador opera en modo simulacion: no realiza llamadas reales de registro. Usa `REGISTRAR_PEDIDOS=1` para habilitar el registro contra el backend autorizado.
