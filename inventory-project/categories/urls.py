from django.urls import path
from categories.controllers import views

urlpatterns = [
    path("", views.category_detail),   # GET /api/v1/categories/
                                        # POST /api/v1/categories/
    path("<str:category_id>/", views.category_detail)    # GET /api/v1/categories/<id>/
                                                        # PATCH /api/v1/categories/<id>/
    
]