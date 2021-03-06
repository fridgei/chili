from django.core.urlresolvers import NoReverseMatch, reverse


class ObjectUrlMixin(object):
    """
    This is a mixin that adds important url methods to a model. This
    class uses the ``_meta.db_table`` instance variable of an object to
    calculate URLs. Because of this, you must use the app label of your
    class when declaring urls in your urls.py.
    """
    @classmethod
    def get_list_url(cls):
        """
        Return the 'list' url of an object. Class method since don't
        need specific instance of object.
        """
        try:
            return reverse(cls._meta.db_table)
        except NoReverseMatch:
            return ''

    @classmethod
    def get_create_url(cls):
        """
        Return the create url of the type of object (to be posted to).
        """
        try:
            return reverse(cls._meta.db_table + '-create')
        except NoReverseMatch:
            return ''

    def get_update_url(self):
        """
        Return the update url of an object (to be posted to). Not class method
        because object pk needed.
        """
        try:
            return reverse(self._meta.db_table + '-update', args=[self.pk])
        except NoReverseMatch:
            return ''

    def get_delete_url(self):
        """
        Return the delete url of an object (to be posted to).
        """
        try:
            return reverse(self._meta.db_table + '-delete', args=[self.pk])
        except NoReverseMatch:
            return ''

    def get_detail_url(self):
        """
        Return the detail url of an object.
        """
        try:
            return reverse(self._meta.db_table + '-detail', args=[self.pk])
        except NoReverseMatch:
            return ''

    def details(self):
        """
        Return base details with generic postback URL for editable tables.
        """
        try:
            return {'url': reverse(self._meta.db_table + '-table-update',
                                   args=[self.pk])}
        except NoReverseMatch:
            return {'url': ''}
