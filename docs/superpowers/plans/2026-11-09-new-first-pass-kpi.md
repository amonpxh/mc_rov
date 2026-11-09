# Primera aceptación conjunta de equipos nuevos

Continúa la definición ya aprobada, no agrega un KPI nuevo: RND y TRN obligatorias,
basta un fallo real, observaciones informativas pueden aprobar sin corrección ni
reensayo. Primer fallo y desconocidos se conservan desde captura inmutable.

## Adaptador de lectura

API elegida por implementación: mc.rov.new.acceptance.kpi.get_summary(production_ids).
Selección explícita actual de fabricaciones, análoga al adaptador actual de selección
de reparaciones. No afirma cohortes por período, entregas físicas, liberación FEN,
cumplimiento comercial ni tablero de negocio terminado.

Autorizar primero cuenta interna con consulta del equipo, empresas activas y todas
las fabricaciones/productos elegidos, sin exigir escritura. Resolver unidades con
la función nativa _produced_lots: fabricación terminada, salida principal positiva,
producto serializado. Solo ROVs de la raíz configurada; sin raíz el servicio falla
explícitamente, sin producir un cero falso. Excluir fabricación incompleta y
productos fuera del giro. Contar una unidad por empresa/serie, sin duplicar por
selección repetida o separaciones administrativas del mismo grupo de fabricación.

Consultar episodios/intentos privados solo después de autorización de origen.
Comprobar fabricación original, serie, producto y ambas revisiones históricas antes
de usar evidencia: una fuente restringida rechaza la selección completa, nunca
oculta un fallo. No ampliar ACL privada. Verificar identidad/producto/grupo del
episodio frente a la unidad seleccionada; un origen ambiguo no se escoge por azar.

Normalizar estado y first_pass_snapshot sellados para first_pass_status existente.
Sin intento formal=unknown incluso si hay pruebas antiguas confirmadas. Un intento
pending=pending; failed=failed; confirmed solo pasa si first_pass_snapshot=passed.
Una aceptación técnica con flags desconocidos no entra como primera aprobación.
Éxitos posteriores, reaperturas, políticas apagadas o cambios de respuesta no
sustituyen la primera presentación.

Salida: basis selected_productions_new_units_current, población, passed/failed/
pending/unknown, evaluated, porcentaje passed/evaluated, cobertura evaluated/población
y episodios mínimos autorizados (empresa, serie, grupo, estado, primer ordinal).
Sin denominador=valor None; no confundir vacío o desconocido con cero. Sin JSON
privado, notas de pruebas, nombres de clientes ni resultados individuales crudos.

## Validación

RED30 contratos y4 controles nativos, conservando241 anteriores=275 focalizados;
total declarado1521. GREEN mismos casos, backup/recuperación freshDB y snapshot
estricto sin cambios de datos/ACL. Luego regresión, lectura autorizada/QA visual y
revisión independiente antes de entregar el incremento completo. No producción,
activación de políticas ni clasificación retrospectiva. Inline/TDD autorizado.
