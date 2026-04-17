from django.urls import path
from products.controllers import views

urlpatterns = [
    path("", views.products),   # GET /api/v1/products/ 
                                # POST /api/v1/products/
                                                                

    path("bulk/", views.bulk_upload),  # POST /api/v1/products/bulk/

    path("<str:product_id>/", views.product_detail),    # GET /api/v1/products/<id>/
                                                        # PUT /api/v1/products/<id>/
                                                        # PATCH /api/v1/products/<id>/
                                                        # DELETE /api/v1/products/<id>/
]