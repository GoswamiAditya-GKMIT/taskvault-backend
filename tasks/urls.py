from django.urls import path
from tasks.views import  TaskListCreateAPIView , TaskDetailUpdateDeleteAPIView , TaskHistoryListAPIView , TaskCommentListCreateAPIView , TaskCommentDetailUpdateDeleteAPIView

urlpatterns = [
    # path("tasks/", TaskCreateAPIView.as_view()),
    path("tasks/", TaskListCreateAPIView.as_view()),
    path("tasks/<uuid:id>/", TaskDetailUpdateDeleteAPIView.as_view()),

    path("tasks/<uuid:task_id>/history/", TaskHistoryListAPIView.as_view()),

    path(
        "tasks/<uuid:task_id>/comments/",
        TaskCommentListCreateAPIView.as_view(),
    ),
    path(
        "tasks/<uuid:task_id>/comments/<uuid:comment_id>/",
        TaskCommentDetailUpdateDeleteAPIView.as_view(),
    ),


]
