# F2: detenciones efectivas de Reparación y Fabricación

Fuentes: catálogo consolidado 2026-11-04 y decisión de Paulo 2026-11-17:
«Taller y Supervisor, según su acceso a la orden». Implementación local autorizada;
publicación, instalación, integración y activación mantienen sus alcances propios.

## Contrato

- Registrar una detención solo cuando el trabajo no pueda avanzar. Disponibilidad,
  reservas y estados nativos son señales; no crean detenciones automáticamente.
- Órdenes ROV de reparación/fabricación confirmadas y abiertas; sin prototipos.
- Causas: materiales, cliente, ingeniería, documentación, personal/equipo de prueba,
  servicio externo y Otro (explicación obligatoria). Se admiten causas simultáneas.
- Inicio/fin efectivos prospectivos con reloj UTC del servidor, actor de registro,
  empleado responsable de destrabar y explicación. No reconstruir el pasado.
- Taller/Supervisor requieren cuenta interna y escritura nativa en la orden y su
  empresa activa. Consultas del tablero requieren el permiso existente de equipo
  y lectura del origen. No dar nuevos permisos sobre órdenes, stock ni empleados.
- No reemplazar la identidad de la orden/empresa ni editar/borrar evidencia por RPC.
  Al registrar fin se conserva quién abrió, cuándo y por qué. Cierre repetido idempotente.
- No pausar/cerrar la orden ni las actividades, ni cambiar cantidades, reservas,
  plazos prometidos o calendarios. El cierre/cancelación nativo termina intervalos
  abiertos como «Fin por cierre de orden», nunca como reanudación inventada.
- Un mismo motivo puede repetirse tras un fin; un inicio repetido con causa todavía
  abierta informa que ya existe. Serializar cambios sobre el origen entre conexiones.
- Total detenido por orden = unión de intervalos, recortados al período y corte.
  Total por causa = unión de sus intervalos; causas no aditivas entre sí. Sumar
  órdenes produce horas-orden, no horas-persona ni capacidad perdida inferida.
- Mostrar abiertas detenidas / abiertas elegibles al corte actual, intervalos,
  duración conocida y cobertura. Sin captura no demuestra ausencia histórica.
  No reconstruir saldos históricos desde estados actuales ni mostrar desconocidos como cero.

## Decisiones de implementación de Codex

Historial privado y asistentes nativos en ambas órdenes; responsable usa
hr.employee.public como el reparto existente, separado del usuario que registra.
Las correcciones históricas requieren incremento auditado posterior: no se habilita
edición genérica ni borrado para limpiar cifras. Esta limitación será visible.
Primer incremento: motor de intervalos y contratos nativos; después registro,
interfaz y tablero, con pruebas nativas y revisión antes de publicar/instalar.
