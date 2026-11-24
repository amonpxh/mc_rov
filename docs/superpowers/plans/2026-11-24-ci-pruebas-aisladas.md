# Selección de pruebas y base de CI por ejecución

El fallo del [PR #134](https://github.com/amonpxh/mc_rov/pull/134) dejó en evidencia
que el checkout aislado seguía actualizando una base compartida. Un cambio
documental debe pasar validaciones documentales sin abrir Odoo. Un cambio en la
fórmula compartida de Trabajo asignado ejecuta las pruebas puras y el grupo nativo
`work_kpi`. Los cambios sin clasificación segura conservan la suite completa.

1. Probar el clasificador con casos documentales, fórmula, pruebas puras y cambios
   mixtos o sensibles. Contrastar los archivos del HEAD exacto de #134.
2. Crear por ejecución una base desde `template0` y un directorio de datos temporal.
   Instalar el addon candidato antes de las pruebas. Pasar el destino a las pruebas
   nativas y de navegador. Aislar la copia usada por las carreras y conservar sus
   comprobaciones de descubrimiento.
3. Conservar logs y retirar solo los recursos creados por la ejecución. Validar el
   flujo completo en el runner del PR de infraestructura. Los controles vigentes
   del #134 cambian cuando adopte el workflow nuevo después de su integración.
