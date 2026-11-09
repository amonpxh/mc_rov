# Resultados nativos del intento conjunto RND/TRN

Continúa la apertura conjunta aprobada GREEN161, baseline145 fuentes. Usuario:
ambas pruebas obligatorias; un fallo real en cualquiera adjudica fallo conjunto.
Inline/TDD, sin UI nueva ni activación real; revisión independiente antes de entrega.

## Resultado e historia

Cada confirmación nativa de una fuente seleccionada congela su veredicto, flags
corrección/reensayo, autor y evidencia contra el alcance guardado al inicio. Nada se
crea para revisiones sin intento formal. No inferir observación informativa desde
la etiqueta nativa: flags unknown impiden afirmar primer pase aprobado.

Un rechazo o requerimiento explícito de corrección/reensayo cierra el intento
fallido, aunque falte la otra prueba. Dos fuentes aprobadas sin esos requerimientos
cierran confirmado; first_pass_snapshot passed solo con ambos flags no de ambas
pruebas; unknown si falta clasificación. Mantener técnica aprobada y primer pase
desconocido como datos separados. Una nota informativa puede pasar.

Acción explícita de interrupción en la revisión seleccionada exige motivo y evidencia
real (chequeo no_ok, continuo con_problemas o hallazgo bloqueante); puede cerrar
protocolo incompleto. No convierte Hecho/Cancelar de una actividad en ejecución.
No sobreescribir una fase ya capturada. Reapertura de fase capturada durante un
intento pendiente se rechaza; después de cerrar, correcciones no cambian snapshots.
El siguiente intento usa dos revisiones nuevas en borrador del mismo episodio.
Reutilizar una prueba anterior requeriría un tratamiento técnico distinto no aprobado.

## Integridad

Cerrar revisión y capturar fase en el mismo savepoint; error de captura revierte
confirmación. Repeticiones idempotentes no reemplazan actor/fecha/evidencia. Resultado
posterior de la otra fuente no modifica un intento ya fallido. Guardar closed_at,
finished_by_id, first_pass_snapshot y results en JSON privado. Únicamente capacidad
Python interna puede modificar campos de resultado mientras pending; identidades,
ordinal y configuración siguen inmutables. Contexto RPC no autoriza confirmación cruda.

Locks MO→serie→revisiones→episodio, relectura tras locks. Validar digest y alcance
inicial sin comparar nombres vivos del catálogo. Mantener permisos/empresas de
fuentes; no ampliar ACL de historia ni necesitar recordatorios encendidos.

## Pasos

1. RED30 contratos de eventos y4 controles nativos; conservar161 anteriores=195.
2. GREEN195 mismos casos, backup/recovery freshDB y pruebas restauradas.
3. Fronteras adicionales, concurrencia y suite integral sobre producto final.
4. Presentación/KPI, QA aislado y revisión independiente final antes de entregar.
