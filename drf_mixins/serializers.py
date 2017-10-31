"""
    serializers
    ~~~~~~~~~~~

    All our DRF serializer mixins used across apps
"""


class EagerInstanceMixin:
    """ DRF serializer mixin

    This introduces a pattern that is much needed IMO where
    incoming data is validated & coerced on a field level &
    then immediately applied to the instance.

    NOTE: with this mixin the native `create()` method
          is never called because an instance is always
          available so `save()` calls `update()`.
    """

    def apply_to_instance(self, instance, data):
        """ Very basic way to merge incoming data with an instance """

        for field, value in data.items():
            setattr(instance, field, value)
        return instance

    # pylint: disable=unused-argument
    def update(self, instance, validated_data):
        """ DRF override to avoid blasting the model again """

        instance.save()
        return instance

    def validate(self, data):
        """ DRF override to better separate concerns

        With this improved `validate()` be sure to validate
        against the object since it should be consistent.
        """

        data = super().validate(data)
        instance = self.instance or self.Meta.model()
        self.instance = self.apply_to_instance(instance, data)
        self.instance = self.validate_instance(instance)
        return data

    def validate_instance(self, instance):
        """ Instance validation checks """

        return instance


class PolymorphicMixin:
    """ A polymorphic serializer

    This mixin kicks into action in 2 different ways.

    When invoked as a MANY serializer an instance of `cls`, or
    the polymorphic serializer is used & the DRF native
    `to_representation` method is simply hijacked to use the
    proper serializer.

    If not MANY then the "real" serializer instance will be
    used by overriding pythons `cls.__new__` method. The "real"
    serializer will be selected in the following way:

        1. get the field name by grabbing the mandatory
           `cls.Meta.polymorphic_field` attribute.

        2. interrogate the passed in `data` checking for
           the `polymorphic_field` value & return the real
           serializer based on its value.

        3. if no data was passed in, no `polymorphic_field` was
           present in it, or it's value was None then check the
           value of the `polymorphic_field` on the instance &
           return the real serializer based on its value.

        4. if no instance or match then simply fail back to
           returning a serializer instance of this polymorphic
           serializer.

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

    def __new__(cls, *args, **kwargs):
        """ Python override, see comments above """

        if kwargs.get('many'):
            return super().__new__(cls, *args, **kwargs)

        field = cls.Meta.polymorphic_field

        try:
            value = kwargs.get('data', {}).get(field)
            value = value or getattr(args[0], field)
        except (AttributeError, IndexError):
            value = None

        try:
            serializer = cls.Meta.polymorphic_serializers[value]
            return serializer(*args, **kwargs)
        except KeyError:
            return super().__new__(cls, *args, **kwargs)

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


class WriteOnceMixin:
    """ Adds support for write once fields to serializers.

    To use it, specify a list of fields as `write_once_fields`
    on the serializer's Meta:

    ```
    class Meta:
        model = SomeModel
        fields = '__all__'
        write_once_fields = ('collection', )
    ```

    Now the fields in `write_once_fields` can be set during
    POST (create), but cannot be changed afterwards via PUT
    or PATCH (update).
    """

    def __init__(self, *args, **kwargs):
        """ Override the DRF constructor """

        super().__init__(*args, **kwargs)

        write_once_fields = getattr(self.Meta, 'write_once_fields', [])
        if not isinstance(write_once_fields, (list, tuple)):
            raise TypeError(
                'The `write_once_fields` option must be a list or tuple. '
                'Got {}.'.format(type(write_once_fields).__name__)
            )

        if write_once_fields and self.instance:
            for field in write_once_fields:
                self.fields[field].read_only = True
