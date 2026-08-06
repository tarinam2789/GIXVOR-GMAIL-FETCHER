from django.urls import path

from . import views

app_name = "fetcher"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("connect/", views.connect, name="connect"),
    path("history/", views.history, name="history"),
    path("disconnect/", views.disconnect, name="disconnect"),
    path("results/<int:pk>/", views.results, name="results"),
    path("results/<int:pk>/refresh/", views.refresh, name="refresh"),
    path("results/<int:pk>/email/<int:email_pk>/", views.email_detail, name="email_detail"),
]
