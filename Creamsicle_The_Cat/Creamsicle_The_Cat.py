import pygame
import sys
import random
import itertools

# --- Settings ---
WINDOW_WIDTH, WINDOW_HEIGHT = 800, 600
FPS = 60
IMAGE_PATH = "player.png"
IMAGE2_PATH = "player2.png"
IMAGE3_PATH = "player3.png"
SCALE_FACTOR = 0.1
BAR_HEIGHT = 50
FONT_SIZE = 24

SPAWN_INTERVAL = 5000   # ms
SPAWN_DURATION = 2000   # ms

# --- Init ---
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Squishy Sprite (solid objects)")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, FONT_SIZE)

# --- Load originals ---
player_original = pygame.image.load(IMAGE_PATH).convert_alpha()
player2_original = pygame.image.load(IMAGE2_PATH).convert_alpha()
player3_original = pygame.image.load(IMAGE3_PATH).convert_alpha()

orig_w, orig_h = player_original.get_size()
aspect = orig_w / orig_h

def base_size(w, h):
    base = int(min(w, h) * SCALE_FACTOR)
    bw = max(1, base)
    bh = max(1, int(bw / aspect))
    return bw, bh

def scaled_surface(original_img, w, h, sx=1.0, sy=1.0):
    bw, bh = base_size(w, h)
    nw = max(1, int(bw * sx))
    nh = max(1, int(bh * sy))
    return pygame.transform.smoothscale(original_img, (nw, nh))

# --- spawn id generator ---
_id_gen = itertools.count(1)

# --- Game state ---
points = 0
squish_x = False
squish_y = False

player_surf = scaled_surface(player_original, WINDOW_WIDTH, WINDOW_HEIGHT)
player_rect = player_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
speed = 5

active_objects = []  # list of dicts: {id,type,orig,center,expire}
last_spawn_time = 0
colliding_object_ids = set()

def spawn_object(play_area, player_rect):
    typ, orig = random.choice([("p2", player2_original), ("p3", player3_original)])
    surf = scaled_surface(orig, WINDOW_WIDTH, WINDOW_HEIGHT)
    w, h = surf.get_size()

    for _ in range(100):
        cx = random.randint(play_area.left + w // 2, play_area.right - w // 2)
        cy = random.randint(play_area.top + h // 2, play_area.bottom - h // 2)
        test_rect = surf.get_rect(center=(cx, cy))
        if not test_rect.colliderect(player_rect):
            break
    else:
        cx, cy = play_area.center

    entry = {
        'id': next(_id_gen),
        'type': typ,
        'orig': orig,
        'center': (cx, cy),
        'expire': pygame.time.get_ticks() + SPAWN_DURATION
    }
    active_objects.append(entry)

def build_object_rects():
    res = []
    for e in active_objects:
        surf = scaled_surface(e['orig'], WINDOW_WIDTH, WINDOW_HEIGHT)
        rect = surf.get_rect(center=e['center'])
        res.append((e, surf, rect))
    return res

while True:
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        elif event.type == pygame.VIDEORESIZE:
            WINDOW_WIDTH, WINDOW_HEIGHT = event.w, event.h
            screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)

    # Input
    keys = pygame.key.get_pressed()
    dx = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * speed
    dy = (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * speed

    # Bar + play area
    bar_rect = pygame.Rect(0, WINDOW_HEIGHT - BAR_HEIGHT, WINDOW_WIDTH, BAR_HEIGHT)
    play_area = screen.get_rect().copy()
    play_area.height -= BAR_HEIGHT

    # Spawn timer
    if now - last_spawn_time > SPAWN_INTERVAL:
        spawn_object(play_area, player_rect)
        last_spawn_time = now

    # Remove expired objects
    active_objects = [e for e in active_objects if e['expire'] > now]
    active_object_ids = {e['id'] for e in active_objects}
    colliding_object_ids &= active_object_ids

    obj_tups = build_object_rects()
    prev_rect = player_rect.copy()

    # --- Horizontal move ---
    player_rect.x += dx
    horiz_collision = None
    if player_rect.left < play_area.left:
        player_rect.left = play_area.left
        horiz_collision = {'type': 'wall', 'side': 'left', 'anchor_rect': play_area}
    elif player_rect.right > play_area.right:
        player_rect.right = play_area.right
        horiz_collision = {'type': 'wall', 'side': 'right', 'anchor_rect': play_area}
    else:
        for (entry, surf, rect) in obj_tups:
            if player_rect.colliderect(rect):
                if dx > 0 and prev_rect.right <= rect.left:
                    player_rect.right = rect.left
                    horiz_collision = {'type': 'obj','side':'right','anchor_rect':rect,
                                       'obj_id': entry['id'],'obj_type': entry['type']}
                elif dx < 0 and prev_rect.left >= rect.right:
                    player_rect.left = rect.right
                    horiz_collision = {'type': 'obj','side':'left','anchor_rect':rect,
                                       'obj_id': entry['id'],'obj_type': entry['type']}
                break

    # --- Vertical move ---
    prev_rect_after_h = player_rect.copy()
    player_rect.y += dy
    vert_collision = None
    if player_rect.top < play_area.top:
        player_rect.top = play_area.top
        vert_collision = {'type': 'wall','side':'top','anchor_rect': play_area}
    elif player_rect.bottom > play_area.bottom:
        player_rect.bottom = play_area.bottom
        vert_collision = {'type': 'wall','side':'bottom','anchor_rect': play_area}
    else:
        for (entry, surf, rect) in obj_tups:
            if player_rect.colliderect(rect):
                if dy > 0 and prev_rect.bottom <= rect.top:
                    player_rect.bottom = rect.top
                    vert_collision = {'type': 'obj','side':'bottom','anchor_rect':rect,
                                      'obj_id': entry['id'],'obj_type': entry['type']}
                elif dy < 0 and prev_rect.top >= rect.bottom:
                    player_rect.top = rect.bottom
                    vert_collision = {'type': 'obj','side':'top','anchor_rect':rect,
                                      'obj_id': entry['id'],'obj_type': entry['type']}
                break

    player_rect.clamp_ip(play_area)

    # --- Squish + scoring ---
    old_squish_x, old_squish_y = squish_x, squish_y
    squish_x = horiz_collision is not None
    squish_y = vert_collision is not None

    if squish_x and not old_squish_x: points += 10
    if squish_y and not old_squish_y: points += 10

    current_colliding_ids = set()
    if horiz_collision and horiz_collision.get('type') == 'obj':
        current_colliding_ids.add(horiz_collision['obj_id'])
    if vert_collision and vert_collision.get('type') == 'obj':
        current_colliding_ids.add(vert_collision['obj_id'])

    for obj_id in current_colliding_ids:
        if obj_id not in colliding_object_ids:
            match = next((e for e in active_objects if e['id'] == obj_id), None)
            if match:
                if match['type'] == 'p2': points += 100
                elif match['type'] == 'p3': points = 0
            colliding_object_ids.add(obj_id)

    colliding_object_ids &= (current_colliding_ids & active_object_ids if active_objects else set())

    # --- Rescale + anchor ---
    sx, sy = (0.5 if squish_x else 1.0), (0.5 if squish_y else 1.0)
    new_player_surf = scaled_surface(player_original, WINDOW_WIDTH, WINDOW_HEIGHT, sx, sy)

    anchor_rect = play_area
    contact_left = contact_right = contact_top = contact_bottom = False
    if horiz_collision:
        anchor_rect = horiz_collision['anchor_rect']
        if horiz_collision['side'] == 'left': contact_left = True
        else: contact_right = True
    if vert_collision:
        anchor_rect = vert_collision['anchor_rect']
        if vert_collision['side'] == 'top': contact_top = True
        else: contact_bottom = True

    new_rect = new_player_surf.get_rect(center=player_rect.center)
    if contact_left: new_rect.left = anchor_rect.right if anchor_rect != play_area else play_area.left
    if contact_right: new_rect.right = anchor_rect.left if anchor_rect != play_area else play_area.right
    if contact_top: new_rect.top = anchor_rect.bottom if anchor_rect != play_area else play_area.top
    if contact_bottom: new_rect.bottom = anchor_rect.top if anchor_rect != play_area else play_area.bottom

    new_rect.clamp_ip(play_area)

    # --- Extra separation to avoid overlap loops ---
    for (entry, surf, rect) in obj_tups:
        if new_rect.colliderect(rect):
            if contact_left: new_rect.left = rect.right
            if contact_right: new_rect.right = rect.left
            if contact_top: new_rect.top = rect.bottom
            if contact_bottom: new_rect.bottom = rect.top

    player_surf, player_rect = new_player_surf, new_rect

    # --- Draw ---
    screen.fill((30, 30, 30))
    for (entry, surf, rect) in obj_tups:
        screen.blit(surf, rect)
    screen.blit(player_surf, player_rect)

    pygame.draw.rect(screen, (50, 50, 70), bar_rect)
    text = font.render(f"Points: {points}", True, (255, 255, 255))
    screen.blit(text, (10, WINDOW_HEIGHT - BAR_HEIGHT + (BAR_HEIGHT - FONT_SIZE) // 2))

    pygame.display.flip()
    clock.tick(FPS)
