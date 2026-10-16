# Piloto: seguimiento automático de fabricación

Versión: **19.0.25.1.0**. Instalar no elige destinatarios, crea políticas ni
reconstruye actividades de órdenes antiguas. La activación real sigue pendiente
de disponer de una cuenta Taller y verificar su configuración; no se usa Dev.

## Configuración y permisos

Con **Coordinar asignaciones**, abrir **Centro de trabajo → Configuración →
Seguimiento automático**. **Consultar trabajo del equipo** es otro permiso
independiente; ser coordinador no concede acceso a documentos ajenos ni a RRHH.

- **Control general:** por empresa, pausa la creación de nuevos pendientes
  automáticos de reparación y fabricación. Una fila ausente equivale a permitir
  creación si la política del proceso es válida. No apaga automatismos nativos.
- **Fabricación:** cuenta interna activa con acceso de lectura/escritura a la
  orden, empleado opcional, calendario/zona y plazo. El destinatario no hereda las
  empresas adicionales del coordinador. No se infiere del creador o editor.
- **Seguimiento de reparaciones:** conserva sus dos plazos de dos días laborables;
  comparte únicamente el interruptor general de creación.

Las configuraciones nuevas vienen activadas por defecto. Sin política, cuenta y
calendario válidos, el evento deja un aviso en la orden y no genera el pendiente.
La configuración QA se crea expresamente desactivada para empezar la prueba manual.
Pausar no retira pendientes ni impide sus cierres; reactivar no hace backfill.

## Plazos

Fabricación usa **28 días corridos**, cuatro semanas desde la confirmación efectiva.
Es configurable entre 1 y 365 días. Se suma a la fecha local del evento en la zona
del calendario, incluyendo fines de semana y festivos; no se suman horas laborales.

Una fecha límite explícita anterior de la orden prevalece. Una posterior no amplía
el plazo y una ya vencida permanece vencida. Una fecha estimada de finalización no
se interpreta como compromiso comercial. Cambiar la política afecta solo a eventos
futuros; los pendientes existentes no se alargan solos.

Para cambiar una fecha, usar **Repartir actividades**, marcar únicamente los campos
que deben cambiar e indicar motivo. Se conserva el resto y se registra auditoría
en la orden. Cuenta y empleado son distintos: Taller puede gestionar trabajo de Pedro.

## Eventos y decisiones

| Evento efectivo | Resultado |
| --- | --- |
| Confirmar una orden de producto bajo la raíz ROV | Crear «Completar fabricación», una vez |
| Reconfirmar o editar | No duplicar ni reconstruir el pendiente |
| Fabricar un componente ajeno a la raíz ROV | No generar seguimiento ROV |
| Terminar realmente la orden | Completar su pendiente como fabricación terminada |
| Cancelar y quedar cancelada | Cancelar el pendiente, sin acreditarlo como realizado |
| Abrir un asistente antes del cierre o quedar «Por cerrar» | Mantener el pendiente |
| Marcar la actividad hecha manualmente | Registrar decisión manual, sin terminar la orden |
| Cancelar, archivar o retirar manualmente la actividad | Registrar decisión, sin cancelar la orden |
| Duplicar una orden | Esperar confirmación propia, sin copiar historial |

Se observa el estado efectivo tras las acciones nativas, incluidos movimientos
de inventario y finalización desde operaciones. No se sustituyen los controles de
Calidad o los asistentes de Odoo. Terminar una MO tampoco confirma RND/TRN, FEN
ni la aceptación del equipo. Las actividades manuales ajenas al seguimiento,
aunque tengan el mismo título, no se alteran.

Resultado, cuenta autora y motivo se conservan en historial privado. Una decisión
manual no se transforma después en un resultado automático de negocio. Mientras
haya pendiente, no se puede sustituir producto/empresa ni el origen de la actividad.
Una orden con historial no se borra: se conserva y se cancela cuando corresponda.
Las consultas nativas y el filtro Fabricación respetan acceso al origen; el historial
técnico no tiene ACL pública ni exportación para las cuentas operativas.

## Fabricación parcial

La orden restante confirmada recibe su propia actividad e identidad. Si la original
tenía seguimiento, hereda su vencimiento vigente, incluso reprogramado o después
de retirar la actividad original. Un límite explícito anterior de la nueva orden
puede acortarlo: producir parcialmente no reinicia otras cuatro semanas.

Sin seguimiento original, la nueva orden aplica el plazo de su nuevo evento y su
límite explícito, sin reconstruir la original. Los controles siguen aplicándose.
El empleado se toma de la política, no se copia del reparto de la original.

El MRP auditado no ofrece una acción nativa para volver una orden cancelada a
borrador. Esta ampliación no incorpora un botón o proceso de reapertura.

## Verificación y entrega

STAGING: **594/594**, cero fallos/errores, cada prueba descubierta exactamente una
vez, incluidos 171 contratos de automatismos. Producto instalado coincidente con
el candidato, configuraciones/PDFs intactos y pruebas temporales retiradas.

Concurrencia real en copia sin cron/correo: dos conexiones de Taller partieron del
mismo estado. Confirmar dejó un seguimiento y un pendiente; finalizar dejó el mismo
seguimiento y cero pendientes activos. Hubo reintento completo por serialización,
cero huérfanos, y el cierre repetido encontró la validación nativa de serie ya
fabricada. No duplicó el resultado.

Evidencia del workspace: `.tmp/manufacturing-activity-pilot/`. Respaldos:

- Suite: `/var/tmp/mc-rov-manufacturing-regression-nFRdU2`.
- Concurrencia: `/var/tmp/mc-rov-manufacturing-concurrency-t0JTV0`.
- Copia conservada con conexiones bloqueadas: `mc_rov_manufacturing_ci_t0JTV0`.

Falta QA operativa y retirar su escenario conservando historial, antes de cerrar
la entrega mediante PR/CI. Producción no contiene esta ampliación. Despliegue y
activación real requieren aprobación y una cuenta operativa elegida explícitamente.

## QA manual temporal

El script del workspace `staging-manufacturing-activity-qa-users.ps1` crea cuentas
Taller/Supervisor QA, dos empleados, un producto ficticio, cuatro series y cuatro
órdenes en borrador: normal, parcial, cancelación y pausa. Respalda la base y registra
sus IDs para retirar solo lo propio. No cambia cuentas o calendarios existentes.
Reutilizar no cambia contraseñas; un escenario archivado no se reactiva solo.

La política QA queda desactivada, con Taller QA y 28 días corridos, usando un
calendario QA en America/Santiago. El script se niega a sustituir una política
preexistente ajena al escenario. En STAGING usar únicamente las órdenes QA.

Probar confirmar/repartir la normal y terminarla con su serie QA; fabricar una
unidad de la parcial y comprobar el pendiente restante; cancelar otra y confirmar
la última con la política pausada. Reactivar y editarla no debe reconstruirla.
