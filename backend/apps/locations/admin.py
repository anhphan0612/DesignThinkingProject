from django.contrib.gis import admin

from .models import District, Landmark, University, Ward


admin.site.register(District)
admin.site.register(Ward)
admin.site.register(University, admin.GISModelAdmin)
admin.site.register(Landmark, admin.GISModelAdmin)

