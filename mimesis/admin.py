from django.contrib import admin

from mimesis.models import MediaUpload, MediaAssociation

class MediaUploadAdmin(admin.ModelAdmin):
	#filter_horizontal = ('creator')
	list_display = ('__unicode__', 'creator', 'created')
	list_filter = ('created', 'creator')
	date_heirarchy = 'created'
	search_fields = ('caption',)
	ordering = ('-created',)

admin.site.register(MediaUpload, MediaUploadAdmin)
admin.site.register(MediaAssociation)
