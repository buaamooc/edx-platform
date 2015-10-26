import os
import urllib
from datetime import datetime

import logging
from functools import partial
import math
import json

from django.http import HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf import settings

from edxmako.shortcuts import render_to_response
from django.core.cache import cache

from contentstore.utils import reverse_course_url
from xmodule.modulestore.django import modulestore
from xmodule.exceptions import NotFoundError
from django.core.exceptions import PermissionDenied
from opaque_keys.edx.keys import CourseKey

from util.date_utils import get_default_time_display
from util.json_request import JsonResponse
from django.http import HttpResponseNotFound
from django.utils.translation import ugettext as _
from student.auth import has_course_author_access
from xmodule.modulestore.exceptions import ItemNotFoundError

__all__ = ['local_videos_handler']
VIDEO_URL_BASE = 'http://files.mooc.buaa.edu.cn/videos'
VIDEO_PATH_BASE = '/edx/var/files/videos'


# pylint: disable=unused-argument
@login_required
@ensure_csrf_cookie
def local_videos_handler(request, course_key_string=None, asset_key_string=None):
    """
    The restful handler for videos.
    It allows retrieval of all the videos (as an HTML page), as well as uploading new videos,
    deleting videos, and changing the "locked" state of an video.

    GET
        html: return an html page which will show all course videos. Note that only the video container
            is returned and that the actual videos are filled in with a client-side request.
        json: returns a page of videos. The following parameters are supported:
            page: the desired page of results (defaults to 0)
            page_size: the number of items per page (defaults to 50)
            sort: the video field to sort by (defaults to "date_added")
            direction: the sort direction (defaults to "descending")
    POST
        json: create (or update?) an video. The only updating that can be done is changing the lock state.
    PUT
        json: update the locked state of an video
    DELETE
        json: delete an video
    """
    course_key = CourseKey.from_string(course_key_string)
    if not has_course_author_access(request.user, course_key):
        raise PermissionDenied()

    response_format = request.REQUEST.get('format', 'html')
    if response_format == 'json' or 'application/json' in request.META.get('HTTP_ACCEPT', 'application/json'):
        if request.method == 'GET':
            return _local_videos_json(request, course_key)
        else:
            video_key = asset_key_string[4:] if asset_key_string else None
            return _local_update_video(request, course_key, video_key)
    elif request.method == 'GET':  # assume html
        return _local_video_index(request, course_key)
    else:
        return HttpResponseNotFound()


def _local_video_index(request, course_key):
    """
    Display an editable video library.

    Supports start (0-based index into the list of videos) and max query parameters.
    """
    course_module = modulestore().get_course(course_key)

    return render_to_response('local_video_index.html', {
        'context_course': course_module,
        'max_file_size_in_mbs': settings.MAX_VIDEO_UPLOAD_FILE_SIZE_IN_MB,
        'chunk_size_in_mbs': settings.VIDEO_UPLOAD_CHUNK_SIZE_IN_MB,
        'max_file_size_redirect_url': settings.MAX_VIDEO_UPLOAD_FILE_SIZE_URL,
        'asset_callback_url': reverse_course_url('local_videos_handler', course_key)
    })


def _local_videos_json(request, course_key):
    """
    Display an editable video library.

    Supports start (0-based index into the list of videos) and max query parameters.
    """
    requested_page = int(request.REQUEST.get('page', 0))
    requested_page_size = int(request.REQUEST.get('page_size', 50))
    requested_sort = request.REQUEST.get('sort', 'date_added')
    sort_ascending = False
    if request.REQUEST.get('direction', '').lower() == 'asc':
        sort_ascending = True

    current_page = max(requested_page, 0)
    start = current_page * requested_page_size
    videos, total_count = _local_get_videos_for_page(request, course_key, current_page, requested_page_size, requested_sort, sort_ascending)
    end = start + len(videos)

    # If the query is beyond the final page, then re-query the final page so that at least one video is returned
    if requested_page > 0 and start >= total_count:
        current_page = int(math.floor((total_count - 1) / requested_page_size))
        start = current_page * requested_page_size
        videos, total_count = _local_get_videos_for_page(request, course_key, current_page, requested_page_size, requested_sort, sort_ascending)
        end = start + len(videos)

    return JsonResponse({
        'start': start,
        'end': end,
        'page': current_page,
        'pageSize': requested_page_size,
        'totalCount': total_count,
        'assets': videos,
        'sort': requested_sort,
    })


def _local_get_videos_for_page(request, course_key, current_page, page_size, sort, ascending):
    """
    Returns the list of videos for the specified page and page size.
    """
    start = current_page * page_size
    end = start + page_size
    course_path = os.path.join(VIDEO_PATH_BASE, course_key.org, course_key.course)
    url_path_base = course_key.org + '/' + course_key.course
    cache_name = 'videos:' + course_key.org + '+' + course_key.course
    if cache.get(cache_name) is None:
        video_files = []
        for run in os.listdir(course_path):
            for name in os.listdir(os.path.join(course_path, run)):
                full_path = os.path.join(course_path, run, name)
                if os.path.isfile(full_path):
                    st = os.stat(full_path)
                    video_files.append(_local_get_video_json(name, datetime.utcfromtimestamp(st.st_mtime), st.st_size, run, url_path_base + '/' + run + '/' + name))
        cache.set(cache_name, video_files)
    else:
        video_files = cache.get(cache_name)

    return [sorted(video_files, lambda a,b: cmp(a[sort], b[sort]) if ascending else cmp(b[sort], a[sort]))[start:end], len(video_files)]


def _local_write_video_file(upload_file, file_path, start = 0, end = 0, length = 0):
     with open(file_path, "rb+" if start > 0 else "wb+") as fp:
        if start > 0: fp.seek(start)
        if upload_file.multiple_chunks():
            for chunk in upload_file.chunks():
                fp.write(chunk)
        else:
            fp.write(upload_file.read())


@require_POST
@ensure_csrf_cookie
@login_required
def _local_upload_video(request, course_key):
    '''
    This method allows for POST uploading of files into the course video
    library, which will be supported by file system.
    '''
    # Does the course actually exist?!? Get anything from it to prove its
    # existence
    try:
        modulestore().get_course(course_key)
    except ItemNotFoundError:
        # no return it as a Bad Request response
        logging.error("Could not find course: %s", course_key)
        return HttpResponseBadRequest()

    # compute a 'filename' which is similar to the location formatting, we're
    # using the 'filename' nomenclature since we're using a FileSystem paradigm
    # here. We're just imposing the Location string formatting expectations to
    # keep things a bit more consistent
    upload_file = request.FILES['file']
    file_name = upload_file.name.replace('/', '_')
    path_name = '/' + course_key.org + '/' + course_key.course + '/' + course_key.run

    content_loc = path_name + '/' + file_name
    file_path = VIDEO_PATH_BASE + content_loc
    dir_path = VIDEO_PATH_BASE + path_name

    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    if 'HTTP_CONTENT_RANGE' in request.META and request.META['HTTP_CONTENT_RANGE'].startswith('bytes '):
        content_range, total_length = request.META['HTTP_CONTENT_RANGE'][6:].split('/')
        content_start, content_end = content_range.split('-')
        _local_write_video_file(upload_file, file_path, int(content_start), int(content_end), int(total_length))
    else:
        _local_write_video_file(upload_file, file_path)

    cache.delete('videos:' + course_key.org + '+' + course_key.course)

    st = os.stat(file_path)
    response_payload = {
        'asset': _local_get_video_json(upload_file.name, datetime.utcfromtimestamp(st.st_mtime), st.st_size, course_key.run, content_loc),
        'msg': _('Upload completed')
    }

    return JsonResponse(response_payload)


@require_http_methods(("DELETE", "POST", "PUT"))
@login_required
@ensure_csrf_cookie
def _local_update_video(request, course_key, video_key):
    """
    restful CRUD operations for a course video.
    Currently only DELETE, POST, and PUT methods are implemented.

    video_path_encoding: the odd /c4x/org/course/category/name repr of the video (used by Backbone as the id)
    """
    if request.method == 'DELETE':
        # Make sure the item to delete actually exists.
        try:
            file_path = VIDEO_PATH_BASE + _local_add_slash(video_key)
        except:
            return HttpResponseBadRequest()
        if os.path.exists(file_path):
            os.remove(file_path)
            cache.delete('videos:' + course_key.org + '+' + course_key.course)
            return JsonResponse()
        else:
            return JsonResponse(status=404)

    elif request.method in ('PUT', 'POST'):
        if 'file' in request.FILES:
            return _local_upload_video(request, course_key)
        else:
            # Update existing video
            try:
                modified_video = json.loads(request.body)
            except ValueError:
                return HttpResponseBadRequest()
            return JsonResponse(modified_video, status=201)


def _local_get_video_json(display_name, date, size, run, location):
    """
    Helper method for formatting the video information to send to client.
    """
    video_url = VIDEO_URL_BASE + _local_add_slash(urllib.quote(location.encode('utf-8')))
    return {
        'display_name': display_name,
        'date_added': get_default_time_display(date),
        'run': run,
        'url': video_url,
        'video_size': size,
        'portable_url': video_url,
        'id': unicode('/c4x' + _local_add_slash(location))
    }


def _local_add_slash(url):
    if not url.startswith('/'):
        url = '/' + url  # TODO - re-address this once LMS-11198 is tackled.
    return url

