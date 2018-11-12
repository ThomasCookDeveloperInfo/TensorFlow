from tkinter import *
from math import *
from rx import Observable
import multiprocessing
from rx.concurrency import ThreadPoolScheduler
from rx.concurrency import TkinterScheduler
import tensorflow as tf
from tensorflow import keras

SIM_WIDTH = 1000.0
SIM_HEIGHT = 1000.0
ROT_DRAG_COEFFICIENT = 0.75
VEL_DRAG_COEFFICIENT = 0.9
MAX_ROT_VEL = 60.0
MAX_VEL = 25.0
BULLET_SPEED = 25.0
MAX_BULLETS = 10
TORQUE = 3.0
THRUST = 3.0
GRID_COLUMNS = 5
GRID_ROWS = GRID_COLUMNS
BULLET_RADIUS = 5.0
PHYSICS_PER_SECOND = 60
FRAMES_PER_SECOND = 60
ASTEROIDS = 2

root = Tk()
optimal_thread_count = multiprocessing.cpu_count()
pool_scheduler = ThreadPoolScheduler(optimal_thread_count)
tkinter_scheduler = TkinterScheduler(root)


class GuiController(object):
    def __init__(self):
        self.simulations = list(map(lambda index: (Simulation()), range(0, GRID_COLUMNS * GRID_ROWS)))


class Ship(object):
    def __init__(self):
        self.shape = [(-10.0, -10.0), (0.0, 20.0), (10.0, -10.0)]
        self.x = SIM_WIDTH / 2.0
        self.y = SIM_HEIGHT / 2.0
        self.vx = 0.0
        self.vy = 0.0
        self.vrot = 0.0
        self.rot = 0.0
        self.angularTorque = 0.0
        self.thrust = 0.0
        self.can_shoot = True
        self.shooting = False
        self.bullets = []
        self.reloadDisposable = Observable.interval(1000 / 3) \
            .observe_on(pool_scheduler) \
            .subscribe(on_next=lambda i: self.reload())

    def reload(self):
        self.can_shoot = True

    def get_shape(self, scale_x, scale_y):
        return list(map(lambda point: (
            (
                ((point[0] * cos(radians(self.rot)) - point[1] * sin(radians(self.rot))) + self.x) * scale_x,
                ((point[0] * sin(radians(self.rot)) + point[1] * cos(radians(self.rot))) + self.y) * scale_y
            )
        ), self.shape))

    def update(self):
        self.vrot += self.angularTorque
        if self.vrot > MAX_ROT_VEL:
            self.vrot = MAX_ROT_VEL
        elif self.vrot < -MAX_ROT_VEL:
            self.vrot = -MAX_ROT_VEL

        self.rot += self.vrot

        self.vx += self.thrust * -sin(radians(self.rot))
        if self.vx > MAX_VEL:
            self.vx = MAX_VEL
        elif self.vx < -MAX_VEL:
            self.vx = -MAX_VEL

        self.vy += self.thrust * cos(radians(self.rot))
        if self.vy > MAX_VEL:
            self.vy = MAX_VEL
        elif self.vy < -MAX_VEL:
            self.vy = -MAX_VEL

        self.vx *= VEL_DRAG_COEFFICIENT
        self.vy *= VEL_DRAG_COEFFICIENT
        self.vrot *= ROT_DRAG_COEFFICIENT

        self.x += self.vx
        self.y += self.vy

        if self.x > SIM_WIDTH:
            self.x = 0.0
        elif self.x < 0:
            self.x = SIM_WIDTH
        if self.y > SIM_HEIGHT:
            self.y = 0.0
        elif self.y < 0:
            self.y = SIM_HEIGHT

        if self.shooting and self.can_shoot:
            if len(self.bullets) >= MAX_BULLETS:
                self.bullets.remove(self.bullets[0])

            bullet = Bullet(self.x, self.y, self.vx, self.vy, self.rot)

            bullet_disposable = Observable.just(None)\
                    .delay(1000) \
                    .observe_on(pool_scheduler) \
                    .subscribe(on_completed=lambda: dispose_bullet())

            def dispose_bullet():
                self.bullets.remove(bullet)
                bullet_disposable.dispose()

            self.bullets.append(bullet)

            self.can_shoot = False

        for bullet in self.bullets:
            bullet.update()


class Bullet(object):
    def __init__(self, origin_x, origin_y, initial_vel_x, initial_vel_y, rotation):
        self.x = origin_x
        self.y = origin_y
        self.rotation = rotation
        self.vx = initial_vel_x + (BULLET_SPEED * -sin(radians(rotation)))
        self.vy = initial_vel_y + (BULLET_SPEED * cos(radians(rotation)))

    def update(self):
        self.x += self.vx
        self.y += self.vy

        if self.x > SIM_WIDTH:
            self.x = 0.0
        elif self.x < 0:
            self.x = SIM_WIDTH
        if self.y > SIM_HEIGHT:
            self.y = 0.0
        elif self.y < 0:
            self.y = SIM_HEIGHT


class Asteroid(object):
    def __init__(self, origin):
        self.shape = [(-30.0, -30.0), (-30.0, 30.0), (30.0, 30.0), (30.0, -30.0)]
        self.origin = origin

    def get_shape(self, scale_x, scale_y):
        return list(map(lambda point: (
            (
                (point[0] + self.origin[0]) * scale_x,
                (point[1] + self.origin[1]) * scale_y
            )
        ), self.shape))


class Simulation(object):
    def __init__(self):
        self.asteroids = list(map(lambda i: Asteroid((SIM_WIDTH / 3.0, SIM_HEIGHT / 3.0)), range(0, ASTEROIDS - 1)))
        self.ship = Ship()

    def get_shapes(self, scale_x, scale_y):
        shapes = []
        for asteroid in self.asteroids:
            shapes.append(asteroid.get_shape(scale_x, scale_y))
        shapes.append(self.ship.get_shape(scale_x, scale_y))
        for bullet in self.ship.bullets:
            shapes.append([
                ((bullet.x - BULLET_RADIUS) * scale_x, (bullet.y - BULLET_RADIUS) * scale_y),
                ((bullet.x + BULLET_RADIUS) * scale_x, (bullet.y + BULLET_RADIUS) * scale_y)])
        return shapes


controller = GuiController()


def key_down(event):
    if event.keysym == "Left":
        for sim in controller.simulations:
            sim.ship.angularTorque = -TORQUE
    if event.keysym == "Right":
        for sim in controller.simulations:
            sim.ship.angularTorque = TORQUE
    if event.keysym == "Up":
        for sim in controller.simulations:
            sim.ship.thrust = THRUST
    if event.keysym == "space":
        for sim in controller.simulations:
            sim.ship.shooting = True


def key_up(event):
    if event.keysym == "Left":
        for sim in controller.simulations:
            sim.ship.angularTorque = 0.0
    if event.keysym == "Right":
        for sim in controller.simulations:
            sim.ship.angularTorque = 0.0
    if event.keysym == "Up":
        for sim in controller.simulations:
            sim.ship.thrust = 0.0
    if event.keysym == "space":
        for sim in controller.simulations:
            sim.ship.shooting = False


root.bind('<KeyPress>', key_down)
root.bind('<KeyRelease>', key_up)
canvas = Canvas(root)
canvas.pack()


def update_sims():
    for sim in controller.simulations:
        sim.ship.update()

    canvas.pack(fill=BOTH, expand=1)

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    column_width = canvas_width / GRID_COLUMNS
    row_height = canvas_height / GRID_ROWS

    scale_x = column_width / SIM_WIDTH
    scale_y = row_height / SIM_HEIGHT

    return list(map(lambda sim: get_shapes(scale_x, scale_y, sim), controller.simulations))


def get_shapes(scale_x, scale_y, sim):
    return sim.get_shapes(scale_x, scale_y)


class State(object):
    def __init__(self):
        self.simulations = []

    def update_state(self, sims):
        self.simulations = sims


state = State()


def draw():
    canvas.delete("all")
    canvas.pack(fill=BOTH, expand=1)

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    column_width = canvas_width / GRID_COLUMNS
    row_height = canvas_height / GRID_ROWS

    sim_index = 0
    for sim in state.simulations:
        column = sim_index % GRID_COLUMNS
        row = int(sim_index / GRID_COLUMNS)

        column_origin = column * column_width
        row_origin = row * row_height

        canvas.create_line(column_origin, row_origin, column_origin + column_width, row_origin)
        canvas.create_line(column_origin + column_width, row_origin, column_origin + column_width,
                           row_origin + row_height)

        for shape in sim:
            previous_point = None
            for point in shape:
                if previous_point is not None:
                    canvas.create_line(previous_point[0] + column_origin, previous_point[1] + row_origin,
                                       point[0] + column_origin, point[1] + row_origin)
                if point == shape[-1]:
                    canvas.create_line(point[0] + column_origin, point[1] + row_origin,
                                       shape[0][0] + column_origin, shape[0][1] + row_origin)

                previous_point = point

        sim_index += 1


Observable.interval(1000 / PHYSICS_PER_SECOND) \
    .map(lambda i: update_sims()) \
    .observe_on(pool_scheduler) \
    .subscribe(on_next=lambda sims: state.update_state(sims))

Observable.interval(1000 / FRAMES_PER_SECOND) \
    .subscribe_on(pool_scheduler) \
    .observe_on(tkinter_scheduler) \
    .subscribe(on_next=lambda interval: draw())

root.mainloop()

model = keras.sequential([
    keras.layers.Dense(ASTEROIDS, input_dim=2, activation='relu'),
    keras.layers.Dense(ASTEROIDS * 2, activation='relu'),
    keras.layers.Dense(2, activation='sigmoid')
])