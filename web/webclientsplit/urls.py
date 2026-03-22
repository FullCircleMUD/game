from django.urls import path

from web.webclientsplit import views

app_name = "webclientsplit"

urlpatterns = [
    path("", views.webclientsplit, name="index"),
]
