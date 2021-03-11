#!/usr/bin/env python

import argparse
import math
from math import sin, cos

import skimage.draw
import skimage.io
import skimage.transform


def make_thread_art(image_path, on_next_line, pins_count=200, threshold=15, start_pin=None,
                    max_radius=500, scale=1.0, min_radius=200):
    pixels = skimage.io.imread(image_path, True)
    pixels = skimage.util.invert(pixels)
    pixels = skimage.util.img_as_ubyte(pixels)

    height, width = pixels.shape
    radius = min(width, height) // 2

    if radius < min_radius:
        scale = min_radius / radius

    if radius > max_radius:
        scale = max_radius / radius

    if scale != 1.0:
        skimage.transform.rescale(pixels, scale)
        height, width = pixels.shape
        radius = min(width, height) // 2

    center_x = (width - 1) // 2
    center_y = (height - 1) // 2

    pins = []
    for n in range(pins_count):
        angle = math.pi / 2 - math.pi * 2 * n / pins_count
        pins.append((-int(sin(angle) * radius + center_y), int(cos(angle) * radius + center_x)))

    if start_pin is None:
        start_pin = max(range(pins_count), key=lambda pin: pixels[pins[pin]])

    lines_set = set([(n, n) for n in range(pins_count)])
    cur_pin = start_pin

    while True:
        def process_pin(pin):
            line = skimage.draw.line(*pins[cur_pin], *pins[pin])
            yy, xx = line
            avg_sum = sum(pixels[yy, xx]) // len(yy)
            return pin, avg_sum, line

        try_pins = (
            pin for pin in range(pins_count)
            if ((cur_pin, pin) not in lines_set and (pin, cur_pin) not in lines_set)
        )

        guess = map(process_pin, try_pins)

        best_pin, best_avg, best_line = max(guess, key=lambda g: g[1])

        if best_avg < threshold:
            break

        lines_set.add((cur_pin, best_pin))

        if on_next_line:
            on_next_line(cur_pin, best_pin)

        pixels[best_line] = 0

        cur_pin = best_pin


class TurtlePreviewEdgeHandler:
    def __init__(self, pins_count=200, radius=500):
        import turtle
        self.turtle = turtle

        self.turtle.tracer(False)

        self.pins = []

        for n in range(pins_count):
            angle = math.pi / 2 - math.pi * 2 * n / pins_count
            pin = int(cos(angle) * radius), int(sin(angle) * radius)
            self.pins.append(pin)

            self.turtle.pu()
            self.turtle.goto(*pin)
            self.turtle.pd()
            self.turtle.dot(10, "red")

        self.turtle.update()

    def draw_edge(self, pin1, pin2):
        self.turtle.pu()
        self.turtle.goto(*self.pins[pin1 - 1])
        self.turtle.pd()
        self.turtle.goto(*self.pins[pin2 - 1])
        self.turtle.update()

        print(pin1 + 1, pin2 + 1)

    def done(self):
        self.turtle.done()


class StdOutEdgeHandler:
    def draw_edge(self, pin1, pin2):
        print(pin1 + 1, pin2 + 1)

    def done(self):
        pass


parser = argparse.ArgumentParser()
parser.add_argument("image", help="image file", type=str)
parser.add_argument("-p", "--pins", default=200, help="Pins count", type=int, dest='pins_count')
parser.add_argument("-t", "--threshold", default=20, help="Fill threshold", type=int, dest='threshold')
parser.add_argument("-s", "--start", default=None, help="Start pin", type=int, dest='start_pin')
parser.add_argument("--max-radius", default=500, help="Max art radius", type=int, dest='max_radius')
parser.add_argument("--min-radius", default=200, help="Min art radius", type=int, dest='min_radius')
parser.add_argument("-x", "--scale", default=1.0, help="Image scale factor", type=float, dest='scale')
parser.add_argument("-v", "--preview", action='store_true', help="Image scale factor", dest='preview')
parser.add_argument("--preview-radius", default=500, help="Preview radius", type=int, dest='preview_radius')


args = parser.parse_args()

edge_handler = None

if args.preview:
    edge_handler = TurtlePreviewEdgeHandler(pins_count=args.pins_count, radius=args.preview_radius)
else:
    edge_handler = StdOutEdgeHandler()


make_thread_art(args.image, edge_handler.draw_edge,
                pins_count=args.pins_count, threshold=args.threshold, start_pin=args.start_pin,
                max_radius=args.max_radius, min_radius=args.min_radius, scale=args.scale)

edge_handler.done()
