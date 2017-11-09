"""
    models
    ~~~~~~

    All our django model mixins used across apps
"""


class ChangeMgmtMixin:
    """ Model support for drfchangemgmt """

    def get_changed_fields(self):
        """ Return the changed fields data structure """

        return getattr(self, '_changed_fields', {})
