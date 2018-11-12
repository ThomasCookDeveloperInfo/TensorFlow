from Tkinter import *
from math import *

SIM_WIDTH = 800.0
SIM_HEIGHT = 600.0
ROT_DRAG_COEFFICIENT = 0.75
VEL_DRAG_COEFFICIENT = 0.9
MAX_ROT_VEL = 60.0
MAX_VEL = 30.0


class GuiController(object):
    def __init__(self):
        self.simulations = [Simulation()]


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

    def get_shape(self):
        return map(lambda point: (
            (
                point[0] * cos(radians(self.rot)) - point[1] * sin(radians(self.rot)),
                point[0] * sin(radians(self.rot)) + point[1] * cos(radians(self.rot))
            )
        ), self.shape)

    def update(self):
        self.vrot += self.angularTorque
        self.vrot *= ROT_DRAG_COEFFICIENT
        if self.vrot > MAX_ROT_VEL:
            self.vrot = MAX_ROT_VEL
        elif self.vrot < -MAX_ROT_VEL:
            self.vrot = -MAX_ROT_VEL

        self.rot += self.vrot

        self.vx += self.thrust * -sin(radians(self.rot))
        self.vx *= VEL_DRAG_COEFFICIENT
        if self.vx > MAX_VEL:
            self.vx = MAX_VEL

        self.vy += self.thrust * cos(radians(self.rot))
        self.vy *= VEL_DRAG_COEFFICIENT
        if self.vy > MAX_VEL:
            self.vy = MAX_VEL

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


class Simulation(object):
    def __init__(self):
        asteroid1 = Asteroid((SIM_WIDTH / 3.0, SIM_HEIGHT / 3.0))
        asteroid2 = Asteroid(((SIM_WIDTH / 3.0) * 2.0, (SIM_HEIGHT / 3.0) * 2.0))
        self.asteroids = [asteroid1, asteroid2]
        self.ship = Ship()

    def get_shapes(self, scale_x, scale_y):
        shapes = []
        for asteroid in self.asteroids:
            shapes.append(map(lambda point: ((point[0] + asteroid.origin[0]) * scale_x, (point[1] + asteroid.origin[1]) * scale_y),
                              asteroid.shape))
        shapes.append(map(lambda point: ((point[0] + self.ship.x) * scale_x, (point[1] + self.ship.y) * scale_y),
                          self.ship.get_shape()))
        return shapes


controller = GuiController()


def key_down(event):
    if event.keysym == "Left":
        for sim in controller.simulations:
            sim.ship.angularTorque = -5.0
    if event.keysym == "Right":
        for sim in controller.simulations:
            sim.ship.angularTorque = 5.0
    if event.keysym == "Up":
        for sim in controller.simulations:
            sim.ship.thrust = 10.0


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


root = Tk()
root.bind('<KeyPress>', key_down)
root.bind('<KeyRelease>', key_up)
canvas = Canvas(root)
canvas.pack()


def task():
    canvas.delete("all")
    canvas.pack(fill=BOTH, expand=1)

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    scale_x = canvas_width / SIM_WIDTH
    scale_y = canvas_height / SIM_HEIGHT

    for sim in controller.simulations:
        sim.ship.update()

        for shape in sim.get_shapes(scale_x, scale_y):
            previous_point = None
            for point in shape:
                if previous_point is not None:
                    canvas.create_line(previous_point[0], previous_point[1], point[0], point[1])
                if point == shape[-1]:
                    canvas.create_line(point[0], point[1], shape[0][0], shape[0][1])
                previous_point = point

    root.after(30, task)


root.after(30, task)
root.mainloop()
