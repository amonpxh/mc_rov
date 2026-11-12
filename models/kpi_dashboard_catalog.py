"""Fichas acordadas: una definición pendiente nunca representa un cero medido."""

INITIAL_FAMILIES = (
    (
        "F1",
        "Cartera y antigüedad",
        "partial",
        "Órdenes ROV actuales",
        "Separar cierre técnico, salida física y cortes históricos.",
    ),
    (
        "F2",
        "Detenciones y causas",
        "capture_pending",
        "Intervalos confirmados",
        "Registrar inicio, fin, causa y responsable de destrabar.",
    ),
    (
        "F3",
        "Compromisos al cliente",
        "capture_pending",
        "Compromisos de entrega",
        "Conservar promesa original y constancia de salida efectiva.",
    ),
    (
        "F4",
        "Reparaciones terminadas",
        "source_pending",
        "Visitas y series distintas",
        "Comprobar primer cierre válido, reapertura y recierre.",
    ),
    (
        "F5",
        "Unidades por hito",
        "source_pending",
        "Unidades ROV fabricadas",
        "Conciliar cantidades, series, parciales y los hitos posteriores.",
    ),
    (
        "F6",
        "Plazo de reparación",
        "source_pending",
        "Visitas con límites conocidos",
        "Comprobar recepción, diagnóstico, autorización, cierre y salida.",
    ),
    (
        "Q1",
        "Primera aceptación",
        "available",
        "Selección actual autorizada",
        "Reparaciones y equipos nuevos separados; pendientes y sin evidencia visibles.",
    ),
    (
        "Q2",
        "Retornos relacionados",
        "capture_pending",
        "Visitas con seguimiento observado",
        "Vincular retorno y dictamen; ventana de 180 días efectivamente observada.",
    ),
    (
        "Q3",
        "Retrabajo y causas",
        "capture_pending",
        "Episodios y HH registradas",
        "Distinguir corrección de alcance adicional y evitar duplicar horas.",
    ),
    (
        "Q4",
        "Hallazgos y Pareto",
        "source_pending",
        "Observaciones, visitas o series",
        "Comprobar fecha, agrupación y cobertura antes de contar incidentes únicos.",
    ),
    (
        "A1",
        "Cumplimiento de proveedores",
        "source_pending",
        "Líneas de compra y recepción",
        "Comprobar compromiso original, parciales y recepción completa.",
    ),
)

# Definiciones de las fichas aprobadas; describir una fórmula no implica haberla medido.
DEFINITIONS = {
    "F1": {
        "decision": "Priorizar la carga pendiente y distinguir cierre técnico de salida del taller.",
        "source": "Estados autorizados de Reparación y Fabricación; eventos históricos por verificar.",
        "population": (
            "Órdenes ROV accesibles al corte. Cartera técnica y cartera hasta salida física "
            "separadas."
        ),
        "formula": (
            "Saldo inicial + entradas + reaperturas − salidas − cancelaciones/ajustes = saldo "
            "final. Hoy solo se muestra cartera administrativa actual."
        ),
    },
    "F2": {
        "decision": "Identificar qué impide avanzar y quién debe destrabarlo.",
        "source": (
            "Intervalos confirmados con inicio, fin, causa y responsable; disponibilidad nativa "
            "como señal."
        ),
        "population": (
            "Órdenes abiertas elegibles e intervalos de detención real; una falta sin detención no"
            " entra."
        ),
        "formula": (
            "Detenidas confirmadas / abiertas elegibles. Tiempo detenido = unión de intervalos "
            "hasta fin o corte. Los tiempos por causa pueden no ser aditivos."
        ),
    },
    "F3": {
        "decision": "Vigilar compromisos en riesgo y cumplimiento de la salida registrada al cliente.",
        "source": (
            "Promesa original firme y recompromisos en Odoo; transferencia y constancia de salida "
            "efectiva."
        ),
        "population": (
            "Compromisos por visita/serie/línea, cantidad y requisitos. Vencimientos y completados"
            " del período son poblaciones distintas."
        ),
        "formula": (
            "Vista vencimientos: completos a tiempo / elegibles que vencían, incluidas abiertas "
            "vencidas. Vista completados: a tiempo / elegibles completados. No sustituir la "
            "promesa original por la última fecha."
        ),
    },
    "F4": {
        "decision": "Medir volumen terminado y mezcla de intervenciones sin duplicar visitas.",
        "source": (
            "Orden, serie y primer evento de cierre técnico validado; reaperturas y recierres "
            "conservados."
        ),
        "population": (
            "Visitas ROV con primer cierre válido en el período; series distintas se cuentan "
            "aparte."
        ),
        "formula": (
            "Una terminación única por visita y su primer cierre válido. Reabrir/recerrar no crea "
            "otra visita. Salidas al cliente y recierres son otras medidas."
        ),
    },
    "F5": {
        "decision": "Distinguir lo fabricado, aceptado, liberado y salido al cliente.",
        "source": (
            "Salida fabricada, cantidades/series y parciales; aceptación sellada, liberación "
            "respaldada y transferencia."
        ),
        "population": (
            "Episodios y series de producto final ROV. Componentes, subproductos y prototipos "
            "separados."
        ),
        "formula": (
            "Una unidad por episodio/serie en cada hito válido. Divisiones de MO no duplican "
            "unidades. Los saldos entre hitos requieren estados y reversos al corte."
        ),
    },
    "F6": {
        "decision": "Comprometer plazos realistas y localizar demoras del recorrido.",
        "source": (
            "Recepción física, diagnóstico, autorización, cierre y salida respaldados; HH como "
            "medida separada."
        ),
        "population": (
            "Visitas salidas al cliente en el período con ambos límites conocidos; incompletas "
            "visibles en cobertura."
        ),
        "formula": (
            "Tiempo = salida registrada − recepción física. Mediana, distribución y P80 cuando la "
            "base permita interpretarlo. No restar espera ni ocultar visitas largas."
        ),
    },
    "Q1": {
        "decision": "Evaluar la calidad de la primera presentación formal y la necesidad de repetir trabajo.",
        "source": (
            "Primer intento sellado de aceptación final; en equipo nuevo, rendimiento y terreno "
            "conjuntos."
        ),
        "population": (
            "Selección actual completa y autorizada; visitas de reparación y unidades nuevas "
            "realmente fabricadas separadas. No es cohorte mensual."
        ),
        "formula": (
            "Aprobados al primer intento / evaluados con veredicto. Pendientes y desconocidos "
            "fuera del denominador. cobertura = evaluados / población consultada. Un fallo inicial"
            " no desaparece con una aprobación posterior."
        ),
    },
    "Q2": {
        "decision": "Detectar retornos técnicamente relacionados con la reparación previa.",
        "source": "Visita original, retorno, dictamen y seguimiento efectivamente observado en MC.",
        "population": (
            "Visitas originales con 180 días de seguimiento observado. Recientes y relación "
            "pendiente se muestran aparte."
        ),
        "formula": (
            "Visitas con al menos un retorno relacionado confirmado dentro de 180 días / visitas "
            "maduras observadas. Varios retornos de una visita no multiplican el numerador. Con "
            "dictámenes pendientes es mínimo confirmado, no tasa definitiva."
        ),
    },
    "Q3": {
        "decision": "Reducir repetición evitable y distinguirla de alcance adicional legítimo.",
        "source": (
            "Evento de retrabajo documentado, causa, episodio y HH vinculadas sin multiplicación "
            "por joins."
        ),
        "population": (
            "Episodios elegibles cerrados en el período; HH registradas elegibles como otra "
            "población."
        ),
        "formula": (
            "Episodios con retrabajo / episodios elegibles cerrados. Por separado: HH de retrabajo"
            " / HH registradas elegibles. No sumar ambas tasas ni inferir costo sin atribución."
        ),
    },
    "Q4": {
        "decision": "Priorizar hallazgos, componentes y causas que requieren acción.",
        "source": (
            "Observaciones estructuradas, revisión y categoría; incidente único requiere identidad"
            " validada."
        ),
        "population": (
            "Observaciones, visitas afectadas o series afectadas, según la unidad elegida. "
            "Condición recibida, proceso y retorno separados."
        ),
        "formula": (
            "Frecuencia por unidad explícita y porcentaje acumulado del Pareto. No mezclar "
            "observación con incidente único ni calcular horas/costo sin atribución fiable."
        ),
    },
    "A1": {
        "decision": "Elegir proveedores y anticipar riesgo o demora de abastecimiento.",
        "source": (
            "Compra y recepción nativas; compromiso original por línea y recepción completa por "
            "comprobar."
        ),
        "population": (
            "Líneas elegibles cuyo compromiso original vencía en el período, incluidas pendientes;"
            " componentes críticos separados."
        ),
        "formula": (
            "Líneas recibidas completas a tiempo / líneas elegibles que vencían. Plazo de "
            "recepción completa como otra medida; parciales no completan la línea y la "
            "reprogramación no sustituye la promesa original."
        ),
    },
}
