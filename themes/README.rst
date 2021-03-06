#####################
Comprehensive Theming
#####################


Comprehensive Theming lets you customize the appearance of your Open edX
installation.  You can override Sass and CSS settings, images, or entire HTML
templates.

Eventually, Comprehensive Theming will obsolete existing theming mechanisms,
but for now they co-exist peacefully. This document describes how to use
Comprehensive Theming, and also the changes you'll need to make to keep other
theming mechanisms working.


Creating a theme
================

A theme is a directory of assets.  You can create this directory wherever you
like, it does not have to be inside the edx-platform directory.  The structure
within this directory mirrors the assets in the edx-platform repo itself.
Files you provide in your theme are used in place of the same-named files in
edx-platform.  Here's a sample::

    my-theme
    └── lms
        ├── static
        │   ├── images
        │   │   └── logo.png
        │   └── sass
        │       ├── _overrides.scss
        │       ├── lms-main-rtl.scss
        │       └── lms-main.scss
        └── templates
            ├── footer.html
            └── header.html

The top directory is named whatever you like.  This example uses "my-theme".
The files provided here override the files in edx-platform.  In this case, the
``my-theme/lms/static/sass/lms-main.scss`` file is used in place of the
``edx-platform/lms/static/sass/lms-main.scss`` file.


Images
------

Images can be substituted simply by placing the new image at the right place
in the theme directory.  In our example above, the lms/static/images/logo.png
image is overridden.


Sass/CSS
--------

Most CSS styling in Open edX is done with Sass files compiled to CSS.  You can
override individual settings by creating a new Sass file that uses the existing
file, and overrides the few settings you want.

For example, to change the fonts used throughout the site, you can create an
``lms/static/sass/_overrides.scss`` file with the change you want::

    $sans-serif: 'Helvetica';

The variables that can currently be overridden are defined in
``lms/static/sass/base/_variables.scss``.

**Note:** We are currently in the middle of a re-engineering of the Sass
variables.  They will change in the future.  If you are interested, you can see
the new development in the `edX Pattern Library`_.

.. _edX Pattern Library: http://ux.edx.org/

Then create ``lms/static/sass/lms-main.scss`` to use those overrides, and also
the rest of the definitions from the original file::

    // Our overrides for settings we want to change.
    @import 'overrides';

    // Import the original styles from edx-platform.
    @import 'lms/static/sass/lms-main';

Do this for each .scss file your site needs.


HTML Templates
--------------

You can make changes to HTML templates by copying them to your theme directory
in the appropriate place, and making the changes you need.  Keep in mind that
in the future if you upgrade the Open edX code, you may have to update the
copied template in your theme also.


Installing your theme
---------------------

To use your theme, you need to add a configuration value pointing to your theme
directory. There are two ways to do this.

#.  If you usually edit server-vars.yml:

    #.  As the vagrant user, edit (or create)
        /edx/app/edx_ansible/server-vars.yml to add the
        ``edxapp_comp_theme_dir`` value::

            edxapp_comp_theme_dir: '/full/path/to/my-theme'

    #.  Run the update script::

            $ sudo /edx/bin/update configuration master
            $ sudo /edx/bin/update edx-platform HEAD

#.  Otherwise, edit the /edx/app/edxapp/lms.env.json file to add the
    ``COMP_THEME_DIR`` value::

        "COMP_THEME_DIR": "/full/path/to/my-theme",

Restart your site.  Your changes should now be visible.


"Stanford" theming
==================

If you want to continue using the "Stanford" theming system, there are a few
changes you'll need to make.

Create the following new files in the ``sass`` directory of your theme:

* lms-main.scss
* lms-main-rtl.scss
* lms-course.scss
* lms-course-rtl.scss
* lms-footer.scss
* lms-footer-rtl.scss

The contents of each of these files will be very similar. Here's what
``lms-main.scss`` should look like::

    $static-path: '../../../..';
    @import 'lms/static/sass/lms-main';
    @import '_default';

Each file should set the ``$static-path`` variable to a relative path that
points to the ``lms/static`` directory inside of ``edx-platform``. Then,
it should ``@import`` the sass file under ``lms/static/sass`` that matches
its name: ``lms-footer.scss`` should import ``lms/static/sass/lms-footer``,
for example. Finally, the file should import the ``_default`` name, which
refers to the ``_default.scss`` Sass file that should already exist in your
Stanford theme directory.

If your theme uses a different name than "default", you'll need to use that
name in the ``@import`` line.

Run the ``update_assets`` command to recompile the theme::

    $ paver update_assets lms --settings=aws
