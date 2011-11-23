import os.path

from django.conf import settings
from django.db import models, connection, reset_queries
from django.test import TestCase
from django.core.files import File
from django.contrib.auth.models import User

from mimesis.managers import WithMediaManager
from mimesis.models import MediaUpload, MediaAssociation


class ModelTestCase(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user('user', 'mail@mail.com')
    
    def test_add_media_from_filesystem(self):
        test_file = open(os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            'test_media',
            'test.jpg'
        ), 'rb')
        media_upload = MediaUpload.objects.create(
            media=File(test_file),
            creator=self.user
        )
        self.assertEqual(media_upload.media_type, 'image')
        self.assertEqual(media_upload.media_subtype, 'jpeg')


class TestModel(models.Model):
    objects = models.Manager()
    with_media = WithMediaManager()


class QuerySetEfficiencyTestCase(TestCase):
    
    def setUp(self):
        settings.DEBUG = True
        for i in range(3):
            TestModel.objects.create()
        reset_queries()
    
    def tearDown(self):
        settings.DEBUG = False
    
    def test_lazy_evaluation(self):
        obj_list = TestModel.with_media.all()
        self.assertEqual(len(connection.queries), 0)

    def test_attach_all(self):
        obj_list = list(TestModel.with_media.all())
        query_count = len(connection.queries)
        
        for obj in obj_list:
            obj.media
        self.assertEqual(len(connection.queries), query_count)
    
    def test_num_queries(self):
        obj_list = list(TestModel.with_media.all())
        self.assertEqual(len(connection.queries), 2)
    
    def test_len(self):
        len(TestModel.with_media.all())
        self.assertEqual(len(connection.queries), 2)
    
    def test_membership_test(self):
        obj = TestModel.objects.create()
        self.assertTrue(obj in TestModel.with_media.all())
    
    def test_iteration(self):
        obj_qs = TestModel.with_media.all()
        for obj in obj_qs:
            obj.media
        self.assertEqual(len(connection.queries), 2)
    
    def test_slicing(self):
        qs = TestModel.with_media.all()
        qs_slice = qs[:2]
        for obj in qs_slice:
            obj.media
        self.assertEqual(len(connection.queries), 2)
    
    def test_indexing(self):
        qs = TestModel.with_media.all()
        qs[2].media
        self.assertEqual(len(connection.queries), 2)


class QuerySetAttachedMediaTestCase(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user('user', 'mail@mail.com')
    
    def test_none_attached(self):
        TestModel.objects.create()
        self.assertEqual(len(TestModel.with_media.get().media), 0)
    
    def test_one_attached(self):
        obj = TestModel.objects.create()
        media = MediaUpload.objects.create(caption='media', media='blah', creator=self.user)
        MediaAssociation.objects.create(media=media, content_object=obj)
        obj_media = TestModel.with_media.get().media
        self.assertEqual(len(obj_media), 1)
        self.assertEqual(obj_media[0], media)
    
    def test_two_attached(self):
        obj = TestModel.objects.create()
        media1 = MediaUpload.objects.create(caption='media1', media='blah', creator=self.user)
        media2 = MediaUpload.objects.create(caption='media2', media='blah', creator=self.user)
        MediaAssociation.objects.create(media=media1, content_object=obj)
        MediaAssociation.objects.create(media=media2, content_object=obj)
        obj_media = TestModel.with_media.get().media
        self.assertEqual(len(obj_media), 2)
        self.assertTrue(all(m in obj_media for m in [media1, media2]))
