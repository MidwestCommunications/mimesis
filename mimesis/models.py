import mimetypes
import os

from django.db import models
from django.utils import timezone

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from mimesis.managers import MediaAssociationManager
from taggit.managers import TaggableManager


def _get_upload_path(instance, filename):
    return instance.created.strftime('mimesis/%Y-%m/%d/') + os.path.basename(filename)
    
class MediaUpload(models.Model):
    
    caption = models.CharField(max_length=500)
    media = models.FileField(upload_to=_get_upload_path, max_length=500)
    creator = models.ForeignKey(User)
    created = models.DateTimeField(default=timezone.now)
    media_type = models.CharField(editable=False, max_length=100)
    media_subtype = models.CharField(editable=False, max_length=100)
    
    tags = TaggableManager()
    
    def __unicode__(self):
        if self.caption:
            return self.caption
        else:
            return self.media_type + ' created by ' + str(self.creator)
    
    @property
    def thumbnail_img_url(self):
        if self.media_type == 'image':
            return self.media.url
        if self.media_type == 'audio':
            return "http://placekitten.com/48/48/"
        if self.media_type == 'video' and self.media_subtype == 'youtube':
            return "http://img.youtube.com/vi/" + self.media.name + "/0.jpg"
        if self.media_type == 'application' and self.media_subtype == 'pdf':
            return "http://placekitten.com/48/48/"
        return ''
    
    @property
    def mime_type(self):
        return "%s/%s" % (self.media_type, self.media_subtype)
    
    def save(self, *args, **kwargs):
        super(MediaUpload, self).save()
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
