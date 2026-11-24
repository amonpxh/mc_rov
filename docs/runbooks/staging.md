# Staging y QA aislado

| Entorno | Uso |
| --- | --- |
| CI | Checkout aislado y `odoo_test`. Sigue el [runbook de pruebas](testing.md). |
| STAGING | Verificar compatibilidad e instalación con el alcance expresamente autorizado. Tiene código, base, configuración y servicio propios. Verificar la identificación efectiva antes de ejecutar. |
| Copia QA | Reproducir permisos, concurrencia o recorridos de usuarios con datos ficticios y código identificado. Seguir el [ensayo de aceptación](aceptacion-operativa-rov.md). |
| Producción | Cambios por entrega autorizada, siguiendo [despliegue](deploy.md). |

## Preparar una validación

- Elegir entorno, commit exacto, propósito de la prueba y evidencia esperada. Crear una copia cuando el ensayo requiera mutaciones, acceso de usuarios o condiciones repetibles y el entorno compartido no sea apropiado.
- Si se necesitan datos de origen, acordar el alcance antes de copiar. Preferir casos ficticios y datos mínimos. La copia requiere su propia base, filestore, addon y configuración; verificar que la restauración, actualización y HTTP apuntan a ella.
- Antes de exponer una copia, neutralizar correo, cron e integraciones y deshabilitar accesos copiados. Preparar cuentas ficticias con el rol necesario, restringir el acceso y comprobar el destino desde el navegador. Gestionar las contraseñas fuera del repositorio y del chat.
- Para cambios de módulo, datos, acceso o servicio en un servidor, confirmar autorización vigente para el alcance concreto. Registrar qué se ejecutó, el commit y los resultados. Separar la evidencia técnica de lo observado en el ensayo de usuario.

## Cierre

Conservar evidencia y respaldo en la ubicación autorizada. Detener el servicio de la copia y bloquear sus conexiones al cerrar. Si una copia se cerró, conservar su historial. La reapertura o recreación requiere una necesidad y alcance explícitos. Registrar el estado en [pendientes](../pendientes.md).
