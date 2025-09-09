# ----------------- Professional 3D Dino Runner -----------------
# PyOpenGL + GLUT
# pip install PyOpenGL PyOpenGL_accelerate

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import sys, math, time, random
from OpenGL.GLUT import glutLeaveMainLoop

# Window and Camera :

WIN_W, WIN_H = 1280, 720
ASPECT = WIN_W / WIN_H
FOV = 60.0

view_first_person = False
CAM_THIRD = [0.0, 5.5, 28.0]
CAM_FIRST = [0.0, 2.0, 3.0]
CAM_TARGET = [0.0, 1.5, 0.0]
cam_yaw = 0.0
cam_pitch = 20.0
cam_dist = 28.0

# Colors :

SKY  = (0.85, 0.92, 1.0)  # sky blue
GROUND= (0.396, 0.263, 0.129)  # dark brown
RIVER= (0.96, 0.92, 0.62)  # light yellow river
TREE_BARK= (0.55, 0.35, 0.2)
TREE_LEAF= (0.25, 0.65, 0.3)
DINO_COL= (0.0, 0.4, 0.3)

CACTUS_COL = (0.0, 0.6, 0.6)
PTERO_COL = (0.6, 0.8, 0.2)
COIN_COL = (1.0, 0.85, 0.25)
WHITE = (1.0, 1.0, 1.0)
BLACK  = (0.0, 0.0, 0.0)

EGG_COL = (1.0, 0.95, 0.85)
PATH_COL= (1.0, 1.0, 0.2)  # light yellow track
NIGHT_SKY = (0.07, 0.10, 0.18)
PEBBLE_COL= (0.55, 0.47, 0.40)

# Game State :

running = True
game_over = False
invuln_t = 0.0
lives = 3
score = 0
eggs_collected = 0
time_score_acc = 0.0
last_time = time.time()
is_night = False
game_time = 0.0

# Dino Varibables:

dino = {"x":0.0,"y":0.0,"z":0.0,"w":1.6,"h":2.2,"d":0.9,"vy":0.0,"jumping":False,"crouch":False}
GRAVITY = -22.0
JUMP_V = 11.5
GROUND_Y = 0.0

# World :

WORLD_SPEED = 10.0
SPAWN_T, COIN_T, CLOUD_T = 0.0, 0.0, 0.0
SPAWN_INT_BASE, SPAWN_INT_JIT = 1.2, 0.5
COIN_INT_BASE, COIN_INT_JIT = 1.3, 0.9
CLOUD_INT_BASE, CLOUD_INT_JIT = 1.0, 0.8

obstacles, coins, clouds, trees = [], [], [], []
next_id = 1

# Single-lane setup (center lane at z=0) :

lane_speed = 0.0  # no lateral movement needed

# Stars for night sky :

stars = [(random.uniform(0, WIN_W), random.uniform(WIN_H*0.55, WIN_H-10)) for _ in range(90)]

# Fonts :

FONT_BIG = GLUT_BITMAP_HELVETICA_18
FONT_SMALL = GLUT_BITMAP_9_BY_15



#  2D Drawing :

def begin_2d():

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)

def end_2d():

    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glEnable(GL_LIGHTING)

def draw_text(x, y, s, font=FONT_SMALL, color=BLACK):

    glColor3f(*color)
    glRasterPos2f(x, y)

    for ch in s:
        glutBitmapCharacter(font, ord(ch))

# Geometry :
#  
def draw_box(w,h,d):

    w2,h2,d2 = w/2,h/2,d/2
    glBegin(GL_QUADS)

    # Front:

    glNormal3f(0,0,1); glVertex3f(-w2,-h2,d2); glVertex3f(w2,-h2,d2)
    glVertex3f(w2,h2,d2); glVertex3f(-w2,h2,d2)

    # Back:

    glNormal3f(0,0,-1); glVertex3f(-w2,-h2,-d2); glVertex3f(-w2,h2,-d2)
    glVertex3f(w2,h2,-d2); glVertex3f(w2,-h2,-d2)

    # Left:

    glNormal3f(-1,0,0); glVertex3f(-w2,-h2,-d2); glVertex3f(-w2,-h2,d2)
    glVertex3f(-w2,h2,d2); glVertex3f(-w2,h2,-d2)

    # Right:

    glNormal3f(1,0,0); glVertex3f(w2,-h2,-d2); glVertex3f(w2,h2,-d2)
    glVertex3f(w2,h2,d2); glVertex3f(w2,-h2,d2)

    # Top:

    glNormal3f(0,1,0); glVertex3f(-w2,h2,-d2); glVertex3f(-w2,h2,d2)
    glVertex3f(w2,h2,d2); glVertex3f(w2,h2,-d2)

    # Bottom :

    glNormal3f(0,-1,0); glVertex3f(-w2,-h2,-d2); glVertex3f(w2,-h2,-d2)
    glVertex3f(w2,-h2,d2); glVertex3f(-w2,-h2,d2)
    glEnd()

def draw_disc(radius=0.35, thick=0.12, slices=24):

    h,r = thick, radius
    glBegin(GL_TRIANGLE_FAN)
    glNormal3f(0,1,0); glVertex3f(0,h/2,0)

    for i in range(slices+1):
        a = 2*math.pi*i/slices
        glVertex3f(r*math.cos(a),h/2,r*math.sin(a))
    glEnd()

    glBegin(GL_TRIANGLE_FAN)
    glNormal3f(0,-1,0); glVertex3f(0,-h/2,0)

    for i in range(slices+1):
        a = 2*math.pi*i/slices
        glVertex3f(r*math.cos(a),-h/2,r*math.sin(a))
    glEnd()
    glBegin(GL_QUAD_STRIP)

    for i in range(slices+1):

        a =2*math.pi*i/slices; nx, nz = math.cos(a), math.sin(a)
        glNormal3f(nx,0,nz)
        glVertex3f(r*nx,-h/2,r*nz)
        glVertex3f(r*nx,h/2,r*nz)
    glEnd()

def aabb(ax,ay,az,aw,ah,ad,bx,by,bz,bw,bh,bd):

    return (abs(ax-bx)*2 < (aw+bw) and
            abs(ay-by)*2 < (ah+bh) and
            abs(az-bz)*2 < (ad+bd))

#  Environment Drawing:

def draw_ground():

    glColor3f(*GROUND)
    glPushMatrix()
    glTranslatef(0,-0.02,0)
    glScalef(260,0.04,22)
    draw_box(1,1,1)
    glPopMatrix()

    # Center running track (light yellow) at z=0 :

    glColor3f(*PATH_COL)
    glPushMatrix()
    glTranslatef(0,0,0)
    glScalef(260,0.021,3.2)
    draw_box(1,1,1)
    glPopMatrix()

def draw_tree(x,z):

    glPushMatrix()
    glTranslatef(x,0,z)
    glColor3f(*TREE_BARK)
    glPushMatrix(); glTranslatef(0,1.2,0); draw_box(0.5,2.4,0.5); glPopMatrix()

    # Layered leafy canopy (spherical clusters):

    glDisable(GL_LIGHTING)
    glColor3f(*TREE_LEAF)
    glPushMatrix(); glTranslatef(0,3.0,0); q=gluNewQuadric(); gluSphere(q,0.9,16,12); glPopMatrix()
    glPushMatrix(); glTranslatef(0.6,2.6,0); q=gluNewQuadric(); gluSphere(q,0.7,16,12); glPopMatrix()
    glPushMatrix(); glTranslatef(-0.6,2.6,0); q=gluNewQuadric(); gluSphere(q,0.7,16,12); glPopMatrix()
    glPushMatrix(); glTranslatef(0,2.3,0.6); q=gluNewQuadric(); gluSphere(q,0.6,16,12); glPopMatrix()
    glPushMatrix(); glTranslatef(0,2.3,-0.6); q=gluNewQuadric(); gluSphere(q,0.6,16,12); glPopMatrix()
    glEnable(GL_LIGHTING)
    glPopMatrix()

def draw_cloud_entity(c):

    glDisable(GL_LIGHTING)

    if is_night:
        glColor3f(0.55,0.55,0.6)

    else:
        glColor3f(1,1,1)
    glPushMatrix()
    glTranslatef(c["x"], c["y"], c["z"])
    glScalef(c["s"],c["s"],1)

    for (ox,oy,r) in [(-1,0,1),(0,0.5,1.2),(1,0,1)]:
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(ox,oy,0)

        for i in range(28):
            a = 2*math.pi*i/27
            glVertex3f(ox+r*math.cos(a),oy+r*math.sin(a),0)
        glEnd()
    glPopMatrix()
    glEnable(GL_LIGHTING)

# Entities :

#Dino Draw:

def draw_dino():
     
	glColor3f(*DINO_COL)
	x, y, z = dino["x"], dino["y"], dino["z"]
	h = dino["h"] * (0.65 if dino["crouch"] and not dino["jumping"] else 1.0)
	w, d = dino["w"], dino["d"]
	glPushMatrix()
	glTranslatef(x, y + h/2, z)

	# Torso Drawing:
     
	draw_box(w, h*0.6, d)

	# Head Drawing :
     
	glPushMatrix()
	glTranslatef(w*0.15, h*0.45, d*0.05)
	draw_box(w*0.55, h*0.35, d*0.6)
	# Snout
	glTranslatef(w*0.25, -h*0.05, 0)
	draw_box(w*0.25, h*0.18, d*0.45)
     
	# Eyes Drawing:
     
	glColor3f(0,0,0)
	glPushMatrix(); glTranslatef(w*0.08, h*0.08, d*0.31); draw_box(0.08,0.08,0.02); glPopMatrix()
	glPushMatrix(); glTranslatef(w*0.08, h*0.08,-d*0.31); draw_box(0.08,0.08,0.02); glPopMatrix()
	glColor3f(*DINO_COL)
	glPopMatrix()

	#Legs Drawing :
     
	for sx in (-w*0.25, w*0.25):

		glPushMatrix()
		glTranslatef(sx, -h*0.25, d*0.18)
		draw_box(w*0.25, h*0.5, d*0.22)
		glPopMatrix()
		glPushMatrix()
		glTranslatef(sx, -h*0.25, -d*0.18)
		draw_box(w*0.25, h*0.5, d*0.22)
		glPopMatrix()

	# Tiny arms Drawing:
     
	for side in (-1, 1):
		glPushMatrix()
		glTranslatef(side*w*0.35, h*0.05, d*0.15*side)
		glRotatef(-20, 0, 0, 1)
		draw_box(w*0.18, h*0.22, d*0.16)
		glPopMatrix()

	# Tail Drawing:
     
	glPushMatrix()
	glTranslatef(-w*0.55, -h*0.05, 0)
	glRotatef(-20, 0, 0, 1)
	draw_box(w*0.4, h*0.15, d*0.18)
	glTranslatef(-w*0.25, 0.02, 0)
	glRotatef(-10, 0, 0, 1)
	draw_box(w*0.25, h*0.12, d*0.14)
	glTranslatef(-w*0.35, 0.01, 0)
	
	glPopMatrix()

	glPopMatrix()
     
#Cactus Draw:

def draw_cactus(o):
	glColor3f(*CACTUS_COL)
	glPushMatrix()
	glTranslatef(o["x"], o["y"], o["z"])

	# Main trunk with segmented look:
     
	seg_h = o["h"]/3.0

	for i in range(3):
		glPushMatrix()
		glTranslatef(0, seg_h*(i+0.5), 0)
		scl = 1.0 - 0.08*i
		draw_box(o["w"]*scl, seg_h*0.95, o["d"]*scl)
		glPopMatrix()

	# Arms:
     
	for dir, up, off in [(-1, 1, 0.35), (1, 1, 0.5)]:

		glPushMatrix()
		glTranslatef(dir*o["w"]*0.85, seg_h*1.4, 0)
		glRotatef(20*dir, 0, 0, 1)
		draw_box(o["w"]*0.45, seg_h*0.9, o["d"]*0.45)
		glPushMatrix(); glTranslatef(0, seg_h*0.55, 0); draw_box(o["w"]*0.35, seg_h*0.35, o["d"]*0.35); glPopMatrix()
		glPopMatrix()

	# Top cap :
     
	glPushMatrix()
	glTranslatef(0, o["h"]*0.98, 0)
	draw_box(o["w"]*0.6, seg_h*0.4, o["d"]*0.6)
	glPopMatrix()

	# Simple spikes :
     
	sp = max(3, int(6*o["h"]))//6
	for i in range(sp):
		yy=(i+1)*o["h"]/sp
        
		for s in (-1,1):

			glPushMatrix(); glTranslatef(s*o["w"]*0.55, yy, 0); draw_box(0.06,0.12,0.06); glPopMatrix()
			glPushMatrix(); glTranslatef(0, yy, s*o["d"]*0.55); draw_box(0.06,0.12,0.06); glPopMatrix()
               
	# Base roots :
     
	glPushMatrix(); glTranslatef(0,-0.05,0); draw_box(o["w"]*1.2, 0.1, o["d"]*1.2); glPopMatrix()
	glPopMatrix()
     
#Ptero Drawing:


def draw_ptero(o):
    glColor3f(*PTERO_COL)
    glPushMatrix()
    glTranslatef(o["x"], o["y"]+o["h"]/2,o["z"])
    draw_box(o["w"],o["h"],o["d"])
    glPopMatrix()

#Egg Drawing:

def draw_coin(c):
     
	# Draw an egg instead of a coin :
     
	glColor3f(*EGG_COL)
	glPushMatrix()
	glTranslatef(c["x"], c["y"], c["z"])
	# Gentle wobble
	glRotatef((time.time()*40)%360, 0, 1, 0)
	glScalef(0.35, 0.5, 0.35)
	q = gluNewQuadric()
	gluSphere(q, 1.0, 20, 16)
	glPopMatrix()

# Spawning:


def spawn_coin():
    x = 28.0
    z = 0.0
    y = 0.9 if random.random()<0.6 else 0.6
    coins.append({"x":x,"y":y,"z":z,"w":0.5,"h":0.5,"d":0.2,"speed":WORLD_SPEED*1.05})

def spawn_obstacle():

    global next_id
    kind = random.choice(["cactus","ptero"])
    x = 28.0
    z = 0.0

    if kind=="cactus": 
        w,h,d=0.9,1.6,0.7; y=GROUND_Y

    else: 
        w,h,d=1.0,0.7,0.9; y=1.7  # air for crouch

    obstacles.append({"id":next_id,"type":kind,"x":x,"y":y,"z":z,"w":w,"h":h,"d":d,"speed":WORLD_SPEED,"counted":False})
    next_id += 1

def spawn_cloud():

    x = 28.0
    z = random.choice([-2,2]) * random.uniform(12.0, 16.0) 
    y = random.uniform(3.8,6.5)

    clouds.append({"x":x,"y":y,"z":z,"s":random.uniform(0.8,1.4),"speed":WORLD_SPEED*0.45})



def seed_trees():

    for i in range(14):

        x = 8+i*10
        trees.append((x, -7.5 if i%2==0 else 7.5))

# Update:

def update(dt):

    global SPAWN_T, COIN_T, CLOUD_T, running, game_over, score, time_score_acc, invuln_t, lives, eggs_collected, game_time

    if not running or game_over: 
        return
    
    game_time+= dt
    time_score_acc+= dt

    if time_score_acc >= 1.0:
        add =int(time_score_acc); score += add; time_score_acc -= add

    if invuln_t > 0: 
        invuln_t =max(0, invuln_t - dt)

    if dino["jumping"]:

        dino["vy"] += GRAVITY*dt
        dino["y"] += dino["vy"]*dt

        if dino["y"] <= GROUND_Y:
            dino["y"]=GROUND_Y; dino["jumping"]=False; dino["vy"]=0

    # Global speed multiplier increases over time (caps out)
    speed_mul = 1.0 + min(game_time * 0.008, 0.2)

    for o in obstacles[:]:

        o["x"] -= o["speed"]*speed_mul*dt
        dh = dino["h"]*(0.65 if dino["crouch"] and not dino["jumping"] else 1.0)

        if invuln_t<=0 and aabb(dino["x"],dino["y"]+dh/2,dino["z"],dino["w"],dh,dino["d"],
                                o["x"],o["y"]+o["h"]/2,o["z"],o["w"],o["h"],o["d"]):
            lives -= 1; invuln_t=1.2

        if o["x"] < -40: 
            obstacles.remove(o)

    for c in coins[:]:

        c["x"] -= c["speed"]*speed_mul*dt
        dh = dino["h"]*(0.65 if dino["crouch"] and not dino["jumping"] else 1.0)

        if aabb(dino["x"],dino["y"]+dh/2,dino["z"],dino["w"],dh,dino["d"],
                c["x"],c["y"],c["z"],0.6,0.6,0.6):
            
            eggs_collected += 1
            score += 10
            coins.remove(c)

        if c["x"] < -40: 
            coins.remove(c)

    for cl in clouds[:]:
        cl["x"] -= cl["speed"]*speed_mul*dt

        if cl["x"] < -80:
            clouds.remove(cl)

    speed_factor =(0.985)**(score//5)
    SPAWN_T -= dt; COIN_T -= dt; CLOUD_T -= dt

    if SPAWN_T<=0: 
        SPAWN_T =max(0.3, random.uniform(SPAWN_INT_BASE, SPAWN_INT_BASE+SPAWN_INT_JIT)*speed_factor); spawn_obstacle()

    if COIN_T<=0: 
        COIN_T =max(0.2, random.uniform(0.8, 1.4)*speed_factor); spawn_coin()

    if CLOUD_T<=0: 
        CLOUD_T =max(0.25, random.uniform(CLOUD_INT_BASE, CLOUD_INT_BASE+CLOUD_INT_JIT)); spawn_cloud()

    if lives <=0: 
        game_over=True; running=False

# Rendering:

def setup_lighting():
    glEnable(GL_LIGHTING); glEnable(GL_LIGHT0)

    if is_night:

        glLightfv(GL_LIGHT0,GL_POSITION,(0,10,8,1))
        glLightfv(GL_LIGHT0,GL_DIFFUSE,(0.65,0.65,0.7,1))
        glLightfv(GL_LIGHT0,GL_AMBIENT,(0.15,0.15,0.2,1))

    else:

        glLightfv(GL_LIGHT0,GL_POSITION,(6,10,12,1))
        glLightfv(GL_LIGHT0,GL_DIFFUSE,(1,1,1,1))
        glLightfv(GL_LIGHT0,GL_AMBIENT,(0.35,0.35,0.35,1))

    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK,GL_AMBIENT_AND_DIFFUSE)

def display():

    glClearColor(*(NIGHT_SKY if is_night else SKY),1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity(); gluPerspective(FOV,ASPECT,0.1,400)
    
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if view_first_person:

    # Camera position: Dino head :

        eye = [dino["x"], dino["y"] + 8, dino["z"]]

    # Look forward in the +Y (track) direction :

        ctr = [dino["x"], dino["y"] + 8, dino["z"] + 40]

    else:

        tx, ty, tz = dino["x"] + CAM_TARGET[0], CAM_TARGET[1], dino["z"] + CAM_TARGET[2]
        ry, rp = math.radians(cam_yaw), math.radians(cam_pitch)
        dx = math.cos(rp)*math.sin(ry)
        dy = math.sin(rp)
        dz = math.cos(rp)*math.cos(ry)
        eye = [tx + dx*cam_dist, ty + dy*cam_dist, tz + dz*cam_dist]
        ctr = [tx, ty, tz]

    gluLookAt(*eye, *ctr, 0,1,0)

    setup_lighting()
    draw_ground()

    for tx,tz in trees: draw_tree(tx - dino["x"], tz)
    for cl in clouds: draw_cloud_entity(cl)

    for o in obstacles:

        if o["type"]=="cactus":
            draw_cactus(o)

        else: 
            draw_ptero(o)
    for c in coins: 

        draw_coin(c)  # eggs

    draw_dino()
    glDisable(GL_LIGHTING)
    begin_2d()

    # Stars overlay at night

    if is_night:

        glDisable(GL_LIGHTING)
        glPointSize(2.0)
        glBegin(GL_POINTS)
        glColor3f(0.9,0.9,1.0)
        for sx, sy in stars: glVertex2f(sx, sy)
        glEnd()
        glEnable(GL_LIGHTING)

    draw_text(14, WIN_H-26, f"Score: {score}", FONT_BIG, BLACK)
    draw_text(14, WIN_H-54, f"Lives: {lives}", FONT_BIG, BLACK)
    draw_text(14, WIN_H-82, f"Eggs: {eggs_collected}", FONT_BIG, BLACK)

    if not running and not game_over:

        draw_text(WIN_W/2-70, WIN_H/2+10, "PAUSED", FONT_BIG, BLACK)
        draw_text(WIN_W/2-170, WIN_H/2-20, "Press P to resume | R to restart", FONT_SMALL, BLACK)

    if game_over:

        draw_text(WIN_W/2-80, WIN_H/2+10, "GAME OVER", FONT_BIG, BLACK)
        draw_text(WIN_W/2-160, WIN_H/2-20, "Press R to restart | Q to quit", FONT_SMALL, BLACK)

    end_2d()
    glutSwapBuffers()

#Input :

def keyboard(key, x, y):

    global running, dino, view_first_person, lives, score, game_over, obstacles, coins, clouds, eggs_collected, is_night
    key = key.decode("utf-8").lower()

    if key == 'w' and not dino["jumping"]:

        dino["vy"] = JUMP_V; dino["jumping"]=True

    if key == 's':

        dino["crouch"]=True

    # Removed A/D/Q/E lane/road switching :

    if key == 'p': 
        running = not running
    if key == 'c':
        view_first_person = not view_first_person
    if key == 'n':
        is_night = not is_night
    if key == 'r':
        lives=3; score=0; eggs_collected=0; obstacles.clear(); coins.clear(); clouds.clear(); dino["y"]=0; dino["z"]=0.0; dino["jumping"]=False; game_over=False; running=True
    if key =='q'and game_over : 
        glutLeaveMainLoop()

def keyboard_up(key,x,y):

    key = key.decode("utf-8").lower()
    if key=='s': dino["crouch"]=False

def special_keyboard(key, x, y):

    global cam_yaw, cam_pitch, cam_dist

    if key == GLUT_KEY_LEFT:  
        cam_yaw -= 5.0

    if key == GLUT_KEY_RIGHT: 
        cam_yaw += 5.0

    if key == GLUT_KEY_UP:    
        cam_dist -= 1.0

    if key == GLUT_KEY_DOWN:
        cam_dist += 1.0

    if key == GLUT_KEY_PAGE_UP:   
        cam_pitch += 3.5

    if key == GLUT_KEY_PAGE_DOWN: 
        cam_pitch -= 3.5

    if key == GLUT_KEY_HOME:

        cam_yaw, cam_pitch, cam_dist = 0.0, 20.0, 28.0
    cam_pitch = max(-10.0, min(60.0, cam_pitch))
    cam_dist = max(6.0, min(60.0, cam_dist))

#  Timer :

def timer(t):

    global last_time
    curr = time.time(); dt = curr-last_time; last_time = curr
    update(dt)
    glutPostRedisplay()
    glutTimerFunc(16, timer, 0)

# Main :

def main():
    
    glutInit(); glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H); glutInitWindowPosition(100,50)
    glutCreateWindow(b"3D Dino Runner")
    glEnable(GL_DEPTH_TEST)
    seed_trees()
    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard)
    glutKeyboardUpFunc(keyboard_up)
    glutSpecialFunc(special_keyboard)
    glutTimerFunc(0,timer,0)
    glutMainLoop()

if __name__=="__main__":
        main()