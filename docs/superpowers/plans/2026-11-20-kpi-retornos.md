# Q2 Retornos relacionados

Taller vincula desde la visita de retorno, con escritura en esa visita y lectura
de ambas visitas, la serie y las transferencias que acreditan las fechas.
Supervisor con el mismo acceso y el permiso específico registra un dictamen
único con fundamento. Se conserva el vínculo, el autor y el momento de cada paso.
La selección es explícita y exige la misma serie y empresa, una salida F3 vigente
y inequívoca, y una llegada F6 acreditada. El día de salida conserva su precisión
original. Los retornos posteriores al día 180 conservan el dictamen.

El tablero muestra retornos observados por fecha de llegada, relación confirmada,
dictamen pendiente y otra causa, así como casos posteriores al día 180.
El porcentaje queda pendiente de una fuente de seguimiento que acredite
la cobertura de la cohorte. No se rellenan visitas históricas.

## QA operativo y concurrencia

- Crear dos visitas de retorno ficticias en la copia aislada de CI. Vincular
  ambas desde Reparación con Taller. Dictaminar una como relacionada y
  otra como otra causa con Supervisor. Contrastar el historial y el tablero.
- Lanzar dos conexiones PostgreSQL por caso: vínculo idéntico, dictamen
  idéntico, dictámenes opuestos y rollback de un dictamen. Comprobar la
  fila persistente, la evidencia original y el autor del dictamen desde
  una tercera conexión.
- Exigir descubrimiento y resultado de ambos roles, de las carreras y
  de la regresión existente. El PR #131 sigue en borrador.
