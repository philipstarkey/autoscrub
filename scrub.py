import os
import re
from subprocess import Popen, call, PIPE

def findSilences(log_output):
    matches = re.findall(r"(silence_[a-z]+): ([\-\d\.]+)", log_output)
    matches = [(k, float(v)) for (k, v) in matches]
    return [dict(matches[i:i + 3]) for i in xrange(0, len(matches), 3)]

def findLoudness(log_output):
    summary= re.split(r"Parsed_ebur128.+\r\n", log_output)[-1]
    matches = re.findall(r"([A-Z][A-Za-z ]*): +([\-\d\.]+)", summary)
    return dict([(k, float(v)) for (k, v) in matches])

def generateFilterGraph(silences, factor, audio_rate=44100, delay=0.25, rescale=True, pan_audio='left', gain=0):
    if 'silence_end' not in silences[-1]:
        silences = silences[:-1]
    if silences[0]['silence_start'] <= 0.:
        silences = silences[1:]    
    tf_last = 0
    vstrings = []
    astrings = []
    concat_string = ''
    n = len(silences)
    n_segs = 2*n + 1 # number of segments
    for i, s in enumerate(silences):
        i += 1
        t0 = '%.4f' % tf_last
        ti = '%.4f' % (s['silence_start'] + delay)
        tf = '%.4f' % (s['silence_end'] - delay)
        ta = '%.4f' % (s['silence_start'] + delay + (s['silence_duration'] - 2*delay)/factor)
        vstrings.append('[0:v]trim=%s:%s,setpts=PTS-STARTPTS[v%i];' % (t0, ti, (2*i-1)))
        vstrings.append('[0:v]trim=%s:%s,setpts=(PTS-STARTPTS)/%i[v%i];' % (ti, tf, factor, (2*i)))
        astrings.append('[0:a]atrim=%s:%s,asetpts=PTS-STARTPTS[a%i];' % (t0, ti, (2*i-1)))
        astrings.append('[0:a]atrim=%s:%s,asetpts=PTS-STARTPTS[a%i];' % (ti, ta, (2*i)))
        # astrings.append('[0:a]atrim=%s:%s,asetpts=PTS-STARTPTS,asetrate=%i,aresample=%i,volume=0.0[a%i];' % (ti, tf, (factor*audio_rate), audio_rate, (2*i)))
        concat_string += '[v%i][a%i][v%i][a%i]' % ((2*i-1), (2*i-1), (2*i), (2*i))
        tf_last = s['silence_end'] - delay
    vstrings.append('[0:v]trim=start=%.4f,setpts=PTS-STARTPTS[v%i];' % (tf_last, n_segs))
    astrings.append('[0:a]atrim=start=%.4f,asetpts=PTS-STARTPTS[a%i];' % (tf_last, n_segs))
    concat_string += '[v%i][a%i]concat=n=%i:v=1:a=1[vn][an];' % (n_segs, n_segs, n_segs)
    concat_string = [concat_string]
    if rescale:
        concat_string.append('[vn]scale=w=1920:h=1080:force_original_aspect_ratio=decrease[scaled];')
        concat_string.append('[scaled]pad=1920:1080:(ow-iw)/2:(oh-ih)/2[v];')
    else:
        concat_string[-1] = concat_string[-1].replace('vn', 'v')
    if pan_audio == 'left':
        concat_string.append('[an]pan=stereo|c0=c0|c1=c0,volume=%.1fdB[a]' % gain)
    elif pan_audio == 'right':
        concat_string.append('[an]pan=stereo|c0=c1|c1=c1,volume=%.1fdB[a]' % gain)
    else:
        concat_string[-1] = concat_string[-1].replace('an', 'a')
    if concat_string[-1].endswith(';'):
        concat_string[-1] = concat_string[-1][:-1]
    return '\n'.join(vstrings + astrings + concat_string)

def hhmmssd_to_seconds(s):
    assert isinstance(s, str)
    return reduce(lambda t60, x: t60 * 60 + x, map(float, s.split(':')))

def trim(input_path, tstart=0, tstop=None, output_path=None, overwrite=None):
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
    p = Popen(command, cwd=folder if folder else '.')
    stdout, stderr = p.communicate()

def getDuration(filename):
    p = Popen(['ffprobe', filename], stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    matches = re.findall('Duration: +([\d\:\.]+)', s)
    if matches:
        duration = matches[0]
        seconds = hhmmssd_to_seconds(duration)
        return seconds
    else:
        return None

if __name__ == '__main__':
    # Loudness normalisation
    target_lufs = -18.0

    # Silence detection
    target_threshold_dB = -18.0
    silence_duration = 2.0

    # Filepaths
    # input_path = 'lecture.mp4'
    # input_path = "C:\\Users\\russ\\Videos\\Production\\ffmpeg\\trec_sample_2736x1824\\sample.trec"
    # input_path = "C:\\Users\\russ\\Videos\\Production\\ffmpeg\\focusrite_xlr_test\\capture-1.trec"
    # input_path = "C:\\Users\\russ\\Videos\\Production\\lightboard\\Light_Record-[2017-02-23_11-30-03]-000.mp4"
    # input_path = "C:\\Users\\russ\\Documents\\Teaching\\PHS3051\\LectureRecordings\\2015\\PHS3051 Lecture 1 Martijn Jasperse-8y2Qbt3LdhA.mp4"
    # input_path = "C:\\Users\\russ\\Documents\\Teaching\\PHS3051\\LectureRecordings\\2017\\Lecture2\\ModernOpticsLecture2.trec"
    # input_path = "C:\\Users\\russ\\Documents\\Teaching\\PHS3051\\LectureRecordings\\2017\\Lecture3\\ModernOpticsLecture3.trec"
    input_path = "C:\\Users\\russ\\Documents\\Teaching\\PHS3051\\LectureRecordings\\2017\\Lecture4\\ModernOpticsLecture4.trec"
    # input_path = "C:\\Users\\russ\\Videos\\YouTube\\Group3questionc-Fxdl0e3bfx8.mp4"
    suffix = 'scrub'

    # Flags
    overwrite = True
    run_command = True
    rescale = True
    # pan_audio = False
    pan_audio = 'left'
    factor = 8
    
    print('Setting up paths...')
    folder, filename = os.path.split(input_path)
    filename_prefix = os.path.splitext(filename)[0]
    filter_script_path = '%s.filter-script' % filename_prefix
    silence_path = '%s_silences.txt' % filename_prefix
    if folder is not '':
        os.chdir(folder)
    if not os.path.exists(filter_script_path) or overwrite:
        print('Running ffprobe on %s' % filename)
        command = 'ffprobe -i "%s"' % filename
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()

        print('\nGetting audio sample rate...')
        matches = re.findall(', ([\d]+) Hz', stderr)
        if matches:
            input_sample_rate = int(matches[-1])
            print('Input audio sample rate is %i Hz' % input_sample_rate)
        else:
            input_sample_rate = 44100
            print('WARNING: Could not determine input audio sample rate. Defaulting to 44100 Hz')

        print('\nChecking loudness of file...')
        command = 'ffmpeg -i "%s" -c:v copy -af ebur128 -f null NUL' % filename
        print(command)
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        loudness = findLoudness(stderr)
        input_lufs = loudness['I']
        gain = target_lufs - input_lufs
        if pan_audio:
            gain -= 3
        input_threshold_dB = input_lufs + target_threshold_dB - target_lufs
        print('Measured loudness = %.1f LUFS; Silence threshold = %.1f dB; Gain to apply = %.1f dB' % (input_lufs, input_threshold_dB, gain))

        print('\nSearching for silence...')
        command = 'ffmpeg -i "%s" -af silencedetect=n=%.1fdB:d=%s -f null NUL' % (filename, input_threshold_dB, silence_duration)
        print(command)
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()

        print('\nGetting silences from output...')
        silences = findSilences(stderr)
        # with open(silence_path, 'w') as f:
        #     for silence in silences:
        #         f.write('%s,%s,%s\n' % (silence['silence_start'], silence['silence_end'], silence['silence_duration']))
        
        print('\nFound %i silences. Generating ffmpeg filtergraph...' % len(silences))
        cstring = generateFilterGraph(silences, factor=factor, audio_rate=input_sample_rate, pan_audio=pan_audio, gain=gain, rescale=rescale)
        with open(filter_script_path, 'w') as f:
            f.write(cstring)
    else:
        print('\nUsing existing filter_complex script.')
    
    # Concatenate the command
    header = 'ffmpeg -i "%s"' % filename
    youtube_video = '-c:v libx264 -crf 20 -bf 2 -flags +cgop -g 15 -pix_fmt yuv420p -movflags +faststart' # -tune stillimage
    youtube_audio = '-c:a aac -r:a 48000 -b:a 192k'
    youtube_other = '-strict -2'
    filter_command = '-filter_complex_script "%s" -map [v] -map [a]' % filter_script_path
    tail = '"%s_%s.mp4"' % (filename_prefix, suffix)
    if overwrite:
        tail = '-y ' + tail
    command_list = [header, youtube_video, youtube_audio, youtube_other, filter_command, tail]
    command = ' '.join(command_list)
    print('\nRunning ffmpeg command: \n' + command)
    if run_command:
        p = Popen(command)
        stdout, stderr = p.communicate()