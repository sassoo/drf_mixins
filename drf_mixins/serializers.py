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

        WARN: this will create a new serializer instance on every
              object when dealing with many's. This could be super wasteful.
        """

        field = self.Meta.polymorphic_field

        try:
            value = getattr(instance, field, None)
            serializer = self.Meta.polymorphic_serializers[value]
            serializer = serializer(context=self.context)
            return serializer.to_representation(instance)
        except KeyError:
            return super().to_representation(instance)


class ReadOnlyHelpersMixin:
    """ Common read-only shortcuts

    The source is super simple & readable but a basic example of forcing
    the `foo` field to read-only during "create", `bar` field to read-only
    during "update", & `is_god` field to read-only if not an admin is:

        ```
        class BigSerializer(serializers.Serializer):

            <fields names> = <field types>

            class Meta:
                read_only_not_admin_fields = ('is_admin',)
                read_only_on_create_fields = ('foo',)
                read_only_on_update_fields = ('bar',)
        ```
    """

    def get_fields(self):
        """ DRF override """

        def _set_read_only(helper):
            try:
                names = getattr(meta, helper, ())
                for name in names:
                    fields[name].read_only = True
            except KeyError as exc:
                msg = '{}.Meta.{} attribute contains invalid field names'.format(
                    self.__class__.__name__, helper)
                raise Exception(msg) from exc
            except TypeError as exc:
                msg = '{}.Meta.{} attribute must be iterable. Got {}.'.format(
                    self.__class__.__name__, helper, type(names).__name__)
                raise Exception(msg) from exc

        try:
            fields = super().get_fields()
            meta = self.Meta
        except AttributeError:
            return fields

        try:
            is_admin = self.context['request'].user.is_admin
        except (AttributeError, KeyError):
            is_admin = True

        if not is_admin:
            _set_read_only('read_only_not_admin_fields')
        if not self.instance:
            _set_read_only('read_only_on_create_fields')
        if self.instance:
            _set_read_only('read_only_on_update_fields')

        return fields
