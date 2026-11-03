"""Aserciones de integración al sustituir los antiguos cierres manuales permitidos."""

from contextlib import contextmanager

from odoo.exceptions import UserError


@contextmanager
def assert_automatic_close_rejected(case, run):
    """Un rechazo conserva el pendiente, su auditoría, plazo y documento de negocio."""
    # El savepoint vacía el tracking diferido de la preparación del caso.
    # Materializarlo antes permite atribuir cambios solo al cierre rechazado.
    case.env.flush_all()
    case.cr.precommit.run()
    run.ensure_one()
    case.assertEqual(run.outcome, "pending")
    activity = run.activity_id
    case.assertTrue(activity.exists() and activity.active)
    source = case.env[activity.res_model].browse(activity.res_id)
    run_fields = [
        name
        for name in (
            "outcome",
            "activity_id",
            "original_deadline",
            "current_deadline",
            "finished_at",
            "finished_by_id",
            "finish_reason",
        )
        if name in run._fields
    ]
    source_fields = [
        name
        for name in ("state", "estado", "stage_id", "resultado", "active", "message_ids")
        if name in source._fields
    ]
    before_run = run.read(run_fields)
    before_activity = activity.read(
        ["active", "user_id", "mc_employee_id", "res_model", "res_id", "date_deadline"]
    )
    before_source = source.read(source_fields or ["id"])
    cycle = run.cycle_id if "cycle_id" in run._fields else None
    cycle_fields = (
        [name for name in ("original_deadline", "current_deadline") if name in cycle._fields]
        if cycle
        else []
    )
    before_cycle = cycle.read(cycle_fields) if cycle_fields else None
    with case.assertRaises(UserError) as rejection, case.cr.savepoint():
        yield
    # Un AccessError heredado no demuestra que funcione la regla de cierre real.
    case.assertIs(type(rejection.exception), UserError)
    run.invalidate_recordset()
    activity.invalidate_recordset()
    source.invalidate_recordset()
    case.assertEqual(run.read(run_fields), before_run)
    case.assertTrue(activity.exists() and activity.active)
    case.assertEqual(activity.read(list(before_activity[0].keys())), before_activity)
    case.assertEqual(source.read(source_fields or ["id"]), before_source)
    if before_cycle is not None:
        cycle.invalidate_recordset()
        case.assertEqual(cycle.read(cycle_fields), before_cycle)
