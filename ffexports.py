import ffmpeg
import textwrap


# # Generate palette
# ffmpeg.input(input_file, ss=start_time, to=end_time) \
#     .filter('fps', fps=20) \
#     .filter('palettegen') \
#     .output('palette.png') \
#     .run()

# # Convert video to GIF using the palette
# ffmpeg.input(input_file, ss=start_time, to=end_time) \
#     .input('palette.png') \
#     .lavfi('fps', fps=20) \
#     .lavfi('[x][1:v] paletteuse') \
#     .output(output_file) \
#     .run()

# def output_gif(stream, output):
#   split = (
#     stream
#     .filter('scale', 512, -1, flags='lanczos') # Scale width to 512px, retain aspect ratio
#     .filter('fps', fps=12)
#     .split()
#   )

#   palette = (
#     split[0]
#     .filter('palettegen')
#   )

#   (
#     ffmpeg
#     .filter([split[1], palette], 'paletteuse')
#     .output(f'{output}.gif')
#     .overwrite_output()
#     .run()
#   )


def output_video_cut(input, output, start_time, end_time):

    stream = ffmpeg.input(input, ss= start_time, to=end_time)

    stream = ffmpeg.output(stream, output,  acodec="copy", vcodec = "copy" ).overwrite_output()

    ffmpeg.run(stream)


def convert(input, output, video_size, crf,audio_track, volume, title, preset_,start_time, end_time, crop, format):

    thecrop = crop

    codec = "libx264" if format != "webm" else "libvpx-vp9"

    print("codec is: ", codec)

    webm_preset = preset_

    audio_codec = "aac" if format != "webm" else "libopus"
    audio_bitrate = "192k" if audio_codec == "aac" else "96k" # Opus audio codec is great, 96k is pretty good quality

    if format == "webm":
        corrected = preset_.split("=")[1]
        webm_preset = corrected
    

    stream = ffmpeg.input(input, ss= start_time, to=end_time)

    video = stream.video

    if crop != "no":
        video = video.filter('crop',*thecrop.split(":"))

    video = video.filter('scale', video_size, -2, flags="lanczos")






    #normalize_increment = volume_detect(input, start_time, end_time)

    audio = stream[f'a:{audio_track}']

    audio = audio.filter('aformat', channel_layouts='stereo')

    audio = audio.filter('volume', f'{volume}dB')

    stream = ffmpeg.output(video,audio, output, acodec=audio_codec, audio_bitrate=audio_bitrate, vcodec = codec, preset=preset_, speed=webm_preset , crf=crf, pix_fmt="yuv420p" ,metadata= f'Title={title}').overwrite_output()

    print(stream.get_args())

    ffmpeg.run(stream)




def convert_gif(input_file, output, start_time, end_time, input_text, size, crop, fps, speed):
    
    stream = ffmpeg.input(input_file, ss=start_time, to=end_time)

    #thetext = textwrap.fill(thetext, width=40)

    #thefont = "font.ttf"

    thecrop = crop

    speed = 1 / float(speed)

    if crop != "no":
        stream = stream.filter('crop',*thecrop.split(":"))


    stream = stream.filter('fps', fps=fps) 
    stream = stream.filter('scale', size, -1, flags='lanczos')

    if input_text:
        stream = stream.filter("drawtext", text=input_text, fontsize=16,  text_align="C",x="(w-text_w)/2",y="h-th-10", fontcolor="Yellow", borderw=3,bordercolor="black")
    if speed != 1:
        stream = stream.filter('setpts', f'{speed}*PTS') #speed
    
    split = stream.split()

    palette = (
        split[0]
        .filter('palettegen')
    )

    (
        ffmpeg
        .filter([split[1], palette], 'paletteuse', dither="bayer", bayer_scale=5)
        .output(f'{output}.gif',)
        .overwrite_output()
        .run()
    )



# def volume_detect(input, start,end):

#     print("starting subprocess")
#     result = subprocess.run(
#     ["ffmpeg", "-i", input,"-af", "volumedetect", "-f", "null", "-"],
#     stderr=subprocess.PIPE,
#     text=True

#     )

#     print(result)

    
#     m = re.search(r"max_volume: ([\-\d\.]+) dB", result.stderr)

#     print(m)

    
#     if m:
#         max_volume = float(m.group(1))
#         print(f"Max volume: {max_volume} dB")
#         # Compute gain to reach -4 dB peak
#         required_gain = -4 - max_volume
#         print(f"Required gain: {required_gain} dB")

#         return required_gain
