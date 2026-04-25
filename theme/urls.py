from django.urls import path
from . import views

urlpatterns = [
    # Path '' (root) akan memanggil fungsi views.home
    path('dashboard/', views.dashboard  , name='dashboard'),
]
