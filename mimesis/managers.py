from django.db import models
from django.db.models.query import QuerySet
from django.db.models.loading import get_model
from django.utils.encoding import force_unicode
from django.contrib.contenttypes.models import ContentType


class MediaAssociationManager(models.Manager):
    
    def for_model(self, model, content_type=None):
        """
        QuerySet returning all media for a particular model (either an
        instance or a class).
        """
        ct = content_type or ContentType.objects.get_for_model(model)
        qs = self.get_query_set().filter(content_type=ct)
        if isinstance(model, models.Model):
            qs = qs.filter(object_pk=force_unicode(model._get_pk_val()))
        return qs


class WithMediaManager(models.Manager):
    """
    A manager which automatically (but still lazily) fetches related media in
    efficient queries and attaches it to the returned objects.
    """
    
    def __init__(self, media_attr_name='media'):
        self.media_attr_name = media_attr_name
        super(WithMediaManager, self).__init__()
    
    def get_query_set(self):
        """Returns a WithMediaQuerySet for this manager's model."""
        return WithMediaQuerySet(
            self.model,
            using=self.db,
            media_attr_name=self.media_attr_name
        )


class WithMediaQuerySet(QuerySet):
    """
    A queryset that fetches and attaches related media efficiently.
    
    The _result_iter and __contains__ methods are copied from Django and
    modified to attach media to results that have been cached.
    """
    
    def __init__(self, *args, **kwargs):
        self.media_attr_name = kwargs.pop('media_attr_name', 'media')
        self.MediaAssociation = get_model('mimesis', 'mediaassociation')
        super(WithMediaQuerySet, self).__init__(*args, **kwargs)

    def __len__(self):
        # Since __len__ is called quite frequently (for example, as part of
        # list(qs), we make some effort here to be as efficient as possible
        # whilst not messing up any existing iterators against the QuerySet.
        start_pos = 0 # WithMediaQuerySet
        if self._result_cache is None:
            if self._iter:
                self._result_cache = list(self._iter)
            else:
                self._result_cache = list(self.iterator())
        elif self._iter:
            start_pos = len(self._result_cache) # WithMediaQuerySet
            self._result_cache.extend(list(self._iter))
        self._attach_media(start_pos) # WithMediaQuerySet
        return len(self._result_cache)

    def _result_iter(self):
        pos = 0
        while 1:
            upper = len(self._result_cache)
            while pos < upper:
                yield self._result_cache[pos]
                pos = pos + 1
            if not self._iter:
                raise StopIteration
            if len(self._result_cache) <= pos:
                self._fill_cache()
                self._attach_media(pos) # WithMediaQuerySet
    
    def __contains__(self, val):
        # The 'in' operator works without this method, due to __iter__. This
        # implementation exists only to shortcut the creation of Model
        # instances, by bailing out early if we find a matching element.
        pos = 0
        if self._result_cache is not None:
            if val in self._result_cache:
                return True
            elif self._iter is None:
                # iterator is exhausted, so we have our answer
                return False
            # remember not to check these again:
            pos = len(self._result_cache)
        else:
            # We need to start filling the result cache out. The following
            # ensures that self._iter is not None and self._result_cache is not
            # None
            it = iter(self)
        
        # Note the start position (before filling any results)
        start_pos = pos # WithMediaQuerySet
        # Carry on, one result at a time.
        while True:
            if len(self._result_cache) <= pos:
                self._fill_cache(num=1)
            if self._iter is None:
                # we ran out of items
                self._attach_media(start_pos) # WithMediaQuerySet
                return False
            if self._result_cache[pos] == val:
                self._attach_media(start_pos) # WithMediaQuerySet
                return True
            pos += 1

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        if not isinstance(k, (slice, int, long)):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
                "Negative indexing is not supported."

        if self._result_cache is not None:
            if self._iter is not None:
                # The result cache has only been partially populated, so we may
                # need to fill it out a bit more.
                if isinstance(k, slice):
                    if k.stop is not None:
                        # Some people insist on passing in strings here.
                        bound = int(k.stop)
                    else:
                        bound = None
                else:
                    bound = k + 1
                if len(self._result_cache) < bound:
                    self._fill_cache(bound - len(self._result_cache))
                    self._attach_media(len(self._result_cache)) # WithMediaQuerySet
            return self._result_cache[k]

        if isinstance(k, slice):
            qs = self._clone()
            if k.start is not None:
                start = int(k.start)
            else:
                start = None
            if k.stop is not None:
                stop = int(k.stop)
            else:
                stop = None
            qs.query.set_limits(start, stop)
            return k.step and list(qs)[::k.step] or qs
        try:
            qs = self._clone()
            qs.query.set_limits(k, k + 1)
            return list(qs)[0]
        except self.model.DoesNotExist, e:
            raise IndexError(e.args)
    
    def _attach_media(self, fill_from):
        item_pks = [item.pk for item in self._result_cache[fill_from:]]
        model_ct = ContentType.objects.get_for_model(self.model)
        assocs = self.MediaAssociation.objects.filter(
            content_type=model_ct,
            object_pk__in=item_pks
        ).select_related('media')
        media_by_pk = {}
        for assoc in assocs:
            media_by_pk.setdefault(assoc.object_pk, []).append(assoc.media)
        for item in self._result_cache:
            setattr(item, self.media_attr_name, media_by_pk.get(item.pk, []))
