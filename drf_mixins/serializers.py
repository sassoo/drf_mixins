"""
    serializers
    ~~~~~~~~~~~

    All our DRF serializer mixins used across apps
"""

import operator

from django.db import models
from django.core.exceptions import ObjectDoesNotExist


def _flatten_data(data, _lkey=''):
    """ Flatten a nested dict into a dotted key with value """

    ret = {}
    for rkey, val in data.items():
        key = _lkey + rkey
        if isinstance(val, dict):
            ret.update(_flatten_data(val, _lkey=key + '.'))
        else:
            ret[key] = val
    return ret


class ChangeMgmtMixin:
    """ DRF Serializer mixin for added change management functionality

    The `_changed_fields` property contains an empty dict if no
    changes were made & if changes are present then each key is
    named after the field & the value is:

        {
            old: <old value>
            new: <new value>
        }

    INFO: Change tracking only occurs on the initial input of
          data from the requesting client against EXISTING models.
          New models are completely skipped & mutations after the
          fact by custom business logic are not tracked.
          This is by design.
    """

    def to_internal_value(self, data):
        """ Override the DRF native to_internal_value method

        Use the output from the native `to_internal_value` to
        automatically prune the list of fields to compare. It
        will only return fields that are both "writable" & provided
        by the requesting user.

        The bulk of the complexity is handling scenarios where
        serializer fields are using a `source` parameter and/or
        are nested which DRF maps to dicts.

        We always use the source of the field to find the instance
        field & create a mapping so the values are properly discovered
        while the name of the field modified is always the one on
        the serializer. Basically, it preserves the serializers fields
        in name rather than using the django model field names.
        """

        ret = super().to_internal_value(data)
        # new model so skip
        if not self.instance:
            return ret

        changes = self.instance._changed_fields = {}
        new_data = _flatten_data(ret)
        source_map = {v.source: k for k, v in self.fields.items()}

        for key, new_val in new_data.items():
            try:
                old_val = operator.attrgetter(key)(self.instance)
            except (AttributeError, ObjectDoesNotExist):
                old_val = None

            if new_val and isinstance(new_val, models.Model):
                new_val = new_val.pk
            if old_val and isinstance(old_val, models.Model):
                old_val = old_val.pk

            if new_val != old_val:
                serializer_field_name = source_map[key]
                changes[serializer_field_name] = {
                    'old': old_val,
                    'new': new_val,
                }

        # since we're overriding
        return ret


class PolymorphicMixin:
    """ A READ-ONLY polymorphic serializer

    The field whose value is used to discern which serializer
    should be used is specified by a `polymorphic_field` property
    on the Meta object & the serializers should be a dict with a
    key that is the value:

        ```
        class Meta:
            polymorphic_field = 'species'
            polymorphic_serializers = {
                'cat': CatSerializer,
                'dog': DogSerializer,
            }
        ```
    """

    def to_representation(self, instance):
        """ DRF override, use the real serializer on the instance

        WARN: this will create a new serializer instance on
              every object when dealing with many's. This
              could be super wasteful.
        """

        field = self.Meta.polymorphic_field

        try:
            value = getattr(instance, field, None)
            serializer = self.Meta.polymorphic_serializers[value]
            serializer = serializer(context=self.context)
            return serializer.to_representation(instance)
        except KeyError:
            return super().to_representation(instance)


class WriteAdminOnlyMixin:
    """ Adds support for writable fields for only admins to serializers.

    To use it, specify a list of fields as `write_admin_only_fields`
    on the serializers Meta:

    ```
    class Meta:
        model = SomeModel
        fields = '__all__'
        write_admin_only_fields = ('is_admin', 'can_be_god')
    ```

    Now the fields in `write_admin_only_fields` can be written only
    by users with the `is_admin` field equal to True.
    """

    def get_fields(self):
        """ DRF override """

        fields = super().get_fields()

        try:
            is_admin = self.context['request'].user.is_admin
        except (AttributeError, KeyError):
            is_admin = True

        write_admin_only_fields = getattr(self.Meta, 'write_admin_only_fields', ())
        if not isinstance(write_admin_only_fields, (list, tuple)):
            raise TypeError(
                'The `write_admin_only_fields` option must be a list or tuple. '
                'Got {}.'.format(type(write_admin_only_fields).__name__)
            )

        for field in write_admin_only_fields:
            fields[field].read_only = not is_admin
        return fields


class WriteCreateOnlyMixin:
    """ Adds support for write protected fields on update to serializers.

    To use it, specify a list of fields as `write_create_only_fields`
    on the serializers Meta:

    ```
    class Meta:
        model = SomeModel
        fields = '__all__'
        write_create_only_fields = ('foo', 'bar')
    ```

    Now the fields in `write_create_only_fields` can be written only if
    the serializer is creating a new instance.
    """

    def get_fields(self):
        """ DRF override """

        fields = super().get_fields()
        creating = not bool(self.instance)

        write_create_only_fields = getattr(self.Meta, 'write_create_only_fields', ())
        if not isinstance(write_create_only_fields, (list, tuple)):
            raise TypeError(
                'The `write_create_only_fields` option must be a list or tuple. '
                'Got {}.'.format(type(write_create_only_fields).__name__)
            )

        if not creating:
            for field in write_create_only_fields:
                fields[field].read_only = True
        return fields


class WriteUpdateOnlyMixin:
    """ Adds support for write protected fields on create to serializers.

    To use it, specify a list of fields as `write_update_only_fields`
    on the serializers Meta:

    ```
    class Meta:
        model = SomeModel
        fields = '__all__'
        write_update_only_fields = ('foo', 'bar')
    ```

    Now the fields in `write_update_only_fields` can be written only if
    the serializer is updating an existing instance.
    """

    def get_fields(self):
        """ DRF override """

        fields = super().get_fields()
        updating = bool(self.instance)

        write_update_only_fields = getattr(self.Meta, 'write_update_only_fields', ())
        if not isinstance(write_update_only_fields, (list, tuple)):
            raise TypeError(
                'The `write_update_only_fields` option must be a list or tuple. '
                'Got {}.'.format(type(write_update_only_fields).__name__)
            )

        if not updating:
            for field in write_update_only_fields:
                fields[field].read_only = True
        return fields
