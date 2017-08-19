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

import click
import autoscrub
import tempfile
import os
import subprocess

def check_ffmpeg():
    # check ffmpeg exists
    try:
        subprocess.check_output("ffmpeg -L", stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, WindowsError):
        click.echo("Could not find ffmpeg executable. Check that ffmpeg is in the local folder or your system PATH and that you can run 'ffmpeg -L' from the command line.")
        raise click.Abort()
        
    # check ffprobe exists
    try:
        subprocess.check_output("ffprobe -L", stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, WindowsError):
        click.echo("Could not find ffprobe executable. Check that ffprobe is in the local folder or your system PATH and that you can run 'ffprobe -L' from the command line.")
        raise click.Abort()

def format_nice_time(t_in_seconds):
    t_in_seconds = float(t_in_seconds)
    
    # handle negative time
    s = ''
    if t_in_seconds < 0:
        s = '-'
        t_in_seconds *= -1

    hours, remainder = divmod(t_in_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    s += '{:02d}:{:02d}:{:06.3f}'.format(int(hours), int(minutes), seconds)
    return s

def make_click_dict(*args, **kwargs):    
    return (args, kwargs)

_option__silence_duration = make_click_dict('--silence-duration', '-d', default=2.0, type=float, help='The minimum duration of continuous silence (in seconds) required to trigger speed up of that segment.', show_default=True)
_option__hasten_audio = make_click_dict('--hasten-audio', '-h', default='tempo', type=click.Choice(['trunc', 'pitch', 'tempo']), help="The method of handling audio during the speed up of silent segments.", show_default=True)
_option__target_lufs = make_click_dict('--target-lufs', '-l', default=-18.0, type=float, help='The target LUFS for the output audio', show_default=True)
_option__pan_audio = make_click_dict('--pan-audio', '-p', type=click.Choice(['left', 'right']), help="Copies the specified audio channel (left|right) to both audio channels.", show_default=True)
_option__rescale = make_click_dict('--rescale', '-r', nargs=2, type=int, metavar="WIDTH HEIGHT", help='rescale the input video file to the resolution specified  [usage: -r 1920 1080]')
_option__speed = make_click_dict('--speed', '-s', default=8, type=float, help='The factor by which to speed up the video during silent segments', show_default=True)
_option__target_threshold = make_click_dict('--target-threshold', '-t', default=-18.0, type=float, help='The audio threshold for detecting silent segments in dB', show_default=True)
_option__silent_volume = make_click_dict('--silent-volume', '-v', default=1.0, type=float, help='The factor to scale the audio volume during silent segments', show_default=True)
_option__delay = make_click_dict('--delay', default=0.25, type=float, help='The length of time (in seconds) to delay the start of the speed up of a silent segment. This also ends the speedup early, by the same amount, and must satisfy the condition 2*delay < silence-duration', show_default=True)
_option__start = make_click_dict('--start', default=0, type=float, help='Content before this time is removed', show_default=True)
_option__stop = make_click_dict('--stop', type=float, help='Content after this time is removed', show_default=True)
_option__codec = make_click_dict('--re-encode', nargs=1, type=str, metavar='CODEC', help='Re-encode the file with the codec specified', show_default=True)

def create_filtergraph(input, filter_graph_path, speed, rescale, target_lufs, target_threshold, pan_audio, hasten_audio, silence_duration, delay, silent_volume):    
    folder, filename = os.path.split(input)
    click.echo('============ Processing %s ==========' % filename)
    
    # determine audio sample rate
    click.echo('\nGetting audio sample rate...')
    input_sample_rate = autoscrub.getSampleRate(input)
    try:
        click.echo("Measured sample rate = %d Hz"%input_sample_rate)
    except Exception:
        click.echo("Could not determine the audio samplerate of your file")
        raise click.abort()
        
    click.echo('\nChecking loudness of file...')
    loudness = autoscrub.getLoudness(input)
    try:
        input_lufs = loudness['I']
    except Exception:
        click.echo("Could not determine the loudness of your file")
        raise click.abort()
    
    # Calculate gain
    gain = target_lufs - input_lufs
    
    # Apply gain correction if pan_audio is used (when one stereo channel is silent)
    if pan_audio in ['left', 'right']:
        click.echo('Reducing gain by 3dB due to audio pan')
        gain -= 3
    
    # calculate input_threshold
    input_threshold_dB = input_lufs + target_threshold - target_lufs
    
    # print audio data to terminal
    click.echo('Measured loudness = %.1f LUFS; Silence threshold = %.1f dB; Gain to apply = %.1f dB' % (input_lufs, input_threshold_dB, gain))

    # find silent segments
    click.echo('\nSearching for silence...')
    silences = autoscrub.getSilences(input, input_threshold_dB, silence_duration, False)
    if silences:
        durations = [s['silence_duration'] for s in silences if 'silence_duration' in s]
        mean_duration = sum(durations)/len(durations)
        click.echo('Found %i silences of average duration %.1f seconds.' % (len(silences), mean_duration))
    else:
        click.confirm("No silences found. Do you wish to continue?", abort=True)

    # Generate the filtergraph
    click.echo('\nGenerating ffmpeg filter_complex script...')
    autoscrub.writeFilterGraph(filter_graph_path, silences, factor=speed, audio_rate=input_sample_rate, pan_audio=pan_audio, gain=gain, rescale=rescale, hasten_audio=hasten_audio, delay=delay, silent_volume=silent_volume)

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
@click.option(*_option__silence_duration[0], **_option__silence_duration[1])
@click.option(*_option__hasten_audio[0],     **_option__hasten_audio[1])
@click.option(*_option__target_lufs[0],      **_option__target_lufs[1])
@click.option(*_option__pan_audio[0],        **_option__pan_audio[1])
@click.option(*_option__rescale[0],          **_option__rescale[1])
@click.option(*_option__speed[0],            **_option__speed[1])
@click.option(*_option__target_threshold[0], **_option__target_threshold[1])
@click.option(*_option__silent_volume[0],    **_option__silent_volume[1])
@click.option(*_option__delay[0],            **_option__delay[1])
@click.option('--debug', help="Retains the generated filtergraph file for inspection", is_flag=True)
@click.argument('input', type=click.Path(exists=True), metavar="input_filepath")
@click.argument('output', type=click.Path(exists=False), metavar="output_filepath")
def autoprocess(input, output, speed, rescale, target_lufs, target_threshold, pan_audio, hasten_audio, silence_duration, delay, silent_volume, debug):
    """automatically process the input video and write to the specified output file"""
    
    # check executables exist
    check_ffmpeg()
    
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    output = os.path.abspath(output)
    
    # ensure that there will always be some part of a silent segment that experiences a speedup
    if not (2*delay < silence_duration):
        click.echo("ERROR: The value for delay must be less than half of the silence_duration specified")
        return
    
    # check if output file exists and prompt
    if os.path.exists(output):
        click.confirm('The specified output file [{output}] already exists. Do you want to overrite?'.format(output=output), abort=True)
    
    # adjust hasten_audio if 'trunc'
    if hasten_audio == 'trunc':
        hasten_audio = None
        
    # Make a temporary file for the filterscript
    handle, filter_graph_path = tempfile.mkstemp()
    # Python returns an open handle which we don't want, so close it
    os.close(handle)

    create_filtergraph(input, filter_graph_path, speed, rescale, target_lufs, target_threshold, pan_audio, hasten_audio, silence_duration, delay, silent_volume)
    
    # Process the video file using ffmpeg and the filtergraph
    result = autoscrub.ffmpegComplexFilter(input, filter_graph_path, output, run_command=True, overwrite=True)
        
    # delete the filtergraph temporary file unless we are debugging
    if not debug:
        # delete the temporary file
        os.remove(filter_graph_path)
    else:
        click.echo('For debugging purposes, the filter script is located at: {filter_graph_path}'.format(filter_graph_path=filter_graph_path))

@cli.command(name='loudness-adjust')
@click.option(*_option__target_lufs[0], **_option__target_lufs[1])
@click.argument('input', type=click.Path(exists=True), metavar="input_filepath")
@click.argument('output', type=click.Path(exists=False), metavar="output_filepath")
def match_loudness(input, output, target_lufs):
    """Adjusts the loudness of the input file"""
    
    # check executables exist
    check_ffmpeg()
    
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    output = os.path.abspath(output)
    
    autoscrub.matchLoudness(input, target_lufs, output)
    
@cli.command(name='display-video-properties')
@click.argument('input', type=click.Path(exists=True), metavar="input_filepath")
def get_properties(input):
    """Displays properties about the input file"""
    
    # check executables exist
    check_ffmpeg()
    
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    
    # run ffprobe and extract data
    ffprobe_log = autoscrub.ffprobe(input)
    duration = autoscrub.findDuration(ffprobe_log)
    samplerate = autoscrub.findSampleRate(ffprobe_log)
    loudness = autoscrub.getLoudness(input)
    
    try:
        click.echo("Duration: {:.3f}s".format(duration))
    except Exception:
        click.echo("Duration: unknown")
    try:
        click.echo("Audio sample rate: {}Hz".format(samplerate))
    except Exception:
        click.echo("Audio sample rate: unknown")
    try:
        click.echo("Loudness: {}LUFS".format(loudness['I']))
    except Exception:
        click.echo("Loudness: unknown")
    
@cli.command(name='identify-silences')
@click.option(*_option__silence_duration[0], **_option__silence_duration[1])
@click.option(*_option__target_threshold[0], **_option__target_threshold[1])
@click.argument('input', type=click.Path(exists=True), metavar="input_filepath")
def get_silences(input, silence_duration, target_threshold):
    """Displays a table of detected silent segments"""
    
    # check executables exist
    check_ffmpeg()
    
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    
    # output a message before beginning
    click.echo("Scanning for silent segments (this may take some time)...")
    
    silences = autoscrub.getSilences(input, target_threshold, silence_duration, save_silences=False)
    
    click.echo("#\tstart   \tend     \tduration")
    for i, silence in enumerate(silences):
        ti = format_nice_time(silence['silence_start'])
        tf = format_nice_time(silence['silence_end']) if 'silence_end' in silence else ''
        dt = format_nice_time(silence['silence_duration']) if 'silence_duration' in silence else ''
        click.echo("{num}\t{start}\t{end}\t{duration}".format(num=i, start=ti, end=tf, duration=dt))
    
@cli.command()
@click.option(*_option__start[0], **_option__start[1])
@click.option(*_option__stop[0],  **_option__stop[1])
@click.option(*_option__codec[0], **_option__codec[1])
@click.argument('input', type=click.Path(exists=True), metavar="input_filepath")
@click.argument('output', type=click.Path(exists=False), metavar="output_filepath")
def trim(input, output, start, stop, re_encode):
    """removes unwanted content from the start and end of the input file"""
    
    # check executables exist
    check_ffmpeg()
    
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    output = os.path.abspath(output)
    
    # check if output file exists and prompt
    if os.path.exists(output):
        click.confirm('The specified output file [{output}] already exists. Do you want to overrite?'.format(output=output), abort=True)
        
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
@click.argument('input', type=click.Path(exists=True), metavar="input_filepath")
def make_filtergraph(input, speed, rescale, target_lufs, target_threshold, pan_audio, hasten_audio, silence_duration, delay, silent_volume):
    """Generates a filter-graph file for use with ffmpeg. 
    
    \b
    This command is useful if you want to manually edit the filter-graph file before processing your video."""
    
    # check executables exist
    check_ffmpeg()
    
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    
    # ensure that there will always be some part of a silent segment that experiences a speedup
    if not (2*delay < silence_duration):
        click.echo("ERROR: The value for delay must be less than half of the silence_duration specified")
        return
        
    # determine the path of the filter graph file based on the name of the input file
    folder, filename = os.path.split(input)
    filter_graph_path = os.path.join(folder, '.'.join(filename.split('.')[:-1])+'.filter-graph')
    
    # check if output file exists and prompt
    if os.path.exists(filter_graph_path):
        click.confirm('The specified filtergraph output file [{output}] already exists. Do you want to overrite?'.format(output=filter_graph_path), abort=True)
    
    # adjust hasten_audio if 'trunc'
    if hasten_audio == 'trunc':
        hasten_audio = None
    
    create_filtergraph(input, filter_graph_path, speed, rescale, target_lufs, target_threshold, pan_audio, hasten_audio, silence_duration, delay, silent_volume)
    
@cli.command(name='process-filtergraph')
@click.argument('input', type=click.Path(exists=True), metavar="input_filepath")
@click.argument('output', type=click.Path(exists=False), metavar="output_filepath")
def use_filtergraph(input, output):
    """Processes a video file using the filter-graph file created by the autoscrub make-filtergraph command"""
    
    # check executables exist
    check_ffmpeg()
    
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    output = os.path.abspath(output)
    
    # determine the path of the filter script file based on the name of the input file
    folder, filename = os.path.split(input)
    filter_graph_path = os.path.join(folder, '.'.join(filename.split('.')[:-1])+'.filter-graph')
    
    if not os.path.exists(filter_graph_path):
        raise Exception('Could not fnd filter-graph file for the specified input video (if you are unsure of what a filter-graph file is, consider using "autoscrub autoprocess"). Ensure that {path} exists. This file can be generated by using "autoscrub make-filtergraph".')
    
    # check if output file exists and prompt
    if os.path.exists(output):
        click.confirm('The specified output file [{output}] already exists. Do you want to overrite?'.format(output=output), abort=True)
    
    # Process the video file using ffmpeg and the filtergraph
    result = autoscrub.ffmpegComplexFilter(input, filter_graph_path, output, run_command=True, overwrite=True)
    
    
if __name__ == "__main__":
    cli(prog_name='autoscrub')