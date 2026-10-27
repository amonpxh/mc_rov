# Inventario y navegación adaptable del Centro

Usuario aprobó añadir un acceso nativo a Inventario y ocho botones del mismo ancho:
una fila amplia, dos filas de cuatro en tamaño mediano y dos columnas en móvil.

- Orden: Trabajo asignado, Reparar, Fabricar, Aceptar, Consultar equipo, Calidad,
  Inventario, Diseño / BoM. Etiquetas cortas solo en navegación; conservar encabezados.
- Inventario abre existencias/ubicaciones mediante `stock.quant.action_view_quants`
  con `always_show_loc=True`, conservando contexto/empresas y permisos nativos.
  No es la pantalla de conteo físico `action_view_inventory`.
- Capacidad declarada sin consultar cantidades: usuario interno, grupo nativo de
  Inventario y acceso de lectura a quants. Ocultar el botón sin permiso; el método
  público vuelve a comprobarlo, incluidas empresas activas, antes de invocar Odoo.
- No conceder ACL/grupos ni usar sudo para leer cantidades. No duplicar modelos,
  agregar estados o filtrar solo ROV: materiales y repuestos también son inventario.
- Salida del Centro conserva la protección de cambios sin guardar y la restauración
  de estado. Error/revocación de permiso no debe dejar el Centro en una pantalla vacía.
- CSS grid según ancho del contenedor: >=1360px ocho columnas; >=768px cuatro;
  por debajo dos. Mantener todo el ancho, botones iguales, texto legible y sin scroll
  horizontal. Colores nativos y foco de teclado conservados.
- Solo STAGING durante desarrollo/QA. Producción, PDFs, calendarios, automatismos y
  configuración real intactos. El código anterior tiene CI828/828 aprobado.

Decisión técnica del implementador: usar container queries, no la anchura global de
la ventana; los puntos de corte son una propuesta técnica dentro del diseño aprobado.

Fuente primaria contrastada (volver a validar contra código instalado):
https://github.com/odoo/odoo/blob/19.0/addons/stock/models/stock_quant.py
El acceso nativo puede ejecutar mantenimiento de quants propio de Odoo; no prometer
que ese mecanismo nativo es una consulta SQL estrictamente de solo lectura.
