# Copyright 2017 Russell Anderson, Philip Starkey
#
# This file is part of autoscrub.
#
# autoscrub is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# autoscrub is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with autoscrub.  If not, see <http://www.gnu.org/licenses/>.

import tempfile
import os
import subprocess
import time

import autoscrub
import click
import requests

def check_ffmpeg():
    # check ffmpeg exists
    try:
        subprocess.check_output(["ffmpeg", "-L"], stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, OSError):
        click.echo("[autoscub:error]: Could not find ffmpeg executable. Check that ffmpeg is in the local folder or your system PATH and that you can run 'ffmpeg -L' from the command line.")
        raise click.Abort()
        
    # check ffprobe exists
    try:
        subprocess.check_output(["ffprobe", "-L"], stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, OSError):
        click.echo("[autoscub:error] Could not find ffprobe executable. Check that ffprobe is in the local folder or your system PATH and that you can run 'ffprobe -L' from the command line.")
        raise click.Abort()
        
def check_for_new_autoscrub_version():
    try:
        r = requests.get('https://pypi.python.org/pypi/autoscrub/json', timeout=0.1)
        online_version = r.json()['info']['version']
        if online_version != autoscrub.__version__:
            # check to see if version is newer
            o_major, o_minor, o_patch = online_version.split('.')
            l_major, l_minor, l_patch = autoscrub.__version__.split('.')
            
            upgrade = False
            if int(l_major) < int(o_major):
                upgrade = True
            elif int(l_major) == int(o_major) and int(l_minor) < int(o_minor):
                upgrade = True
            elif int(l_major) == int(o_major) and int(l_minor) == int(o_minor) and int(l_patch) < int(o_patch):
                upgrade = True
            
            if upgrade:
                click.echo(click.style("[autoscub:info] A new version of autoscrub is available", fg='green', bg='black'))
                click.echo(click.style("[autoscub:info] You are running autoscrub version: {}".format(autoscrub.__version__), fg='green', bg='black'))
                click.echo(click.style("[autoscub:info] The latest autoscrub version is: {}".format(online_version), fg='green', bg='black'))
                click.echo(click.style("[autoscub:info] To upgrade, run: pip install -U autoscrub", fg='green', bg='black'))
                return True
                
    except Exception:
        pass
    
    return False


# code for printing percentage complete
class NewLineCallback(object):
    def __init__(self, duration):
        self.time_since_last_print = time.time()
        self.update_every_n_seconds = 1
        self.start_time = time.time()
        self.duration = duration
        self.last_percentage = 0
        
    def new_line_callback(self, line):
        # Only update every N seconds
        if time.time() - self.time_since_last_print < self.update_every_n_seconds:
            return
        # ignore (for speed since this interrupts reading the output from the subprocess) if the line doesn't contain what we want
        if 'time=' not in line:
            return
               
        try:
            # get time text
            time_text = line.split('time=')[-1].split(' ')[0]
            # speed_text = line.split('speed=')[-1].split('x')[0]            
            # speed = float(speed_text)
            
            # format it into seconds
            seconds = autoscrub.hhmmssd_to_seconds(time_text)
            # hack because the bar.update method takes the number of steps to increase, not the current position
            percentage = min(float(seconds)/self.duration, 1)*100
            
            time_remaining = (time.time()-self.start_time)/percentage*(100-percentage)
            
            if self.last_percentage != int(percentage):
                click.echo("[ffmpeg:filter_complex_script] {:3d}% complete [{} remaining]\r".format(int(percentage), autoscrub.seconds_to_hhmmssd(time_remaining, decimal=False)), nl=False)
                self.last_percentage = int(percentage)
        except Exception:
            raise
            click.echo("[autoscrub:warning] Could not determine percentage completion. Consider not suppressing the FFmpeg output by running autoscrub with the option --show-ffmpeg-output")
        else:
            self.time_since_last_print = time.time()
    

def make_click_dict(*args, **kwargs):    
    return (args, kwargs)

_option__silence_duration = make_click_dict('--silence-duration', '-d', default=2.0, type=float, help='The minimum duration of continuous silence (in seconds) required to trigger speed up of that segment.', show_default=True)
_option__hasten_audio = make_click_dict('--hasten-audio', '-h', default='tempo', type=click.Choice(['trunc', 'pitch', 'tempo']), help="The method of handling audio during the speed up of silent segments.", show_default=True)
_option__target_lufs = make_click_dict('--target-lufs', '-l', default=-18.0, type=float, help='The target loudness in dBLUFS for the output audio', show_default=True)
_option__pan_audio = make_click_dict('--pan-audio', '-p', type=click.Choice(['left', 'right']), help="Copies the specified audio channel (left|right) to both audio channels.", show_default=True)
_option__rescale = make_click_dict('--rescale', '-r', nargs=2, type=int, metavar="WIDTH HEIGHT", help='rescale the input video file to the resolution specified  [usage: -r 1920 1080]')
_option__speed = make_click_dict('--speed', '-s', default=8, type=float, help='The factor by which to speed up the video during silent segments', show_default=True)
_option__target_threshold = make_click_dict('--target-threshold', '-t', default=-18.0, type=float, help='The audio threshold for detecting silent segments in dB', show_default=True)
_option__silent_volume = make_click_dict('--silent-volume', '-v', default=1.0, type=float, help='The factor to scale the audio volume during silent segments', show_default=True)
_option__delay = make_click_dict('--delay', default=0.25, type=float, help='The length of time (in seconds) to delay the start of the speed up of a silent segment. This also ends the speedup early, by the same amount, and must satisfy the condition 2*delay < silence-duration', show_default=True)
_option__start = make_click_dict('--start', default=0, type=float, help='Content before this time is removed', show_default=True)
_option__stop = make_click_dict('--stop', type=float, help='Content after this time is removed', show_default=True)
_option__codec = make_click_dict('--re-encode', nargs=1, type=str, metavar='CODEC', help='Re-encode the file with the codec specified', show_default=True)
_option__show_ff_output = make_click_dict('--show-ffmpeg-output', help="Prints the raw FFmpeg and FFprobe output to the terminal", is_flag=True)
_option__no_prompt = make_click_dict('--suppress-prompts', help="Suppresses confirmation prompts to overwrite output file(s) and proceeds even if no silences are detected in input file.", is_flag=True)

def create_filtergraph(input, filter_graph_path, speed, rescale, target_lufs, target_threshold, pan_audio, hasten_audio, silence_duration, delay, silent_volume, suppress_prompts):    
    folder, filename = os.path.split(input)
    click.echo('[autoscrub:info] Processing %s' % filename)
    
    # determine audio sample rate
    click.echo('[ffprobe] Getting audio sample rate...')
    input_sample_rate = autoscrub.getSampleRate(input)
    try:
        input_sample_rate # click.echo("Measured sample rate = %d Hz"%input_sample_rate)
    except Exception:
        click.echo("[autoscrub:error] Could not determine the audio samplerate of your file")
        raise click.Abort()
        
    click.echo('[ffmpeg:ebur128] Checking loudness of file...')
    loudness = autoscrub.getLoudness(input)
    try:
        input_lufs = loudness['I']
    except Exception:
        click.echo("[autoscrub:error] Could not determine the loudness of your file")
        raise click.Abort()
    
    # Calculate gain
    gain = target_lufs - input_lufs
    
    # Apply gain correction if pan_audio is used (when one stereo channel is silent)
    if pan_audio in ['left', 'right']:
        click.echo('[autoscrub:info] Reducing gain by 3dB due to audio pan')
        gain -= 3
    
    # calculate input_threshold
    input_threshold_dB = input_lufs + target_threshold - target_lufs
    
    # print audio data to terminal
    click.echo('[autoscrub:info] Measured loudness = %.1f dBLUFS; Silence threshold = %.1f dB; Gain to apply = %.1f dB' % (input_lufs, input_threshold_dB, gain))

    # find silent segments
    click.echo('[ffmpeg:silencedetect] Searching for silence...')
    silences = autoscrub.getSilences(input, input_threshold_dB, silence_duration, False)
    durations = [s['silence_duration'] for s in silences if 'silence_duration' in s]
    if len(durations):
        mean_duration = sum(durations)/len(durations)
        click.echo('[autoscrub:info] Found %i silences of average duration %.1f seconds.' % (len(silences), mean_duration))
    elif not suppress_prompts:
        click.confirm("[autoscrub:warning] No silences found. Do you wish to continue?", abort=True)

    # Generate the filtergraph
    click.echo('[autoscrub:info] Generating ffmpeg filter_complex script...')
    autoscrub.writeFilterGraph(filter_graph_path, silences, factor=speed, audio_rate=input_sample_rate, pan_audio=pan_audio, gain=gain, rescale=rescale, hasten_audio=hasten_audio, delay=delay, silent_volume=silent_volume)
    
    return silences

@click.group()
def cli():
    """Welcome to autoscrub!
    
    \b
    If you're unsure which command you want to run, you likely want:
        autoscrub autoprocess <input video path> <output video path>
    To view the additional options for autoprocessing, run:
        autoscrub autoprocess --help
    
    \b
    To see command line arguments for the other autoscrub commands, run:
        autoscrub COMMAND --help
    where the available commands are listed below.
    """
    pass

@cli.command()
def version():
    """Displays the autoscrub version"""
    
    # print out version if upgrade not available 
    # (upgrade text prints out current version, so the current version is printed either way)
    if not check_for_new_autoscrub_version():    
        click.echo("[autoscrub:info] version: {}".format(autoscrub.__version__))
    
@cli.command()
@click.option(*_option__silence_duration[0], **_option__silence_duration[1])
@click.option(*_option__hasten_audio[0],     **_option__hasten_audio[1])
@click.option(*_option__target_lufs[0],      **_option__target_lufs[1])
@click.option(*_option__pan_audio[0],        **_option__pan_audio[1])
@click.option(*_option__rescale[0],          **_option__rescale[1])
@click.option(*_option__speed[0],            **_option__speed[1])
@click.option(*_option__target_threshold[0], **_option__target_threshold[1])
@click.option(*_option__silent_volume[0],    **_option__silent_volume[1])
@click.option(*_option__delay[0],            **_option__delay[1])
@click.option(*_option__show_ff_output[0],   **_option__show_ff_output[1])
@click.option(*_option__no_prompt[0],        **_option__no_prompt[1])
@click.option('--debug', help="Retains the generated filtergraph file for inspection", is_flag=True)
@click.argument('input', type=click.Path(exists=True), metavar="input_filepath")
@click.argument('output', type=click.Path(exists=False), metavar="output_filepath")
def autoprocess(input, output, speed, rescale, target_lufs, target_threshold, pan_audio, hasten_audio, silence_duration, delay, silent_volume, show_ffmpeg_output, suppress_prompts, debug):
    """automatically process the input video and write to the specified output file"""
    
    if show_ffmpeg_output:
        autoscrub.suppress_ffmpeg_output(False)
    else:
        autoscrub.suppress_ffmpeg_output(True)
    
    # check executables exist
    check_ffmpeg()
    
    # check autoscrub version
    check_for_new_autoscrub_version()
    
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    output = os.path.abspath(output)
    
    # ensure that there will always be some part of a silent segment that experiences a speedup
    if not (2*delay < silence_duration):
        click.echo("[autoscrub:error] The value for delay must be less than half of the silence_duration specified")
        return
    
    # check if output file exists and prompt
    if os.path.exists(output) and not suppress_prompts:
        click.confirm('[autoscrub:warning] The specified output file [{output}] already exists. Do you want to overwrite it?'.format(output=output), abort=True)
    
    # adjust hasten_audio if 'trunc'
    if hasten_audio == 'trunc':
        hasten_audio = None
        
    # Make a temporary file for the filterscript
    handle, filter_graph_path = tempfile.mkstemp()
    # Python returns an open handle which we don't want, so close it
    os.close(handle)

    silences = create_filtergraph(input, filter_graph_path, speed, rescale, target_lufs, target_threshold, pan_audio, hasten_audio, silence_duration, delay, silent_volume, suppress_prompts)
    
    estimated_duration = autoscrub.getDuration(input)
    for silence in silences:
        if 'silence_duration' in silence:
            estimated_duration -= (silence['silence_duration']-2*delay)*(1-1.0/speed)
            
    click.echo("[autoscrub:info] autoscrubbing video")
    # commented out because it's a bit confusing and could be incorrectly interpretted as the estimated conversion time, not video duration
    # click.echo("Estimated duration of autoscrubbed video is {}".format(autoscrub.seconds_to_hhmmssd(estimated_duration)))
    
    nlc = NewLineCallback(estimated_duration)
    if not show_ffmpeg_output:
        callback = nlc.new_line_callback
    else:
        callback = None
    
    # Process the video file using ffmpeg and the filtergraph
    result = autoscrub.ffmpegComplexFilter(input, filter_graph_path, output, run_command=True, overwrite=True, stderr_callback=callback)
    start_time = callback.__self__.start_time if autoscrub.six.PY3 else callback.im_self.start_time
    seconds_taken = time.time() - start_time
    time_taken = autoscrub.seconds_to_hhmmssd(seconds_taken, decimal=False)
    click.echo("[ffmpeg:filter_complex_script] Completed in {} ({:.1f}x speed)   ".format(time_taken, estimated_duration/seconds_taken))
    click.echo("[autoscrub:info] Done!")
    click.echo("[autoscrub:info] FFmpeg command run was: ")
    click.echo("   " + subprocess.list2cmdline(result))
        
    # delete the filtergraph temporary file unless we are debugging
    if not debug:
        # delete the temporary file
        os.remove(filter_graph_path)
    else:
        click.echo('[autoscrub:debug] The filter script is located at: {filter_graph_path}'.format(filter_graph_path=filter_graph_path))

@cli.command(name='loudness-adjust')
@click.option(*_option__target_lufs[0],     **_option__target_lufs[1])
@click.option(*_option__show_ff_output[0],  **_option__show_ff_output[1])
@click.option(*_option__no_prompt[0],       **_option__no_prompt[1])
@click.argument('input', type=click.Path(exists=True), metavar="input_filepath")
@click.argument('output', type=click.Path(exists=False), metavar="output_filepath")
def match_loudness(input, output, target_lufs, show_ffmpeg_output, suppress_prompts):
    """Adjusts the loudness of the input file"""
    
    if show_ffmpeg_output:
        autoscrub.suppress_ffmpeg_output(False)
    else:
        autoscrub.suppress_ffmpeg_output(True)
    
    # check executables exist
    check_ffmpeg()
    
    # check autoscrub version
    check_for_new_autoscrub_version()
    
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    output = os.path.abspath(output)
    
    # check if output file exists and prompt
    if os.path.exists(output) and not suppress_prompts:
        click.confirm('[autoscrub:warning] The specified output file [{output}] already exists. Do you want to overwrite?'.format(output=output), abort=True)
    
    autoscrub.matchLoudness(input, target_lufs, output, overwrite=True)
    
@cli.command(name='display-video-properties')
@click.option(*_option__show_ff_output[0],  **_option__show_ff_output[1])
@click.argument('input', type=click.Path(exists=True), metavar="input_filepath")
def get_properties(input, show_ffmpeg_output):
    """Displays properties about the input file"""
    
    if show_ffmpeg_output:
        autoscrub.suppress_ffmpeg_output(False)
    else:
        autoscrub.suppress_ffmpeg_output(True)
    
    # check executables exist
    check_ffmpeg()
    
    # check autoscrub version
    check_for_new_autoscrub_version()
    
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    
    # run ffprobe and extract data
    ffprobe_log = autoscrub.ffprobe(input)
    duration = autoscrub.findDuration(ffprobe_log)
    samplerate = autoscrub.findSampleRate(ffprobe_log)
    loudness = autoscrub.getLoudness(input)
    
    try:
        click.echo("[ffprobe] Duration: {:.3f}s".format(duration))
    except Exception:
        click.echo("[ffprobe] Duration: unknown")
    try:
        click.echo("[ffprobe] Audio sample rate: {}Hz".format(samplerate))
    except Exception:
        click.echo("[ffprobe] Audio sample rate: unknown")
    try:
        click.echo("[ffmpeg:ebur128] Loudness: {}LUFS".format(loudness['I']))
    except Exception:
        click.echo("[ffmpeg:ebur128] Loudness: unknown")
    
@cli.command(name='identify-silences')
@click.option(*_option__silence_duration[0], **_option__silence_duration[1])
@click.option(*_option__target_threshold[0], **_option__target_threshold[1])
@click.option(*_option__show_ff_output[0],   **_option__show_ff_output[1])
@click.argument('input', type=click.Path(exists=True), metavar="input_filepath")
def get_silences(input, silence_duration, target_threshold, show_ffmpeg_output):
    """Displays a table of detected silent segments"""
    
    if show_ffmpeg_output:
        autoscrub.suppress_ffmpeg_output(False)
    else:
        autoscrub.suppress_ffmpeg_output(True)
    
    # check executables exist
    check_ffmpeg()
    
    # check autoscrub version
    check_for_new_autoscrub_version()
    
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    
    # output a message before beginning
    click.echo("[autoscub:info] Scanning for silent segments...")
    
    silences = autoscrub.getSilences(input, target_threshold, silence_duration, save_silences=False)
    
    click.echo("#\tstart   \tend     \tduration")
    for i, silence in enumerate(silences):
        ti = autoscrub.seconds_to_hhmmssd(silence['silence_start'])
        tf = autoscrub.seconds_to_hhmmssd(silence['silence_end']) if 'silence_end' in silence else ''
        dt = autoscrub.seconds_to_hhmmssd(silence['silence_duration']) if 'silence_duration' in silence else ''
        click.echo("{num}\t{start}\t{end}\t{duration}".format(num=i, start=ti, end=tf, duration=dt))
    
@cli.command()
@click.option(*_option__start[0], **_option__start[1])
@click.option(*_option__stop[0],  **_option__stop[1])
@click.option(*_option__codec[0], **_option__codec[1])
@click.option(*_option__show_ff_output[0],  **_option__show_ff_output[1])
@click.option(*_option__no_prompt[0],       **_option__no_prompt[1])
@click.argument('input', type=click.Path(exists=True), metavar="input_filepath")
@click.argument('output', type=click.Path(exists=False), metavar="output_filepath")
def trim(input, output, start, stop, re_encode, show_ffmpeg_output, suppress_prompts):
    """removes unwanted content from the start and end of the input file"""
    
    if show_ffmpeg_output:
        autoscrub.suppress_ffmpeg_output(False)
    else:
        autoscrub.suppress_ffmpeg_output(True)
    
    # check executables exist
    check_ffmpeg()
    
    # check autoscrub version
    check_for_new_autoscrub_version()
    
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    output = os.path.abspath(output)
    
    # check if output file exists and prompt
    if os.path.exists(output) and not suppress_prompts:
        click.confirm('[autoscrub:warning] The specified output file [{output}] already exists. Do you want to overwrite?'.format(output=output), abort=True)
        
    if re_encode is None:
        re_encode = 'copy'
        
    autoscrub.trim(input, start, stop, output, True, re_encode)
    
# these two should be subcommands of autoprocess?
# no because that syntax is silly with click. So we'll need to define
# common parameters for autoprocess and make_filtergraph and have them at the same level (aka both decorated by @cli.command()
@cli.command(name='make-filtergraph')
@click.option(*_option__silence_duration[0], **_option__silence_duration[1])
@click.option(*_option__hasten_audio[0],     **_option__hasten_audio[1])
@click.option(*_option__target_lufs[0],      **_option__target_lufs[1])
@click.option(*_option__pan_audio[0],        **_option__pan_audio[1])
@click.option(*_option__rescale[0],          **_option__rescale[1])
@click.option(*_option__speed[0],            **_option__speed[1])
@click.option(*_option__target_threshold[0], **_option__target_threshold[1])
@click.option(*_option__silent_volume[0],    **_option__silent_volume[1])
@click.option(*_option__delay[0],            **_option__delay[1])
@click.option(*_option__show_ff_output[0],   **_option__show_ff_output[1])
@click.option(*_option__no_prompt[0],        **_option__no_prompt[1])
@click.argument('input', type=click.Path(exists=True), metavar="input_filepath")
def make_filtergraph(input, speed, rescale, target_lufs, target_threshold, pan_audio, hasten_audio, silence_duration, delay, silent_volume, show_ffmpeg_output, suppress_prompts):
    """Generates a filter-graph file for use with ffmpeg. 
    
    \b
    This command is useful if you want to manually edit the filter-graph file before processing your video."""
    
    if show_ffmpeg_output:
        autoscrub.suppress_ffmpeg_output(False)
    else:
        autoscrub.suppress_ffmpeg_output(True)
    
    # check executables exist
    check_ffmpeg()
    
    # check autoscrub version
    check_for_new_autoscrub_version()
    
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    
    # ensure that there will always be some part of a silent segment that experiences a speedup
    if not (2*delay < silence_duration):
        click.echo("[autoscrub:error] The value for delay must be less than half of the silence_duration specified")
        return
        
    # determine the path of the filter graph file based on the name of the input file
    folder, filename = os.path.split(input)
    filter_graph_path = os.path.join(folder, '.'.join(filename.split('.')[:-1])+'.filter-graph')
    
    # check if output file exists and prompt
    if os.path.exists(filter_graph_path) and not suppress_prompts:
        click.confirm('[autoscrub:warning] The specified filtergraph output file [{output}] already exists. Do you want to overwrite?'.format(output=filter_graph_path), abort=True)
    
    # adjust hasten_audio if 'trunc'
    if hasten_audio == 'trunc':
        hasten_audio = None
    
    create_filtergraph(input, filter_graph_path, speed, rescale, target_lufs, target_threshold, pan_audio, hasten_audio, silence_duration, delay, silent_volume, suppress_prompts)
    
@cli.command(name='process-filtergraph')
@click.option(*_option__show_ff_output[0],  **_option__show_ff_output[1])
@click.option(*_option__no_prompt[0],       **_option__no_prompt[1])
@click.argument('input', type=click.Path(exists=True), metavar="input_filepath")
@click.argument('output', type=click.Path(exists=False), metavar="output_filepath")
def use_filtergraph(input, output, show_ffmpeg_output, suppress_prompts):
    """Processes a video file using the filter-graph file created by the autoscrub make-filtergraph command"""
    
    if show_ffmpeg_output:
        autoscrub.suppress_ffmpeg_output(False)
    else:
        autoscrub.suppress_ffmpeg_output(True)
    
    # check executables exist
    check_ffmpeg()
    
    # check autoscrub version
    check_for_new_autoscrub_version()
    
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    output = os.path.abspath(output)
    
    # determine the path of the filter script file based on the name of the input file
    folder, filename = os.path.split(input)
    filter_graph_path = os.path.join(folder, '.'.join(filename.split('.')[:-1])+'.filter-graph')
    
    if not os.path.exists(filter_graph_path):
        raise Exception('[autoscrub:error] Could not find filter-graph file for the specified input video (if you are unsure of what a filter-graph file is, consider using "autoscrub autoprocess"). Ensure that {path} exists. This file can be generated by using "autoscrub make-filtergraph".')
    
    # check if output file exists and prompt
    if os.path.exists(output) and not suppress_prompts:
        click.confirm('[autoscrub:warning] The specified output file [{output}] already exists. Do you want to overrite?'.format(output=output), abort=True)
    
    # Process the video file using ffmpeg and the filtergraph
    result = autoscrub.ffmpegComplexFilter(input, filter_graph_path, output, run_command=True, overwrite=True)
    
    
if __name__ == "__main__":
    cli(prog_name='autoscrub')