from __future__ import absolute_import

from django import forms
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from sentry import roles, options
from sentry.web.frontend.base import ProjectView
from sentry.utils.email import MessageBuilder
from sentry.models import OrganizationMember


class TransferProjectForm(forms.Form):
    email = forms.CharField(label=_('Organization Owner'), max_length=200,
        widget=forms.TextInput(attrs={'placeholder': _('user@company.com')}))


class TransferProjectView(ProjectView):
    required_scope = 'project:admin'
    sudo_required = True

    def get_form(self, request):
        if request.method == 'POST':
            return TransferProjectForm(request.POST)
        return TransferProjectForm()

    def handle(self, request, organization, team, project):
        form = self.get_form(request)

        if form.is_valid():
            email = form.cleaned_data.get('email')

            if OrganizationMember.objects.filter(
                role=roles.get_top_dog().id,
                user__is_active=True,
                user__email=email,
            ).exists():
                context = {
                    'email': email,
                    'project_name': project.name,
                    'request_time': timezone.now(),
                    'url': 'dev.getsentry.net:8000/accept-transfer/?project_id=' + '%s' % (project.id),
                    'requester': request.user
                }
                MessageBuilder(
                    subject='%sRequest for Project Transfer' % (options.get('mail.subject-prefix'),),
                    template='sentry/emails/transfer_project.txt',
                    html_template='sentry/emails/transfer_project.html',
                    type='org.confirm_delete',
                    context=context,
                ).send_async([email])

            messages.add_message(
                request, messages.SUCCESS,
                _(u'A request was sent to move project %r to a different organization') % (project.name.encode('utf-8'),))

            return HttpResponseRedirect(
                reverse('sentry-organization-home', args=[team.organization.slug])
            )

        context = {
            'form': form,
        }

        return self.respond('sentry/projects/transfer.html', context)
