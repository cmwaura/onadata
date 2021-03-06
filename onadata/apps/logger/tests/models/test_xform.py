import os

from pyxform.tests_v1.pyxform_test_case import PyxformTestCase

from onadata.apps.main.tests.test_base import TestBase
from onadata.apps.logger.models import XForm, Instance


class TestXForm(PyxformTestCase, TestBase):
    def test_submission_count_filters_deleted(self):
        self._publish_transportation_form_and_submit_instance()

        # update the xform object the num_submissions seems to be cached in
        # the in-memory xform object as zero
        self.xform = XForm.objects.get(pk=self.xform.id)
        self.assertEqual(self.xform.submission_count(), 1)
        instance = Instance.objects.get(xform=self.xform)
        instance.set_deleted()
        self.assertIsNotNone(instance.deleted_at)

        # update the xform object, the num_submissions seems to be cached in
        # the in-memory xform object as one
        self.xform = XForm.objects.get(pk=self.xform.id)
        self.assertEqual(self.xform.submission_count(), 0)

    def test_set_title_in_xml_unicode_error(self):
        xls_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../..",  "fixtures", "tutorial", "tutorial_arabic_labels.xls"
        )
        self._publish_xls_file_and_set_xform(xls_file_path)

        self.assertTrue(isinstance(self.xform.xml, unicode))

        # change title
        self.xform.title = u'Random Title'

        self.assertNotIn(self.xform.title, self.xform.xml)

        # convert xml to str
        self.xform.xml = self.xform.xml.encode('utf-8')
        self.assertTrue(isinstance(self.xform.xml, str))

        # set title in xform xml
        self.xform._set_title()
        self.assertIn(self.xform.title, self.xform.xml)

    def test_version_length(self):
        """Test Xform.version can store more than 12 chars"""
        self._publish_transportation_form_and_submit_instance()
        xform = XForm.objects.get(pk=self.xform.id)
        xform.version = u'12345678901234567890'
        xform.save()

        self.assertTrue(len(xform.version) > 12)

    def test_soft_delete(self):
        self._publish_transportation_form_and_submit_instance()
        xform = XForm.objects.get(pk=self.xform.id)

        # deleted_at is None
        self.assertIsNone(xform.deleted_at)

        # deleted-at suffix not present
        self.assertNotIn("-deleted-at-", xform.id_string)
        self.assertNotIn("-deleted-at-", xform.sms_id_string)

        # '&' should raise an XLSFormError exception when being changed, for
        # deletions this should not raise any exception however
        xform.title = 'Trial & Error'

        xform.soft_delete()
        xform.reload()

        # deleted_at is not None
        self.assertIsNotNone(xform.deleted_at)

        # deleted-at suffix is present
        self.assertIn("-deleted-at-", xform.id_string)
        self.assertIn("-deleted-at-", xform.sms_id_string)

    def test_get_survey_element(self):
        md = """
        | survey |
        |        | type                   | name   | label   |
        |        | begin group            | a      | Group A |
        |        | select one fruits      | fruita | Fruit A |
        |        | select one fruity      | fruity | Fruit Y |
        |        | end group              |        |         |
        |        | begin group            | b      | Group B |
        |        | select one fruits      | fruitz | Fruit Z |
        |        | select_multiple fruity | fruitb | Fruit B |
        |        | end group              |        |         |
        | choices |
        |         | list name | name   | label  |
        |         | fruits    | orange | Orange |
        |         | fruits    | mango  | Mango  |
        |         | fruity    | orange | Orange |
        |         | fruity    | mango  | Mango  |
        """
        kwargs = {'name': 'favs', 'title': 'Fruits', 'id_string': 'favs'}
        survey = self.md_to_pyxform_survey(md, kwargs)
        xform = XForm()
        xform._survey = survey

        # non existent field
        self.assertIsNone(xform.get_survey_element("non_existent"))

        # get fruita element by name
        fruita = xform.get_survey_element('fruita')
        self.assertEqual(fruita.get_abbreviated_xpath(), "a/fruita")

        # get exact choices element from choice abbreviated xpath
        fruita_o = xform.get_survey_element("a/fruita/orange")
        self.assertEqual(fruita_o.get_abbreviated_xpath(), "a/fruita/orange")

        fruity_m = xform.get_survey_element("a/fruity/mango")
        self.assertEqual(fruity_m.get_abbreviated_xpath(), "a/fruity/mango")

        fruitb_o = xform.get_survey_element("b/fruitb/orange")
        self.assertEqual(fruitb_o.get_abbreviated_xpath(), "b/fruitb/orange")
