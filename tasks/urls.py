from django.urls import path
from tasks.views import  TaskListCreateAPIView , TaskDetailUpdateDeleteAPIView , TaskHistoryListAPIView , TaskCommentListCreateAPIView , TaskCommentDetailUpdateDeleteAPIView

urlpatterns = [
    # path("tasks/", TaskCreateAPIView.as_view()),
    path("tasks/", TaskListCreateAPIView.as_view(), name="task-list-create"),
    path("tasks/<uuid:id>/", TaskDetailUpdateDeleteAPIView.as_view(), name="task-detail"),

    path("tasks/<uuid:task_id>/history/", TaskHistoryListAPIView.as_view(), name="task-history"),

    path(
        "tasks/<uuid:task_id>/comments/",
        TaskCommentListCreateAPIView.as_view(),
        name="comment-list-create"
    ),
    path(
        "tasks/<uuid:task_id>/comments/<uuid:comment_id>/",
        TaskCommentDetailUpdateDeleteAPIView.as_view(),
        name="comment-detail-update-delete"
    ),


]
