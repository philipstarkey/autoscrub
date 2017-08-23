**************************
Example command line usage
**************************
The installation process of autoscrub automatically creates a command line utility for you to use. Here we will show examples of the most common usage. To see the full set of available commands and options run :code:`autoscrub --help` from a terminal or look in the :ref:`command_line_reference` documentation.

.. note:: As autoscrub is a wrapper around FFmpeg, autoscrub will accept any input video format that FFmpeg does. This includes :code:`.trec` files produced by Camtasia.

.. note:: autoscrub automatically transcodes your video to match the `recommended upload settings for YouTube`_. This means that the output file extension should always be :code:`.mp4`.

.. _`recommended upload settings for YouTube`: https://support.google.com/youtube/answer/1722171?hl=en
===========
autoprocess
===========
The most common command you will use is :code:`autoscrub autoprocess`. The autoprocess command accepts a variety of options, however they have been preconfigured with sensible defaults that will suit many users. 

To use the default options, run (replace paths as appropriate)::

    autoscrub autoprocess input_file.mp4 output_file.mp4

The most common options you are likely to want to adjust are:

 * :code:`-d` (or :code:`--silence-duration`): This specifies the minimum length that autoscrub will use in detecting a silent segment (which will be sped up). Silent segments of audio that are shorter than this time will not be sped up. Adjust this to match your presentation style.
 * :code:`-t` (or :code:`--target-threshold`): This specifies the audio level used to determine whether there is silence or not. If the audio is below this level, for at least the length of time specified by :code:`--silence-duration`, then autoscrub will speed up this segment. Adjust this to compensate for a noisy background or quite speaking volume. The units are specified in decibels (dB).
 
Here we specify custom values for both these options (5 second silent duration, -20dB silence threshold) as an example::

    autoscrub autoprocess -d 5 -t -20 input_file.mp4 output_file.mp4

To see all available options for autoprocess, run::

    autoscrub autoprocess --help