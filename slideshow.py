import pygame
import time
from datetime import datetime
import pytz
import queue

# --- Constants ---
SCREEN_WIDTH = 1430
SCREEN_HEIGHT = 1060
SLIDE_DURATION = 14  # Seconds to display a slide
FADE_DURATION = 1    # Seconds for the crossfade transition
TOTAL_SLIDE_TIME = SLIDE_DURATION + FADE_DURATION

def run_slideshow(update_queue):
    """
    Initializes a pygame window and runs a slideshow of active weather alerts.
    
    Args:
        update_queue (queue.Queue): A thread-safe queue to receive new alert info
                                    in the format (image_path, expiration_time_iso).
    """
    pygame.init()
    programIcon = pygame.image.load('cincyweathernobg.png')
    pygame.display.set_icon(programIcon)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Cincy Weather Graphics - Live Alerts")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('sans-serif', 50, bold=True)

    active_slides = []
    current_slide_index = 0
    last_switch_time = time.time()

    running = True
    while running:
        # Get the current dimensions of the display window
        current_screen_width, current_screen_height = screen.get_size()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # We don't need a specific VIDEORESIZE event handler
            # because `get_image` will now check and re-scale if needed.

        # --- 1. Update the list of active slides ---
        # Check for new slides posted by the main thread
        while not update_queue.empty():
            try:
                path, expires_iso = update_queue.get_nowait()
                expires_dt = datetime.fromisoformat(expires_iso)
                # Add new alert if its graphic path isn't already in our list
                if not any(s['path'] == path for s in active_slides):
                    print(f"[Slideshow] Adding new alert: {path}")
                    active_slides.append({'path': path, 'expires': expires_dt, 'original_image': None, 'scaled_image': None})
            except queue.Empty:
                break # No more items in the queue

        # Remove expired slides by checking their expiration time against the current UTC time
        now_utc = datetime.now(pytz.utc)
        active_slides = [s for s in active_slides if s['expires'] > now_utc]

        # --- 2. Render the display ---
        screen.fill((20, 20, 20))  # Dark grey background

        if not active_slides:
            # Display a placeholder message if no alerts are active
            text_surf = font.render('No Active Alerts', True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(current_screen_width / 2, current_screen_height / 2))
            screen.blit(text_surf, text_rect)
            last_switch_time = time.time() # Reset timer
        else:
            # Ensure the index is valid after slides may have been removed
            if current_slide_index >= len(active_slides):
                current_slide_index = 0
            
            # --- Image Loading and Scaling (lazy loading & dynamic scaling) ---
            def get_image(index):
                if not active_slides: return None # Handle empty list after removal
                slide = active_slides[index]
                
                # If the original image hasn't been loaded yet
                if slide['original_image'] is None:
                    try:
                        slide['original_image'] = pygame.image.load(slide['path']).convert()
                    except pygame.error as e:
                        print(f"[Slideshow] ERROR: Could not load image {slide['path']}: {e}")
                        # Remove problematic slide and return a placeholder
                        active_slides.pop(index)
                        return None
                
                # Check if the scaled image needs to be updated (due to window resize or first display)
                if slide['scaled_image'] is None or slide['scaled_image'].get_size() != (current_screen_width, current_screen_height):
                    slide['scaled_image'] = pygame.transform.scale(slide['original_image'], (current_screen_width, current_screen_height))
                
                return slide['scaled_image']

            current_img = get_image(current_slide_index)
            if current_img is None: continue # Skip this frame if image failed to load

            # --- Slideshow and Fade Logic ---
            time_since_switch = time.time() - last_switch_time

            if time_since_switch < SLIDE_DURATION:
                # Display the current slide
                screen.blit(current_img, (0, 0)) #using a lot of memory
            elif time_since_switch < TOTAL_SLIDE_TIME:
                # Perform the crossfade transition
                next_index = (current_slide_index + 1) % len(active_slides)
                next_img = get_image(next_index)
                if next_img is None: continue

                fade_progress = (time_since_switch - SLIDE_DURATION) / FADE_DURATION
                
                # Fade out the current image
                current_img.set_alpha(255 * (1 - fade_progress))
                screen.blit(current_img, (0, 0))
                
                # Fade in the next image
                next_img.set_alpha(255 * fade_progress)
                screen.blit(next_img, (0, 0))
            else:
                # Time to switch to the next slide
                current_slide_index = (current_slide_index + 1) % len(active_slides)
                # Ensure index is valid after any slide removals
                if current_slide_index >= len(active_slides):
                    current_slide_index = 0
                next_img = get_image(current_slide_index)
                if next_img is None: continue # Handle case where next image also fails or list becomes empty

                next_img.set_alpha(255) # Ensure it's fully opaque
                screen.blit(next_img, (0, 0))
                last_switch_time = time.time()

        pygame.display.flip()
        clock.tick(30)  # Limit to 30 FPS

    pygame.quit()