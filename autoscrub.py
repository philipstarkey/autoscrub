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


def ffmpeg(filename, args=[], output_path=None, output_type=None):
    """Runs ffmpeg on filename with the specified args."""
    command = ['ffmpeg', '-i', '"%s"' % filename.replace('\\', '/')]
    command += args
    if output_path is None:
        filename_prefix, file_extension = os.path.splitext(filename)
        if output_type is not None:
            file_extension = output_type
        output_path = filename_prefix + '_processed' + file_extension
    command += ['"%s"' % output_path.replace('\\', '/')]
    print(' '.join(command))
    p = Popen(command)
    stdout, stderr = p.communicate()
    return output_path


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


def trim(input_path, tstart=0, tstop=None, output_path=None, overwrite=None, codec='copy', output_type=None):
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
    if codec == 'copy':
        command += ['-c', 'copy']
    else:
        command += codec
    if overwrite is not None:
        command.append('-y' if overwrite==True else '-n')
    if output_path is None:
        filename_prefix, file_extension = os.path.splitext(filename)
        if output_type is not None:
            file_extension = output_type
        output_path = filename_prefix + '_trimmed' + file_extension
    command.append(output_path)
    try:
        p = Popen(command, cwd=folder if folder else '.')
        stdout, stderr = p.communicate()
        return os.path.join(folder, output_path)
    except Exception, e:
        print(e)
        return None 


def trimSegments(input_path, trimpts, output_path=None, output_type=None, **kwargs):
    """Extract segments of a file using a list of (tstart, tstop) tuples.
    Each segment is saved as a file of the same type as the original, in a
    folder called temp unless output_path is specified.
    See docstring for trim for information on supported timestamp formats.
    """
    folder, filename = os.path.split(input_path)
    filename_prefix, file_extension = os.path.splitext(filename)
    if output_type is not None:
        file_extension = output_type
    temp_folder = output_path if output_path else os.path.join(folder, 'temp')
    if not os.path.exists(temp_folder):
        os.mkdir(temp_folder)
    segment_paths = []
    for i, (tstart, tstop) in enumerate(trimpts):
        segment_file = filename_prefix + '_%03i' % i + file_extension
        segment_path = os.path.join(temp_folder, segment_file)
        trim(input_path, tstart, tstop, segment_path, **kwargs)
        print('Trimmed segment %03i of %s (from %s to %s).' % (i, filename, tstart, tstop))
        segment_paths.append(segment_path)
    return segment_paths


def concatFileList(concat_path, output_path, overwrite=None):
    """Take a file list for the ffmpeg concat demuxer and save to output_path.
    The concat file must contain lines of the form:

    file '/path/to/file1'
    file '/path/to/file2'
    file '/path/to/file3'  

    This avoids a re-encode and can be used with formats that do not support file level concatenation.
    """
    command = 'ffmpeg -safe 0 -f concat -i "%s" -c copy' % concat_path
    if overwrite is not None:
        command += ' -y ' if overwrite==True else ' -n '
    command += ' "%s"' % output_path
    print(command)
    try:
        p = Popen(command)
        stdout, stderr = p.communicate()
        return output_path
    except Exception, e:
        print(e)
        return None         


def concatSegments(segment_paths, output_path=None, overwrite=None):
    """Concatenate a list of inputs (specified by path) using the ffmpeg conact demuxer.
    A concat file will be created of the form 

    file '/path/to/file1'
    file '/path/to/file2'
    file '/path/to/file3'  

    This avoids a re-encode and can be used with formats that do not support file level concatenation.
    """
    folder, first_path = os.path.split(segment_paths[0])
    first_prefix, file_extension = os.path.splitext(first_path)
    filename_prefix = '_'.join(first_prefix.split('_')[:-1])
    concat_file = ''.join(filename_prefix) + '_concat.txt'
    concat_path = os.path.join(folder, concat_file)
    if not os.path.exists(concat_path) or overwrite:
        with open(concat_path, 'w') as f:
            f.write('\n'.join(["file '%s'" % path for path in segment_paths]))
    if not output_path:
        output_path = os.path.join(folder, filename_prefix + '_concat' + file_extension)
    concatFileList(concat_path, output_path, overwrite)


def silenceFilterGraph(silences, factor, delay=0.25, audio_rate=44100, hasten_audio=False,
                       v_in='[0:v]', a_in='[0:a]', v_out='[v]', a_out='[a]'):
    """Generate a filtergraph string (for processing with the -filter_complex
    flag of ffmpeg) using the trim and atrim filters to speed up periods in the
    video designated by a list of silences (dictonaries with keys:

    silence_start: the timestamp of the detected silent interval in seconds
    silence_end:   the timestamp of the detected silent interval in seconds
    silence_duration:  duration of the silent interval in seconds
    
    Arguments:
    silences -- A list of silence dictionaries generated from getSilences
    factor -- to speed up video during (a subset of) each silent interval

    Keyword arguments:
    delay -- to omit from silent intervals when changing speed (default 0.25s)
    audio_rate -- Sample rate of audio input (in Hz, default 44100) used in 
                  asetrate/aresample filters when hasten_audio=True
    hasten_audio -- Speed up audio during silent segment with asetrate and 
                    aresample filters (increases pitch)
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
        vstrings.append('%strim=%s:%s,setpts=PTS-STARTPTS[v%i];' % (v_in, t0, ti, (2*i-1)))

        # Trim video during this silence and speed up using setpts
        vstrings.append('%strim=%s:%s,setpts=(PTS-STARTPTS)/%i[v%i];' % (v_in, ti, tf, factor, (2*i)))

        # Trim video before this silence (regular speed)
        astrings.append('%satrim=%s:%s,asetpts=PTS-STARTPTS[a%i];' % (a_in, t0, ti, (2*i-1)))
        if hasten_audio:
            # Speed up audio during silent segment with asetrate and aresample filters (increases pitch)
            astrings.append('%satrim=%s:%s,asetpts=PTS-STARTPTS,asetrate=%i,aresample=%i,volume=0.0[a%i];' % (a_in, ti, tf, (factor*audio_rate), audio_rate, (2*i)))
        else:
            # Use first 1/factor samples of silence for audio (no pitch increase)
            astrings.append('%satrim=%s:%s,asetpts=PTS-STARTPTS[a%i];' % (a_in, ti, ta, (2*i)))

        # Append these streams to the concat filter input
        concat_string += '[v%i][a%i][v%i][a%i]' % ((2*i-1), (2*i-1), (2*i), (2*i))
        tf_last = s['silence_end'] - delay
    
    # Trim the final segment (regular speed) without specifying the end time
    vstrings.append('%strim=start=%.4f,setpts=PTS-STARTPTS[v%i];' % (v_in, tf_last, n_segs))
    astrings.append('%satrim=start=%.4f,asetpts=PTS-STARTPTS[a%i];' % (a_in, tf_last, n_segs))
    
    # Finish the concat filter call
    concat_string += '[v%i][a%i]concat=n=%i:v=1:a=1%s%s;' % (n_segs, n_segs, n_segs, v_out, a_out)
    
    # Collect lines of the filter script after the trim/atrim calls 
    return '\n'.join(vstrings + astrings + [concat_string])


def resizeFilterGraph(v_in='[0:v]', width=1920, height=1080, pad=True,
                      mode='decrease', v_out='[v]'):
    """Generate a filtergraph string (for processing with the -filter_complex
    flag of ffmpeg) using the scale and pad filters to scale & pad the video 
    for width x height display, with optional padding.
    
    Keyword arguments:
    v_in -- Named input video stream of the form '[0:v]', '[v1]', etc.
            (default '[0:v]')
    width -- of display on which the output stream must fit (default 1920)
    height -- of display on which the output stream must fit (default 1080)
    pad -- add letter- or pillar-boxes to the output as required to fill 
           width x height 
    mode -- argument of ffmpeg scale filter (default 'decrease')
    v_out -- Named output video stream of the form '[v]', '[vout]', etc.
            (default '[v]')
    """
    vstrings = []
    v_scaled = '[scaled]' if pad else v_out
    vstrings.append('%sscale=w=%i:h=%i:force_original_aspect_ratio=%s%s;' % (v_in, width, height, mode, v_scaled))
    if pad:
        vstrings.append('%spad=%s:%s:(ow-iw)/2:(oh-ih)/2%s;' % (v_scaled, width, height, v_out))
    return '\n'.join(vstrings)


def panGainAudioGraph(a_in='[0:a]', duplicate_ch='left', gain=0, a_out='[a]'):
    """Generate a filtergraph string (for processing with the -filter_complex
    flag of ffmpeg) using the pan and volume filters to duplicate audio from
    one stereo channel to another, and optionally change the volume by gain. 

    Keyword arguments:
    a_in -- Named input audio stream of the form '[0:a]', '[a1]', etc.
            (default '[0:a]')
    duplicate_ch -- 'left', 'right', or None/False specify whether to
            duplicate a stereo channel of input audio stream 
            (default 'left')
    gain -- to apply (in dB) to the audio stream using the volume filter 
    a_out -- Named output audio stream of the form '[a]', '[aout]', etc.
            (default '[a]')
    """
    head = a_in
    tail = a_out + ';'
    astrings = []
    if isinstance(duplicate_ch, str):
        if duplicate_ch.lower() == 'left':
            # Duplicate left channel of input on right channel
            astrings.append('pan=stereo|c0=c0|c1=c0')
        if duplicate_ch.lower() == 'right':
            # Duplicate right channel of input on left channel
            astringsde.append('pan=stereo|c0=c1|c1=c1')
    if gain:
        astrings.append('volume=%.1fdB' % gain)
    if len(astrings):
        return head + ','.join(astrings) + tail 
    else:
        return None


def generateFilterGraph(silences, factor, delay=0.25, rescale=True, pan_audio='left', gain=0, audio_rate=44100, hasten_audio=False):
    """Generate a filtergraph string (for processing with the -filter_complex
    flag of ffmpeg) using the trim and atrim filters to speed up periods in the
    video designated by a list of silences (dictonaries with keys:

    silence_start: the timestamp of the detected silent interval in seconds
    silence_end:   the timestamp of the detected silent interval in seconds
    silence_duration:  duration of the silent interval in seconds
    
    Arguments:
    silences -- A list of silence dictionaries generated from getSilences
    factor -- to speed up video during (a subset of) each silent interval

    Keyword arguments:
    delay -- to omit from silent intervals when changing speed (default 0.25s)
    rescale -- Scale and pad the video (pillar- or letter-box as required) for
               1920 x 1080 display (default True)
    pan_audio -- 'left', 'right', or None/False specify whether to duplicate a
                 stereo channel of input audio stream (default 'left')
    gain -- in dB to apply when pan_audio is 'left' or 'right'
    audio_rate -- Sample rate of audio input (in Hz, default 44100) used in 
                  asetrate/aresample filters when hasten_audio=True
    hasten_audio -- Speed up audio during silent segment with asetrate and 
                    aresample filters (increases pitch)
    """
    filter_graph = silenceFilterGraph(silences, factor, audio_rate=audio_rate,
                        v_out='[vn]' if rescale else '[v]', a_out='[an]' if gain or pan_audio else '[a]')
    if rescale:
        filter_graph += '\n' + resizeFilterGraph(v_in='[vn]')
    if pan_audio or gain:
        filter_graph += '\n' + panGainAudioGraph(a_in='[an]', duplicate_ch=pan_audio, gain=gain)
    if filter_graph.endswith(';'):
        filter_graph = filter_graph[:-1]
    return filter_graph


def writeFilterGraph(filter_script_path, silences, **kwargs):
    """Generate a filtergraph string (for processing with the -filter_complex
    flag of ffmpeg) using the trim and atrim filters to speed up periods in the
    video designated by a list of silences (dictonaries with keys:

    silence_start: the timestamp of the detected silent interval in seconds
    silence_end:   the timestamp of the detected silent interval in seconds
    silence_duration:  duration of the silent interval in seconds
    
    Arguments:
    filter_script_path -- Path to save the filter script 
    silences -- A list of silence dictionaries generated from getSilences
    factor -- to speed up video during (a subset of) each silent interval

    Keyword arguments:
    delay -- to omit from silent intervals when changing speed (default 0.25s)
    rescale -- Scale and pad the video (pillar- or letter-box as required) for
               1920 x 1080 display (default True)
    pan_audio -- 'left', 'right', or None/False specify whether to duplicate a
                 stereo channel of input audio stream (default 'left')
    gain -- in dB to apply when pan_audio is 'left' or 'right'
    audio_rate -- Sample rate of audio input (in Hz, default 44100) used in 
                  asetrate/aresample filters when hasten_audio=True
    hasten_audio -- Speed up audio during silent segment with asetrate and 
                    aresample filters (increases pitch)
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
    # input_path = "C:\\Users\\rander\\Documents\\Teaching\\PHS3051Optics\\LectureRecordings\\2017\\Lecture4\\ModernOpticsLecture4.trec"
    # input_path = "C:\\Users\\rander\\Documents\\Teaching\\PHS3051Optics\\LectureRecordings\\2017\\Lecture5\\ModernOpticsLecture5.trec"
    input_path = "C:\\Users\\rander\\Documents\\Teaching\\PHS3051Optics\\LectureRecordings\\2017\\Lecture6\\ModernOpticsLecture6.trec"
    suffix = 'scrub'

    # Flags
    overwrite = True
    run_command = True
    rescale = True
    # pan_audio = False
    pan_audio = 'left'
    factor = 8
    
    # Implementation
    folder, filename = os.path.split(input_path)
    filename_prefix, file_extension = os.path.splitext(filename)
    output_path = '%s_%s.mp4' % (filename_prefix, suffix)
    filter_script_path = '%s.filter-script' % filename_prefix
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
    
    print('\nRequired ffmpeg command:')
    result = ffmpegComplexFilter(input_path, filter_script_path, output_path, run_command, overwrite)