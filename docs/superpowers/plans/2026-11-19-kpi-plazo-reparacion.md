# F6: plazo de reparación

1. Acreditar llegada desde la visita, enlazando una transferencia validada
   del cliente al taller que contiene la misma serie. Confirmar si se
   validó al llegar o registrar la fecha y hora efectiva anterior con motivo.
   El permiso exige escritura nativa en ambos documentos. La evidencia es
   privada, inmutable y única por visita y por recepción de esa serie.
2. Usar la constancia F3 vigente por visita, incluso sin promesa. Mostrar
   días calendario en Santiago, mediana, distribución y P80 desde diez
   casos. Mostrar aparte salidas sin llegada acreditada o con cronología
   indeterminada. Varias salidas vigentes y accesibles de una visita requieren resolver
   cuál la completa. Conservar las HH como medida independiente.
3. Exponer F6 en Indicadores respetando acceso a la visita, serie y
   transferencias. Verificar primero el cálculo, después los contratos
   nativos de captura, permisos y la presentación.

Este incremento mide recepción–salida. Los tramos de diagnóstico y
autorización requieren eventos de negocio acordados. El primer cierre
histórico de F4 no se asumirá como cierre definitivo de una visita reabierta.
Sin reconstruir llegadas antiguas al instalar.

## QA en la copia de CI

- Abrir la visita como operador ficticio y pasar por el asistente en
  navegador para recepción al llegar y para validación posterior. Contrastar
  ambos sellos, motivo, autor y cómputo en el tablero.
- Sincronizar dos conexiones por escenario. Verificar reintento idéntico,
  decisiones de fecha incompatibles, dos visitas reclamando la misma serie
  en una recepción y reversión seguida por el registro del segundo actor.
- Guardar resultados técnicos en CI y verificar que la referencia
  `odoo_test` se conserve.
