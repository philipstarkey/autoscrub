import os
import re
from subprocess import Popen, call, PIPE

NUL = os.devnull

def hhmmssd_to_seconds(s):
    """Convert a '[hh:]mm:ss[.d]' string to seconds. The hours and decimal seconds are optional."""
    assert isinstance(s, str)
    return reduce(lambda t60, x: t60 * 60 + x, map(float, s.split(':')))


def ffprobe(filename):
    """Runs ffprobe on filename and returns the log output from stderr."""
    command = 'ffprobe -i "%s"' % filename
    p = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    return stderr


def findDuration(log_output):
    """Finds the duration in seconds from ffprobe log_output."""
    matches = re.findall('Duration: +([\d\:\.]+)', log_output)
    if matches:
        duration = matches[0]
        seconds = hhmmssd_to_seconds(duration)
        return seconds
    else:
        return None


def getDuration(filename):
    """Runs ffprobe on filename and extracts duration in seconds."""
    ffprobe_log = ffprobe(filename)
    return findDuration(ffprobe_log)


def findSampleRate(log_output):
    """Finds the audio sample rate in Hz from ffprobe log_output."""
    matches = re.findall(', ([\d]+) Hz', log_output)
    if matches:
        return int(matches[-1])
    else:
        return None


def getSampleRate(filename):
    """Runs ffprobe on filename and extracts audio sample rate in Hz."""
    ffprobe_log = ffprobe(filename)
    return findDuration(ffprobe_log)


def findSilences(log_output):
    """Extract silences from ffmpeg log_output when using the silencedetect filter."""
    matches = re.findall(r"(silence_[a-z]+): ([\-\d\.]+)", log_output)
    matches = [(k, float(v)) for (k, v) in matches]
    if matches:
        return [dict(matches[i:i + 3]) for i in xrange(0, len(matches), 3)]
    else:
        return None


def getSilences(filename, input_threshold_dB=-18.0, silence_duration=2.0, save_silences=True):
    """Runs the ffmpeg filter silencedetect with specified settings and returns a list
    of silence dictionaries, with keys:

    silence_start: the timestamp of the detected silent interval in seconds
    silence_end:   the timestamp of the detected silent interval in seconds
    silence_duration:  duration of the silent interval in seconds

    Keyword arguments:
    input_threshold -- instantaneous level (in dB) to detect silences with (default -18)
    silence_duration -- seconds for which level mustn't exceed threshold to declare silence (default 2)
    save_silences -- print the above timestamps to CSV file (default = True)
    """
    command = 'ffmpeg -i "%s" -af silencedetect=n=%.1fdB:d=%s -f null %s' % (filename, input_threshold_dB, silence_duration, NUL)
    p = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    silences = findSilences(stderr)
    if save_silences:
        filename_prefix, file_extension = os.path.splitext(filename)
        silence_path = '%s_silences.csv' % filename_prefix
        with open(silence_path, 'w') as f:
            for silence in silences:
                ti = silence['silence_start']
                tf = silence['silence_end'] if 'silence_end' in silence else ''
                dt = silence['silence_duration'] if 'silence_duration' in silence else ''
                f.write('%s,%s,%s\n' % (ti, tf, dt))
    return silences


def findLoudness(log_output):
    """Extract loudness (key, value) pairs from ffmpeg log_output when using the ebur128 filter."""
    log_split = re.split(r"Parsed_ebur128.+\r\n", log_output)
    if len(log_split) > 1:
        summary = log_split[-1]
        matches = re.findall(r"([A-Z][A-Za-z ]*): +([\-\d\.]+)", summary)
        if matches:
            return dict([(k, float(v)) for (k, v) in matches])
    return None


def getLoudness(filename):
    """Runs the ffmpeg ebur128 filter on filename and returns a loudness dictionary with keys:

    I:   integrated loudness in dBLUFS
    LRA: loudness range in dBLUFS
    LRA high
    LRA low
    Threshold         
    """
    command = 'ffmpeg -i "%s" -c:v copy -af ebur128 -f null %s' % (filename, NUL)
    p = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    return findLoudness(stderr)


def trim(input_path, tstart=0, tstop=None, output_path=None, overwrite=None):
    """Extract contents of input_path between tstart and tstop.
    
    Keyword arguments:
    tstart -- A integer/float in seconds, or a '[hh:]mm:ss[.d]' string (default 0)
    tstop -- A integer/float in seconds, or a '[hh:]mm:ss[.d]' string (default None)
    output_path -- Defaults to appending '_trimmed' to input_path
    overwrite -- Optionally specify addition of -y or -n flag to ffmpeg
    """
    folder, filename = os.path.split(input_path)
    if not isinstance(tstart, str):
        tstart = '%.4f' % tstart
    if tstop and not isinstance(tstop, str):
        tstop = '%.4f' % tstop
    command = ['ffmpeg', '-i', filename]
    if hhmmssd_to_seconds(tstart) > 0:
        command += ['-ss', tstart]
    if tstop is not None:
        command += ['-to', tstop]
    command += ['-c', 'copy']
    if overwrite is not None:
        command.append('-y' if overwrite==True else '-n')
    if output_path is None:
        filename_prefix, file_extension = os.path.splitext(filename)
        output_path = filename_prefix + '_trimmed' + file_extension
    command.append(output_path)
    try:
        p = Popen(command, cwd=folder if folder else '.')
        stdout, stderr = p.communicate()
        return os.path.join(folder, output_path)
    except Exception, e:
        print(e)
        return None 


def trimSegments(input_path, trimpts, output_path=None, overwrite=None):
    """Extract segments of a file using a list of (tstart, tstop) tuples.
    Each segment is saved as a file of the same type as the original, in a
    folder called temp unless output_path is specified.
    See docstring for trim for information on supported timestamp formats.
    """
    folder, filename = os.path.split(input_path)
    filename_prefix, file_extension = os.path.splitext(filename)
    temp_folder = output_path if output_path else os.path.join(folder, 'temp')
    if not os.path.exists(temp_folder):
        os.mkir(temp_folder)
    segment_paths = []
    for i, (tstart, tstop) in enumerate(segments):
        segment_file = filename_prefix + '_%03i' % i + file_extension
        segment_path = os.path.join(temp_folder, segment_file)
        trim(input_path, tstart, tstop, outfile, overwrite)
        print('Trimmed segment %03i of %s (from %s to %s).' % (i, filename, tstart, tstop))
        segment_paths.append(segment_path)
    return segment_paths


def generateFilterGraph(silences, factor, delay=0.25, rescale=True, pan_audio='left', gain=0, audio_rate=44100, hasten_audio=False):
    """Generate a complex filter (filtergraph string) for processing with the filter_complex argument of ffmpeg.

    silences -- A list of silence dictionaries generated from getSilences function
    factor -- to speed up or slow down video during (a subset of) each silent interval
    delay -- in seconds to omit from the detected silent intervals when making the speed change (defaut 0.25)
    rescale -- Scale and pad the video (pillar- or letter-box as required) for 1920 x 1080 display (default True)
    pan_audio -- 'left', 'right', or None/False specify whether to duplicate one stereo channel of input audio stream (defult 'left')
    gain -- in dB to apply when pan_audio is 'left' or 'right'
    audio_rate -- Sample rate of audio input (in Hz, default 44100) used in asetrate/aresample filters when hasten_audio=True
    hasten_audio -- Speed up audio during silent segment with asetrate and aresample filters (increases pitch)
    """
    # Omit silences at the start/end of the file
    if 'silence_end' not in silences[-1]:
        silences = silences[:-1]
    if silences[0]['silence_start'] <= 0.:
        silences = silences[1:]    

    # Timestamp of end of most recently processed segment
    tf_last = 0

    # Container for calls to trim (video) and atrim (audio) filters 
    vstrings = []
    astrings = []

    # String to call concat filter with
    concat_string = ''

    # Number of silences to process
    n = len(silences)

    # Number of segments (only because any beginning/end silences are gone)
    n_segs = 2*n + 1
    
    # Generate 4 x filtergraph lines for each silence
    for i, s in enumerate(silences):
        # Number segments in filtergraph from 1 to n_segs
        i += 1

        # Cast end of last segment to string
        t0 = '%.4f' % tf_last

        # Begin trim (& speedup) delay seconds after silence_start
        ti = '%.4f' % (s['silence_start'] + delay)

        # End trim (& speedup) delay seconds before silence_end
        tf = '%.4f' % (s['silence_end'] - delay)

        # Predicted duration of sped up segment based on above and factor 
        ta = '%.4f' % (s['silence_start'] + delay + (s['silence_duration'] - 2*delay)/factor)

        # Trim video before this silence (regular speed)
        vstrings.append('[0:v]trim=%s:%s,setpts=PTS-STARTPTS[v%i];' % (t0, ti, (2*i-1)))

        # Trim video during this silence and speed up using setpts
        vstrings.append('[0:v]trim=%s:%s,setpts=(PTS-STARTPTS)/%i[v%i];' % (ti, tf, factor, (2*i)))

        # Trim video before this silence (regular speed)
        astrings.append('[0:a]atrim=%s:%s,asetpts=PTS-STARTPTS[a%i];' % (t0, ti, (2*i-1)))
        if hasten_audio:
            # Speed up audio during silent segment with asetrate and aresample filters (increases pitch)
            astrings.append('[0:a]atrim=%s:%s,asetpts=PTS-STARTPTS,asetrate=%i,aresample=%i,volume=0.0[a%i];' % (ti, tf, (factor*audio_rate), audio_rate, (2*i)))
        else:
            # Use first 1/factor samples of silence for audio (no pitch increase)
            astrings.append('[0:a]atrim=%s:%s,asetpts=PTS-STARTPTS[a%i];' % (ti, ta, (2*i)))

        # Append these streams to the concat filter input
        concat_string += '[v%i][a%i][v%i][a%i]' % ((2*i-1), (2*i-1), (2*i), (2*i))
        tf_last = s['silence_end'] - delay
    
    # Trim the final segment (regular speed) without specifying the end time
    vstrings.append('[0:v]trim=start=%.4f,setpts=PTS-STARTPTS[v%i];' % (tf_last, n_segs))
    astrings.append('[0:a]atrim=start=%.4f,asetpts=PTS-STARTPTS[a%i];' % (tf_last, n_segs))
    
    # Finish the concat filter call (outputs 'vn' and 'an')
    concat_string += '[v%i][a%i]concat=n=%i:v=1:a=1[vn][an];' % (n_segs, n_segs, n_segs)
    
    # Collect lines of the filter script after the trim/atrim calls 
    tail = [concat_string]
    if rescale:
        # Scale and pad the video for 1920 x 1080 display
        tail.append('[vn]scale=w=1920:h=1080:force_original_aspect_ratio=decrease[scaled];')
        tail.append('[scaled]pad=1920:1080:(ow-iw)/2:(oh-ih)/2[v];')
    else:
        # Rename the video output of concat to 'v' for processing
        tail[-1] = concat_string[-1].replace('vn', 'v')
    if pan_audio == 'left':
        # Duplicate left channel of input on right channel of output and apply gain
        concat_string.append('[an]pan=stereo|c0=c0|c1=c0,volume=%.1fdB[a]' % gain)
    elif pan_audio == 'right':
        # Duplicate right channel of input on left channel of output and apply gain
        concat_string.append('[an]pan=stereo|c0=c1|c1=c1,volume=%.1fdB[a]' % gain)
    else:
        # Rename the audio output of concat to 'a' for processing
        concat_string[-1] = concat_string[-1].replace('an', 'a')
    if concat_string[-1].endswith(';'):
        # Remove trailing ';' in final line of filter script
        concat_string[-1] = concat_string[-1][:-1]
    return '\n'.join(vstrings + astrings + concat_string)


def writeFilterGraph(filter_script_path, silences, **kwargs):
    """Generate a complex filter script (filtergraph file) for processing with the filter_complex argument of ffmpeg.

    filter_script_path -- Path to save the filter script 
    silences -- A list of silence dictionaries generated from getSilences function
    factor -- to speed up or slow down video during (a subset of) each silent interval
    delay -- in seconds to omit from the detected silent intervals when making the speed change (defaut 0.25)
    rescale -- Scale and pad the video (pillar- or letter-box as required) for 1920 x 1080 display (default True)
    pan_audio -- 'left', 'right', or None/False specify whether to duplicate one stereo channel of input audio stream (defult 'left')
    gain -- in dB to apply when pan_audio is 'left' or 'right'
    audio_rate -- Sample rate of audio input (in Hz, default 44100) used in asetrate/aresample filters when hasten_audio=True
    hasten_audio -- Speed up audio during silent segment with asetrate and aresample filters (increases pitch)
    """
    filter_graph = generateFilterGraph(silences, **kwargs)
    with open(filter_script_path, 'w') as f:
        f.write(filter_graph)


def ffmpegComplexFilter(input_path, filter_script_path, output_path=NUL, run_command=True, overwrite=None):
    """Prepare and execute (if run_command) ffmpeg command for processing input_path with an
    ffmpeg filter_complex string (filtergraph) in filter_script_path, and save to output_path.
    As this requires re-encoding, video and audio settings are chosen to be compliant with YouTube's
    'streamable content' specifications, available at (as of April 2017):
        https://support.google.com/youtube/answer/1722171
    
    Flags:
    ======
    run_command: If False, simply prepare and return the command for debugging or later use.
    overwrite:   Optionally specify addition of -y or -n flag to ffmpeg (useful for unattended scripting).
    """
    header = 'ffmpeg -i "%s"' % filename
    youtube_video = '-c:v libx264 -crf 20 -bf 2 -flags +cgop -g 15 -pix_fmt yuv420p -movflags +faststart' # -tune stillimage
    youtube_audio = '-c:a aac -r:a 48000 -b:a 192k'
    youtube_other = '-strict -2'
    filter_command = '-filter_complex_script "%s" -map [v] -map [a]' % filter_script_path
    tail = '"%s"' % output_path
    if overwrite is not None:
        tail = ('-y ' + tail) if overwrite==True else ('-n ' + tail)
    command_list = [header, youtube_video, youtube_audio, youtube_other, filter_command, tail]
    command = ' '.join(command_list)
    print(command)
    if run_command:
        p = Popen(command)
        stdout, stderr = p.communicate()
        return output_path
    else:
        return command


if __name__ == '__main__':
    # Loudness normalisation
    target_lufs = -18.0

    # Silence detection
    target_threshold_dB = -18.0     # should be close or equal to above
    silence_duration = 2.0          # should be greater than or equal to 2 (seconds)

    # Filepaths
    # input_path = 'lecture.mp4'
    # input_path = "C:\\Users\\russ\\Documents\\Teaching\\PHS3051\\LectureRecordings\\2017\\Lecture2\\ModernOpticsLecture2.trec"
    # input_path = "C:\\Users\\russ\\Documents\\Teaching\\PHS3051\\LectureRecordings\\2017\\Lecture3\\ModernOpticsLecture3.trec"
    input_path = "C:\\Users\\rander\\Documents\\Teaching\\PHS3051Optics\\LectureRecordings\\2017\\Lecture4\\ModernOpticsLecture4.trec"
    suffix = 'scrub'

    # Flags
    overwrite = True
    run_command = False
    rescale = True
    # pan_audio = False
    pan_audio = 'left'
    factor = 8
    
    # Implementation
    folder, filename = os.path.split(input_path)
    output_path = '%s_%s.mp4' % (filename_prefix, suffix)
    if folder is not '':
        os.chdir(folder)
    if not os.path.exists(filter_script_path) or overwrite:
        print('============ Processing %s ==========' % filename)
        print('\nGetting audio sample rate...')
        input_sample_rate = getSampleRate(filename)

        print('\nChecking loudness of file...')
        loudness = getLoudness(filename)
        input_lufs = loudness['I']
        gain = target_lufs - input_lufs
        # Apply gain correction if pan_audio is used (when one stereo channel is silent)
        if pan_audio:
            gain -= 3
        input_threshold_dB = input_lufs + target_threshold_dB - target_lufs
        print('Measured loudness = %.1f LUFS; Silence threshold = %.1f dB; Gain to apply = %.1f dB' % (input_lufs, input_threshold_dB, gain))

        print('\nSearching for silence...')
        silences = getSilences(filename, input_threshold_dB, silence_duration)
        durations = [s['silence_duration'] for s in silences if 'silence_duration' in s]
        mean_duration = sum(durations)/len(durations)
        print('Found %i silences of average duration %.1f seconds.' % (len(silences), mean_duration))

        print('\nGenerating ffmpeg filter_complex script...')
        writeFilterGraph(filter_script_path, silences, factor=factor, audio_rate=input_sample_rate, pan_audio=pan_audio, gain=gain, rescale=rescale)
    else:
        print('\nUsing existing filter_complex script....')   
    
    print('\nRequired ffmpeg command: \n' + command)
    result = ffmpegComplexFilter(input_path, filter_script_path, output_path, run_command, overwrite)