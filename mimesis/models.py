import datetime
import mimetypes

from django.db import models

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from mimesis.managers import MediaAssociationManager
from taggit.managers import TaggableManager


class MediaUpload(models.Model):
    
    caption = models.CharField(max_length=500)
    media = models.FileField(upload_to="mimesis", max_length=500)
    creator = models.ForeignKey(User)
    created = models.DateTimeField(default=datetime.datetime.now)
    media_type = models.CharField(editable=False, max_length=100)
    media_subtype = models.CharField(editable=False, max_length=100)
    
    tags = TaggableManager()
    
    def __unicode__(self):
        return self.caption
    
    @property
    def mime_type(self):
        return "%s/%s" % (self.media_type, self.media_subtype)
    
    def save(self, *args, **kwargs):
        if not self.media_type:
            (mime_type, encoding) = mimetypes.guess_type(self.media.path)
            try:
                mime = mime_type.split("/")
                self.media_type = mime[0]
                self.media_subtype = mime[1]
            except:
                # Mime type unknown, use text/plain
                self.media_type = "text"
                self.media_subtype = "plain"
        super(MediaUpload, self).save()


class MediaAssociation(models.Model):
    """
    A generic association of a MediaUpload object and any other Django model.
    """
    
    media = models.ForeignKey(MediaUpload)
    
    content_type = models.ForeignKey(ContentType)
    object_pk = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey("content_type", "object_pk")
    
    is_primary = models.BooleanField(default=False)
    
    objects = MediaAssociationManager()
    
    class Meta:
        unique_together = ('media', 'content_type', 'object_pk')
        ordering = ['-is_primary']

    def __unicode__(self):
        return "Attached to " + str(self.content_object) + ": " + str(self.media)
