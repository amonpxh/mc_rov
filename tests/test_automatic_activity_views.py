"""Las vistas nativas ocultan cierres de automáticas y conservan navegación."""

from . import test_work_assignment as assignment


class TestAutomaticActivityViews(assignment.ActivityAssignmentCommon):
    """Inspecciona la vista combinada con la cuenta de Taller, sin rol técnico."""

    _native_view = assignment.TestWorkAssignmentActivityViews._native_view

    def _view(self, key):
        views = {
            "kanban": ("mail.mail_activity_view_kanban_open_target", "kanban"),
            "list": ("mail.mail_activity_view_tree_open_target", "list"),
            "form": ("mail.mail_activity_view_form_popup", "form"),
            "fallback": ("mail.mail_activity_view_form_without_record_access", "form"),
            "calendar": ("mail.mail_activity_view_calendar", "calendar"),
        }
        return self._native_view(*views[key])

    def _assert_field_loaded(self, key):
        self.assertTrue(
            self._view(key).xpath("//field[@name='mc_automatic_pending']"),
            "Missing automatic presentation field in native view",
        )

    def _assert_close_buttons_conditional(self, key, xpath):
        buttons = self._view(key).xpath(xpath)
        self.assertTrue(buttons, "Native closing controls unexpectedly absent")
        self.assertTrue(
            all("mc_automatic_pending" in button.get("invisible", "") for button in buttons),
            "Missing automatic condition on native closing controls",
        )

    def test_kanban_loads_automatic_identity(self):
        self._assert_field_loaded("kanban")

    def test_list_loads_automatic_identity(self):
        self._assert_field_loaded("list")

    def test_form_loads_automatic_identity(self):
        self._assert_field_loaded("form")

    def test_restricted_form_loads_automatic_identity(self):
        self._assert_field_loaded("fallback")

    def test_calendar_loads_automatic_identity(self):
        self._assert_field_loaded("calendar")

    def test_kanban_hides_done_and_cancel_for_automatics(self):
        self._assert_close_buttons_conditional(
            "kanban", "//button[@name='action_done' or @name='unlink']"
        )

    def test_list_rows_hide_done_and_cancel_for_automatics(self):
        self._assert_close_buttons_conditional(
            "list", "//list/button[@name='action_done' or @name='unlink']"
        )

    def test_form_hides_generic_done_for_automatics(self):
        self._assert_close_buttons_conditional("form", "//button[@name='action_done']")

    def test_restricted_form_hides_generic_done_for_automatics(self):
        self._assert_close_buttons_conditional(
            "fallback", "//button[@name='action_done_redirect_to_other']"
        )

    def test_list_has_selection_aware_native_controller(self):
        self.assertEqual(
            self._view("list").get("js_class"),
            "mc_automatic_activity_list",
            "Missing automatic list selection integration",
        )

    def test_native_kanban_opens_document_without_extra_button(self):
        arch = self._view("kanban")
        self.assertEqual(
            (arch.get("action"), arch.get("type")), ("action_open_document", "object")
        )
        self.assertFalse(arch.xpath("//button[@name='action_open_document']"))

    def test_native_list_opens_document_without_extra_button(self):
        arch = self._view("list")
        self.assertEqual(
            (arch.get("action"), arch.get("type")), ("action_open_document", "object")
        )
        self.assertFalse(arch.xpath("//button[@name='action_open_document']"))
