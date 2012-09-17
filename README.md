Continous deployment scripts for Aegir
======================================

*Warning:* These scripts aren't fully finished and should be considered dangerous.

Setup
-----

You will need to create a simple configuration file in your Drupal repository: `.aegir-deploy.yml` options can be specified globally or per-branch, with the branch ones taking precedence.

### master_server

(required) This is the Aegir master server to run the deployment commands against. This should be accesible via ssh.

### site_name

(required) This is the Aegir name for your site, which is usually the FQDN.

### platform_base

(optional, recommended) This is used as the beginning portion of the generated platform name. This will probably want to be your site's name for example.

### web_server

(required, default: `localhost`) This is the webserver to deploy the platform on to. This should be the Aegir machine name for this server, not including the `server_` portion.

### makefile_template

(required, default: `aegir-make.template`) This tells the deployment script where the makefile template for building the platform is. When building, this file will be copied, and `%TAG%` will be replaced with the tag that is being built by the script.

### aegir_user

(required, default: `aegir`) This is the user to use when connecting to the Aegir master server to issue commands.

### master_server_tmp

(required, `/tmp`) This a temporary location on the Aegir master server for storing temporarly generated make files.

### template_target

(required, default: `time.strftime('aegir-deploy-%Y-%m-%d-%H%M%S.make')`) This is the name of the temporary make file that will be generated by the build process.

### branches

(optional, recommended) This is a dictionary with keys that are the names of branches, and values that themselves are dictionaries that can have any of the other configuration options that should be used when building that specific branch. See the examples section for a specific example.

Example configuration files
---------------------------

    master_server: 'master-server.example.com'
    platform_base: 'Example site'
    web_server: 'remote_server'
    branches:
        master:
            site_name: 'live.example.com'
        develop:
            site_name: 'staging.example.com'

This is a fairly standard setup, we have a Aegir master server at `master-server.example.com` and we want to create platforms that are prefixed with `Example site`, these will be created on the `remote_server` web server. Additionally when building the master and develop branches we use a specific `site_name`.

Usage
-----

Point this script at your git checkout of your codebase, where .aegir-deploy,yml should be stored:

    fab setup:/path/to/checkout scan_for_tags

This will setup the fabfile with the configuration, and then look for a tag on the currently checked out HEAD, if it finds one then it'll:

1. Use the makefile template to generate a new makefile with the tag in it.
2. Move that generated makefile to the Aegir master server.
3. Create a new platform on the Aegir master using the generated makefile.
4. Migrate the specified site onto the new platform.

If the current HEAD doesn't have a tag associated with it, then this process will exit gracefully and not do anything.
