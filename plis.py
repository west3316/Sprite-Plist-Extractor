#! /usr/lical/bin/python
import os
import sys
from PIL import Image
from xml.etree import ElementTree
import json
import plistlib


def tree_to_dict(tree):
    d = {}
    for index, item in enumerate(tree):
        if item.tag == 'key':
            if tree[index + 1].tag == 'string':
                d[item.text] = tree[index + 1].text
            elif tree[index + 1].tag == 'true':
                d[item.text] = True
            elif tree[index + 1].tag == 'false':
                d[item.text] = False
            elif tree[index + 1].tag == 'dict':
                d[item.text] = tree_to_dict(tree[index + 1])
    return d


def frames_from_data(filename, format):
    if format == 'plist':
        data_filename = filename + '.plist'
        root = ElementTree.fromstring(open(data_filename, 'r').read())
        plist_dict = tree_to_dict(root[0])
        to_list = lambda x: x.replace('{', '').replace('}', '').split(',')
        frames = plist_dict['frames'].items()
        for k, v in frames:
            frame = v
            rectlist = to_list(frame['frame'])
            width = int(rectlist[3] if frame['rotated'] else rectlist[2])
            height = int(rectlist[2] if frame['rotated'] else rectlist[3])
            frame['box'] = (
                int(rectlist[0]),
                int(rectlist[1]),
                int(rectlist[0]) + width,
                int(rectlist[1]) + height
            )
            real_rectlist = to_list(frame['sourceSize'])
            real_width = int(real_rectlist[1] if frame['rotated'] else real_rectlist[0])
            real_height = int(real_rectlist[0] if frame['rotated'] else real_rectlist[1])
            real_sizelist = [real_width, real_height]
            frame['real_sizelist'] = real_sizelist
            offsetlist = to_list(frame['offset'])
            offset_x = int(offsetlist[1] if frame['rotated'] else offsetlist[0])
            offset_y = int(offsetlist[0] if frame['rotated'] else offsetlist[1])
            frame['result_box'] = (
                int((real_sizelist[0] - width) / 2 + offset_x),
                int((real_sizelist[1] - height) / 2 + offset_y),
                int((real_sizelist[0] + width) / 2 + offset_x),
                int((real_sizelist[1] + height) / 2 + offset_y)
            )
        return frames

    elif format == 'json':
        data_filename = filename + '.json'
        json_data = open(data_filename)
        data = json.load(json_data)
        frames = {}
        for f in data['frames']:
            x = int(f["frame"]["x"])
            y = int(f["frame"]["y"])
            w = int(f["frame"]["h"] if f['rotated'] else f["frame"]["w"])
            h = int(f["frame"]["w"] if f['rotated'] else f["frame"]["h"])
            real_w = int(f["sourceSize"]["h"] if f['rotated'] else f["sourceSize"]["w"])
            real_h = int(f["sourceSize"]["w"] if f['rotated'] else f["sourceSize"]["h"])
            d = {
                'box': (
                    x,
                    y,
                    x + w,
                    y + h
                ),
                'real_sizelist': [
                    real_w,
                    real_h
                ],
                'result_box': (
                    int((real_w - w) / 2),
                    int((real_h - h) / 2),
                    int((real_w + w) / 2),
                    int((real_h + h) / 2)
                ),
                'rotated': f['rotated']
            }
            frames[f["filename"]] = d
        json_data.close()
        return frames.items()
    elif format == 'xml':
        data_filename = filename + '.xml'
        data = ElementTree.parse(data_filename).getroot()
        print(data.get("imagePath"))
        data2 = data.findall('SubTexture')
        frames = {}
        for f in data:
            print(f.get('name'))
            x = int(f.get('x'))
            y = int(f.get('y'))
           
            if 'rotated' not in f.attrib:
                rotated = False
            else:
                rotated = True

            w = int(f.get('width'))
            h = int(f.get('height'))

            if 'frameHeight' in f.attrib:
                real_w = int(f.get('frameHeight') if rotated else f.get('frameWidth'))
                real_h = int(f.get('frameWidth') if rotated else f.get('frameHeight'))
            else:
                real_w = w;
                real_h = h;
            d = {
                'box': (
                    x,
                    y,
                    x + w,
                    y + h
                ),
                'real_sizelist': [
                    real_w,
                    real_h
                ],
                'result_box': (
                    int((real_w - w) / 2),
                    int((real_h - h) / 2),
                    int((real_w + w) / 2),
                    int((real_h + h) / 2)
                ),
                'rotated': rotated
            }
            frames[f.get('name')] = d
        return frames.items()
    elif format == 'cocos':
        data_filename = filename + ".plist"
        pl = plistlib.readPlist(data_filename)
        data = pl['frames'].items()
        frames = {}
        for k, f in data:
            x = int(f["x"])
            y = int(f["y"])
            w = int(f["width"])
            h = int(f["height"])
            real_w = int(f["originalWidth"])
            real_h = int(f["originalHeight"])
            d = {
                'box': (
                    x,
                    y,
                    x + w,
                    y + h
                ),
                'real_sizelist': [
                    real_w,
                    real_h
                ],
                'result_box': (
                    int((real_w - w) / 2),
                    int((real_h - h) / 2),
                    int((real_w + w) / 2),
                    int((real_h + h) / 2)
                ),
                'rotated': False
            }
            frames[k] = d
        return frames.items()
    else:
        print("Wrong data format on parsing: '" + format + "'!")
        exit(1)


def gen_png_from_data(filename, format):
    big_image = Image.open(filename + ".png")
    frames = frames_from_data(filename, format)
    for k, v in frames:
        frame = v
        print v;
        box = frame['box']
        rect_on_big = big_image.crop(box)
        real_sizelist = frame['real_sizelist']
        if frame['rotated']:
            width, height = real_sizelist
            max_value = max(width, height)
            result_image = Image.new('RGBA', (max_value, max_value), (0, 0, 0, 0))
        else:
            result_image = Image.new('RGBA', real_sizelist, (0, 0, 0, 0))

        result_box = frame['result_box']
        result_image.paste(rect_on_big, result_box, mask=0)
        if frame['rotated']:
            result_image = result_image.rotate(90)
            real_sizelist = (result_box[0], result_box[1], result_box[3], result_box[2])
            result_image = result_image.crop(real_sizelist)
        outfile = (filename + '/' + k).replace('gift_', '') + '.png'
        dirname = os.path.dirname(outfile)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        print(outfile, "generated")
        print result_image.format, result_image.size, result_image.mode
        result_image.save(outfile)


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print("You must pass filename as the first parameter!")
        exit(1)
    filename = sys.argv[1]

    format = 'plist'
    ext = '.plist'
    if len(sys.argv) < 3:
        print("No data format passed, assuming .plist")
    else:
        format = sys.argv[2]

    if format == 'plist':
        print(".plist data format passed")
    elif format == 'json':
        ext = '.json'
        print(".json data format passed")
    elif format == 'xml':
        ext = '.xml'
        print(".xml data format passed")
    elif format == 'cocos':
        print(".cocos data format passed")
    else:
        print("Wrong data format passed '" + format + "'!")
        exit(1)

    data_filename = filename + ext
    png_filename = filename + '.png'
    if os.path.exists(data_filename) and os.path.exists(png_filename):
        gen_png_from_data(filename, format)
    else:
        print("Make sure you have both " + data_filename + " and " + png_filename + " files in the same directory")
