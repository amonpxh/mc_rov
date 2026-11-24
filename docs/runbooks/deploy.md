# Despliegue de mc_rov

El [flujo Git](../agents/git-flow.md) y [las reglas de entrega](../agents/releases.md) separan el squash, la release, la instalación y la activación. Paulo autoriza la instalación de un paquete concreto. Una aprobación del PR cubre el merge del HEAD revisado.

## Preparación

1. Identificar commit de `main`, versión nueva cuando cambie producto, CI del commit y archivos exactos. Revisar migraciones, cambios de permisos y compatibilidad. Consultar el estado realmente instalado, [staging](staging.md) y [pruebas](testing.md).
2. Preparar un paquete reproducible con huellas, validaciones, alcance de datos, límites y procedimiento de recuperación. Ensayar las migraciones y la recuperación en una copia aislada cuando corresponda. Documentar cualquier comprobación pendiente.
3. Confirmar entorno, versión de origen, espacio y respaldos. Antes de la actualización, respaldar y comprobar base de datos, filestore, código y configuración de la entrega. Registrar huellas y evidencia en el canal autorizado. Introducir SSH solo en el terminal autorizado.
4. Obtener autorización explícita para instalar esa versión, commit, paquete y entorno. Usar el instalador revisado de la entrega. Las fuentes del CI y las de producción usan checkouts separados.

## Instalación y verificación

Aplicar el paquete, comprobar que termine la actualización y verificar la integridad de datos, esquema, permisos y documentos dentro del alcance revisado. Reiniciar el servicio según el procedimiento autorizado. Confirmar servicio activo, respuesta HTTP y versión instalada, y verificar la huella del recibo. Registrar en [pendientes](../pendientes.md) qué se instaló, qué se verificó y qué activación quedó pendiente.

## Fallo y recuperación

Conservar la evidencia y diagnosticar el intento antes de repetirlo. Antes de liberar el servicio, recuperar únicamente con el procedimiento revisado del paquete. Después de liberar el servicio, evaluar las operaciones posteriores al respaldo y obtener autorización específica antes de restaurar datos. Un revert de código no revierte una migración ni una actualización de datos. Si se requiere un revert en Git, tramitarlo por rama y PR con squash autorizado.

Asignar responsables, permisos, calendarios, notificaciones e integraciones reales requiere aprobación separada.
