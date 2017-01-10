# -*- coding: utf-8 -*-

from gettext import gettext as _
import logging

from pulp_win.common import constants
from pulp_win.plugins.db import models


_logger = logging.getLogger(__name__)

type_done_map = {
    models.MSI.TYPE: 'msi_done',
    models.MSM.TYPE: 'msm_done',
}

type_total_map = {
    'msi_total': models.MSI.TYPE,
    'msm_total': models.MSM.TYPE,
}


class DistributionReport(dict):
    def __init__(self):
        self['error_details'] = []
        self['items_total'] = 0
        self['items_left'] = 0
        self['state'] = constants.STATE_NOT_STARTED

    def set_initial_values(self, items_total):
        self['items_total'] = items_total
        self['items_left'] = items_total


class ContentReport(dict):
    def __init__(self):
        self['error_details'] = []
        self['items_total'] = 0
        self['items_left'] = 0
        self['size_total'] = 0
        self['size_left'] = 0
        self['state'] = constants.STATE_NOT_STARTED
        self['details'] = {
            'msi_done': 0,
            'msi_total': 0,
            'msm_done': 0,
            'msm_total': 0,
        }

    def set_initial_values(self, counts, total_size):
        self['size_total'] = total_size
        self['size_left'] = total_size
        self['items_total'] = sum(counts.values())
        self['items_left'] = sum(counts.values())
        for total_name, total_type in type_total_map.iteritems():
            self['details'][total_name] = counts[total_type]

    def success(self, model):
        self['items_left'] -= 1
        if self['items_left'] % 100 == 0:
            _logger.debug(_('%(n)s items left to download.') %
                          {'n': self['items_left']})
        self['size_left'] -= model.size
        done_attribute = type_done_map[model._content_type_id]
        self['details'][done_attribute] += 1
        return self

    def failure(self, model, error_report):
        self['items_left'] -= 1
        self['size_left'] -= model.size
        done_attribute = type_done_map[model._content_type_id]
        self['details'][done_attribute] += 1
        self['error_details'].append(error_report)
        return self
