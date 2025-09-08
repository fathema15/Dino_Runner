
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import sys, random, math, time

# ----------------------- Window & World -----------------------
WIN_W, WIN_H = 1500, 600
ASPECT = WIN_W / float(WIN_H)
FOV = 60.0

# Colors (RGBA-friendly floats)
LIGHT_PEACH = (1.0, 0.93, 0.86)     # background
BROWN       = (0.59, 0.29, 0.0)     # ground
BOTTLE_GRN  = (0/255.0, 106/255.0, 78/255.0)   # Dino
VIRIDIAN    = (0/255.0, 150/255.0, 152/255.0)  # Cacti
YELL_GRN    = (154/255.0, 205/255.0, 50/255.0) # Pterodactyl
CYAN        = (0.0, 1.0, 1.0)       # Play/Pause button
RED         = (1.0, 0.0, 0.0)       # Exit button
WHITE       = (1.0, 1.0, 1.0)
BLACK       = (0.0, 0.0, 0.0)

# UI layout
BTN_PAD = 16
BTN_SIZE = 36  # square
UI_BORDER = 5  # "periphery" thickness for edge-clicks

# Game state
running = True          # paused/play
game_over = False
score = 0
last_passed_id = None

# Camera
view_mode_first_person = False
cam_target = [0.0, 1.0, 0.0]  # where camera looks
cam_pos_third = [-8.0, 4.0, 12.0]  # relative to Dino
cam_pos_first = [0.0, 1.8, 2.5]    # near Dino head
cam_nudge = [0.0, 0.0, 0.0]        # arrow-key offsets

# Dino (at world origin along X, runs in place; world scrolls toward -X)
dino = {
    "x": 0.0, "y": 0.0, "z": 0.0,
    "w": 1.4, "h": 2.2, "d": 0.8,  # body size
    "jumping": False,
    "vy": 0.0
}
GRAVITY = -22.0
JUMP_VELOCITY = 10.0
GROUND_Y = 0.0

# Obstacles & Clouds
obstacles = []  # each: dict with type: 'cactus' or 'ptero', id, x,y,z, w,h,d, vy, speed
clouds = []     # visual-only
next_id = 1

# World motion
WORLD_SPEED = 10.0    # how fast world moves towards Dino (constant)
SPAWN_TIMER = 0.0
SPAWN_INTERVAL_BASE = 1.2   # seconds (base mean)
SPAWN_INTERVAL_JITTER = 0.5 # +/- random

# Cloud spawn
CLOUD_INTERVAL_BASE = 1.0
CLOUD_INTERVAL_JITTER = 0.8
CLOUD_TIMER = 0.0

# Fonts
FONT_TITLE = GLUT_BITMAP_HELVETICA_18
FONT_TEXT  = GLUT_BITMAP_9_BY_15

# ----------------------- Utilities -----------------------
def now():
    return time.time()

last_time = now()

def reset_game():
    global running, game_over, score, obstacles, clouds, SPAWN_TIMER, CLOUD_TIMER, dino, cam_nudge, last_passed_id
    running = True
    game_over = False
    score = 0
    obstacles = []
    clouds = []
    SPAWN_TIMER = 0.0
    CLOUD_TIMER = 0.0
    dino["x"], dino["y"], dino["z"] = 0.0, 0.0, 0.0
    dino["jumping"] = False
    dino["vy"] = 0.0
    cam_nudge = [0.0, 0.0, 0.0]
    last_passed_id = None

def billboard_text(x, y, text, font=FONT_TEXT, color=BLACK, align_center=False):
    glColor3f(*color)
    if align_center:
        w = sum([glutBitmapWidth(font, ord(ch)) for ch in text])
        glRasterPos2f(x - w/2.0, y)
    else:
        glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))

def set_2d():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_DEPTH_TEST)

def unset_2d():
    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()

def spawn_interval():
    # Every 5 points => 1.5% faster (shorter interval)
    steps = score // 5
    factor = (0.985) ** steps
    base = max(0.45, SPAWN_INTERVAL_BASE * factor)  # clamp
    jitter = SPAWN_INTERVAL_JITTER * factor
    return random.uniform(base - jitter, base + jitter)

def spawn_cloud_interval():
    steps = score // 5
    factor = (0.985) ** steps
    base = max(0.30, CLOUD_INTERVAL_BASE * factor)
    jitter = CLOUD_INTERVAL_JITTER * factor
    return random.uniform(base - jitter, base + jitter)

def aabb_overlap(ax, ay, az, aw, ah, ad, bx, by, bz, bw, bh, bd):
    return (abs(ax - bx) * 2 < (aw + bw) and
            abs(ay - by) * 2 < (ah + bh) and
            abs(az - bz) * 2 < (ad + bd))

# ----------------------- Drawing Primitives -----------------------
def draw_box(w, h, d):
    # centered on origin, simple quads (no normals)
    w2, h2, d2 = w/2.0, h/2.0, d/2.0
    glBegin(GL_QUADS)
    # Front
    glVertex3f(-w2,-h2, d2); glVertex3f(w2,-h2, d2); glVertex3f(w2,h2, d2); glVertex3f(-w2,h2, d2)
    # Back
    glVertex3f(-w2,-h2,-d2); glVertex3f(-w2,h2,-d2); glVertex3f(w2,h2,-d2); glVertex3f(w2,-h2,-d2)
    # Left
    glVertex3f(-w2,-h2,-d2); glVertex3f(-w2,-h2, d2); glVertex3f(-w2,h2, d2); glVertex3f(-w2,h2,-d2)
    # Right
    glVertex3f(w2,-h2,-d2); glVertex3f(w2,h2,-d2); glVertex3f(w2,h2, d2); glVertex3f(w2,-h2, d2)
    # Top
    glVertex3f(-w2,h2,-d2); glVertex3f(-w2,h2, d2); glVertex3f(w2,h2, d2); glVertex3f(w2,h2,-d2)
    # Bottom
    glVertex3f(-w2,-h2,-d2); glVertex3f(w2,-h2,-d2); glVertex3f(w2,-h2, d2); glVertex3f(-w2,-h2, d2)
    glEnd()

def draw_cylinder(r, h, slices=16):
    # Top cap (triangles)
    glBegin(GL_TRIANGLES)
    top_y = h/2
    for i in range(slices):
        a0 = 2*math.pi*i/slices
        a1 = 2*math.pi*(i+1)/slices
        glVertex3f(0, top_y, 0)
        glVertex3f(r*math.cos(a0), top_y, r*math.sin(a0))
        glVertex3f(r*math.cos(a1), top_y, r*math.sin(a1))
    glEnd()

    # Bottom cap
    glBegin(GL_TRIANGLES)
    bot_y = -h/2
    for i in range(slices):
        a0 = 2*math.pi*i/slices
        a1 = 2*math.pi*(i+1)/slices
        glVertex3f(0, bot_y, 0)
        glVertex3f(r*math.cos(a1), bot_y, r*math.sin(a1))
        glVertex3f(r*math.cos(a0), bot_y, r*math.sin(a0))
    glEnd()

    # Side as quads
    glBegin(GL_QUADS)
    for i in range(slices):
        a0 = 2*math.pi*i/slices
        a1 = 2*math.pi*(i+1)/slices
        x0, z0 = r*math.cos(a0), r*math.sin(a0)
        x1, z1 = r*math.cos(a1), r*math.sin(a1)
        glVertex3f(x0, -h/2, z0)
        glVertex3f(x0,  h/2, z0)
        glVertex3f(x1,  h/2, z1)
        glVertex3f(x1, -h/2, z1)
    glEnd()

def draw_cloud():
    # 3 overlapping billowy discs as quick-and-cute cloud
    # Each disc approximated by triangles (triangle fan implemented with GL_TRIANGLES)
    for (ox, oy, r) in [(-1.0, 0.0, 1.0), (0.0, 0.4, 1.2), (1.0, 0.0, 1.0)]:
        # center triangles
        num = 32
        glBegin(GL_TRIANGLES)
        for i in range(num):
            a0 = 2 * math.pi * i / num
            a1 = 2 * math.pi * (i + 1) / num
            glVertex3f(ox, oy, 0.0)
            glVertex3f(ox + r * math.cos(a0), oy + r * math.sin(a0), 0.0)
            glVertex3f(ox + r * math.cos(a1), oy + r * math.sin(a1), 0.0)
        glEnd()

# ----------------------- Entities -----------------------
def draw_ground():
    glColor3f(*BROWN)
    glPushMatrix()
    glTranslatef(0, -0.01, 0)
    glScalef(200, 0.02, 20)  # long strip
    draw_box(1,1,1)
    glPopMatrix()

def draw_dino():
    glColor3f(*BOTTLE_GRN)
    x, y, z = dino["x"], dino["y"], dino["z"]
    glPushMatrix()
    glTranslatef(x, y + dino["h"]/2.0, z)

    # Body
    draw_box(dino["w"], dino["h"], dino["d"])

    # Head (front)
    glPushMatrix()
    glTranslatef(dino["w"]/2.0 + 0.5, 0.6, 0.0)
    draw_box(0.9, 0.9, 0.8)
    glPopMatrix()

    # Tail (tapered boxes)
    glPushMatrix()
    glTranslatef(-dino["w"]/2.0 - 0.6, 0.3, 0.0)
    glRotatef(10, 0,0,1)
    draw_box(0.8, 0.3, 0.4)
    glTranslatef(-0.6, 0.05, 0.0)
    draw_box(0.5, 0.2, 0.3)
    glPopMatrix()

    # Legs (slightly forward)
    leg_z = dino["d"]/2.0 - 0.15
    glPushMatrix()
    glTranslatef(0.15, -dino["h"]/2.0 + 0.4, leg_z)
    draw_box(0.25, 0.8, 0.25)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0.25, -dino["h"]/2.0 + 0.4, -leg_z)
    draw_box(0.25, 0.8, 0.25)
    glPopMatrix()

    glPopMatrix()

def draw_cactus(obs):
    glColor3f(*VIRIDIAN)
    glPushMatrix()
    glTranslatef(obs["x"], obs["y"] + obs["h"]/2.0, obs["z"])
    # main trunk
    draw_box(obs["w"]*0.5, obs["h"], obs["d"]*0.5)
    # arms
    glPushMatrix()
    glTranslatef(0.0, 0.3*obs["h"], obs["d"]*0.3)
    draw_box(obs["w"]*0.4, obs["h"]*0.4, obs["d"]*0.4)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0.0, 0.1*obs["h"], -obs["d"]*0.3)
    draw_box(obs["w"]*0.35, obs["h"]*0.35, obs["d"]*0.35)
    glPopMatrix()
    glPopMatrix()

def draw_ptero(obs):
    glColor3f(*YELL_GRN)
    glPushMatrix()
    glTranslatef(obs["x"], obs["y"] + obs["h"]/2.0, obs["z"])
    # body
    draw_box(obs["w"], obs["h"]*0.6, obs["d"])
    # wings (thin boxes)
    glPushMatrix()
    glTranslatef(0.0, 0.2, 0.0)
    glScalef(2.8, 0.1, 0.2)
    draw_box(obs["w"], obs["h"], obs["d"])
    glPopMatrix()
    # beak
    glPushMatrix()
    glTranslatef(obs["w"]/2.0 + 0.4, 0.1, 0.0)
    draw_box(0.6, 0.15, 0.15)
    glPopMatrix()
    glPopMatrix()

def draw_cloud_entity(c):
    glColor3f(1.0,1.0,1.0)
    glPushMatrix()
    glTranslatef(c["x"], c["y"], c["z"])
    glScalef(c["scale"], c["scale"], 1.0)
    draw_cloud()
    glPopMatrix()

# ----------------------- Spawning -----------------------
def spawn_obstacle():
    global next_id
    # Randomly cactus or ptero (50/50)
    kind = random.choice(["cactus", "ptero"])
    x = 40.0
    z = 0.0
    if kind == "cactus":
        # a bit smaller per request
        w, h, d = 0.7, 1.2, 0.6
        y = GROUND_Y
    else:
        # pterodactyl flies such that collision only when Dino jumps
        w, h, d = 0.9, 0.6, 0.8
        y = 1.2 + random.uniform(0.2, 0.4)  # around jump mid-height
    obs = {
        "type": kind, "id": next_id,
        "x": x, "y": y, "z": z,
        "w": w, "h": h, "d": d,
        "speed": WORLD_SPEED,
        "counted": False,          # for scoring when passed
        "passed_close": False,     # for ptero evasion logic
    }
    next_id += 1
    obstacles.append(obs)

def spawn_cloud():
    x = 40.0
    z = -2.0 + random.random()*4.0
    y = 2.2 + random.uniform(0.6, 1.6)  # well above cactus/ptero range, but on-screen
    c = {
        "x": x, "y": y, "z": z,
        "scale": random.uniform(0.6, 1.2),
        "speed": WORLD_SPEED * random.uniform(0.35, 0.55)
    }
    clouds.append(c)

# ----------------------- Update -----------------------
def update(dt):
    global SPAWN_TIMER, CLOUD_TIMER, running, game_over, score

    if running and not game_over:
        # Dino physics
        if dino["jumping"]:
            dino["vy"] += GRAVITY * dt
            dino["y"] += dino["vy"] * dt
            if dino["y"] <= GROUND_Y:
                dino["y"] = GROUND_Y
                dino["jumping"] = False
                dino["vy"] = 0.0

        # Move obstacles & check collisions
        remove_ids = []
        for obs in obstacles:
            obs["x"] -= obs["speed"] * dt

            # Collision rules
            if obs["type"] == "cactus":
                # only when Dino is on/near ground (must jump to avoid)
                if not dino["jumping"] and aabb_overlap(
                    dino["x"], dino["y"] + dino["h"]/2.0, dino["z"], dino["w"], dino["h"], dino["d"],
                    obs["x"],  obs["y"]  + obs["h"]/2.0,  obs["z"],  obs["w"],  obs["h"],  obs["d"]
                ):
                    game_over = True
            else:  # ptero
                # Can only collide while jumping
                if dino["jumping"] and aabb_overlap(
                    dino["x"], dino["y"] + dino["h"]/2.0, dino["z"], dino["w"], dino["h"], dino["d"],
                    obs["x"],  obs["y"]  + obs["h"]/2.0,  obs["z"],  obs["w"],  obs["h"],  obs["d"]
                ):
                    game_over = True

            # Scoring:
            # Cactus: +1 when Dino jumped and it passed behind without collision
            # Ptero : +2 when Dino was in-air at closest approach and it passed without collision
            if not obs["counted"] and obs["x"] < (dino["x"] - 0.5):
                if obs["type"] == "cactus":
                    if obs["x"] < dino["x"] and obs["x"] > dino["x"] - obs["speed"]*dt*3:
                        # passed just now
                        if obs["type"] == "cactus" and (not game_over) and obs["x"] < dino["x"]:
                            # require that Dino was airborne at some moment nearby pass
                            if obs.get("seen_airborne", False):
                                score += 1
                            # else no score (player didn't jump)
                else:
                    if obs.get("passed_close", False) and (not game_over):
                        score += 2
                obs["counted"] = True

            # Track "passed_close" and "seen_airborne" windows around closest approach
            if abs(obs["x"] - dino["x"]) < 0.8:
                if obs["type"] == "ptero" and dino["jumping"]:
                    obs["passed_close"] = True
                if obs["type"] == "cactus" and dino["jumping"]:
                    obs["seen_airborne"] = True

            # cleanup far-left
            if obs["x"] < -60:
                remove_ids.append(obs)

        for o in remove_ids:
            if o in obstacles:
                obstacles.remove(o)

        # Move clouds
        clouds_to_remove = []
        for c in clouds:
            c["x"] -= c["speed"] * dt
            if c["x"] < -60:
                clouds_to_remove.append(c)
        for c in clouds_to_remove:
            clouds.remove(c)

        # Spawning
        SPAWN_TIMER -= dt
        CLOUD_TIMER -= dt
        if SPAWN_TIMER <= 0:
            spawn_obstacle()
            SPAWN_TIMER = max(0.15, spawn_interval())
        if CLOUD_TIMER <= 0:
            spawn_cloud()
            CLOUD_TIMER = max(0.15, spawn_cloud_interval())

# ----------------------- Rendering -----------------------
def display():
    glClearColor(*LIGHT_PEACH, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # 3D camera
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOV, ASPECT, 0.1, 300.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # Determine camera based on mode + nudge
    if view_mode_first_person:
        eye = [dino["x"] + cam_pos_first[0] + cam_nudge[0],
               dino["y"] + cam_pos_first[1] + cam_nudge[1],
               dino["z"] + cam_pos_first[2] + cam_nudge[2]]
        ctr = [dino["x"] + cam_target[0], dino["y"] + cam_target[1], dino["z"] + cam_target[2]]
    else:
        eye = [dino["x"] + cam_pos_third[0] + cam_nudge[0],
               dino["y"] + cam_pos_third[1] + cam_nudge[1],
               dino["z"] + cam_pos_third[2] + cam_nudge[2]]
        ctr = [dino["x"] + cam_target[0], dino["y"] + cam_target[1], dino["z"] + cam_target[2]]
    gluLookAt(eye[0], eye[1], eye[2], ctr[0], ctr[1], ctr[2], 0,1,0)

    # NOTE: lighting removed to comply with allowed functions
    glEnable(GL_DEPTH_TEST)

    # Ground plane
    draw_ground()

    # Clouds (draw behind via z)
    for c in clouds:
        glPushMatrix()
        glTranslatef(0,0,-5.0)  # give them a consistent far backdrop layer
        draw_cloud_entity(c)
        glPopMatrix()

    # Dino
    draw_dino()

    # Obstacles
    for obs in obstacles:
        if obs["type"] == "cactus":
            draw_cactus(obs)
        else:
            draw_ptero(obs)

    # 2D UI Overlay
    set_2d()
    draw_ui()
    unset_2d()

    glutSwapBuffers()

def draw_ui():
    # Title top middle
    title = "3D Dino Runner"
    billboard_text(WIN_W/2, WIN_H-28, title, FONT_TITLE, BLACK, align_center=True)

    # Score bottom middle
    s = f"Score: {score}"
    billboard_text(WIN_W/2 - 40, 16, s, FONT_TEXT, BLACK, align_center=False)

    # Play/Pause button (top-left)
    px, py = BTN_PAD, WIN_H - BTN_PAD - BTN_SIZE
    draw_playpause_button(px, py, BTN_SIZE, BTN_SIZE, CYAN)

    # Exit button (top-right)
    ex, ey = WIN_W - BTN_PAD - BTN_SIZE, WIN_H - BTN_PAD - BTN_SIZE
    draw_exit_button(ex, ey, BTN_SIZE, BTN_SIZE, RED)

    if game_over:
        billboard_text(WIN_W/2, WIN_H/2 + 10, "GAME OVER", FONT_TITLE, BLACK, align_center=True)
        billboard_text(WIN_W/2, WIN_H/2 - 20, "Press R to Restart", FONT_TEXT, BLACK, align_center=True)

def draw_playpause_button(x, y, w, h, color):
    glColor3f(*color)
    # Outline using GL_LINES (explicit)
    glBegin(GL_LINES)
    # left edge
    glVertex2f(x, y); glVertex2f(x, y+h)
    # top edge
    glVertex2f(x, y+h); glVertex2f(x+w, y+h)
    # right edge
    glVertex2f(x+w, y+h); glVertex2f(x+w, y)
    # bottom edge
    glVertex2f(x+w, y); glVertex2f(x, y)
    glEnd()
    # Symbol
    if running and not game_over:
        # Pause (two bars)
        bar_w = w * 0.22
        pad = w * 0.18
        glBegin(GL_QUADS)
        glVertex2f(x+pad, y+8); glVertex2f(x+pad+bar_w, y+8); glVertex2f(x+pad+bar_w, y+h-8); glVertex2f(x+pad, y+h-8)
        glVertex2f(x+w-pad-bar_w, y+8); glVertex2f(x+w-pad, y+8); glVertex2f(x+w-pad, y+h-8); glVertex2f(x+w-pad-bar_w, y+h-8)
        glEnd()
    else:
        # Play triangle
        glBegin(GL_TRIANGLES)
        glVertex2f(x+w*0.30, y+8)
        glVertex2f(x+w*0.30, y+h-8)
        glVertex2f(x+w*0.75, y+h*0.5)
        glEnd()

def draw_exit_button(x, y, w, h, color):
    glColor3f(*color)
    # Outline with lines
    glBegin(GL_LINES)
    glVertex2f(x, y); glVertex2f(x, y+h)
    glVertex2f(x, y+h); glVertex2f(x+w, y+h)
    glVertex2f(x+w, y+h); glVertex2f(x+w, y)
    glVertex2f(x+w, y); glVertex2f(x, y)
    glEnd()
    glBegin(GL_LINES)
    glVertex2f(x+6, y+6); glVertex2f(x+w-6, y+h-6)
    glVertex2f(x+w-6, y+6); glVertex2f(x+6, y+h-6)
    glEnd()

# ----------------------- Input -----------------------
def keyboard(key, x, y):
    global running, view_mode_first_person
    k = key.decode('utf-8').lower()
    if k == 'q' or ord(key) == 27:
        sys.exit(0)
    elif k == 'p':
        toggle_pause()
    elif k == 'r':
        reset_game()
    elif k == ' ':
        do_jump()

def special(key, x, y):
    # Arrow keys nudge camera
    amt = 0.4
    if key == GLUT_KEY_LEFT:  cam_nudge[0] -= amt
    if key == GLUT_KEY_RIGHT: cam_nudge[0] += amt
    if key == GLUT_KEY_UP:    cam_nudge[1] += amt
    if key == GLUT_KEY_DOWN:  cam_nudge[1] -= amt

def mouse(button, state, mx, my):
    global view_mode_first_person
    # Flip y to bottom-origin
    my = WIN_H - my

    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        view_mode_first_person = not view_mode_first_person
        return

    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        # Check UI button hit on periphery
        # Play/Pause
        if hit_button_periphery(mx, my, BTN_PAD, WIN_H - BTN_PAD - BTN_SIZE, BTN_SIZE, BTN_SIZE):
            toggle_pause()
        # Exit
        if hit_button_periphery(mx, my, WIN_W - BTN_PAD - BTN_SIZE, WIN_H - BTN_PAD - BTN_SIZE, BTN_SIZE, BTN_SIZE):
            sys.exit(0)

def hit_button_periphery(mx, my, x, y, w, h):
    inside = (mx >= x and mx <= x+w and my >= y and my <= y+h)
    if not inside: return False
    # Periphery ring: within UI_BORDER of the rectangle edges
    near_left   = abs(mx - x) <= UI_BORDER
    near_right  = abs(mx - (x+w)) <= UI_BORDER
    near_top    = abs(my - (y+h)) <= UI_BORDER
    near_bottom = abs(my - y) <= UI_BORDER
    return near_left or near_right or near_top or near_bottom

def toggle_pause():
    global running
    if not game_over:
        running = not running

def do_jump():
    if not game_over and not dino["jumping"] and dino["y"] <= GROUND_Y + 1e-5:
        dino["jumping"] = True
        dino["vy"] = JUMP_VELOCITY

# ----------------------- Main Loop -----------------------
def reshape(w, h):
    global WIN_W, WIN_H, ASPECT
    WIN_W, WIN_H = max(1, w), max(1, h)
    ASPECT = WIN_W / float(WIN_H)
    glViewport(0, 0, WIN_W, WIN_H)

def timer(_=0):
    global last_time
    curr = now()
    dt = curr - last_time
    last_time = curr
    update(dt)
    glutPostRedisplay()
    glutTimerFunc(16, timer, 0)  # ~60 FPS

def init_gl():
    glEnable(GL_DEPTH_TEST)
    # Removed glShadeModel(GL_SMOOTH), GL_NORMALIZE, and GL_CULL_FACE (disallowed)
    reset_game()

def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutCreateWindow(b"3D Dino Runner")
    init_gl()
    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special)
    glutMouseFunc(mouse)
    glutTimerFunc(0, timer, 0)
    glutMainLoop()

if __name__ == "__main__":
    main()