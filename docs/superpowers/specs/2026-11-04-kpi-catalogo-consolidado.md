# Catálogo y fichas de KPI para Marine Connection

Fecha:2026-11-04. Estado: consolidación autorizada; definiciones técnicas propuestas
y decisiones de negocio pendientes. Este documento sustituye las listas alternativas
como catálogo de trabajo. No autoriza metas, responsables reales ni despliegue.

## Alcance y estructura

Se mantienen22 **familias empresariales**. Cada familia puede contener varias medidas
que se nombran por separado; no son22 números intercambiables. El primer resumen
incluye11 familias: F1–F6, Q1–Q4 y A1. D1 es apoyo de calidad de datos. Tres paneles
operativos conservan las señales críticas y de preparación sin ocultarlas por quedar
fuera de esas11 fichas. No se suman10+11 ni22+23.

| ID | Familia | Primera versión y ampliaciones explícitas |
|---|---|---|
| F1 | Cartera, entrada/salida y antigüedad | Resumen inicial; cartera hasta cierre técnico y hasta salida al cliente separadas |
| F2 | Detenciones y causas | Resumen inicial; detención confirmada e intervalos, no solo señales de falta material |
| F3 | Cumplimiento de compromisos al cliente | Resumen inicial; vencimientos del período y compromisos completados en el período como vistas distintas |
| F4 | Reparaciones terminadas y equipos distintos | Resumen inicial; visitas, series y recierres separados |
| F5 | Unidades ROV por hito | Resumen inicial; fabricación, aceptación, liberación y salida al cliente |
| F6 | Plazo total y tramos de reparación | Resumen inicial; recepción física, diagnóstico, autorización, cierre y salida |
| F7 | Plazo total y tramos de fabricación | Posterior; hasta liberación/salida, con inicio acordado |
| Q1 | Aceptación al primer intento | Resumen inicial; episodio por visita/orden, serie y protocolo/versión |
| Q2 | Retornos relacionados tras reparación | Captura inicial; tasa solo con cohorte y ventana acordadas y observadas |
| Q3 | Retrabajo y causas | Resumen inicial; casos y HH, costo cuando esté conciliado |
| Q4 | Hallazgos y Pareto | Resumen inicial; observaciones, visitas/series afectadas e incidentes fiables separados |
| Q5 | Fallas posteriores de equipos nuevos | Posterior; cohortes de entregas, atribución y seguimiento |
| Q6 | Expediente y liberación | Completitud actual visible desde el principio; porcentaje correcto a primera revisión posterior |
| A1 | Cumplimiento y plazo de proveedores | Resumen inicial; estándar nativo y compromiso original por línea separados |
| A2 | Calidad de recepción | Posterior; población inspeccionada explícita |
| A3 | Disponibilidad de material crítico y confianza en inventario | Posterior; quiebres y exactitud de conteos como medidas distintas; preparación actual en P-PRE |
| A4 | Inventario envejecido y obsolescencia | Posterior; cantidades y valor separados, ventana por acordar |
| E1 | Hitos y flujo de ingeniería | Posterior; ECO por etapa/antigüedad y cumplimiento de hitos con sus propias fechas |
| E2 | Efecto de cambios de ingeniería | Posterior; series afectadas y esfuerzo, distinguiendo mejora/corrección/alcance |
| C1 | Capacidad y programa de trabajo | Posterior; carga/capacidad y cumplimiento de programa congelado como medidas diferentes |
| C2 | Esfuerzo registrado y previsto | Posterior; HH por tipo y desvío previsto/real; sin ranking por cuenta |
| C3 | Costos, desvío y rentabilidad | Condicionado; costo previsto/real y margen requieren bases diferentes y conciliadas |

Espera de autorización del cliente se observa en F2/F6. Tiempo de emitir cotización
o tasa comercial de aceptación no equivale a ese tiempo: queda como extensión
comercial por definir con su propia población, sin desaparecer de los pendientes.
OEE de un recurso concreto, MTBF/MTTR de equipo propio y métricas de operador quedan
condicionados; no se usan como resultado global del taller.

## Señales que acompañan el resumen

- **P-NC:** no conformidades críticas abiertas, antigüedad, evidencia y responsable
  de resolver. Los requisitos de bloqueo de liberación se acuerdan por protocolo;
  un promedio o Pareto no oculta un caso crítico.
- **P-PRE:** preparación para iniciar (material disponible/reservado, documentación/
  configuración y recurso requeridos) y para liberar. Regla de liberación
  acordada2026-11-04: pruebas obligatorias aprobadas, documentación requerida completa
  y ninguna no conformidad bloqueante pendiente, vinculadas al trabajo/serie.
  Listo para entregar es un hito separado de salida física registrada.
  Mostrar faltantes concretos. Ausencia de bloqueo registrado no demuestra preparación.
- **P-ET:** lista existente de etapas/actividades vencidas. Sus cierres no representan
  unidades producidas ni puntualidad al cliente.
- **D1:** cobertura por dato, población elegible y unidad; faltante, inválido y no
  aplicable separados. Incluye abiertas cuando se evalúan promesas/bloqueos.

## Contrato común de medida

**Unidad:** visita = orden de reparación asociada a un episodio de ingreso. Reabrir
la misma orden no crea otra visita. Serie identifica el equipo, no su única visita
de toda la vida. Episodio de aceptación incorpora orden/visita, serie y protocolo.
En fabricación se concilian producto terminado, cantidades, series y parciales;
no se presupone una MO por serie ni se cuentan subproductos como ROV nuevos.

**Fechas:** separar fecha efectiva del hecho, fecha de registro y programación.
La zona del tablero acordada2026-11-04 es America/Santiago, con reglas de cambio horario,
sin fijar un desplazamiento UTC constante. Semanas de lunes a domingo, meses y años locales;
instantes se conservan en UTC. Consultas por período incluyen inicio local y excluyen
el inicio del día siguiente al fin. Contratos con otra zona se identifican aparte.
Una fecha sin hora no se convierte en un instante físico inventado.

**Historia:** eventos y correcciones conservados, con motivo y autor. Un reverso o
desmontaje posterior no borra que existió fabricación. No reconstruir fechas físicas,
primer resultado o promesas originales desde la última modificación o texto del chatter.
Un saldo histórico se muestra solo si hay eventos/instantánea que cubren ese corte.

**Tasas:** mostrar n/N, población, período y cobertura. Sin denominador se muestra
sin base; sin el dato necesario, desconocido. No aplicar mínimos de muestra, ventanas,
metas o colores de cumplimiento numéricos sin acordarlos. Los agregados de grupos
con elementos compartidos y equipos únicos pueden ser no aditivos: advertirlo.

**Exclusiones:** separar QA/capacitación identificados, prototipos y desarrollo.
Cancelación anterior a ejecución no es producción; correcciones/reversos posteriores
tienen tratamiento explícito. No descartar trabajo válido porque su estado cambió luego.

**Permisos:** usuario interno con consulta del equipo y lectura de los documentos
origen, limitado a empresas autorizadas. Un flujo sin permiso es no disponible, no0.
Los historiales privados mantienen ACL; el tablero no concede roles nuevos.

**Atribución:** cliente del trabajo en el momento correspondiente, no propietario
actual. Fabricación para stock puede no tener cliente. Modelo/variante, serie,
cliente, tipo de intervención y período son filtros donde existan datos autorizados.
Los tipos de intervención múltiples se tratan como etiquetas superpuestas: no sumar
sus subtotales como si fueran categorías exclusivas.

## Fichas del primer resumen

### F1 Cartera y antigüedad

- **Decisión:** qué priorizar, qué carga está pendiente y cómo cambia.
- **Unidad/población:** visitas de reparación por un lado; órdenes y unidades
  pendientes de fabricación en medidas distintas. Cada cartera tiene límites propios.
- **Medidas:** entradas, salidas, reaperturas/ajustes, saldo al corte y antigüedad.
  Saldo inicial + entradas + reaperturas − salidas − cancelaciones/ajustes = saldo final.
  Se descuenta cada salida efectiva de esa cartera, incluidos recierres; no se usa
  el contador de primeras terminaciones únicas de F4 para este balance.
- **Límites:** reparación hasta cierre técnico y reparación hasta salida al cliente
  son dos carteras. Una orden reparada aún en el taller sigue en la segunda.
- **Fechas/fuente:** ingreso físico cuando exista; confirmación como antigüedad
  administrativa rotulada por separado. Estados y eventos nativos/locales; snapshots
  en cortes acordados si no existe historia suficiente.
- **Cobertura:** ingreso sin dato y saldo histórico no reconstruible se informan;
  no se completa retrospectivamente por suposición.
- **Presentación:** entradas/salidas, saldo y lista ordenable por antigüedad. Tramos pendientes.
- **Comprobación:** saldo2 +3 entradas −1 salida −1 cancelación =3; reabrir agrega
  entrada a la cartera correspondiente sin crear otra visita para F4. Entrada,
  cierre, reapertura y recierre dejan saldo0 y una sola terminación única en F4.
- **Estado:** agregación posible para saldo actual; cortes históricos y recepción por auditar.

### F2 Detenciones efectivas

- **Decisión:** qué impide avanzar y quién debe destrabarlo.
- **Unidad/población:** orden/visita abierta; intervalos de detención confirmada.
- **Medidas:** abiertas detenidas / abiertas elegibles; duración detenida total y por causa.
- **Regla:** material esperado, riesgo de atraso o BoM cambiada son alertas de riesgo;
  para detención debe confirmarse que el trabajo no puede avanzar según su recorrido.
- **Causas iniciales acordadas2026-11-04:** repuestos/materiales, autorización o
  información del cliente, ingeniería, documentación, falta de personal/equipo
  de prueba y servicio externo; Otro exige explicación. Registrar inicio/fin,
  causa y responsable de destrabar; el catálogo puede ampliarse conservando historia.
- **Tiempo:** intervalo inicio–fin o inicio–corte si sigue abierto. Total = unión de
  intervalos. Decisión de diseño de Codex: duración por causa como unión de sus
  intervalos, rotulada no aditiva entre causas; no repartir tiempos simultáneos
  arbitrariamente. Conteos por causa usan intervalos registrados como unidad explícita,
  no visitas ni días únicos; un Pareto de tiempo aditivo exigiría otra regla de reparto.
- **Fuentes:** disponibilidad nativa como señal; registros locales de intervalos si
  existen. Falta verificar la captura de inicio/fin/causa/responsable de destrabar.
- **Cobertura:** no marcado no significa que jamás se detuvo. Duración desconocida
  no es0. Colas normales se muestran aparte de bloqueos hasta acordar su clasificación.
- **Comprobación:** falta de repuesto que no impide otras operaciones queda como
  riesgo; dos intervalos superpuestos de2 y3 días pueden sumar3 días, no5.
- **Estado:** causas y criterio de detención acordados; captura, permisos y manejo
  de solapes por comprobar en implementación. No cambia la promesa al cliente.

### F3 Cumplimiento con el cliente

- **Decisión:** compromisos en riesgo y cumplimiento de lo prometido.
- **Unidad:** compromiso de visita/serie/línea de entrega con cantidad y requisitos,
  definido antes del cálculo. No mezclar un pedido de varias series con una sola.
- **Entrega acordada:** salida del taller registrada al cliente, mediante transferencia
  validada con serie y constancia de despacho o retiro. La validación acredita el
  registro; no demuestra por sí sola el movimiento físico ni confirma recepción
  en destino. Identificar retiro por el cliente solo cuando exista esa constancia.
  Criterio aceptado2026-11-04 dentro del circuito de compromiso y salida; el recorrido
  instalado y la constancia concreta siguen por comprobar. Rótulo: salida del taller
  registrada a tiempo.
  Si la validación se registra después del hecho físico, no usar automáticamente
  su hora como hora de salida: hace falta fecha efectiva respaldada por la constancia.
- **Promesa acordada2026-11-04:** conservar en Odoo fecha original y recompromisos,
  motivo y autor. Queda firme cuando el cliente acepta el trabajo y la fecha acordada.
  Sin fecha acordada, mostrar sin compromiso definido. Documento/vínculo y roles
  siguen por precisar; no asumir que toda orden actual ya tiene promesa válida.
- **Vista de vencimientos:** compromisos que vencían en período cumplidos completos
  y a tiempo / compromisos elegibles que vencían en período. Incluye pendientes vencidos.
- **Vista de completados:** compromisos completados del período a tiempo / compromisos
  elegibles completados del período, una sola vez por identidad. Su fecha es la salida
  que completa cantidad y requisitos, no cada transferencia parcial. Responde otra
  pregunta y lleva otro nombre/denominador que la vista de vencimientos.
- **Fuentes:** venta/compromiso y transferencia done desde ubicación del taller hacia
  cliente, con identidad y cantidades conciliadas. No inferir salida desde el cierre
  de reparación ni desde FEN emitida. Excluir movimientos internos, cancelados y
  primera salida parcial como cumplimiento total.
- **Cobertura/exclusiones:** sin promesa original o evidencia suficiente se informa
  aparte. Retraso por causa del cliente se estratifica; no reescribe la promesa original.
- **Comprobación:** de10 compromisos vencidos,8 salieron a tiempo,1 tarde y1 sigue
  pendiente: vista vencimientos8/10; vista de completados8/9 si esos9 compromisos
  se completaron en el período.
- **Estado:** datos base nativos; promesa original, entrega aplicable y cobertura por verificar.
  Referencia de capacidad: [entregas nativas Odoo19](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/shipping_receiving/daily_operations/receipts_delivery_one_step.html)
  y [trazabilidad por serie](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/product_management/product_tracking/serial_numbers.html).
  Esta documentación no demuestra que el recorrido del taller ya esté configurado.

### F4 Reparaciones terminadas

- **Decisión:** volumen terminado y mezcla de intervenciones.
- **Unidad:** visita/orden y, por separado, serie distinta de ROV.
- **Medidas:** visitas con primer cierre técnico válido en período; series distintas;
  recierres/retrabajos y salidas al cliente en medidas independientes.
- **Regla:** una visita aporta una reparación terminada una sola vez. Reabrir/recerrar
  se registra como reapertura/recierre, no como otra visita nueva. Corrección de un
  cierre inválido conserva evento y motivo; no cambia historia sin trazabilidad.
- **Fecha/fuente:** evento de cierre validado. Movimiento del equipo reparado es un
  candidato en cierre estándar; auditar relación, done y cobertura. fecha_entrega_real
  es declarada/editable y no se convierte automáticamente en ese evento.
- **Cortes:** cliente histórico, modelo, tipos de intervención, garantía y período.
- **Cobertura:** órdenes sin serie/producto o con fecha desconocida se muestran aparte;
  una importación nacida cerrada no recibe fecha inventada.
- **Comprobación:**3 visitas cerradas sobre2 series =3 reparaciones y2 equipos;
  reabrir una de esas visitas no convierte el total en4 reparaciones.
- **Estado:** reutilizar análisis nativo de reparación; conciliación de fechas/historia pendiente.

### F5 Unidades por hito de fabricación

- **Decisión:** qué se fabricó, qué está aceptado/liberado y qué salió al cliente.
- **Unidad:** episodio de fabricación y serie de producto final ROV; cada hito válido
  se cuenta una vez por episodio/serie. Una entrega posterior de una reparación
  no genera otra unidad nueva fabricada.
  La identidad del episodio debe permanecer estable a través de MO y backorders;
  una división administrativa no crea otra unidad. Conciliar el vínculo original
  antes de definir su lectura. Los saldos entre hitos requieren estado válido al
  corte y reversos/reaperturas; no son resta ciega de acumulados históricos.
- **Medidas/fechas:** fabricación por salida fabricada done; aceptación por evento
  de aprobación del protocolo; liberación cuando se acreditan pruebas obligatorias
  aprobadas, documentación requerida completa y ninguna NC bloqueante pendiente;
  salida a cliente por transferencia done. Mostrar existencias entre hitos al corte.
- **Fuentes:** MO/salidas/series, revisiones, ficha emitida y transferencia. FEN ya
  conserva pruebas y PDF para equipo nuevo; comprobar las tres condiciones de
  liberación, sin inferirlas solo desde ficha emitida.
  Una ficha nueva no sustituye despacho ni se extiende sin más a reparaciones.
- **Exclusiones:** subproductos, componentes y prototipos separados. Reversos o
  desmontajes posteriores se presentan aparte y no borran la fabricación histórica.
- **Cortes/cobertura:** modelo, período y cliente o para stock/desconocido; conciliar
  cantidades con series sin descartar silenciosamente salidas no serializadas.
- **Comprobación:** una MO con2 ROV y un parcial de1+1 aporta2 unidades finales;
  aceptar1, liberar1 y entregar0 conserva2/1/1/0 por hito.
- **Estado:** criterio de liberación acordado; conciliar movimientos/fechas/evidencia
  y registrar su hito. No asumir división obligatoria de MO.

### F6 Plazo de reparación y tramos

- **Decisión:** comprometer plazos y localizar demoras.
- **Unidad/población:** visitas salidas al cliente en período con límites conocidos.
- **Medida principal:** tiempo transcurrido recepción física–salida registrada;
  mediana, distribución y P80 cuando la base permita interpretarlo. Mostrar N siempre.
- **Tramos:** recepción–diagnóstico, diagnóstico–autorización, autorización–cierre,
  cierre–salida. Definir eventos antes de medir; HH y pruebas físicas van separadas.
- **Fuentes:** recepción/transferencias, revisión/diagnóstico, autorización y cierre.
  No usar creación de cotización como recepción del equipo.
- **Versión parcial:** confirmación–cierre administrativo puede mostrarse con ese
  nombre, nunca como plazo físico total ni serie directamente comparable al nuevo.
- **Cobertura/exclusiones:** pares incompletos fuera de la mediana y visibles como
  cobertura faltante. No excluir visitas largas ni restar espera del plazo total.
- **Comprobación:**10 días transcurridos y4 HH de intervención siguen siendo10 días
  y4 HH; una visita de60 días participa en la distribución, no se oculta.
- **Estado:** las HH ya tienen soporte; falta verificar hitos y cobertura de fechas.

### Q1 Aceptación al primer intento

- **Decisión:** calidad de la primera presentación formal y necesidad de repetir trabajo.
- **Unidad:** episodio de aceptación = visita/orden + serie + protocolo/versión;
  fabricación y reparación separadas. Una serie reparada dos veces tiene dos episodios.
- **Equipo nuevo, decisión2026-11-06:** el intento formal comprende rendimiento y
  terreno; un fallo real en cualquiera adjudica el intento como fallido aunque la
  otra prueba todavía no esté completa. Registrar conjuntamente el alcance y
  conservar los resultados posteriores sin sustituir el primero. Esta regla no
  convierte automáticamente revisiones antiguas ni emisiones FEN en primeros intentos.
- **Reparación final:** ante la propuesta del usuario de usar revisión de reparación
  final, se recomienda esa revisión como comprobación formal del trabajo terminado.
  Debe quedar vinculada explícitamente a la aceptación final; tipo reparacion o
  estado confirmado por sí solos no la identifican. Diagnóstico inicial y pruebas
  durante intervención se mantienen aparte. Rendimiento/terreno se añaden cuando
  el requisito aplicable al trabajo los exija, sin imponerlos a toda reparación.
  No sobrecargar el motivo actual: no contiene una opción de aceptación final.
  Casos del adaptador: diagnóstico rechazado no es primer fallo de aceptación;
  primera revisión final rechazada y segunda aprobada conservan primer pase fallido.
- **Denominador:** episodios con primer intento formal adjudicado aprobado/fallido
  en período. Pendientes e inválidos se muestran aparte; no desaparecen sin estado/motivo.
- **Numerador:** primer intento válido aprobado en todos los requisitos aplicables sin
  reensayo ni retrabajo. Criterio acordado2026-11-04: observaciones únicamente
  informativas permiten contar aprobación al primer intento si se cumplen todas
  las pruebas obligatorias y no hay correcciones ni reensayos pendientes. Una nota
  que exige corregir no se reclasifica como informativa para aprobar.
- **Regla de fallo:** un fallo real que interrumpe el protocolo adjudica el primer
  intento como fallido aunque falten ensayos. Solo falla de instrumentación/procedimiento
  que invalide realmente el intento puede excluirlo, con motivo y autorización.
  El inválido se conserva y el primer intento válido/adjudicable posterior determina
  el resultado. Cambiar versión de protocolo después de fallar no crea por sí solo
  un nuevo episodio ni borra el primer fallo; distinguir cambio real de alcance.
- **Fuentes:** revisión/pase y calidad existentes; conservar primer veredicto y protocolo.
  Volver a borrador/corregir no borra el resultado original. Yield de MO no sirve aquí.
- **Desglose:** ensayo detector, modelo/protocolo, fabricación/reparación y período.
- **Comprobación:** fuga en primer ensayo, reparación y segundo pase aprobado =0/1
  primer pase y1 episodio finalmente aprobado; otra visita de la serie cuenta otro episodio.
- **Estado:** estructura parcial existente; primer resultado durable y versión por auditar/capturar.

### Q2 Retorno relacionado tras reparación

- **Decisión:** investigar eficacia de intervención y recurrencia.
- **Unidad:** visita entregada original, cohorte por salida registrada y tipo de trabajo.
- **Ventana acordada2026-11-04:** W=180 días desde la salida registrada del taller.
  Para especificación se interpretan como días corridos de observación, no180 días
  laborables ni seis meses. Es ventana del indicador, independiente de la garantía
  comercial; conservar la fecha/tipo del evento de salida sin inventar una hora.
  Convención técnica de este incremento: trabajar por fecha civil de Santiago y
  cortes diarios cerrados; el día180 se incluye, el181 no. Un instante se convierte
  a fecha en el adaptador, sin atribuir esa medianoche como hora física de salida.
- **Denominador:** visitas elegibles de una cohorte con W íntegramente observado.
- **Numerador:** visitas originales con al menos un retorno dentro de W y relación
  técnica confirmada con su intervención. Mismo subsistema por sí solo no demuestra relación.
- **Fuentes:** serie, visita anterior, fechas y dictamen técnico. Cualquier retorno
  y relación por confirmar se muestran como medidas diferentes, no tasa definitiva.
- **Exclusiones/cobertura:** mantenimientos programados y daños nuevos documentados
  separados; casos sin seguimiento o sin dictamen no se convierten en ausencia de falla.
  W transcurrida no demuestra seguimiento: exigir registros propios que cubran W y
  rotular siempre retornos observados en MC, sin inferir los no comunicados. Si hay
  retornos con relación pendiente, n confirmados / N maduros se rotula mínimo confirmado
  observado y muestra esos pendientes; no se presenta como tasa definitiva.
- **Comprobación:** una visita con dos retornos relacionados aporta1 visita afectada;
  una visita recién salida no entra a la tasa madura. La tasa observada no es fiabilidad de flota.
  Ejemplo:10 visitas con180 días observados,2 afectadas por3 retornos relacionados
  y4 visitas aún en seguimiento producen2/10, no3/10 ni2/14. Los retornos conocidos
  de visitas recientes se muestran desde su registro, separados de la tasa madura.
  Retorno después del día180 queda fuera de esta tasa, sin desaparecer del historial
  ni del seguimiento operativo.
- **Estado:** W acordada; historia por serie reutilizable, enlace/causalidad,
  cobertura efectiva y reglas de cálculo de bordes por especificar/comprobar.

### Q3 Retrabajo y causas

- **Decisión:** reducir repetición evitable y su esfuerzo.
- **Unidad:** episodio de trabajo/visita/serie y evento de retrabajo; no mezclar órdenes y series en una tasa.
- **Medidas:** episodios cerrados del período con al menos un retrabajo / episodios
  elegibles cerrados; HH de retrabajo / HH registradas elegibles como otra medida.
- **Definición:** repetir/corregir trabajo cuyo resultado no cumplió. Alcance adicional
  legítimo no es retrabajo; una ECO que corrige un defecto puede originarlo, una mejora
  o cambio de alcance no se clasifica automáticamente como tal.
- **Fuentes:** líneas HH/empleado/acción/origen existentes y alertas. Verificar marca
  de retrabajo, evidencia y causalidad; no duplicar por varios hallazgos relacionados.
- **Cobertura:** clasificación desconocida y HH sin dato visibles; no calcular costo
  completo con tarifa o material desconocidos. Inspección normal no es retrabajo.
- **Cortes:** causa confirmada/no determinada, etapa detectora, componente y modelo.
- **Comprobación:** un episodio con tres correcciones cuenta1 episodio con retrabajo,
  tres eventos documentados y suma de sus HH, sin multiplicar las HH por joins.
- **Estado:** reutilizar líneas/causas; clasificación y cobertura por verificar.

### Q4 Hallazgos y Pareto

- **Decisión:** qué fallas, componentes o causas conviene atacar.
- **Unidades:** observación registrada; visita afectada por categoría; serie afectada;
  incidente único solo cuando existe identidad válida y observaciones vinculadas.
- **Incidente:** incorpora instancia/posición del componente y continuidad del caso.
  Visita+catálogo de componente+modo de falla es sugerencia de agrupación, no identidad segura.
- **Medidas:** frecuencias por unidad elegida y porcentaje acumulado; Pareto por
  horas/costo solo con atribución fiable. Criticidad se estratifica, no se suma como
  escala monetaria sin pesos acordados.
- **Fechas/filtros:** detección del hecho/observación, modelo, protocolo, componente,
  cliente histórico y punto de detección. Ventana móvil opcional por acordar.
- **Separaciones:** condición recibida, problema del proceso y retorno; síntoma,
  causa confirmada/no determinada y acción son ejes distintos.
- **Cobertura:** categorías/causas faltantes visibles. Más hallazgos no es meta de
  reducción por sí sola; comparar también visitas inspeccionadas comparables.
- **Comprobación:** una observación repetida en3 revisiones puede ser1 incidente;
  dos propulsores físicos con la misma falla pueden ser2. Sin identidad, no inventar1 ni2.
- **Estado:** catálogo/revisiones existentes; auditar campos/deduplicación antes del rótulo incidente único.

### A1 Proveedores

- **Decisión:** proveedor, plazo de compra y riesgo de abastecimiento.
- **Unidad propuesta:** línea de compra y recepción completa; componentes críticos separados.
- **Puntualidad original:** líneas con recepción completa a tiempo / líneas elegibles
  cuyo compromiso original vencía en período. Incluir pendientes vencidas; sin promesa se informa aparte.
- **Plazo real:** confirmación de compra–última recepción que completa cantidad
  comprometida. Fecha del primer parcial no equivale a recepción completa.
- **Fuentes:** PO/líneas, promesa del proveedor y movimientos done; congelar original
  y conservar modificaciones/cancelaciones. Devoluciones tienen reglas explícitas.
- **Reutilización:** reporte nativo sujeto a comprobar vista, módulo y permisos instalados;
  si pondera unidades y usa fecha vigente se presenta con otro nombre, no como
  continuidad histórica del indicador por líneas/promesa original.
- **Cobertura/exclusiones:** servicios, cancelación antes de ejecutar y cambios de
  alcance se identifican. Faltante no se convierte en plazo0. Nacional/importado
  es filtro solo si existe clasificación fiable.
- **Comprobación:**100 pernos y1 propulsor son2 líneas en la tasa por líneas; otra
  tasa por unidades responde otra pregunta. Un parcial puntual no cumple una línea completa.
- **Estado:** Compras/purchase_stock y campos nativos verificados; compromiso original,
  conciliación de recepción completa y reporte específico aún por validar. Esta
  copia no contiene órdenes ni líneas de compra para comprobar ejemplos históricos.

## D1 Cobertura y trazabilidad de los cálculos

Para cada medida: elegibles, conocidos/válidos, faltantes, inválidos y no aplicables;
porcentaje conocido solo con denominador aplicable. Una visita sin hallazgos no
carece de causa de hallazgo; una orden abierta sí necesita promesa si la medimos
como compromiso. No usar todas las órdenes cerradas como denominador universal.

Cada resultado debe identificar versión de definición, origen, período, unidad,
cobertura y fecha de actualización. Tasas de visitas por tipo superpuesto y series
únicas no se suman entre grupos/períodos sin volver a deduplicar.

## Fuentes instaladas y brechas antes de crear datos nuevos

Auditoría STAGING ejecutada2026-11-04, intento `20261104-115911-124`,34 modelos,
sin modelos solicitados ausentes. Recibo completo revalidado contra139 hashes y
comparado con el JSON guardado. READ ONLY/rollback, archivos y PID intactos;
STAGING activo. Trabajo remoto: `/var/tmp/mc-rov-kpi-catalog-source-fkOLHT`.
Evidencia en el workspace Code:
`.tmp/preparacion-uso-real-pilot/catalog-source-installed-20261104-115911-124.json`.

**Límite de los conteos:** incluyen todos los registros de los modelos, sin separar
QA, componentes, prototipos o ROV elegibles. No representan rendimiento real ni
confirman las poblaciones del tablero. Los conteos por campo no verifican su
intersección, exactitud ni historia; campo presente no equivale a dato fiable.
Producción y copia QA cerrada no fueron consultadas ni modificadas.

| KPI/dato | Reutilización verificada | Brecha que conserva la ficha |
|---|---|---|
| F1 Cartera | Estado de reparación/fabricación, tipo de intervención y serie; reporte nativo de reparación con lista/gráfico/pivote | Saldo actual posible con población acordada; corte histórico y entradas físicas requieren eventos válidos, no create_date |
| F2 Bloqueos | Señales nativas de disponibilidad de piezas/productos | No se acredita un registro de intervalos de detención efectiva; acordar causas y solapes antes de completar captura |
| F3 Salidas al cliente | Picking con origen/destino, cliente, date_done, firma y líneas con serie; sale.order.commitment_date | No se acredita promesa original congelada ni constancia clasificada de retiro/despacho; fecha de validación no prueba hora física |
| F4 Reparaciones terminadas | repair.order con serie, cliente de la visita, tipos, fecha_entrega_real y move_id | Fecha propia es Date editable y se completa al cierre si falta; no equipararla a salida al cliente ni a historia inmutable del primer cierre |
| F5 Unidades fabricadas | MO con fecha de término, cantidades, varias series y vínculo a venta; movimientos terminados y FEN | Conciliar unidades ROV, parciales/reversos y series; MO no equivale a unidad ni exige cliente si se fabrica para stock |
| F6 Plazos de reparación | Orden, revisión, movimiento y relaciones a picking/venta existentes | Verificar semántica y continuidad de recepción, diagnóstico, autorización, cierre y salida; relación a picking no acredita por sí sola cada hito |
| Q1 Primer pase | Revisión, chequeos, motivo, serie/visita, responsable, resultado actual y software/configuración | Primer veredicto adjudicable y protocolo/versión no quedan acreditados como historia durable; secuencia en visita no equivale a primer intento formal |
| Q2 Retornos relacionados | Historia de visitas por serie y revisiones | Mismo equipo no demuestra causalidad; falta acreditar enlace técnico, dictamen, salida original y seguimiento suficiente durante W |
| Q3 Retrabajo | Línea de trabajo con orden, componente/subtipo, acción, empleado, fecha, HH, origen, causa, hallazgo y alerta | Clasificar retrabajo con evidencia; no duplicar campos de HH/persona/causa ni inferir retrabajo desde origen de manufactura |
| Q4 Hallazgos/Pareto | Observaciones de revisión y catálogos de hallazgo, severidad y componente/subtipo | Observación no equivale a incidente único; catálogo de componente no identifica instancia/posición física |
| A1 Proveedores | purchase/purchase_stock instalados; aprobación, fecha prevista, cantidades recibidas, movimientos y líneas | Promesa original por línea, recepción completa/retornos y acción de reporte concreta aún por validar; no usar primer recibo como fin completo |

### Cobertura observada en esta copia

- Reparación:6 órdenes done;4 con serie,4 con cliente,3 con fecha_entrega_real y5
  con movimiento done. Son conteos separados; no aseguran que los mismos registros
  cumplan todos los criterios ni que sean reparaciones ROV reales.
- Fabricación:11 MO done;11 con date_finished,9 con conjunto de series y0 con
  sale_line_id. El9 cuenta órdenes con serie, no nueve equipos; fabricar para stock
  sin cliente puede ser válido.
- Inventario:1 picking done;0 done de tipo outgoing y0 done desde ubicación interna
  hacia cliente. Hay campos para el recorrido propuesto, pero ningún ejemplo de
  salida completa en las poblaciones consultadas. No extrapolar el cero a producción.
- Revisión:31 registros,11 vinculados a reparación,31 con responsable y6 confirmados.
  Diagnóstico/reensayo no se confunden con aceptación formal. resultado puede volver
  a vacío al reabrir y no acredita primer veredicto histórico; confirmar alguna vez
  no conserva por sí solo el veredicto original o protocolo.
- Trabajo/HH:6 líneas,6 con origen clasificado,2 con horas positivas,1 con empleado y0
  con enlace a hallazgo. Se conserva captura existente; no imputar horas ni personas
  faltantes. Los conteos no validan clasificación, duplicación o causalidad.
- Calidad/expediente:20 categorías de hallazgo,0 observaciones de revisión;3 FEN y1
  emitida con PDF. Un catálogo no son20 fallas ocurridas. FEN no acredita salida.
- Compras:0 órdenes y0 líneas. maintenance está instalado, sin equipos/solicitudes;
  sus métricas no aportan una base de fiabilidad ROV en esta copia.

### Qué verifica y qué no verifica esta auditoría

Los metadatos confirman tipos y relaciones; readonly de un campo no demuestra
inmutabilidad histórica ni permisos efectivos por rol. El colector leyó el método
efectivo seleccionado: algunos son envoltorios de quality_repair o mc_rov que
delegan a super, no toda la cadena nativa. No se ejecutaron acciones de negocio.

Se confirmaron acciones de análisis de reparación y producción con gráfico/pivote.
spreadsheet_dashboard base está instalado; la auditoría no acredita una plantilla
específica de Compras/Producción ni una vista KPI utilizable por todos los roles.
Los controles de permiso del servicio de etapas siguen aprobados, pero los nuevos
KPI empresariales necesitarán sus propios casos de empresa/origen/población.

Revisión independiente Q1–Q4: tres fuentes locales cotejadas con los hashes instalados;
reutilización de HH/causas/chequeos/catálogos confirmada. Solo completar historia y
clasificación realmente ausentes tras definir el hecho empresarial; no crear trece
campos nuevos en bloque ni rellenar retrospectivamente desde texto libre.

Revisión técnica adicional del catálogo y aceptación: reutilizar mc.rov.chequeo y
líneas de revisión, snapshots y PDF emitidos. Las semillas XML son noupdate; no
representan necesariamente configuración vigente. El audit34 no incluyó registros
de quality.point ni mc.rov.chequeo; se completó con la consulta siguiente. El catálogo aplica chequeos por tipo de
trabajo; no acredita obligatoriedad/versiones por modelo. Aprobado con observaciones
nativo tampoco acredita por sí solo que sean exclusivamente informativas.

Consulta técnica instalada2026-11-04, intento20261104-145645-429: cinco modelos
presentes y recibo revalidado contra139 hashes. mc.rov.chequeo contiene25 registros,
todos activos:18 aplican a rendimiento,24 a reparación y18 a terreno; categorías
solapadas, no60 pruebas distintas. quality.point contiene un registro inactivo,
sin alcance explícito de producto/categoría, y quality.point.test_type tiene9 tipos.
quality.test_type no está registrado; no crear un sustituto por ese nombre.
No leer esos valores como umbrales aprobados ni reactivar el punto para generar datos.

La consulta confirma reutilización del catálogo vigente, no una matriz aprobada por
modelo ni historia del primer intento. Próxima captura debe guardar instantánea
de requisitos aplicables y veredicto formal, manteniendo configuración actual y
resultados posteriores separados. Los cambios del catálogo no reescriben intentos.
Un aprobado con observaciones requiere clasificar explícitamente corrección/reensayo;
no convertir automáticamente la etiqueta nativa en observación informativa.

Evidencia workspaceCode `.tmp/preparacion-uso-real-pilot/`
`profiles-source-installed-20261104-145645-429.json`, trabajo remoto
`/var/tmp/mc-rov-kpi-profiles-source-sHqsH1`; READ ONLY/rollback, archivos/PID
intactos, sin instalar ni reiniciar y sin consultar QA/producción.

Antes de construir el adaptador, comprobar la divergencia local entre cálculo que
excluye funcionamiento continuo en terreno y validación que lo exige. No se ha
confirmado ni corregido como bug en este incremento. No inventar umbrales de presión,
tiempo o electricidad a partir de comentarios ni imponer nuevas pruebas reales.

## Compromiso de salida: regla acordada y detalle del circuito

Regla empresarial aceptada2026-11-04: registrar en Odoo la promesa original cuando
el cliente acepta el trabajo y la fecha; conservar cambios con motivo y autor;
comparar con la salida validada y mostrar sin compromiso definido cuando no se
haya pactado fecha. Actualmente no se formaliza así: las fechas existentes no se
convierten automáticamente en promesas acordadas. La selección del documento,
vínculo al trabajo, permisos y captura de evidencia son detalles de implementación
todavía por cerrar; no se han creado campos ni desplegado este circuito.

1. En cotización/pedido, reutilizar `sale.order.commitment_date` como candidata a
   fecha acordada. Mientras sea propuesta comercial, distinguirla de una promesa
   firme. Fecha prevista interna, duración estimada y fecha de creación son otras cosas.
2. Cuando el cliente acepta el trabajo y la fecha, conservar el compromiso original,
   documento/alcance, autor y momento de fijación. En reparación normalmente ocurre
   después del diagnóstico/presupuesto, sin darlo por hecho en todos los contratos.
   Si aún no hay acuerdo de fecha, mostrar sin compromiso definido; no inventar uno
   desde schedule_date o el plazo de una actividad.
3. Mantener la fecha original y cada nuevo compromiso con motivo y autorización
   del rol que se defina. Reprogramar trabajo interno no cambia por sí solo lo
   prometido al cliente. No conceder permisos comerciales por tener coordinación
   de actividades ni reemplazar silenciosamente el original al editar el pedido.
4. Vincular las salidas validadas a la serie y al compromiso, conciliando parciales
   y requisitos. `stock.picking.signature` existe y puede ser una evidencia a
   reutilizar; su captura, significado, acceso y recorrido necesitan verificación.
   No identifica por sí sola recepción en destino o modalidad despacho/retiro.
5. Comparar la salida que completa el compromiso con su fecha original; mostrar
   aparte cumplimiento del nuevo compromiso. Conservar pendientes vencidos en la
   vista de vencimientos y mostrar cobertura de los que aún no tienen fecha firme.

No imponer un pedido ficticio a reparaciones sin documento comercial válido: antes
de la implementación, precisar dónde vive el compromiso y su vínculo con cada
trabajo elegible. No registrar promesas retroactivas ni fabricar historia desde
mensajes. El circuito se probará con datos ficticios y roles equivalentes.

## Decisiones de negocio pendientes

1. Documento/vínculo y roles del compromiso F3. La fijación al aceptar trabajo y
   fecha ya está acordada. Identificar contratos con recepción en destino u otro
   hito para tratarlos con su definición propia, sin cambiar el rótulo de salidas.
2. Criterio técnico y registro del retorno relacionado, cobertura de seguimiento
   y casos de borde. W=180 días elegida por el usuario, independiente de garantía.
3. Lista de ensayos/protocolo y documentos exigidos por modelo/tipo de trabajo;
   identificar los perfiles ya existentes antes de completar configuración.
   Observaciones informativas sin corrección/reensayo y las tres condiciones
   de liberación ya están acordadas. No equiparar FEN a despacho.
4. Roles de registro/validación de bloqueo, veredicto, retorno y liberación;
   no inferir permisos nuevos desde cuentas QA o desde la coordinación de actividades.
5. Catálogo de bloqueos acordado; conservar solapes y duración no aditiva por causa,
   salvo que se acuerde después un reparto de tiempo diferente.
6. Calendario del tablero acordado: America/Santiago, lunes–domingo, meses/años
   calendario. Las reglas de días laborables mantienen el calendario operativo;
   contratos con otro calendario se identifican sin cambiar el significado del tablero.

Metas, bandas de color, tramos de antigüedad y ventanas móviles se fijan tras estas
definiciones y una base representativa. Empezar a conservar eventos necesarios no
significa habilitar nuevas cuentas/políticas ni modificar datos históricos.

## Próximo trabajo y límites

Auditoría complementaria terminada y mapa de fuentes actualizado. No repetirla
sin una necesidad nueva. El servicio de cálculo existente no implementa aún las
once fichas empresariales y no hay tablero nuevo instalado por este paso.
Tras responder las decisiones que afecten una ficha, especificar su incremento
con fuentes reales, casos conocidos y permisos; reutilizar reporte nativo antes
de crear otra interfaz. No empezar por programar22 familias de una vez.

Fuentes y contraste: [investigación y revisión detalladas](2026-11-03-work-kpi-design.md).
El servicio actual de etapas está aprobado36/36 y su regresión1282/1282 en STAGING;
esas pruebas no aprueban automáticamente estas nuevas definiciones empresariales.
