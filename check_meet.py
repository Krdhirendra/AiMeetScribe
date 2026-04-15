import asyncio
from playwright.async_api import async_playwright
import tracemalloc
import re
import os

tracemalloc.start()


async def join_meet(page, meet_url: str):
    """Navigates to the Meet URL, fills name, turns off A/V, and asks to join."""
    print("Opening Meet URL...")
    await page.goto(meet_url)

    print("Waiting for page title...")
    print("Page title:", await page.title())
    
    # Wait a moment for dynamic elements to initialize
    await page.wait_for_timeout(3000)

    # 1. Fill Bot Name (Only if requested)
    print("Checking if a name input is required...")
    try:
        # First try looking by placeholder "Your name"
        name_input = page.locator('input[type="text"]')
        await name_input.wait_for(state="visible", timeout=15000)
        await name_input.fill('AI Scribe Bot')
        print("-> Successfully filled in bot name.")
    except Exception:
        print("-> No name input found. It might not be required.")

    # 2. Turn off Microphone/Camera
    try:  
        audio_btn = page.get_by_role("button", name=re.compile(r"Turn off microphone", re.IGNORECASE))
        await audio_btn.wait_for(state="visible", timeout=5000) 
        await audio_btn.click()
        video_btn = page.get_by_role("button", name=re.compile(r"Turn off camera", re.IGNORECASE))
        await video_btn.wait_for(state="visible", timeout=5000) 
        await video_btn.click()
        print("-> Turned off A/V.")
    except Exception:
        print("-> Audio/video already turned off or buttons not found.")
        await page.screenshot(path="AV_error.png")

    # 3. Click "Ask to Join" or "Join now"
    print("Looking for the 'Ask to join' or 'Join now' button...")
    try:
        join_button = page.get_by_role("button", name=re.compile(r"ask to join|join now", re.IGNORECASE))
        await join_button.wait_for(state="visible", timeout=15000)
        await join_button.click()
        print("-> Clicked the Join button!")
    except Exception as e:
        print(f"-> Failed to find or click the Join button: {e}")
        await page.screenshot(path="error_stuck.png")
        raise e

    # 4. Wait for admission into the room
    print("Waiting to be admitted by the host...")
    try:
        # Wait for the "Leave call" or "Turn on captions" button to appear (meaning we are in)
        in_call_indicator = page.get_by_role("button", name=re.compile(r"turn on captions|Send a reaction", re.IGNORECASE)).first
        await in_call_indicator.wait_for(state="visible", timeout=60000) 
        print("-> Admitted into the meeting successfully!")
    except Exception as e:
        print(f"-> Host might have not admitted us in time, or we were denied. Error: {e}")
        await page.screenshot(path="error_admission.png")
        raise e


async def turn_on_captions(page):

    # Handle captions
    try:
        # We wait dynamically until AT LEAST ONE of the caption toggle buttons appears.
        # This regex matches "Turn on captions..." OR "Turn off captions..." and proceeds instantly!
        any_caption_btn = page.get_by_role("button", name=re.compile(r"Turn (on|off) captions", re.IGNORECASE)).first
        await any_caption_btn.wait_for(state="visible", timeout=30000)

        # Now we identify exactly which one became visible
        captions_on_btn = page.get_by_role("button", name=re.compile(r"Turn on captions", re.IGNORECASE)).first
        captions_off_btn = page.get_by_role("button", name=re.compile(r"Turn off captions", re.IGNORECASE)).first

        if await captions_on_btn.is_visible():
            await captions_on_btn.click()
            print("-> Turned on captions")

        elif await captions_off_btn.is_visible():
            print("-> Captions already ON")

        else:
            print("-> Captions button not found")

            
    except Exception as e:
        print(f"-> not admitted to meeting: {e}")
        await page.screenshot(path="error_captions.png")
        # Exit the meet since we are not admitted
        if not page.is_closed():
            await page.close()
        raise Exception("Meeting admission failed, exiting meet.") from e


def get_disjoint_prefix(old_s, new_s):
    """Finds what text fell off the screen (disjoint part) to keep history clean."""
    if not old_s: return ""
    # 1. Normal typing/scrolling overlap
    for i in range(len(old_s)):
        if new_s.startswith(old_s[i:]):
            return old_s[:i]
    # 2. Autocorrect replacement check (if they share >50% and at least 5 chars)
    prefix_len = min(len(old_s), len(new_s)) // 2
    if prefix_len > 5 and old_s[:prefix_len] == new_s[:prefix_len]:
        return "" # Discard old_s because new_s is its corrected form
    # 3. New speaker or complete clear
    return old_s + "\n\n"

async def extract_captions(page):
    """Continuously extracts and saves captions from the meeting without duplication."""
    permanent_history = ""
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
                    
                    # Compute what permanently fell off the screen and add to history
                    disjoint_text = get_disjoint_prefix(last_caption, current_text)
                    permanent_history += disjoint_text
                    last_caption = current_text
                    
                    # Overwrite file with the pristine snapshot (no duplication)
                    os.makedirs("transcripts", exist_ok=True)
                    with open("transcripts/meeting_transcript.txt", "w", encoding="utf-8") as f:
                        f.write(permanent_history + current_text)
        except Exception:
            # Silently pass if elements are removed dynamically
            pass
        
        # Check for new captions every 1 second
        await asyncio.sleep(1)

        # Detect if the meeting has ended by checking if the "Leave call" button is still in the DOM
        try:
            leave_call_btn = page.get_by_role("button", name=re.compile(r"leave call", re.IGNORECASE))
            if await leave_call_btn.count() == 0:
                print("\n-> Meeting ended or bot was removed by the host. Exiting caption extraction.")
                break
        except Exception:
            pass

    return permanent_history + last_caption


async def main(meet_url: str):
    """Main orchestrator function."""
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="user_data",
            headless=False,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--disable-blink-features=AutomationControlled"
            ],
            # permissions=["camera", "microphone"]
        )
        
        page = await browser.new_page()

        try:
            # 1. Join Meet phase
            await join_meet(page, meet_url)
            
            # 2. Turn on Captions phase
            await turn_on_captions(page)
            
            # 3. Extract process
            final_transcript = await extract_captions(page)
            
            print("\n----- Final Transcript Collected -----")
            
            # Trigger summariser script (runs synchronously)
            import subprocess
            import sys
            print("Running summarizer...")
            subprocess.run([sys.executable, "sumarriser.py"])
            
        except Exception as e:
            print(f"Script stopped due to an error: {e}")
        finally:
            if not page.is_closed():
                await browser.close()


import sys

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://meet.google.com/duh-pvyy-rsf"
    asyncio.run(main(target_url))