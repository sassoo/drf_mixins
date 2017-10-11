"""
    serializers
    ~~~~~~~~~~~

    All our DRF serializer mixins used across apps
"""


class EagerInstanceMixin:
    """ DRF model serializer mixin

    This introduces a pattern that is much needed IMO
    where incoming data is validated & coerced on a field
    level & then immediately applied to the instance.

    NOTE: with this mixin the native `create()` method
          is never called because an instance is always
          available so `save()` calls `update()`.
    """

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
        for field, value in data.items():
            setattr(instance, field, value)
        self.instance = self.validate_instance(instance)
        return data

    def validate_instance(self, instance):
        """ Instance validation checks """

        raise NotImplementedError('`validate_instance()` must be implemented.')


class WriteOnceMixin:
    """ Adds support for write once fields to serializers.

    To use it, specify a write_once key in the `extra_kwargs`
    DRF ModelSerializer.Meta class parameter.

    ```
    class Meta:
        model = SomeModel
        fields = '__all__'
        extra_kwargs = {
            'name': {'write_once': True},
        }
    ```

    Now these fields in can be set during POST (create), but
    cannot be changed afterwards via PUT or PATCH (update).
    """

    def get_extra_kwargs(self):
        """ Override the DRF ModelSerializer method """

        extra_kwargs = super().get_extra_kwargs()

        for kwargs in extra_kwargs.values():
            if self.instance and kwargs.get('write_once'):
                kwargs['read_only'] = kwargs.pop('write_once')
