import pygame, math, random, threading, queue
pygame.init()
WIDTH, HEIGHT = 800, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Solar System – Elliptical Orbits + Pluto + Comets + Alien Ship")
clock = pygame.time.Clock()

CX, CY = WIDTH // 2, HEIGHT // 2
TILT = 0.5
zoom = 1.0

planet_elements = {
    'Mercury': (0.3871, 0.2056, 87.969, (180, 180, 180)),
    'Venus':   (0.7233, 0.0068, 224.701, (200, 0, 200)),
    'Earth':   (1.0000, 0.0167, 365.256, (0, 120, 255)),
    'Mars':    (1.5237, 0.0934, 686.980, (255, 80, 80)),
    'Jupiter': (5.2028, 0.0484, 4332.589, (255, 200, 0)),
    'Saturn':  (9.5388, 0.0539, 10759.22, (170, 170, 100)),
    'Uranus':  (19.191, 0.0472, 30688.5, (0, 255, 255)),
    'Neptune': (30.061, 0.0086, 60182, (100, 100, 255)),
    'Pluto':   (39.482, 0.2488, 90560, (220, 200, 160))
}
planet_radii_km = {
    'Mercury': 2439.7, 'Venus': 6051.8, 'Earth': 6371.0, 'Mars': 3389.5,
    'Jupiter': 69911, 'Saturn': 58232, 'Uranus': 25362, 'Neptune': 24622,
    'Pluto': 1188.3
}
SUN_RADIUS_KM = 695700
SUN_COLOR = (255,255,0)
KM_PER_AU = 149_597_870.7
AU_PIXELS_BASE = (WIDTH//2 - 50) / planet_elements['Pluto'][0]

def make_belt(count, r_inner_au, r_outer_au, speed_range):
    return [{"angle": random.random()*2*math.pi,
             "radius_au": random.uniform(r_inner_au, r_outer_au),
             "speed": random.uniform(*speed_range)} for _ in range(count)]
asteroid_belt = make_belt(400, planet_elements['Mars'][0]*1.2,
                          planet_elements['Jupiter'][0]*0.9, (0.001, 0.003))
kuiper_belt = make_belt(300, planet_elements['Neptune'][0]*1.05,
                        planet_elements['Pluto'][0]*0.9, (0.0005,0.001))
oort_cloud = make_belt(200, planet_elements['Pluto'][0]*1.3,
                       planet_elements['Pluto'][0]*1.5, (0.00005,0.00015))
belt_labels = [
    {"text":"Asteroid Belt",
     "radius_au": (planet_elements['Mars'][0]*1.2+planet_elements['Jupiter'][0]*0.9)/2,
     "angle": random.random()*2*math.pi,
     "speed": sum(r["speed"] for r in asteroid_belt)/len(asteroid_belt)},
    {"text":"Kuiper Belt",
     "radius_au": (planet_elements['Neptune'][0]*1.05+planet_elements['Pluto'][0]*0.9)/2,
     "angle": random.random()*2*math.pi,
     "speed": sum(r["speed"] for r in kuiper_belt)/len(kuiper_belt)},
    {"text":"Oort Cloud",
     "radius_au": (planet_elements['Pluto'][0]*1.3+planet_elements['Pluto'][0]*1.5)/2,
     "angle": random.random()*2*math.pi,
     "speed": sum(r["speed"] for r in oort_cloud)/len(oort_cloud)}
]

def solve_kepler(M,e,tol=1e-6):
    E = M if e<0.8 else math.pi
    while True:
        f = E - e*math.sin(E) - M
        fprime = 1 - e*math.cos(E)
        E2 = E - f/fprime
        if abs(E2-E) < tol: return E2
        E = E2
def elliptical_position(a,e,T,t_days):
    n = 2*math.pi/T
    M = (n*t_days) % (2*math.pi)
    E = solve_kepler(M,e)
    nu = 2*math.atan2(math.sqrt(1+e)*math.sin(E/2),
                      math.sqrt(1-e)*math.cos(E/2))
    r = a*(1-e*math.cos(E))
    return r*math.cos(nu), r*math.sin(nu)
def draw_orbit(a,e,scale_pixels,color=(60,60,60)):
    pts=[]
    for deg in range(0,361,2):
        nu = math.radians(deg)
        r = a*(1-e**2)/(1+e*math.cos(nu))
        x = CX + (r*math.cos(nu) - e*a) * scale_pixels
        y = CY + r*math.sin(nu) * scale_pixels * TILT
        pts.append((x,y))
    pygame.draw.lines(screen,color,True,pts,1)
def draw_sphere(surface,x,y,radius,color,light_dir):
    sphere_surf = pygame.Surface((radius*2,radius*2),pygame.SRCALPHA)
    cx, cy = radius, radius
    lx, ly = light_dir
    ln = math.hypot(lx,ly) or 1
    lx/=ln; ly/=ln
    br,bg,bb = color
    for i in range(radius*2):
        for j in range(radius*2):
            dx=i-cx; dy=j-cy
            dist = math.hypot(dx,dy)
            if dist<=radius:
                nx,ny=dx/radius, dy/radius
                dot=nx*lx+ny*ly
                bright=max(0,dot)
                shade = 0.5+0.5*bright
                r2=min(255,int(br*shade+255*bright*0.2))
                g2=min(255,int(bg*shade+255*bright*0.2))
                b2=min(255,int(bb*shade+255*bright*0.2))
                sphere_surf.set_at((i,j),(r2,g2,b2,255))
    surface.blit(sphere_surf,(x-radius,y-radius))

AU_METERS = 1.496e11; GM_SUN = 1.32712440018e20
SECONDS_PER_DAY=86400; G_CONST=6.67430e-11
def color_for_distance(au,q_min,q_max):
    t=(au-q_min)/(q_max-q_min); t=max(0,min(1,t))
    return (255,int(20+t*(255-20)),0)
def test_pericenter(x,y,vx,vy,steps=500):
    mind=1e9; tx,ty=x,y; tvx,tvy=vx,vy
    for _ in range(steps):
        dx=-tx; dy=-ty
        dist=math.sqrt(dx*dx+(dy/TILT)**2)
        mind = min(mind,dist)
        accel=(GM_SUN/(AU_METERS**3)*(SECONDS_PER_DAY**2))/(dist**2)
        tvx += dx/dist * accel
        tvy += dy/dist * accel * TILT
        tx += tvx; ty += tvy
    return mind
total_comets_spawned=0
def spawn_comet(q_min=0.01,q_max=0.05,inner_bias=True):
    global total_comets_spawned
    spawn_r = planet_elements['Pluto'][0]*1.1
    ang=random.random()*2*math.pi
    x=spawn_r*math.cos(ang); y=spawn_r*math.sin(ang)
    base_speed=random.uniform(0.8,1.2)/AU_PIXELS_BASE
    target_peri=random.uniform(q_min,q_max) if inner_bias else random.uniform(0.3,5.0)
    found=False; path_color=(255,160,0); vx=vy=0
    aim=math.atan2(-y,-x)
    for t_ang in [math.radians(a) for a in range(-20,21)]:
        tvx=math.cos(aim+t_ang)*base_speed
        tvy=math.sin(aim+t_ang)*base_speed
        peri=test_pericenter(x,y,tvx,tvy)
        if abs(peri-target_peri)<0.002:
            path_color=color_for_distance(peri,q_min,q_max)
            vx,vy=tvx,tvy; found=True; break
    if not found: vx=math.cos(aim)*base_speed; vy=math.sin(aim)*base_speed
    m=random.uniform(1e11,1e15)
    comet={"x_au":x,"y_au":y,"vx_au_day":vx,"vy_au_day":vy,
           "trail":[],"path_color":path_color,"alive":True,
           "spawn_r_au":spawn_r,"mass_kg":m}
    total_comets_spawned+=1; return comet
comet_queue=queue.Queue()
def comet_worker(q_min,q_max,inner_bias):
    comet_queue.put(spawn_comet(q_min,q_max,inner_bias))


# --- Alien Ship ---
def spawn_spaceship(earth_pos_px):
    spawn_r_au = planet_elements['Pluto'][0]*1.2
    angle = random.random()*2*math.pi
    x_au = spawn_r_au*math.cos(angle)
    y_au = spawn_r_au*math.sin(angle)
    # Velocity: head toward near Earth
    ex, ey = (earth_pos_px[0]-CX)/AU_PIXELS_BASE, (earth_pos_px[1]-CY)/(AU_PIXELS_BASE*TILT)
    dir_to_earth = math.atan2(ey - y_au, ex - x_au)
    speed_au_day = 0.08  # slower than comets for visible pass
    vx = math.cos(dir_to_earth)*speed_au_day
    vy = math.sin(dir_to_earth)*speed_au_day
    return {"x_au":x_au, "y_au":y_au, "vx":vx, "vy":vy, "alive":True, "frame":0}

spaceship = None


# Simulation vars
comets=[spawn_comet(inner_bias=True) for _ in range(4)]
sim_days=0.0; earth_pos_px=(0,0); earth_radius_px=0
explosions=[]; explosion_duration_ms=2000
max_comets_alive=10; comet_spawn_prob=0.4
earth_hits_count=0
stats_font=pygame.font.SysFont(None,26)
label_font=pygame.font.SysFont(None,20)

panning=False; keys_pressed=set()
keyboard_pan_speed=10; cam_vx=cam_vy=0
pan_accel_factor=0.2

running=True
while running:
    screen.fill((0,0,20))
    current_time=pygame.time.get_ticks()
    for event in pygame.event.get():
        if event.type==pygame.QUIT: running=False
        elif event.type==pygame.KEYDOWN: keys_pressed.add(event.key)
        elif event.type==pygame.KEYUP: keys_pressed.discard(event.key)
        elif event.type==pygame.MOUSEWHEEL:
            old_zoom=zoom
            zoom*=1.1 if event.y>0 else 0.9
            zoom=max(0.05,min(45.0,zoom))
            if event.y<0 and zoom<=0.06:
                CX += (WIDTH//2 - CX) * 0.2
                CY += (HEIGHT//2 - CY) * 0.2
            if event.y>0 and old_zoom<=0.06:
                CX += (WIDTH//2 - CX) * 0.1
                CY += (HEIGHT//2 - CY) * 0.1
        elif event.type==pygame.MOUSEBUTTONDOWN:
            if event.button==2: panning=True
        elif event.type==pygame.MOUSEBUTTONUP:
            if event.button==2: panning=False
        elif event.type==pygame.MOUSEMOTION and panning:
            CX += event.rel[0]; CY += event.rel[1]

    # smooth keyboard pan
    dvx=dvy=0
    if pygame.K_a in keys_pressed or pygame.K_LEFT in keys_pressed: dvx+=keyboard_pan_speed
    if pygame.K_d in keys_pressed or pygame.K_RIGHT in keys_pressed: dvx-=keyboard_pan_speed
    if pygame.K_w in keys_pressed or pygame.K_UP in keys_pressed: dvy+=keyboard_pan_speed
    if pygame.K_s in keys_pressed or pygame.K_DOWN in keys_pressed: dvy-=keyboard_pan_speed
    cam_vx += (dvx - cam_vx)*pan_accel_factor
    cam_vy += (dvy - cam_vy)*pan_accel_factor
    CX += cam_vx; CY += cam_vy

    while not comet_queue.empty():
        comets.append(comet_queue.get())

    scale_pixels=AU_PIXELS_BASE*zoom
    size_mult_sun=1.0 if zoom<=10 else 20.0 if zoom>=30 else 1.0+((zoom-10)/20)*(19.0)
    size_mult_planets=1.0 if zoom<=10 else 300.0 if zoom>=30 else 1.0+((zoom-10)/20)*(299.0)

    # belts
    for belt,col,km in [(asteroid_belt,(0,0,139),500),
                        (kuiper_belt,(0,255,255),300),
                        (oort_cloud,(0,255,255),200)]:
        for rock in belt:
            rock["angle"] += rock["speed"]
            rx = CX + rock["radius_au"]*math.cos(rock["angle"])*scale_pixels
            ry = CY + rock["radius_au"]*math.sin(rock["angle"])*scale_pixels*TILT
            pygame.draw.circle(screen,col,(int(rx),int(ry)),max(1,int((km/KM_PER_AU)*scale_pixels)))
    for lbl in belt_labels:
        lbl["angle"] += lbl["speed"]
        lx = CX + lbl["radius_au"]*math.cos(lbl["angle"])*scale_pixels
        ly = CY + lbl["radius_au"]*math.sin(lbl["angle"])*scale_pixels*TILT
        surf=label_font.render(lbl["text"],True,(200,200,150))
        screen.blit(surf,(lx-surf.get_width()/2,ly-surf.get_height()/2))

    # planets
    for name,(a,e,Tp,color) in planet_elements.items():
        x_au,y_au=elliptical_position(a,e,Tp,sim_days)
        x_px=CX+(x_au - e*a)*scale_pixels
        y_px=CY+y_au*scale_pixels*TILT
        r_px=(planet_radii_km[name]/KM_PER_AU)*scale_pixels*size_mult_planets
        if name=="Earth": earth_pos_px=(x_px,y_px); earth_radius_px=r_px
        draw_orbit(a,e,scale_pixels)
        draw_sphere(screen,int(x_px),int(y_px),max(1,int(r_px)),color,(x_px-CX,y_px-CY))
        font_size=max(20,int(max(1,int(r_px))*2.5))
        lbl=pygame.font.SysFont(None,font_size).render(name,True,(255,255,255))
        screen.blit(lbl,(x_px+r_px+4,y_px-lbl.get_height()/2))

    # Sun
    sun_r_px=(SUN_RADIUS_KM/KM_PER_AU)*scale_pixels*size_mult_sun
    draw_sphere(screen,CX,CY,max(2,int(sun_r_px)),SUN_COLOR,(0,0))
    sun_lbl=pygame.font.SysFont(None,max(12,int(max(2,int(sun_r_px))*2.5))).render("Sun",True,SUN_COLOR)
    screen.blit(sun_lbl,(CX+sun_r_px+4,CY-sun_lbl.get_height()/2))

    # comets
    new_comets=[]
    for cm in comets:
        if not cm["alive"]: continue
        dist_au=math.sqrt(cm["x_au"]**2+cm["y_au"]**2)
        if dist_au>=cm["spawn_r_au"]: cm["alive"]=False; continue
        dx=-cm["x_au"]; dy=-cm["y_au"]
        dist=math.sqrt(dx*dx+(dy/TILT)**2)
        GM_total=GM_SUN+cm["mass_kg"]*G_CONST
        GM_total_AU_day2=(GM_total/(AU_METERS**3))*(SECONDS_PER_DAY**2)
        accel=GM_total_AU_day2/(dist**2)
        cm["vx_au_day"] += dx/dist*accel
        cm["vy_au_day"] += dy/dist*accel*TILT
        cm["x_au"] += cm["vx_au_day"]; cm["y_au"] += cm["vy_au_day"]
        cm["trail"].append((cm["x_au"],cm["y_au"]))
        if len(cm["trail"])>200: cm["trail"].pop(0)
        comet_x=CX+cm["x_au"]*scale_pixels
        comet_y=CY+cm["y_au"]*scale_pixels*TILT
        if math.hypot(comet_x-earth_pos_px[0],comet_y-earth_pos_px[1])<=earth_radius_px:
            earth_hits_count+=1
            explosions.append((earth_pos_px,earth_radius_px*2,current_time))
            cm["alive"]=False; continue
        tl_len=len(cm["trail"])
        for i,(tx_au,ty_au) in enumerate(cm["trail"]):
            tx=CX+tx_au*scale_pixels; ty=CY+ty_au*scale_pixels*TILT
            alpha=int(((i+1)/tl_len)*255)
            t_surf=pygame.Surface((3,3),pygame.SRCALPHA)
            t_surf.fill(cm["path_color"]+(alpha,))
            screen.blit(t_surf,(tx,ty))
        pygame.draw.circle(screen,cm["path_color"],(int(comet_x),int(comet_y)),4)
        new_comets.append(cm)
    comets=new_comets
    if len(comets)<max_comets_alive and random.random()<comet_spawn_prob:
        threading.Thread(target=comet_worker,args=(0.01,0.05,random.choice([True,False])),daemon=True).start()

    # Alien spaceship
    if spaceship is None:
        spaceship = spawn_spaceship(earth_pos_px)
    else:
        spaceship["x_au"] += spaceship["vx"]
        spaceship["y_au"] += spaceship["vy"]
        spaceship["frame"] += 1
        ship_x_px = CX + spaceship["x_au"]*scale_pixels
        ship_y_px = CY + spaceship["y_au"]*scale_pixels*TILT
        # shimmer color
        if spaceship["frame"] % 10 < 5:
            ship_color = (255, 50, 50)  # red
        else:
            ship_color = (255, 215, 0)  # gold
        # draw saucer (ellipse)
        ship_rect = pygame.Rect(0, 0, 30, 15)
        ship_rect.center = (ship_x_px, ship_y_px)
        ship_surface = pygame.Surface((30, 15), pygame.SRCALPHA)
        pygame.draw.ellipse(ship_surface, ship_color, (0, 0, 30, 15))
        screen.blit(ship_surface, ship_rect.topleft)
        if math.hypot(ship_x_px-CX, ship_y_px-CY) > planet_elements['Pluto'][0]*AU_PIXELS_BASE*zoom*1.3:
            spaceship = None  # respawn next frame

    # explosions
    for expl in explosions[:]:
        pos,r,start=expl
        if current_time-start<explosion_duration_ms:
            pygame.draw.circle(screen,(255,100,0),(int(pos[0]),int(pos[1])),int(r))
        else: explosions.remove(expl)

    # stats
    earth_years=sim_days/planet_elements["Earth"][2]
    stats_surface=stats_font.render(f"Earth Years: {earth_years:.2f}   Total Comets: {total_comets_spawned}   Earth Hits: {earth_hits_count}",True,(255,255,255))
    screen.blit(stats_surface,(10,5))

    pygame.display.flip()
    clock.tick(60)
    sim_days+=1

pygame.quit()
