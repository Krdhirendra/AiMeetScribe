import asyncio
from playwright.async_api import async_playwright
import tracemalloc
import re

tracemalloc.start()


async def join_meet_and_transcribe(meet_url: str):
    async with async_playwright() as p:
        # Launch browser with fake media to bypass mic/camera prompts
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="user_data",
            headless=False,
            # Optional: slow_mo helps you visually debug, but slows down execution
            # slow_mo=100, 
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--disable-blink-features=AutomationControlled"
            ],
            # permissions=["camera", "microphone"]
        )
        page = await browser.new_page()
        print("Opening Meet URL...")
        await page.goto(meet_url)

        print("Waiting for page title...")
        print("Page title:", await page.title())
        
        # Wait a moment for dynamic elements to initialize
        await page.wait_for_timeout(3000)

        # 1. Fill Bot Name (Only if requested by Google Meet)
        print("Checking if a name input is required...")
        try:
            # First try looking by placeholder "Your name"
            name_input = page.locator('input[type="text"]')
            await name_input.wait_for(state="visible", timeout=15000)
            await name_input.fill('AI Scribe Bot')
            print("-> Successfully filled in bot name.")
        except Exception:
            print("-> No name input found. It might not be required (e.g. already in user_data session).")
        try:  
            audio_btn = page.get_by_role("button", name=re.compile(r"Turn off microphone", re.IGNORECASE))
            await audio_btn.wait_for(state="visible", timeout=5000) 
            await audio_btn.click()
            video_btn = page.get_by_role("button", name=re.compile(r"Turn off camera", re.IGNORECASE))
            await video_btn.wait_for(state="visible", timeout=5000) 
            await video_btn.click()
        except Exception:
            print("audio video already turned off")
            await page.screenshot(path="AV_error.png")
            print("Saved a screenshot to 'AV_error.png' for debugging.")

        # 2. Click "Ask to Join" or "Join now"
        print("Looking for the 'Ask to join' or 'Join now' button...")
        try:
            # We use a regex match so it handles "Ask to join", "Ask to Join", "Join now", "Join Now"
            join_button = page.get_by_role("button", name=re.compile(r"ask to join|join now", re.IGNORECASE))
            await join_button.wait_for(state="visible", timeout=15000)
            await join_button.click()
            print("-> Clicked the Join button!")
        except Exception as e:
            print(f"-> Failed to find or click the Join button: {e}")
            await page.screenshot(path="error_stuck.png")
            print("Saved a screenshot to 'error_stuck.png' for debugging.")
            return # Exit early since we can't join

        # 3. Wait for admission into the room (this requires a host to let the bot in)
        # When you ask to join, Meet waits for someone inside the call to approve.
        print("Waiting to be admitted by the host...")
        
        # We wait for the captions button to appear to know we are successfully inside the call
        print("Looking for the 'Turn on captions' button...")
        try:
            # This locator matches the captions button which only appears once you're fully in the meeting
            captions_btn = page.get_by_role("button", name=re.compile(r"turn on captions", re.IGNORECASE))
            await captions_btn.wait_for(state="visible", timeout=45000) # Give it 45s for host to accept
            await captions_btn.click()
            print("-> Turned on captions.")
        except Exception as e:
            print(f"-> Could not turn on captions. Host might have not admitted us in time. Error: {e}")
            await page.screenshot(path="error_captions.png")

        transcript = ""
        
        print("Starting to extract captions... (Close the browser window to stop and return transcript)")
        last_caption = ""
        
        # Loop to continuously read the captions until the page is closed
        while not page.is_closed():
            try:
                # Find the captions container (using 'i' for case-insensitivity)
                captions_locator = page.locator('[aria-label="Captions" i]')
                
                if await captions_locator.count() > 0:
                    current_text = await captions_locator.inner_text()
                    current_text = current_text.strip()
                    
                    # Only process if the text is not empty and has changed
                    if current_text and current_text != last_caption:
                        # You might see duplicates or partial sentences depending on how Meet updates the DOM,
                        # but this will capture the live updates.
                        print(f"Caption: {current_text}")
                        transcript += current_text + "\n"
                        
                        # Safely backup the caption instantly to a file
                        import os
                        os.makedirs("transcripts", exist_ok=True)
                        with open("transcripts/meeting_transcript.txt", "a", encoding="utf-8") as f:
                            f.write(current_text + "\n")
                            
                        last_caption = current_text
            except Exception:
                # Silently pass if elements are removed dynamically
                pass
            
            # Check for new captions every 1 second
            await asyncio.sleep(1)

        return transcript


asyncio.run(join_meet_and_transcribe("https://meet.google.com/duh-pvyy-rsf"))