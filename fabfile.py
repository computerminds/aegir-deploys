from fabric.api import local, env

import os


def scan_for_tags(location):
    if os.path.exists(location):
        print('===> Searching for valid tags')
        old_env = env.warn_only
        env.warn_only = False
        res = local("cd '%s' && git describe --tags --exact-match" % location, capture=True)
        env.warn_only = old_env
        if res.succeeded:
            print('===> Found a tag')
        else:
            print('===> Could not find a tag')

