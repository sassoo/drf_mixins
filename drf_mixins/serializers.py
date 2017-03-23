"""
    serializers
    ~~~~~~~~~~~

    All our DRF serializer mixins used across apps
"""


class CavsMixin:
    """ DRF model serializer mixin

    This introduces a pattern that is much needed IMO
    where incoming data is validated & coerced on a field
    level & then immediately applied to the instance.

    For short, coerce, apply, validate, save (CAVS) is
    the proper flow.

    NOTE: with this mixin the native `create()` method
          is never called because an instance is always
          available so `save()` calls `update()`.
    """

    def apply_to_instance(self, instance, data):
        """ Apply the attrs to the instance

        Override if additional cleaning or sanitizing
        of the provided data on the instance is needed.

        Most common when the object needs to be consistent
        before object-level validation can safely occur.
        """

        for field, value in data.items():
            setattr(instance, field, value)

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

        if self.instance is None:
            self.instance = self.Meta.model()
        self.apply_to_instance(self.instance, data)
        self.validate_instance(self.instance)
        return super().validate(data)

    def validate_instance(self, instance):
        """ Instance validation checks """

        pass


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

    Inspired by http://stackoverflow.com/a/37487134/627411.
    """

    def get_extra_kwargs(self):
        """ DRF serializer override """

        extra_kwargs = super().get_extra_kwargs()

        write_once_fields = getattr(self.Meta, 'write_once_fields', None)
        if any((not write_once_fields, self.instance is None)):
            return extra_kwargs

        if not isinstance(write_once_fields, (list, tuple)):
            raise TypeError(
                'The `write_once_fields` option must be a list or tuple. '
                'Got {}.'.format(type(write_once_fields).__name__)
            )

        for field in write_once_fields:
            kwargs = extra_kwargs.get(field, {})
            kwargs['read_only'] = True
            extra_kwargs[field] = kwargs

        return extra_kwargs
