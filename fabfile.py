from fabric.api import local, settings, env, put, run
import yaml
import os
import time

# Setup the default settings in the fabric env.
# If you want to allow an option to be specified in the config file, then it
# must be declared here.
env.aegir_deploy = {
    'makefile_template': 'aegir-make.template',
    'location': None,
    'master_server': None,
    'aegir_user': 'aegir',
    'master_server_tmp': '/tmp',
    'template_target': time.strftime('aegir-deploy-%Y-%m-%d-%H%M%S.make'),
    'platform_base': '',
    'site_name': None,
    'web_server': 'localhost',
}


def logger(string):
    print("===> %s" % string)


def setup(location):
    env.aegir_deploy['location'] = location
    # Find the configuration file and read out the settings we need into our env.
    config_file = location + '/.aegir-deploy.yml'
    if not os.path.exists(config_file):
        logger('Could not find configuration file, aborting')
        raise SystemExit(1)
    else:
        logger('Loading configuration from %s' % config_file)
        stream = file(config_file, 'r')
        yaml_config = yaml.load(stream)
        stream.close()

        # Find the current branch.
        # We want to allow for the failure of the git command.
        with settings(warn_only=True):
            current_branch = local("cd '%s' && git rev-parse --symbolic-full-name --abbrev-ref HEAD" % location, capture=True)
        if not current_branch.succeeded:
            logger('Could not determine current branch')
            raise SystemExit(1)

        # Copy the configuration over.
        for k in env.aegir_deploy:
            if (k in yaml_config) and (not k is 'branches'):
                env.aegir_deploy[k] = yaml_config[k]

        # Now copy the branch specific information over.
        # Ensure that we detect at least one branch
        seen_current_branch = False
        if 'branches' in yaml_config.keys():
            if current_branch and current_branch in yaml_config['branches'].keys():
                seen_current_branch = True
                for k in env.aegir_deploy:
                    if k in yaml_config['branches'][current_branch]:
                        env.aegir_deploy[k] = yaml_config['branches'][current_branch][k]

        if not seen_current_branch:
            logger('Build not configured for this branch')
            raise SystemExit(0)


def validate_and_run():
    # We're going to perform some basic sanity checks first.
    location = env.aegir_deploy['location']
    if env.aegir_deploy['master_server'] is None:
        logger('No master server specified')
        raise SystemExit(1)

    if env.aegir_deploy['site_name'] is None:
        logger('No site_name specified')
        raise SystemExit(1)


    # Those have passed, lets move on to the actually running of this thing.
    tag = scan_for_tags()
    if tag is None:
        raise SystemExit(0)
    else:
        logger('Found a tag: [%s]' % tag)
        env.aegir_deploy['release_tag'] = tag
    
    create_make_template()
    put_template()
    build_platform()
    migrate_site()
    import_site()


def scan_for_tags():
    location = env.aegir_deploy['location']
    if os.path.exists(location):
        logger('Searching for valid tags')

        # We want to allow for the failure of the git command.
        with settings(warn_only=True):
            res = local("cd '%s' && git describe --tags --exact-match" % location, capture=True)

        if res.succeeded:
            return res
        else:
            logger('Could not find a tag')
            return None


def create_make_template():
    location = env.aegir_deploy['location']
    template_name = env.aegir_deploy['makefile_template']
    template_target = env.aegir_deploy['template_target']
    release_tag = env.aegir_deploy['release_tag']

    template_source = location + '/' + template_name
    if not os.path.exists(template_source):
        logger('Could not find make template, looked for: %s' % template_source)
        raise SystemExit(1)
    else:
        # The template exists, so we'll use it
        local('sed "s/%%TAG%%/%s/" "%s" > "%s"' % (release_tag, template_source, template_target))


def put_template():
    aegir_user = env.aegir_deploy['aegir_user']
    master_server = env.aegir_deploy['master_server']
    template = env.aegir_deploy['template_target']
    master_server_tmp = env.aegir_deploy['master_server_tmp']

    logger("Copying the template to the remote server")
    with settings(host_string=aegir_user + '@' + master_server):
        put(template, master_server_tmp)


def build_platform():
    aegir_user = env.aegir_deploy['aegir_user']
    master_server = env.aegir_deploy['master_server']
    template = env.aegir_deploy['template_target']
    master_server_tmp = env.aegir_deploy['master_server_tmp']
    platform_base = env.aegir_deploy['platform_base']
    release_tag = env.aegir_deploy['release_tag']
    web_server = env.aegir_deploy['web_server']

    # Compute the platform name
    platform_name = machine_name(platform_base + ' ' + release_tag)
    env.aegir_deploy['platform_name'] = platform_name
    # And the makefile
    makefile = master_server_tmp + '/' + template


    logger("Building the platform")
    with settings(host_string=aegir_user + '@' + master_server, shell='/bin/bash -c'):

        # Lets ensure that the platform that we're about to make doesn't
        # already exist.
        with settings(warn_only=True):
            res = run("test -d '/var/aegir/platforms/%s'" % (platform_name))
            if (res.succeeded):
                # The directory already exists, don't wipe it out, abort.
                logger('Platform path already exists, aborting')
                raise SystemExit(0)


        run("drush make '%s' '/var/aegir/platforms/%s'" % (makefile, platform_name))
        logger('Adding the platform to Aegir')
        run("drush --root='/var/aegir/platforms/%s' provision-save '@platform_%s' --context_type='platform' --makefile='%s' --web_server='@server_%s'" % (platform_name, platform_name, makefile, web_server))
        run("drush @hostmaster hosting-import '@platform_%s'" % platform_name)
        logger('Verifying the platform')
        run("drush @hostmaster hosting-task '@platform_%s' verify" % platform_name)


def migrate_site():
    aegir_user = env.aegir_deploy['aegir_user']
    master_server = env.aegir_deploy['master_server']
    platform_name = env.aegir_deploy['platform_name']
    site_name = env.aegir_deploy['site_name']

    logger('Migrating the site to the new platform')

    with settings(host_string=aegir_user + '@' + master_server, shell='/bin/bash -c'):
        run("drush --verbose @%s provision-migrate '@platform_%s'" % (site_name, platform_name))


def import_site():
    aegir_user = env.aegir_deploy['aegir_user']
    master_server = env.aegir_deploy['master_server']
    site_name = env.aegir_deploy['site_name']

    logger('Updating the site in the Aegir frontend')

    with settings(host_string=aegir_user + '@' + master_server, shell='/bin/bash -c'):
        run("drush --verbose @hostmaster hosting-import '@%s'" % (site_name))


def machine_name(value):
    import re
    # Convert invalid characters to underscores.
    value = re.sub('[^a-zA-Z0-9_]', '_', value)
    # Convert multiple underscores to single ones.
    value = re.sub('_+', '_', value)
    return value
