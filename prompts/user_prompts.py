from targets.websites_targets import get_random_target

# Generate prompt with random target URL
video_url = get_random_target()

inital_orchestrator_prompt = f"""Ask another LLM to connect to a VPN server in USA or any server with authentication, \
Then navigate to YouTube video {video_url}, \
extract the video title and description, and take a screenshot of the page. Click button play and verify video is playing for 6000 SECONDS, then disconnect VPN."""