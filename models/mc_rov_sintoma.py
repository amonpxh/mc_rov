from odoo import models, fields

# Las familias agrupan el catálogo en el buscador de etiquetas. Son Selection y no catálogo
# por el mismo criterio que las secciones de los pasos de testeo: son la estructura del
# documento y no crecen con el uso, mientras que los síntomas de adentro sí.
#
# `temporalidad` reemplaza al campo `momento_falla` que este diseño llegó a tener: que la
# falla vaya y venga es algo que el cliente VIO, así que es un síntoma según el único
# criterio con el que se decide eso (¿lo vio o lo deduce?). Como campo aparte traía un valor
# "No se sabe" por defecto que volvía imposible distinguir "no sabe" de "nadie preguntó";
# como etiqueta el problema no existe, porque no ponerla es honestamente no ponerla.
FAMILIAS_SINTOMA = [
    ("energia", "Energía"),
    ("movimiento", "Movimiento"),
    ("video", "Video"),
    ("comunicacion", "Comunicación"),
    ("sensores", "Sensores"),
    ("accesorios", "Accesorios"),
    ("fisico", "Físico"),
    ("temporalidad", "Cuándo ocurre"),
    ("otro", "Otro"),
]


class McRovSintoma(models.Model):
    """Catálogo de lo que el cliente dice que le pasa al equipo.

    Es la mitad que faltaba de la cadena. `mc.rov.revision.hallazgo` registra **lo que el
    taller comprueba**; hasta ahora lo que **alguien reporta** entraba como párrafo en
    `falla_reportada` y no se podía contar. Sin las dos mitades se pierde el único análisis
    que un taller puede producir y un fabricante no: cuántas veces lo que el cliente creía
    que estaba roto no era lo que estaba roto.

    Es catálogo y no Selection porque va a crecer —entra el USBL, entra un modelo nuevo— y
    porque retirar una entrada tiene que ser desmarcar `active` y no una migración que deje
    huérfanas las órdenes que la tenían.

    El criterio para agregar una entrada: **si dos síntomas mandan a mirar lugares distintos,
    son síntomas distintos.** Lo que no hay que agregar es una opción para lo dudoso: absorbe
    todo lo dudoso y vacía a las demás. Para eso está "Otro" más el texto libre.
    """

    _name = "mc.rov.sintoma"
    _description = "Síntoma reportado en un ROV"
    _order = "familia, sequence, name"

    name = fields.Char(string="Síntoma", required=True)
    sequence = fields.Integer(default=10)
    familia = fields.Selection(FAMILIAS_SINTOMA, string="Familia", required=True, default="otro")
    active = fields.Boolean(default=True)
