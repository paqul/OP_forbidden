from targets.websites_targets import get_random_target

# Generate prompt with random target URL
video_url = get_random_target()

inital_orchestrator_prompt = f"""Ask another LLM to connect to a VPN server in Poland (only), \
Then navigate to YouTube video {video_url}, \
extract the video title and description. \
Click button play, get the full video duration using get_video_duration tool, then watch the video for its full duration, then disconnect VPN."""