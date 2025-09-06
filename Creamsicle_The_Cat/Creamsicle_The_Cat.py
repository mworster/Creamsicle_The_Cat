import pygame
import sys

# --- Settings ---
WINDOW_WIDTH, WINDOW_HEIGHT = 800, 600
FPS = 60
IMAGE_PATH = "player.png"
SCALE_FACTOR = 0.1          # 10% of the shorter window dimension

# --- Init ---
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Squishy Sprite")
clock = pygame.time.Clock()

# --- Load + aspect ratio ---
player_original = pygame.image.load(IMAGE_PATH).convert_alpha()
orig_w, orig_h = player_original.get_size()
aspect = orig_w / orig_h

def base_size(w, h):
    base = int(min(w, h) * SCALE_FACTOR)
    bw = max(1, base)
    bh = max(1, int(bw / aspect))
    return bw, bh

def scaled_image(w, h, sx=1.0, sy=1.0):
    bw, bh = base_size(w, h)
    nw = max(1, int(bw * sx))
    nh = max(1, int(bh * sy))
    return pygame.transform.smoothscale(player_original, (nw, nh))

# Start centered
squish_x, squish_y = 1.0, 1.0
player_img = scaled_image(WINDOW_WIDTH, WINDOW_HEIGHT, squish_x, squish_y)
player_rect = player_img.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))

speed = 5

def anchored_rect(prev_rect, new_img, win_rect, contact_left, contact_right, contact_top, contact_bottom):
    """Create a rect for new_img, keeping the contacted wall(s) fixed."""
    new_rect = new_img.get_rect()
    # Start from previous center to preserve position
    new_rect.center = prev_rect.center

    # Horizontal anchoring
    if contact_left and not contact_right:
        new_rect.left = win_rect.left  # pin to left wall
    elif contact_right and not contact_left:
        new_rect.right = win_rect.right  # pin to right wall
    # If both false, keep centerx from prev_rect (already done).
    # (If both true, window is narrower than sprite; fallback clamp later.)

    # Vertical anchoring
    if contact_top and not contact_bottom:
        new_rect.top = win_rect.top  # pin to top
    elif contact_bottom and not contact_top:
        new_rect.bottom = win_rect.bottom  # pin to bottom

    # Final safety clamp
    new_rect.clamp_ip(win_rect)
    return new_rect

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        elif event.type == pygame.VIDEORESIZE:
            WINDOW_WIDTH, WINDOW_HEIGHT = event.w, event.h
            screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)

    keys = pygame.key.get_pressed()
    dx = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * speed
    dy = (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * speed

    # Move first
    player_rect.x += dx
    player_rect.y += dy

    # Determine contact **before** resizing this frame
    win_rect = screen.get_rect()
    contact_left   = player_rect.left   <= win_rect.left
    contact_right  = player_rect.right  >= win_rect.right
    contact_top    = player_rect.top    <= win_rect.top
    contact_bottom = player_rect.bottom >= win_rect.bottom

    # Clamp to keep inside bounds
    player_rect.clamp_ip(win_rect)

    # Squish state: stay squished while touching that axis
    squish_x = 0.5 if (contact_left or contact_right) else 1.0
    squish_y = 0.5 if (contact_top  or contact_bottom) else 1.0

    # Build new image at the right size
    new_img = scaled_image(WINDOW_WIDTH, WINDOW_HEIGHT, squish_x, squish_y)

    # Rebuild rect anchored to any contacted side(s) so the contacted edge doesn't move
    player_rect = anchored_rect(player_rect, new_img, win_rect,
                                contact_left, contact_right, contact_top, contact_bottom)
    player_img = new_img

    # Draw
    screen.fill((30, 30, 30))
    screen.blit(player_img, player_rect)
    pygame.display.flip()
    clock.tick(FPS)
