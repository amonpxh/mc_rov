# Adaptador de primera aceptación de reparación

Incremento autorizado del catálogo Q1. Se ejecuta inline con TDD y revisión final
independiente antes de entregar. Producción y copia QA cerrada no cambian.

## Contrato

Servicio separado `mc.rov.repair.acceptance.kpi.get_summary(repair_ids)` de solo
lectura para una selección explícita de órdenes. No amplía el resumen de etapas.
Exige usuario interno, consulta del equipo y lectura de todas las órdenes, series,
productos y revisiones históricas, dentro de las empresas activas autorizadas.
Validar IDs positivos únicos (deduplicar selección); entradas inválidas se rechazan.
Un origen inexistente o restringido rechaza toda la consulta, sin resultado parcial.

Cada orden/serie forma un episodio, aun reabierto o con varias revisiones. Se utiliza
el ordinal original de los intentos privados. Diagnóstico confirmado no cuenta como
intento final y no prueba aprobación. Sin intento devuelve unknown. Pending conserva
pending aunque cambien las respuestas vivas. Intento interrumpido por fallo real o
veredicto rechazado =>failed; aprobación con corrección/reensayo requerido =>failed;
aprobación, incluidas observaciones informativas, con ambos flags no =>passed.
Flags desconocidos impiden aprobar. No se implementa invalidación de intentos.

Ruling: el adaptador clasifica la selección actual, sin atribuirla a un período ni
presentarla como producción/entregas. Población, estados, numerador, denominador y
cobertura se devuelven explícitos. Tasa passed/(passed+failed), None sin evaluados;
pending/unknown fuera del denominador, visibles en cobertura. Un filtro temporal y
la elegibilidad empresarial completa serán responsabilidad del futuro tablero.
Solo retorna orden, serie, estado y ordinal primero; no publica snapshots privados.
No modifica datos, ACL, configuración, versiones ni crea interfaz.

## Pasos

1. Tests nativos RED de clasificación, selección, cobertura, privacidad y empresas;
   conservar 57 contratos de captura y 36 del servicio de etapas. Fixtures con
   acciones reales y rollback; controles nativos separados de ausencia del servicio.
2. Ejecutar RED en STAGING con producto/datos intactos; usuario ejecuta SSH.
3. Tras RED confirmado, implementar adaptador que use first_pass_status puro y
   snapshots sellados. GREEN focalizado con los mismos casos, sin relajar aserciones.
4. Revisar permisos/snapshot/cobertura, regresión integral si cambia el producto;
   revisión independiente final, integración y entrega por el flujo existente.

Este paso no entrega el tablero de once familias ni activa cuentas reales.

## Evidencia de ejecución

- RED127 confirmado20261106-104314-691:30 ausencias,97 controles verdes,0 errores.
- Primer GREEN127:126 verdes y1 error de preparación de readonly test por compute
  HTML privado sin rol; recuperación freshDB verificada, fallida KyTIrT conservada.
  Solo esa prueba cambia a snapshots de columnas almacenadas, con el mismo contrato;
  las otras126 y el producto permanecen idénticos. Transformación/hashes fijados.
- GREEN127 aprobado20261106-112304-186, backupQeveTB,144 fuentes, datos/configuraciones
  intactos, pruebas restauradas y STAGING activo. Núcleo puro50/50 y pylint10 locales.
- Revisión independiente del adaptador sin hallazgos accionables; no ejecutó suites
  ni SSH. Elegibilidad empresarial y período quedan explícitamente para el tablero.
- Full1373 preparado:1339 anteriores+34 nuevos, sin sustitución. Preparador exacto y
  parser2válidos/19rechazos locales aprobados. Ejecución nativa aún pendiente.

Full1373 nativo aprobado y recibo revalidado20261106-113317-034, backup
/var/tmp/mc-rov-repair-first-pass-kpi-regression-smA0SI.1339 anteriores+34 nuevos
una vez por nombre,0 errores/fallos;144 fuentes/datos/configuraciones intactos,
tests restaurados y STAGING activo. Commitc8116d8, revisión independiente sin hallazgos.
Incremento validado solo en STAGING; tablero, filtros empresariales/período y entrega
a producción siguen fuera de este paso.
