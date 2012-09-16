from fabric.api import local

import os


def scan_for_tags(location):
    if os.path.exists(location):
        print('===> Searching for valid tags')
        res = local("cd '%s' && git describe --tags --exact-match | true" % location, capture=True)
        if res.succeeded:
            print('===> Found a tag')
        else:
            print('===> Could not find a tag')

