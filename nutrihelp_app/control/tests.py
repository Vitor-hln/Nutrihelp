from django.conf import settings
from django.test import SimpleTestCase


class SettingsSmokeTest(SimpleTestCase):
    def test_secret_key_present(self):
        self.assertTrue(settings.SECRET_KEY, "SECRET_KEY deve estar definida")

    def test_databases_configured(self):
        self.assertIn("default", settings.DATABASES)
        self.assertTrue(settings.DATABASES["default"].get("NAME"))
