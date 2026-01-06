from django.urls import path
from tasks.views import  TaskListCreateAPIView , TaskDetailUpdateDeleteAPIView , TaskHistoryListAPIView

urlpatterns = [
    # path("tasks/", TaskCreateAPIView.as_view()),
    path("tasks/", TaskListCreateAPIView.as_view()),
    path("tasks/<uuid:id>/", TaskDetailUpdateDeleteAPIView.as_view()),

    path("tasks/<uuid:task_id>/history/", TaskHistoryListAPIView.as_view()),

]
