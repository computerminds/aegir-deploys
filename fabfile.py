from fabric.api import local, settings

import os


def scan_for_tags(location):
    if os.path.exists(location):
        print('===> Searching for valid tags')

        # We want to allow for the failure of the git command.
        with settings(warn_only=True):
            res = local("cd '%s' && git describe --tags --exact-match" % location, capture=True)

        if res.succeeded:
            print('===> Found a tag: [%s]' % res)
            create_make_template(res, location, 'aegir-make.template')
        else:
            print('===> Could not find a tag')


def create_make_template(version, location, template_name='aegir-make.make'):
    template_source = location + '/' + template_name
    template_target = template_name.replace('.template', '.make')
    if not os.path.exists(template_source):
        print('===> Could not find make template, looked for: %s' % template_source)
        raise SystemExit(1)
    else:
        # The template exists, so we'll use it
        local('sed "s/%TAG%/%s/" %s > %s' % (version, template_source, template_target))
