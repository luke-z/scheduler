from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator, available_attrs

from django.views.generic.edit import (CreateView, DeleteView, UpdateView,
                                       FormView)
from django.views.generic.base import View, TemplateView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from annoying.decorators import ajax_request
from annoying.functions import get_object_or_None
from .models import Course,Subject,Profile
import urllib2
import json

class ProtectedView(View):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ProtectedView, self).dispatch(*args, **kwargs)

def get_context(context, profile):
    context['allSubjects'] = json.dumps([{"name":s.name,"description":s.description,"courses":[{"catalog_number":c.catalog_number,"title":(c.course_data['title'] if 'title' in c.course_data else "")} for c in s.course_set.all().order_by("catalog_number")]} for s in Subject.objects.all()])
    try:
        courseInfo={}
        context['schedule'] = json.dumps(profile.schedule)
        context['courseList'] = json.dumps(profile.courseList)
        for course in profile.courseList:
            courseData = getCourseInfo(
                            course['subject'],
                            course['catalog_number']
                            )
            courseInfo[course['subject']+course['catalog_number']] = courseData

        for term in profile.schedule:
            for course in term['courses']:
                courseData = getCourseInfo(
                                course['subject'],
                                course['catalog_number']
                                )
                courseInfo[course['subject']+course['catalog_number']] = courseData
        context['courseInfo'] = json.dumps(courseInfo)
        context['startYear'] = profile.startYear
        context['startTerm'] = profile.startTerm
    except:
        context['errors'] = ['Could not parse saved data']
        context['courseInfo'] = json.dumps({})
        context['schedule'] = json.dumps([])
        context['courseList'] = json.dumps([])
        context['startYear'] = 2012
        context['startTerm'] = 0
    return context


class IndexView(ProtectedView, TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        get_context(context,self.request.user.profile)
        return context

class ShareView(DetailView):
    template_name = 'share.html'
    model = Profile
    slug_field = 'user__pk'

    def get_context_data(self, **kwargs):
        context = super(ShareView, self).get_context_data(**kwargs)
        if self.object.user.first_name:
            context['username'] = self.object.user.first_name + self.object.user.last_name 
        else:
            context['username'] = self.object.user.username
        if self.object.share:
            get_context(context, self.object)
        else:
            context['private'] = True
        return context

@ajax_request
@login_required
def Save(request):
    if not request.POST:
        return {'success': False}
    for requiredField in ['schedule','autosave','courseList','startYear','startTerm']:
        if requiredField not in request.POST:
            return {'success': False, 'error':"missing required fields"}

    schedule = request.POST['schedule']
    autosave = request.POST['autosave']
    courseList = request.POST['courseList']
    startYear = request.POST['startYear']
    startTerm = request.POST['startTerm']
    request.user.profile.schedule=schedule
    request.user.profile.autosave=autosave=="true"
    request.user.profile.courseList=courseList
    request.user.profile.startYear=startYear
    request.user.profile.startTerm=startTerm
    request.user.profile.save()
    return {'success':True}




def getCourseInfo(subjectName, catalog_number):
    subjectName = subjectName.upper()
    catalog_number = catalog_number.upper()
    course = get_object_or_None(
        Course, 
        subject__name=subjectName,
        catalog_number=catalog_number
        )
    if not course:
        return None

    course.course_data.update(course.course_data_override)
    return course.course_data

@ajax_request
def CourseInfo(request, subjectName, catalog_number):
    return getCourseInfo(subjectName, catalog_number);

@ajax_request
def ListLookup(request, subjectName):
    subject = get_object_or_None(
        Subject,
        name=subjectName
        )
    if subject:
        courses = subject.course_set.all().order_by('catalog_number')
        return [{"catalog_number":c.catalog_number,"title":c.course_data['title']} for c in courses]
    else:
        return []


