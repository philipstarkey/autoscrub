import click
import autoscrub
import tempfile
import os

def make_click_dict(*args, **kwargs):    
    return (args, kwargs)

_option__target_lufs = make_click_dict('--target-lufs', '-l', default=-18.0, type=float, help='The target LUFS for the output audio', show_default=True)


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
@click.option('--silence-duration', '-d', default=2.0, type=float, help='The minimum duration of continuous silence (in seconds) required to trigger speed up of that segment.', show_default=True)
@click.option('--hasten-audio', '-h', default='tempo', type=click.Choice(['trunc', 'pitch', 'tempo']), help="The method of handling audio during the speed up of silent segments.", show_default=True)
@click.option('--target-lufs', '-l', default=-18.0, type=float, help='The target LUFS for the output audio', show_default=True)
# @click.option(*_option__target_lufs[0], **_option__target_lufs[1])
@click.option('--pan-audio', '-p', type=click.Choice(['left', 'right']), help="Copies the specified audio channel (left|right) to both audio channels.", show_default=True)
@click.option('--rescale', '-r', nargs=2, type=int, metavar="WIDTH HEIGHT", help='rescale the input video file to the resolution specified  [usage: -r 1920 1080]')
@click.option('--speed', '-s', default=8, type=float, help='The factor by which to speed up the video during silent segments', show_default=True)
@click.option('--target-threshold', '-t', default=-18.0, type=float, help='The audio threshold for detecting silent segments in dB', show_default=True)
@click.option('--silent-volume', '-v', default=1.0, type=float, help='The factor to scale the audio volume during silent segments', show_default=True)
@click.option('--delay', default=0.25, type=float, help='The length of time (in seconds) to delay the start of the speed up of a silent segment. This also ends the speedup early, by the same amount, and must satisfy the condition 2*delay < silence-duration', show_default=True)
@click.option('--debug', help="Retains the generated filtergraph file for inspection", is_flag=True)
@click.argument('input', type=click.Path(exists=True))
@click.argument('output', type=click.Path(exists=False))
def autoprocess(input, output, speed, rescale, target_lufs, target_threshold, pan_audio, hasten_audio, silence_duration, delay, silent_volume, debug):
    """automatically process the input video and write to the specified output file"""
    
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
    
    folder, filename = os.path.split(input)
    
    # Make a temporary file for the filterscript
    handle, filter_script_path = tempfile.mkstemp()
    # Python returns an open handle which we don't want, so close it
    os.close(handle)

    click.echo('============ Processing %s ==========' % filename)
    
    # determine audio sample rate
    click.echo('\nGetting audio sample rate...')
    input_sample_rate = autoscrub.getSampleRate(input)
    click.echo("Measured sample rate = %d Hz"%input_sample_rate)

    click.echo('\nChecking loudness of file...')
    loudness = autoscrub.getLoudness(input)
    input_lufs = loudness['I']
    
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
    silences = autoscrub.getSilences(input, input_threshold_dB, silence_duration)
    durations = [s['silence_duration'] for s in silences if 'silence_duration' in s]
    mean_duration = sum(durations)/len(durations)
    click.echo('Found %i silences of average duration %.1f seconds.' % (len(silences), mean_duration))

    # Generate the filtergraph
    click.echo('\nGenerating ffmpeg filter_complex script...')
    autoscrub.writeFilterGraph(filter_script_path, silences, factor=speed, audio_rate=input_sample_rate, pan_audio=pan_audio, gain=gain, rescale=rescale, hasten_audio=hasten_audio, delay=delay, silent_volume=silent_volume)
    
    # Process the video file using ffmpeg and the filtergraph
    result = autoscrub.ffmpegComplexFilter(input, filter_script_path, output, run_command=True, overwrite=True)
        
    # delete the filtergraph temporary file unless we are debugging
    if not debug:
        # delete the temporary file
        os.remove(filter_script_path)
    else:
        click.echo('For debugging purposes, the filter script is located at: {filter_script}'.format(filter_script=filter_script_path))

@cli.command(name='loudness-adjust')
@click.option(*_option__target_lufs[0], **_option__target_lufs[1])
@click.argument('input', type=click.Path(exists=True))
@click.argument('output', type=click.Path(exists=False))
def match_loudness(input, output, target_lufs):
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    output = os.path.abspath(output)
    
    autoscrub.matchLoudness(input, target_lufs, output)
    
@cli.command(name='display-video-properties')
@click.argument('input', type=click.Path(exists=True))
def get_properties(input):
    # convert input/output paths to absolute paths
    input = os.path.abspath(input)
    
    # run ffprobe and extract data
    ffprobe_log = autoscrub.ffprobe(input)
    duration = autoscrub.findDuration(ffprobe_log)
    samplerate = autoscrub.findSampleRate(ffprobe_log)
    loudness = autoscrub.getLoudness(input)
    
    click.echo("Duration: {:.3f}s".format(duration))
    click.echo("Audio sample rate: {}Hz".format(samplerate))
    click.echo("Loudness: {}LUFS".format(loudness['I']))
    
@cli.command(name='indentify-silences')
def get_silences():
    pass
    
@cli.command()
def trim():
    pass
    
# these two should be subcommands of autoprocess?
# no because that syntax is silly with click. So we'll need to define
# common parameters for autoprocess and make_filtergraph and have them at the same level (aka both decorated by @cli.command()
@cli.command(name='make-filtergraph')
def make_filtergraph():
    pass
    
@cli.command(name='process-filtergraph')
def use_filtergraph():
    pass
    
    
if __name__ == "__main__":
    cli(prog_name='autoscrub')