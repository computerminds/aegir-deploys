from fabric.api import local, settings

import os


def scan_for_tags(location):
    if os.path.exists(location):
        print('===> Searching for valid tags')
        with settings(
            warn_only=True
        ):
            res = local("cd '%s' && git describe --tags --exact-match" % location, capture=True)

        if res.succeeded:
            print('===> Found a tag')
        else:
            print('===> Could not find a tag')

