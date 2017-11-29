"""
    views
    ~~~~~

    All our DRF view mixins used across apps
"""

from django.db import transaction


class AtomicUpdateMixin:
    """ Enforce transactions & row-level locking on update

    This should be used in combination with the DRF UpdateModelMixin.

    It enforces row-level locking during the update by the use of
    select_for_update on the queryset & wraps the entire operation
    in a transaction which is required by Django.
    """

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """ DRF override & entry point for the UpdateModelMixin """

        return super().update(request, *args, **kwargs)

    def get_queryset(self):
        """ DRF override to enforce `select_for_update` """

        queryset = super().get_queryset()
        return queryset.select_for_update()
