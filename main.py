#!/usr/bin/env python

import argparse
import math
from math import sin, cos

import skimage.draw
import skimage.io
import skimage.transform
import skimage.exposure
import skimage.filters

import numpy


def make_thread_art(image_path, on_next_line, pins_count=200, start_pin=None, lines_limit=3000,
                    dst_mul_start=1.0, dst_mul_end=1.0, eq_clip=1.0, pin_mul=0.5,
                    max_radius=1000, scale=1.0, min_radius=200, debug=False, save_name=None):

    src_image = skimage.io.imread(image_path, True)

    height, width = src_image.shape
    radius = min(width, height) // 2

    if radius < min_radius:
        scale = min_radius / radius

    if radius > max_radius:
        scale = max_radius / radius

    if scale != 1.0:
        skimage.transform.rescale(src_image, scale)
        height, width = src_image.shape
        radius = min(width, height) // 2

    center_x = (width - 1) // 2
    center_y = (height - 1) // 2

    src_image = skimage.exposure.equalize_adapthist(src_image, clip_limit=eq_clip)
    src_image = skimage.util.img_as_ubyte(src_image)
    dst_image = numpy.zeros(src_image.shape, dtype=numpy.ubyte) + 255

    pins = []
    for n in range(pins_count):
        angle = math.pi / 2 - math.pi * 2 * n / pins_count
        pins.append((-int(sin(angle) * radius + center_y), int(cos(angle) * radius + center_x)))

    if start_pin is None:
        start_pin = max(range(pins_count), key=lambda pin: src_image[pins[pin]])

    lines_set = set([(n, n) for n in range(pins_count)])
    cur_pin = start_pin

    save_count = 0

    line_count = 0

    pin_line_count = {n: 0 for n in range(pins_count)}

    while True:
        dst_multiplier = dst_mul_start + (dst_mul_end - dst_mul_start) * line_count / lines_limit

        def process_pin(pin):
            line = skimage.draw.line(*pins[cur_pin], *pins[pin])

            src_line = src_image[line]
            dst_line = dst_image[line]

            src_avg = numpy.average(src_line)
            dst_avg = numpy.average(dst_line)

            pin_penalty = pin_line_count[pin] * pin_mul

            score = dst_avg * dst_multiplier - src_avg - pin_penalty
            return score, pin, line

        try_pins = (
            pin for pin in range(pins_count)
            if ((cur_pin, pin) not in lines_set and (pin, cur_pin) not in lines_set)
        )

        if not try_pins:
            break

        guess = map(process_pin, try_pins)

        best_score, best_pin, best_line = max(guess, key=lambda g: g[0])

        lines_set.add((cur_pin, best_pin))
        line_count += 1
        pin_line_count[cur_pin] += 1
        pin_line_count[best_pin] += 1

        if debug:
            print("{:.02f} ".format(dst_multiplier), end="")

        if on_next_line:
            on_next_line(cur_pin, best_pin, best_score)

        dst_image[best_line] = 0

        if save_name and (line_count % 300) == 0:
            skimage.io.imsave("{}_{:03d}.png".format(save_name, save_count), dst_image)
            save_count += 1

        if line_count >= lines_limit:
            break

        cur_pin = best_pin

    if save_name:
        skimage.io.imsave("{}_{:03d}.png".format(save_name, save_count), dst_image)


class TurtlePreviewEdgeHandler:
    def __init__(self, pins_count=200, radius=500, debug=False):
        import turtle
        self.turtle = turtle

        self.turtle.tracer(False)

        self.frame_count = 0

        self.pins = []

        self.debug = debug

        for n in range(pins_count):
            angle = math.pi / 2 - math.pi * 2 * n / pins_count
            pin = int(cos(angle) * radius), int(sin(angle) * radius)
            self.pins.append(pin)

            self.turtle.pu()
            self.turtle.goto(*pin)
            self.turtle.pd()
            self.turtle.dot(10, "red")

        self.turtle.update()

    def draw_edge(self, pin1, pin2, score):
        self.turtle.pu()
        self.turtle.goto(*self.pins[pin1 - 1])
        self.turtle.pd()
        self.turtle.goto(*self.pins[pin2 - 1])
        self.turtle.update()

        print(pin1 + 1, pin2 + 1)

    def done(self):
        self.turtle.done()


class StdOutEdgeHandler:
    def __init__(self, debug):
        self.debug = debug

    def draw_edge(self, pin1, pin2):
        print(pin1 + 1, pin2 + 1)

    def done(self):
        pass


parser = argparse.ArgumentParser()
parser.add_argument("image", help="image file", type=str)
parser.add_argument("-p", "--pins", default=200, help="Pins count", type=int, dest='pins_count')
parser.add_argument("-l", "--lines", default=100000, help="Lines count limit", type=int, dest='lines_limit')
parser.add_argument("-s", "--start", default=None, help="Start pin", type=int, dest='start_pin')
parser.add_argument("--max-radius", default=1000, help="Max art radius", type=int, dest='max_radius')
parser.add_argument("--min-radius", default=200, help="Min art radius", type=int, dest='min_radius')
parser.add_argument("-c", "--scale", default=1.0, help="Image scale factor", type=float, dest='scale')
parser.add_argument("-v", "--preview", action='store_true', help="Image scale factor", dest='preview')
parser.add_argument("--preview-radius", default=500, help="Preview radius", type=int, dest='preview_radius')
parser.add_argument("--debug", action='store_true', help="Debug using scikit plots", dest='debug')
parser.add_argument("--save", default=None, help="Save previews", dest='save_name')
parser.add_argument("--dms", "--dst-mul-start", default=1.0, help="Destination multiplier start", dest='dst_mul_start', type=float)
parser.add_argument("--dme", "--dst-mul-end", default=1.0, help="Destination multiplier end", dest='dst_mul_end', type=float)
parser.add_argument("--eq-clip", default=1.0, help="Equalizer clip limit", dest='eq_clip', type=float)
parser.add_argument("--pm", "--pin-mul", default=0.5, help="Pin penalty multiplier", dest='pin_mul', type=float)


args = parser.parse_args()

edge_handler = None

if args.preview:
    edge_handler = TurtlePreviewEdgeHandler(pins_count=args.pins_count, radius=args.preview_radius, debug=args.debug)
else:
    edge_handler = StdOutEdgeHandler(debug=args.debug)


make_thread_art(args.image, edge_handler.draw_edge,
                pins_count=args.pins_count, lines_limit=args.lines_limit, start_pin=args.start_pin,
                max_radius=args.max_radius, min_radius=args.min_radius, scale=args.scale, eq_clip=args.eq_clip,
                dst_mul_start=args.dst_mul_start, dst_mul_end=args.dst_mul_end, pin_mul=args.pin_mul,
                debug=args.debug, save_name=args.save_name)

edge_handler.done()
