# -*- coding: utf-8 -*-

import unittest

from mock import patch

from pulp_win.extensions.admin import units_display
from pulp_win.common.ids import TYPE_ID_MSI, TYPE_ID_MSM


class UnitsDisplayTests(unittest.TestCase):
    def test_details_package(self):
        unit = {'name': 'foo',
                'version': 'bar',
                'release': 'baz',
                'arch': 'qux'}
        self.assertEquals(units_display._details_package(unit), 'foo-bar')

    @patch('pulp_win.extensions.admin.units_display._details_package')
    def test_get_formatter_for_type(self, mock_package):
        self.assertTrue(mock_package is
                        units_display.get_formatter_for_type(TYPE_ID_MSI))
        self.assertTrue(mock_package is
                        units_display.get_formatter_for_type(TYPE_ID_MSM))
