import captacity

captacity.add_captions(
    video_file="video.mp4",
    output_file="video_with_captions.mp4",
    use_local_whisper=True,
)