""" API v1 views. """
import logging

from django.http import Http404
from rest_framework.authentication import SessionAuthentication
from rest_framework_oauth.authentication import OAuth2Authentication
from rest_framework.generics import RetrieveUpdateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated

from commerce.api.v1.models import Course
from commerce.api.v1.permissions import ApiKeyOrModelPermission
from commerce.api.v1.serializers import CourseSerializer
from course_modes.models import CourseMode
from openedx.core.lib.api.mixins import PutAsCreateMixin

log = logging.getLogger(__name__)


class CourseListView(ListAPIView):
    """ List courses and modes. """
    authentication_classes = (OAuth2Authentication, SessionAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = CourseSerializer
    pagination_class = None

    def get_queryset(self):
        return list(Course.iterator())


class CourseRetrieveUpdateView(PutAsCreateMixin, RetrieveUpdateAPIView):
    """ Retrieve, update, or create courses/modes. """
    lookup_field = 'id'
    lookup_url_kwarg = 'course_id'
    model = CourseMode
    authentication_classes = (OAuth2Authentication, SessionAuthentication,)
    permission_classes = (ApiKeyOrModelPermission,)
    serializer_class = CourseSerializer

    # Django Rest Framework v3 requires that we provide a queryset.
    # Note that we're overriding `get_object()` below to return a `Course`
    # rather than a CourseMode, so this isn't really used.
    queryset = CourseMode.objects.all()

    def get_object(self, queryset=None):
        course_id = self.kwargs.get(self.lookup_url_kwarg)
        course = Course.get(course_id)

        if course:
            return course

        raise Http404

    def pre_save(self, obj):
        # There is nothing to pre-save. The default behavior changes the Course.id attribute from
        # a CourseKey to a string, which is not desired.
        pass
