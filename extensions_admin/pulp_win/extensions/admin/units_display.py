# -*- coding: utf-8 -*-

from pulp_win.common.ids import TYPE_ID_MSI, TYPE_ID_MSM


def get_formatter_for_type(type_id):
    """
    Return a method that takes one argument (a unit) and formats a short string
    to be used as the output for the unit_remove command

    :param type_id: The type of the unit for which a formatter is needed
    :type type_id: str
    """
    type_formatters = {
        TYPE_ID_MSI: _details_package,
        TYPE_ID_MSM: _details_package,
    }
    return type_formatters[type_id]


def _details_package(package):
    """
    A formatter that prints detailed package information.

    This is a detailed package formatter that can be used with different
    unit types.

    :param package: The package to have its formatting returned.
    :type package: dict
    :return: The display string of the package
    :rtype: str
    """
    return '%s-%s' % (package['name'], package['version'])
