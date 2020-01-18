************
Installation
************
These installation instructions assume you already have Python installed. If you do not already have a copy of Python, we recommend you install `Anaconda Python`_. 

.. note:: autoscrub's Python 3 support is experimental, and only works with 3.4+. If you run into any troubles with Python 3, please let us know via the `issue tracker`_, and then try Python 2.7 instead.  

.. _`Anaconda Python`: https://www.continuum.io/downloads
.. _`issue tracker`: https://github.com/philipstarkey/autoscrub/issues

======
FFmpeg
======

Autoscrub requires that you have FFmpeg installed in your system, and that it is accessible from the directory autoscrub is run in (usually by appending the location of the FFmpeg executables to the system PATH). 

-----
Linux
-----

FFmpeg can usually be installed via your linux package manager. This typically also ensures that the location of FFmpeg is added to the system PATH.

-------
Windows
-------

Windows binaries can be downloaded `here`__. We recommend using the stable version (the one with a 3 digit version number). You will need to select the version that matches your system architecture (usually 64-bit) and with static linking. We have tested with `FFmpeg v3.3.3 (x64-static)`_ but any newer version should also work.

autoscrub requires the ffmpeg.exe and ffprobe.exe files be accessible from the directory that autoscrub is run from. You can either place the executables in a common location and add that location to the windows PATH environment variable or place the executables in the folder you will run autoscrub from (for example the folder containing your media files you wish to convert).

.. __: https://ffmpeg.zeranoe.com/builds/
.. _`FFmpeg v3.3.3 (x64-static)`: https://ffmpeg.zeranoe.com/builds/win64/static/ffmpeg-3.3.3-win64-static.zip


-------
Mac OSX
-------
FFmpeg builds can be found `here`__.

.. __: https://www.ffmpeg.org/download.html#build-mac

=========
Autoscrub
=========

----
PyPi
----
We recommend installing autoscrub from the Python Package Index. To do this, open a terminal (linux/OSX) or command prompt (Windows) window, and run::

    pip install autoscrub
    
-------------------
Upgrading autoscrub
-------------------

To upgrade to the latest version of autoscrub, run::

    pip install -U autoscrub
    
To upgrade to a specific version of autoscrub (or, alternatively, if you wish to downgrade), run::

    pip install -U autoscrub==<version>
    
where :code:`<version>` is replaced by the version you wish (for example :code:`pip install -U autoscrub==0.1.3`).

-------------------
Development Version
-------------------

If you wish to use the latest development version, you can obtain the source code from our `git repository`_. Once you have cloned our repository, you should run :code:`python setup.py install` in order to build and install the autoscrub package.


.. _`git repository`: https://github.com/philipstarkey/autoscrub