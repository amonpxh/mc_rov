# F3 — Cumplimiento de compromisos al cliente

Diseño aprobado por Paulo el 19 de noviembre de 2026, incluida la constancia
registrada por Supervisor con escritura en Inventario. Validación nativa
del recorrido pendiente en una copia QA con datos ficticios.

## Alcance y decisión

Paulo confirmó que el compromiso vive en el pedido de venta vinculado cuando
existe y en la orden de reparación cuando el trabajo carece de pedido de venta.
Un Supervisor con acceso al trabajo formaliza la promesa y registra los cambios
acordados con el cliente. La regla empresarial ya fija la promesa al aceptar el
cliente tanto el trabajo como la fecha. La entrega se mide como salida efectiva
del taller respaldada por constancia de retiro o despacho.

Se consideraron un origen comercial obligatorio, un origen operativo para cada
trabajo y el origen combinado aprobado. El primero exige ventas artificiales
para ciertas reparaciones. El segundo dispersa la promesa comercial en trabajos
que ya tienen pedido. El origen combinado conserva cada acuerdo donde se
gestiona y permite vincular la evidencia común de Inventario.

F3 abarca captura de promesas, evidencia de salidas y cálculo en el tablero.
El mismo evento de salida podrá servir a otros indicadores en incrementos
posteriores. La medición histórica comienza con la evidencia capturada de
forma explícita. Los registros existentes quedan identificados en cobertura
según la información disponible.

## Compromiso y autorización

- En Venta, el pedido aloja el compromiso y cada línea elegible define su
  alcance, cantidad de unidades ROV y series si están asignadas. Propuesta
  inicial: una promesa por línea y fecha común para sus unidades. Si una
  reparación se cotiza en una línea de servicio, usar la visita y serie
  verificadas incluso cuando el pedido aloja el compromiso. Exigir vínculo
  inequívoco por cada visita. En una reparación sin pedido, la visita y su
  serie identifican el compromiso dentro de su propia orden. El valor nativo
  de fecha prometida se propone para captura y la confirmación conserva
  la fecha aceptada para el alcance concreto.
  Fabricación para stock queda fuera hasta que exista un trabajo con cliente
  y promesa aceptada.
- Propuesta para un pedido asociado después de fijar la promesa en Reparación:
  conservar la identidad y el origen ya registrados y enlazar el pedido como
  referencia posterior. La misma visita o línea vinculada queda excluida de la
  creación de una segunda promesa para el mismo alcance.
- Conservar una fecha original, su precisión, alcance y evidencia de
  aceptación, así como el autor y el momento de captura. Cada recompromiso
  conserva la nueva fecha, motivo, respaldo del acuerdo y autor. Las ediciones
  nativas de fechas de planificación conservan su función operativa. Para
  promesas pactadas solo por día, se propone comparar el día local de
  Santiago. Un plazo pactado con hora usa el instante acordado.
- El rol de Supervisor se comprueba en servidor junto con el permiso efectivo
  de escritura sobre el origen y la empresa autorizada. Identificar la
  capacidad existente que represente al Supervisor en ambos orígenes antes
  de asignarla. Si falta una capacidad común, el diseño técnico debe permitir
  designarla por separado con membresía inicial vacía. El historial se consulta
  con permiso de lectura del origen. La evidencia de transferencia que se
  exponga también exige acceso a esa transferencia. El tablero respeta el
  acceso a registros y empresas. El acceso insuficiente aparece como estado
  de acceso donde corresponda. El despliegue futuro no concede roles reales.
- Las modificaciones de historial se hacen mediante acciones explícitas,
  con validación de origen y empresa. Probar altas simultáneas, doble envío y
  rechazo de cambios directos por RPC o importación. Las correcciones futuras
  conservan la evidencia anterior y su motivo.

## Salida respaldada

- Reutilizar las transferencias nativas validadas del taller hacia el cliente,
  sus líneas, cantidades y series. En Venta, conciliar por línea comercial. En
  Reparación, exigir el movimiento vinculado y su serie. El enlace nativo
  de la visita a su recepción no acredita la devolución al cliente. Cuando
  falte un vínculo de salida, el Supervisor puede indicar la visita en la
  constancia de una transferencia efectivamente validada. Verificar empresa,
  cliente, serie y acceso a ambos documentos. Si falta el enlace o es
  ambiguo, mostrar cobertura pendiente. Los movimientos
  internos y cancelados quedan fuera del cálculo de cumplimiento.
- Propuesta de captura en la transferencia validada. Registrar modalidad
  despacho o retiro, fecha efectiva y referencia a la constancia existente en
  Odoo. Una firma se considera constancia cuando respalda esa modalidad y esa
  fecha. La fecha de validación permanece visible como dato técnico. Si la
  transferencia se valida días después de la salida física, usar la fecha de
  la constancia. La captura corresponde al Supervisor con
  acceso efectivo de escritura a la transferencia.
- Conciliar sólo unidades distintas del alcance pactado. La salida que
  completa todas las cantidades y requisitos fija la fecha de cumplimiento.
  Cada movimiento y serie se concilian una vez. Registrar devoluciones sin
  convertir una reentrega en un segundo cumplimiento. Si una serie regresa
  antes de completar el compromiso, queda pendiente hasta una salida válida.
  Una devolución posterior queda como incidencia separada y conserva el
  primer cumplimiento ya acreditado.
- Una invalidación de evidencia conserva el evento anterior y su corrección.
  Si el compromiso deja de tener salida evaluable, vuelve a cobertura
  pendiente. La primera entrega muestra cancelaciones con evidencia en
  detalle, con fecha y razón. Propuesta: las anuladas mediante acuerdo
  antes de vencer salen del porcentaje. Una cancelación posterior al
  vencimiento conserva el incumplimiento anterior. Una cancelación
  posterior al cumplimiento conserva la salida acreditada.
- La primera entrega conserva cantidades y series pactadas. Ante un cambio
  de alcance, mantener el compromiso anterior con su resolución trazable.
  La ampliación se registra aparte cuando su alcance sea distinguible.
  La sustitución o reducción parcial queda como excepción visible hasta
  definir su tratamiento. No reasignar series ni reducir el alcance histórico
  para mejorar el indicador.

## Tablero y pruebas de aceptación

- **Vencimientos del período**. Compromisos elegibles que vencían según la
  promesa original. Denominador incluye abiertos vencidos. Mostrar completos
  a tiempo, completos tarde, pendientes vencidos y cobertura. Con 10 que
  vencían, 8 a tiempo, 1 tarde y 1 abierto vencido, el resultado es 8/10.
- **Completados en el período**. Compromisos elegibles cuya salida completa
  ocurrió en el período, una vez por compromiso. Con 9 completados y 8 a
  tiempo, el resultado es 8/9. Mostrar aparte la última fecha
  recomprometida y acordada antes de la salida que completa el compromiso.
  Para abiertos, usar el último acuerdo anterior al corte de consulta.
  Un acuerdo firmado después de la salida queda en el historial. El motivo
  de demora atribuible al cliente se muestra si está documentado y no
  modifica el porcentaje contra la promesa original.
- Un compromiso sin fecha aceptada figura como «Sin compromiso definido».
  Una salida con vínculo o fecha sin justificar queda como evidencia
  insuficiente. Un vencido que sigue abierto de forma verificable entra como
  incumplido. Un movimiento registrado cuya salida efectiva es indeterminada
  queda en cobertura, con conteo propio y fuera del porcentaje adjudicable.
  Si la promesa incluye hora pero la constancia solo aporta el mismo día,
  dejarlo como indeterminado. Conservar fecha efectiva y fecha de captura
  para que una constancia tardía pueda aclarar una salida documentada sin
  alterar la promesa. El tablero usa la evidencia disponible al consultarlo.
  Un denominador vacío se muestra sin cálculo. Usar cortes y calendario
  acordados para Santiago.
- Probar los dos orígenes, dos series en una línea, parciales y restante,
  devolución previa y posterior, salida efectiva distinta de la validación,
  reparación que recibe pedido después de fijar, cambio de fecha, cancelación,
  compañías, autorización del origen y de la transferencia, y ausencia de
  evidencia. Cotejar cada caso con la ficha del catálogo en QA aislada antes
  de publicar el cambio.
