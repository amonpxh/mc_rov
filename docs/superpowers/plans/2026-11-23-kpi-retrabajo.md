# Q3 Retrabajo en Reparación

Clasificar sobre la línea de «Cierre» con los permisos nativos. Taller
documenta trabajo previsto, adicional o una propuesta de retrabajo.
La propuesta de retrabajo exige fundamento y un vínculo a un trabajo previo
de la misma serie y empresa, o al hallazgo o alerta de la línea. Supervisor
confirma la propuesta vigente. La confirmación es terminal y el historial
conserva actor, fecha y datos de la decisión. El cierre de Reparación conserva
sus validaciones actuales.

El tablero delimita visitas por el primer cierre técnico F4 en Santiago.
Las visitas sin líneas y las que tienen una clasificación pendiente se
muestran en cobertura. La tasa de visitas usa las visitas completamente
clasificadas. La proporción de HH usa las horas positivas de líneas
clasificadas, con faltantes y HH pendientes visibles. Se consulta el origen
y las HH de la línea nativa al consultar el tablero.

## Ensayo en la copia aislada de CI

Taller clasifica 3 HH como adicionales y propone 2 HH de retrabajo desde
Cierre. El cierre nativo se efectúa con la propuesta pendiente. Supervisor
revisa el fundamento y el trabajo anterior y confirma. El tablero debe
mostrar una visita, 2 de 5 HH y 40 %. Dos conexiones PostgreSQL comprueban
confirmación duplicada, sustitución de propuesta y rollback.
