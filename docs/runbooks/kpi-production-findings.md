# Volumen de producción y hallazgos ROV

## Alcance y estado

Incremento F4/F5/Q4 del PR #124. Su publicación no implica integración,
instalación ni activación. Las fuentes se capturan desde las acciones nativas
futuras; no se clasifican ni fechan retrospectivamente registros antiguos.

## Consulta

Centro de trabajo → tablero KPI → Producción o Hallazgos. Se necesita consulta
de equipo y acceso a los documentos de origen en las empresas activas.
Las tarjetas permiten abrir sus documentos con el mismo período y filtros.
Sin acceso se muestra indisponibilidad, nunca un cero aparente.

Las fechas se interpretan en Santiago e incluyen ambos extremos. «Última» es
la configuración vigente por modelo/variante/código de BoM, no el mayor número
arbitrario. Si hay varias BoM vigentes ambiguas no se elige una por aproximación.
«Todas» incluye hechos sin diseño acreditado; una revisión concreta usa el diseño
sellado al confirmar Fabricación. Un ECO no cambia el diseño del pasado.
Cambiar empresa limpia modelo, cliente y revisión seleccionados.

## Qué cuenta cada tarjeta

- Reparaciones terminadas: primer cierre técnico nativo por orden/visita con
  movimiento y serie ROV acreditados. Se muestran también equipos distintos.
  Reabrir y recerrar la misma visita no agrega otra terminación.
- Fabricadas: una unidad serializada de producto final realmente producida por
  episodio de fabricación. Los parciales no duplican series; componentes y
  subproductos quedan fuera. No se crea una categoría de prototipos.
- Aceptadas: primera aprobación conjunta formal de rendimiento y terreno.
- Liberadas: primera validación explícita de Supervisor, con Ficha de Equipo Nuevo
  emitida y protocolo vigente aprobado. El Supervisor revisa que no haya NC
  bloqueantes; emitir la FEN por sí solo no libera ni entrega el ROV.
- Salidas: primer movimiento efectivo de interno a cliente de la unidad fabricada.
  Las transferencias internas no acreditan salida al cliente.

Los hitos del período conservan sus fechas originales. Reabrir el protocolo o
iniciar otro intento suspende la preparación vigente sin borrar la aceptación,
liberación histórica ni sus PDFs. Un nuevo protocolo aprobado y su FEN permiten
una nueva validación de preparación; no se cuenta otra unidad liberada.

Los saldos usan toda la historia hasta «Hasta», independientemente de «Desde».
Con cliente seleccionado, la cohorte se define por cliente acreditado al fabricar
y se reproducen todos sus movimientos, reaperturas y reversos. Los contadores de
hitos mantienen el cliente acreditado en cada hecho. Devolución y desmontaje
modifican el saldo y conservan el volumen histórico. Un hito sin prerrequisito
acreditado se señala para conciliación.

## Hallazgos

Registrar la fecha real de detección en la revisión, antes de confirmar.
Sin fecha conocida, dejarla vacía: no se usa la fecha de creación como sustituto.
El Pareto permite hallazgo/componente y observaciones/visitas/equipos. Una visita
puede pertenecer a varias categorías; el denominador es pertenencias a categorías
para visitas/equipos, no visitas únicas globales. «Sin clasificar» y «Otros»
conservan su participación. No son incidentes únicos ni costo u horas imputadas.

Una corrección posterior exige motivo en la revisión al reconfirmar; el historial
preserva original, reemplazo/retiro, actor y fecha de registro. Corregir una
observación no equivale a retirar una actividad automática del seguimiento.

## Cobertura y límites

Los registros antiguos, órdenes sin captura, unidades sin serie, detecciones sin
fecha y observaciones sin revisión acreditada se informan como cobertura.
No interpretar la cifra de hitos acreditados como cobertura total del pasado.
Los filtros por cliente usan evidencia histórica, no el propietario actual de la
serie. Ausencia de cliente acreditado no permite inferir un cliente por contexto.

No se agregan metas, rankings personales, causas inferidas, HH ni costos ficticios.
Permanecen pendientes las demás familias acordadas: detenciones, compromisos,
plazos completos de reparación, retornos relacionados, retrabajo y proveedores.

## Verificación antes de integrar o instalar

Exigir CI del HEAD concreto: casos nativos descubiertos por nombre, contratos
focalizados, carreras en copia efímera, HOOT y navegador poblado escritorio/móvil.
Los datos de prueba son propios; no conceder roles ni activar políticas reales.
Revisar versión, esquema privado y ACL del asistente transitorio, respaldo y
recuperación del paquete antes de solicitar autorización de despliegue.
