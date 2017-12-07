"""
    serializers
    ~~~~~~~~~~~

    All our DRF serializer mixins used across apps
"""


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


class WriteHelpers(WriteAdminOnlyMixin, WriteCreateOnlyMixin, WriteUpdateOnlyMixin):
    """ All of our write related helpers """

    pass
