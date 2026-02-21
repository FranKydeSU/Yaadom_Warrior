import cv2 as cv
import numpy as np
import math, time, random, pygame
from collections import deque

# --- Initialize Pygame ---
pygame.init()
WIDTH, HEIGHT = 1280, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("One Hit Kill: Pygame Edition")
font = pygame.font.SysFont("Arial", 32)
large_font = pygame.font.SysFont("Arial", 64)

# --- Game Logic Variables ---
score = 0
game_over = False
start_time = time.time()
initial_time_limit = 10
time_limit = initial_time_limit
gesture_list = [
    "HORIZONTAL_RIGHT", "HORIZONTAL_LEFT", "VERTICAL_DOWN", "VERTICAL_UP",
    "DIAGONAL_UP_RIGHT", "DIAGONAL_UP_LEFT", "DIAGONAL_DOWN_RIGHT", "DIAGONAL_DOWN_LEFT"
]
current_target = ""
last_gesture_time = 0
cooldown_duration = 0.4
display_target = "current_target"
min_time_limit = 1.7
time_limit_drain_rate = 0.35

pts = deque(maxlen=10)

# OpenCV Setup
# colorLower = (35, 40, 40)
# colorUpper = (85, 255, 255)
colorLower = (29, 86, 6)
colorUpper = (64, 255, 255)
video_capture = cv.VideoCapture(0)

def get_gesture_frame():
    # Captures webcam and returns the center of the tracked object.
    ret, frame = video_capture.read()
    if not ret: return None, None
    frame = cv.flip(frame, 1)
    frame = cv.resize(frame, (WIDTH, HEIGHT))
    
    blurred = cv.GaussianBlur(frame, (11, 11), 0)
    hsv = cv.cvtColor(blurred, cv.COLOR_BGR2HSV)
    mask = cv.inRange(hsv, colorLower, colorUpper)
    mask = cv.erode(mask, None, iterations=3)
    mask = cv.dilate(mask, None, iterations=3)
    
    cnts, _ = cv.findContours(mask.copy(), cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    center = None
    if len(cnts) > 0:
        c = max(cnts, key=cv.contourArea)
        
        M = cv.moments(c)
        if M["m00"] > 0:
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
    
    # Convert BGR to RGB for Pygame
    frame_rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
    frame_surface = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
    return frame_surface, center

def get_new_target(gesture_list):
    target = random.choice(gesture_list)
    
    # Create the scrambled version
    words = target.split("_")
    random.shuffle(words)
    display = " ".join(words)
    
    return target, display

def draw_ui(screen, display_target, score, remaining_time, time_limit):
    # 1. Draw a semi-transparent top bar for readability
    overlay = pygame.Surface((WIDTH, 110), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))  # Black with 160/255 transparency
    screen.blit(overlay, (0, 0))

    # 2. Dynamic Time Bar
    bar_width = 400
    current_bar_width = int((remaining_time / time_limit) * bar_width)
    
    # Change color from Green -> Yellow -> Red
    if remaining_time > time_limit * 0.6:
        bar_color = (50, 255, 50) # Green
    elif remaining_time > time_limit * 0.3:
        bar_color = (255, 255, 50) # Yellow
    else:
        bar_color = (255, 50, 50) # Red

    # Draw Bar background and actual progress
    pygame.draw.rect(screen, (100, 100, 100), (WIDTH//2 - bar_width//2, 80, bar_width, 15))
    pygame.draw.rect(screen, bar_color, (WIDTH//2 - bar_width//2, 80, current_bar_width, 15))

    # 3. Target Text with "Glow" (Shadow)
    target_surf = large_font.render(display_target, True, (255, 255, 255))
    shadow_surf = large_font.render(display_target, True, (0, 0, 0))
    
    # Center the target text
    target_rect = target_surf.get_rect(center=(WIDTH//2, 40))
    screen.blit(shadow_surf, (target_rect.x + 3, target_rect.y + 3))
    screen.blit(target_surf, target_rect)

    # 4. Score on the top right below target text
    score_surf = font.render(f"SCORE: {score}", True, (255, 165, 0))
    score_rect = score_surf.get_rect(topright=(WIDTH - 20, target_rect.bottom + 50))
    screen.blit(font.render(f"SCORE: {score}", True, (0, 0, 0)), (score_rect.x + 2, score_rect.y + 2))
    screen.blit(score_surf, score_rect)

def draw_game_over(screen, score, wrong_gesture, display_target):
    target_str= f"EXPECTED: {display_target}"
    # Fill with a deep vignette red
    screen.fill((40, 0, 0))
    
    # Draw scanlines for a "broken monitor" effect
    for i in range(0, HEIGHT, 4):
        pygame.draw.line(screen, (60, 0, 0), (0, i), (WIDTH, i))

    # 1. Main Header
    over_txt = large_font.render("SYSTEM FAILURE", True, (255, 50, 50))
    over_rect = over_txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80))
    screen.blit(over_txt, over_rect)

    if wrong_gesture == "":
        cause_str = "REASON: OUT OF TIME"
    else:
        cause_str = f"DETECTED: {wrong_gesture}"

    # 2. THE WRONG GESTURE (The "Cause of Death")
    # We display what the user actually did wrong
    target_txt = font.render(target_str, True, (255, 255, 0))
    target_rect = target_txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 160))
    screen.blit(target_txt, target_rect)

    cause_txt = font.render(cause_str, True, (255, 255, 255))
    cause_rect = cause_txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10))
    
    # Draw a small box behind the error text
    error_box = cause_rect.inflate(20, 10)
    pygame.draw.rect(screen, (150, 0, 0), error_box)
    screen.blit(cause_txt, cause_rect)

    # 3. Final Stats
    score_txt = font.render(f"FINAL SCORE: {score}", True, (255, 165, 0))
    score_rect = score_txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
    screen.blit(score_txt, score_rect)

    # 4. Restart Hint
    hint_txt = font.render("PRESS 'R' TO REBOOT", True, (150, 150, 150))
    screen.blit(hint_txt, hint_txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 110)))

# --- Main Loop ---
running = True
clock = pygame.time.Clock()

while running:
    current_time = time.time()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    if not game_over:
        frame_surface, center = get_gesture_frame()
        if frame_surface is None: break

        if current_target == "":
            current_target, display_target = get_new_target(gesture_list)

        # Timing Logic
        elapsed_time = current_time - start_time
        remaining_time = max(0, time_limit - elapsed_time)
        if remaining_time <= 0:
            game_over = True
            wrong_gesture = ""

        # Gesture Tracking Logic
        is_cooling_down = (current_time - last_gesture_time) < cooldown_duration
        if center and not is_cooling_down:
            pts.appendleft(center)
        else:
            if not is_cooling_down: pts.clear()

        # Logic Analysis
        if not is_cooling_down and len(pts) == 10:
            start_pt, end_pt = pts[-1], pts[0]
            dx, dy = end_pt[0] - start_pt[0], end_pt[1] - start_pt[1]
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance > 200:
                angle = math.atan2(dy, dx) * 180 / math.pi
                user_gesture = ""
                
                if -30 < angle < 30: user_gesture = "HORIZONTAL_RIGHT"
                elif angle > 150 or angle < -150: user_gesture = "HORIZONTAL_LEFT"
                elif 60 < angle < 120: user_gesture = "VERTICAL_DOWN"
                elif -120 < angle < -60: user_gesture = "VERTICAL_UP"
                elif -67.5 <= angle <= -22.5: user_gesture = "DIAGONAL_UP_RIGHT"
                elif -157.5 <= angle <= -112.5: user_gesture = "DIAGONAL_UP_LEFT"
                elif 22.5 <= angle <= 67.5: user_gesture = "DIAGONAL_DOWN_RIGHT"
                elif 112.5 <= angle <= 157.5: user_gesture = "DIAGONAL_DOWN_LEFT"

                if user_gesture != "":
                    last_gesture_time = current_time
                    if user_gesture == current_target:
                        score += 1
                        time_limit = max(min_time_limit, time_limit - time_limit_drain_rate)
                        start_time = time.time()
                        current_target, display_target = get_new_target(gesture_list)
                        print(f"Score: {score} | New Time Limit: {time_limit:.1f}s")
                        pts.clear()
                    else:
                        game_over = True
                        wrong_gesture = user_gesture

        # --- Rendering Game State ---
        screen.blit(frame_surface, (0, 0))
        
        # Draw Slash Line
        if len(pts) > 1:
            pygame.draw.lines(screen, (255, 255, 0), False, list(pts), 5)

        # UI Overlay
        draw_ui(screen, display_target, score, remaining_time, time_limit)

    else:
        # --- GAME OVER SCENE ---
        draw_game_over(screen, score, wrong_gesture, display_target)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_r]: # Reset Game
            score = 0
            time_limit = initial_time_limit
            current_target, display_target = get_new_target(gesture_list)
            game_over = False
            start_time = time.time()
            pts.clear()
        if keys[pygame.K_q]:
            running = False

    pygame.display.flip()
    clock.tick(30)

video_capture.release()
pygame.quit()