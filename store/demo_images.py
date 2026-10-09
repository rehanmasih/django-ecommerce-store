"""Offline product-image generator for the demo store.

Internet image sources aren't always reachable, and the store must never show broken
images, so every demo product gets its own illustration drawn here with Pillow.
Nothing is downloaded and there are no third-party rights involved.
Each ``art_*`` function draws one kind of product on a 1000x1000 design grid.
"""
import math

from PIL import Image, ImageColor, ImageDraw, ImageFilter

S = 2        # supersampling factor (drawn at 2x, then scaled down for smooth edges)
GRID = 1000  # design coordinate space


def col(c):
    return ImageColor.getrgb(c) if isinstance(c, str) else c


def shade(c, f):
    """Lighten (f>0) or darken (f<0) a colour by a fraction."""
    r, g, b = col(c)[:3]
    t, k = (255, f) if f > 0 else (0, -f)
    return "#%02x%02x%02x" % tuple(int(v + (t - v) * k) for v in (r, g, b))


class Canvas:
    def __init__(self, top, bottom):
        size = (GRID * S, GRID * S)
        mask = Image.linear_gradient("L").resize(size)
        self.im = Image.composite(Image.new("RGB", size, col(bottom)), Image.new("RGB", size, col(top)), mask)
        self.d = ImageDraw.Draw(self.im, "RGBA")  # "RGBA" mode blends translucent fills

    def _b(self, box):
        return [v * S for v in box]

    def rr(self, box, r, fill=None, outline=None, w=0):
        self.d.rounded_rectangle(self._b(box), radius=r * S, fill=col(fill) if fill else None,
                                 outline=col(outline) if outline else None, width=int(w * S))

    def ell(self, box, fill=None, outline=None, w=0):
        self.d.ellipse(self._b(box), fill=col(fill) if fill else None,
                       outline=col(outline) if outline else None, width=int(w * S))

    def pie(self, box, a0, a1, fill):
        self.d.pieslice(self._b(box), a0, a1, fill=col(fill))

    def arc(self, box, a0, a1, fill, w):
        self.d.arc(self._b(box), a0, a1, fill=col(fill), width=int(w * S))

    def poly(self, pts, fill):
        self.d.polygon([(x * S, y * S) for x, y in pts], fill=col(fill))

    def line(self, pts, fill, w):
        self.d.line([(x * S, y * S) for x, y in pts], fill=col(fill), width=int(w * S), joint="curve")

    def shadow(self, cx, cy, rx, ry, alpha=85):
        mask = Image.new("L", self.im.size, 0)
        ImageDraw.Draw(mask).ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=alpha)
        mask = mask.filter(ImageFilter.GaussianBlur(16 * S))
        self.im.paste((20, 24, 32), mask=mask)

    def save(self, path, size=900):
        self.im.resize((size, size), Image.LANCZOS).save(path, "JPEG", quality=88, optimize=True)


def dashed(cv, p1, p2, color, w, dash=18, gap=12):
    (x1, y1), (x2, y2) = p1, p2
    length = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    for i in range(int(length // (dash + gap)) + 1):
        s, e = i * (dash + gap), min(i * (dash + gap) + dash, length)
        cv.line([(x1 + ux * s, y1 + uy * s), (x1 + ux * e, y1 + uy * e)], color, w)


# =============================================================== ELECTRONICS
def art_smartphone(cv, c, c2):
    cv.shadow(500, 900, 200, 26)
    cv.rr((320, 110, 680, 880), 58, "#1b1f27")
    cv.rr((336, 126, 664, 864), 46, c)
    cv.ell((380, 560, 640, 830), shade(c, .18))
    cv.ell((352, 640, 500, 800), shade(c2, -.05))
    cv.rr((450, 140, 550, 162), 11, "#0b0d12")
    icons = ["#ffffffe0", shade(c2, .1), shade(c, .55), shade(c2, -.25)]
    for r in range(3):
        for k in range(4):
            x, y = 360 + k * 74, 210 + r * 84
            cv.rr((x, y, x + 56, y + 56), 15, icons[(r + k) % 4])
    cv.rr((676, 300, 684, 400), 4, "#2a2f3a")


def art_laptop(cv, c, c2):
    cv.shadow(500, 790, 400, 28)
    cv.rr((200, 200, 800, 640), 28, "#2a2e37")
    cv.rr((218, 218, 782, 622), 14, c)
    cv.ell((240, 250, 540, 550), shade(c, .2))
    cv.ell((440, 340, 760, 610), shade(c2, -.05))
    cv.rr((200, 636, 800, 664), 8, "#1b1e25")
    cv.poly([(120, 664), (880, 664), (935, 750), (65, 750)], "#c9cdd6")
    cv.rr((65, 738, 935, 762), 12, "#a5aab5")
    cv.rr((420, 664, 580, 688), 10, "#aeb3be")
    for r in range(3):
        cv.line([(150 - r * 10, 676 + r * 22), (850 + r * 10, 676 + r * 22)], "#b4b9c4", 3)


def art_headphones(cv, c, c2):
    cv.shadow(500, 880, 280, 26)
    cv.arc((230, 140, 770, 760), 180, 360, "#22262e", 46)
    cv.arc((268, 178, 732, 722), 195, 345, c, 12)
    for x0, x1, cx0, cx1, px0, px1 in ((180, 340, 305, 365, 205, 300), (660, 820, 635, 695, 700, 795)):
        cv.rr((x0, 430, x1, 740), 64, c)
        cv.rr((px0, 520, px1, 650), 40, shade(c, .22))
        cv.rr((cx0, 470, cx1, 700), 30, shade(c, -.4))
    cv.ell((225, 560, 275, 610), shade(c2, 0))
    cv.ell((725, 560, 775, 610), shade(c2, 0))


def art_smartwatch(cv, c, c2):
    cv.shadow(500, 940, 180, 22)
    cv.rr((390, 40, 610, 430), 46, c2)
    cv.rr((390, 570, 610, 960), 46, c2)
    for i in range(4):
        cv.ell((490, 700 + i * 55, 510, 720 + i * 55), shade(c2, -.4))
    cv.rr((290, 270, 710, 730), 110, "#20242c")
    cv.rr((704, 400, 726, 470), 8, "#3a404c")
    cv.rr((320, 300, 680, 700), 86, "#06080b")
    b1, b2 = (365, 345, 635, 615), (410, 390, 590, 570)
    cv.arc(b1, 0, 360, "#26382d", 24)
    cv.arc(b1, -90, 170, c, 24)
    cv.arc(b2, 0, 360, "#3a2830", 22)
    cv.arc(b2, -90, 60, "#ff5e78", 22)
    cv.rr((430, 640, 570, 656), 8, "#ffffffd0")


def art_earbuds(cv, c, c2):
    cv.shadow(500, 860, 270, 26)
    cv.rr((270, 470, 730, 810), 120, c)
    cv.rr((270, 470, 730, 610), 100, shade(c, .14))
    cv.line([(285, 600), (715, 600)], shade(c, -.28), 6)
    cv.ell((478, 690, 522, 734), c2)
    for cx in (350, 650):
        cv.rr((cx - 24, 270, cx + 24, 445), 24, "#f4f5f8")
        cv.ell((cx - 72, 140, cx + 72, 300), "#f4f5f8")
        cv.ell((cx - 42, 180, cx + 42, 262), "#dde0e7")
        cv.ell((cx - 16, 204, cx + 16, 238), "#9aa0ad")


def art_speaker(cv, c, c2):
    cv.shadow(500, 780, 330, 28)
    cv.arc((380, 110, 620, 350), 180, 360, "#1b1e24", 22)
    cv.rr((190, 250, 810, 740), 150, c)
    for r in range(6):
        for k in range(15):
            x = 250 + k * 34 + (17 if r % 2 else 0)
            if x < 720:
                cv.ell((x, 300 + r * 52, x + 14, 314 + r * 52), shade(c, -.32))
    for i, x in enumerate((400, 490, 580)):
        cv.ell((x, 640, x + 58, 698), c2 if i == 0 else shade(c, .25))
    cv.rr((650, 660, 730, 680), 10, shade(c, .3))


def art_keyboard(cv, c, c2):
    cv.shadow(500, 770, 430, 26)
    cv.rr((70, 300, 930, 730), 44, c)
    offsets, counts = [0, 22, 34, 48], [13, 12, 11, 10]
    for r in range(4):
        for k in range(counts[r]):
            x, y = 90 + offsets[r] + k * 64, 330 + r * 74
            cv.rr((x, y, x + 56, y + 58), 11, c2 if (r == 0 and k == 0) else "#f1f3f7")
            cv.rr((x, y + 46, x + 56, y + 58), 8, "#d6dae2")
    cv.rr((110, 626, 220, 684), 11, "#f1f3f7")
    cv.rr((232, 626, 342, 684), 11, "#f1f3f7")
    cv.rr((354, 626, 660, 684), 11, "#f1f3f7")
    cv.rr((672, 626, 782, 684), 11, "#f1f3f7")
    cv.rr((794, 626, 904, 684), 11, "#f1f3f7")


def art_mouse(cv, c, c2):
    cv.shadow(500, 860, 200, 26)
    cv.rr((330, 140, 670, 860), 170, c)
    cv.ell((362, 190, 480, 430), shade(c, .2))
    cv.line([(500, 150), (500, 470)], shade(c, -.35), 8)
    cv.line([(340, 470), (660, 470)], shade(c, -.25), 5)
    cv.rr((476, 250, 524, 370), 24, "#20242c")
    cv.rr((484, 264, 516, 286), 8, c2)


# =============================================================== CLOTHING
TEE = [(420, 150), (290, 190), (130, 330), (215, 425), (290, 385), (290, 850), (710, 850),
       (710, 385), (785, 425), (870, 330), (710, 190), (580, 150)]
LONG = [(420, 190), (290, 230), (150, 420), (105, 800), (225, 825), (300, 500), (300, 860),
        (700, 860), (700, 500), (775, 825), (895, 800), (850, 420), (710, 230), (580, 190)]


def art_tshirt(cv, c, c2, mark=False):
    cv.shadow(500, 880, 310, 22)
    cv.poly(TEE, c)
    cv.poly([(500, 190), (710, 190), (870, 330), (785, 425), (710, 385), (710, 850), (500, 850)], "#00000012")
    cv.ell((425, 128, 575, 240), shade(c, -.45))
    cv.arc((425, 128, 575, 240), 5, 175, shade(c, -.18), 16)
    cv.line([(290, 815), (710, 815)], shade(c, -.14), 5)
    cv.line([(150, 350), (232, 440)], shade(c, -.14), 6)
    cv.line([(850, 350), (768, 440)], shade(c, -.14), 6)
    if mark:
        cv.ell((430, 420, 570, 560), c2)
        cv.ell((462, 452, 538, 528), shade(c, 0))


def art_hoodie(cv, c, c2):
    cv.shadow(500, 890, 330, 22)
    cv.poly(LONG, c)
    cv.poly([(500, 230), (710, 230), (850, 420), (895, 800), (775, 825), (700, 500), (700, 860), (500, 860)], "#00000012")
    cv.ell((345, 80, 655, 350), shade(c, -.08))
    cv.ell((398, 128, 602, 305), shade(c, -.5))
    cv.poly([(380, 610), (620, 610), (685, 790), (315, 790)], shade(c, -.1))
    cv.line([(380, 612), (318, 790)], shade(c, -.3), 5)
    cv.line([(620, 612), (682, 790)], shade(c, -.3), 5)
    cv.line([(456, 330), (446, 480)], "#eef0f4", 8)
    cv.line([(544, 330), (554, 480)], "#eef0f4", 8)
    cv.ell((438, 476, 456, 508), c2)
    cv.ell((544, 476, 562, 508), c2)
    cv.rr((300, 832, 700, 870), 10, shade(c, -.2))
    cv.poly([(105, 800), (225, 825), (215, 868), (92, 842)], shade(c, -.2))
    cv.poly([(895, 800), (775, 825), (785, 868), (908, 842)], shade(c, -.2))


def _collar(cv, c, y0=190):
    cv.poly([(420, y0), (580, y0), (500, 310)], shade(c, -.5))
    cv.poly([(420, y0 - 4), (500, 312), (388, 300), (338, y0 + 25)], shade(c, .2))
    cv.poly([(580, y0 - 4), (500, 312), (612, 300), (662, y0 + 25)], shade(c, .12))


def art_jacket(cv, c, c2):
    cv.shadow(500, 890, 330, 22)
    cv.poly(LONG, c)
    cv.poly([(500, 230), (710, 230), (850, 420), (895, 800), (775, 825), (700, 500), (700, 860), (500, 860)], "#00000012")
    _collar(cv, c)
    cv.line([(500, 312), (500, 860)], shade(c, -.3), 6)
    for y in (360, 470, 580, 690, 790):
        cv.ell((487, y, 513, y + 26), c2)
    for x0 in (345, 565):
        cv.rr((x0, 420, x0 + 92, 525), 8, shade(c, .05), outline=shade(c, -.3), w=4)
        cv.rr((x0, 420, x0 + 92, 462), 6, shade(c, -.1))
        cv.ell((x0 + 38, 452, x0 + 54, 468), c2)
    dashed(cv, (300, 838), (700, 838), shade(c2, .1), 4, 14, 10)
    cv.poly([(105, 800), (225, 825), (215, 868), (92, 842)], shade(c, -.2))
    cv.poly([(895, 800), (775, 825), (785, 868), (908, 842)], shade(c, -.2))


def art_pants(cv, c, c2, jogger=False):
    cv.shadow(500, 905, 300, 20)
    if jogger:
        pts = [(300, 120), (700, 120), (690, 880), (540, 880), (500, 420), (460, 880), (310, 880)]
    else:
        pts = [(300, 120), (700, 120), (735, 890), (535, 890), (500, 420), (465, 890), (265, 890)]
    cv.poly(pts, c)
    cv.poly([(500, 120), (700, 120)] + [p for p in pts[2:4]] + [(500, 420)], "#0000000f")
    cv.rr((300, 120, 700, 185), 12, shade(c, -.15))
    for x in (330, 420, 566, 656):
        cv.rr((x, 112, x + 14, 195), 4, shade(c, -.28))
    cv.line([(500, 185), (500, 420)], shade(c, -.3), 5)
    cv.line([(312, 210), (365, 310), (425, 335)], shade(c, -.3), 5)
    cv.line([(688, 210), (635, 310), (575, 335)], shade(c, -.3), 5)
    dashed(cv, (500, 190), (500, 400), c2, 3, 10, 8)
    if jogger:
        cv.rr((305, 830, 465, 885), 18, shade(c, -.2))
        cv.rr((535, 830, 695, 885), 18, shade(c, -.2))
        cv.line([(400, 150), (400, 230)], "#eef0f4", 6)
        cv.line([(600, 150), (600, 230)], "#eef0f4", 6)
    else:
        cv.line([(268, 855), (463, 855)], shade(c, -.2), 5)
        cv.line([(537, 855), (732, 855)], shade(c, -.2), 5)


def art_shirt(cv, c, c2, polo=False):
    cv.shadow(500, 890, 330, 22)
    if polo:
        cv.poly(TEE, c)
        cv.poly([(500, 190), (710, 190), (870, 330), (785, 425), (710, 385), (710, 850), (500, 850)], "#00000012")
        cv.line([(146, 350), (228, 440)], c2, 14)
        cv.line([(854, 350), (772, 440)], c2, 14)
        _collar(cv, c, 155)
        cv.rr((488, 300, 512, 520), 6, shade(c, -.12))
        for y in (330, 400, 470):
            cv.ell((490, y, 510, y + 20), "#f4f1e8")
    else:
        cv.poly(LONG, c)
        cv.poly([(500, 230), (710, 230), (850, 420), (895, 800), (775, 825), (700, 500), (700, 860), (500, 860)], "#00000012")
        _collar(cv, c)
        cv.rr((488, 312, 512, 860), 6, shade(c, -.1))
        for y in range(350, 850, 85):
            cv.ell((490, y, 510, y + 20), "#f4f1e8")
        cv.rr((570, 440, 665, 540), 8, outline=shade(c, -.25), w=4)
        cv.poly([(105, 800), (225, 825), (215, 868), (92, 842)], shade(c, -.15))
        cv.poly([(895, 800), (775, 825), (785, 868), (908, 842)], shade(c, -.15))
        for x in range(320, 700, 40):
            cv.line([(x, 250), (x, 850)], shade(c, .12), 2)


# =============================================================== SHOES
def _sole(cv, c2, top=600, tread="#f5f5f5"):
    cv.rr((150, top, 890, top + 92), 44, tread)
    cv.rr((150, top + 42, 890, top + 64), 8, c2)


def art_sneaker(cv, c, c2, sole="#f6f6f4", running=False):
    cv.shadow(500, 760, 400, 24)
    upper = [(170, 605), (175, 470), (235, 425), (350, 432), (405, 392), (470, 452),
             (610, 482), (790, 545), (865, 600), (870, 625), (170, 625)]
    cv.poly(upper, c)
    cv.poly([(640, 505), (790, 545), (865, 600), (870, 625), (640, 625)], shade(c, .1))
    cv.poly([(240, 430), (350, 436), (400, 398), (388, 462), (250, 470)], shade(c, -.55))
    cv.poly([(405, 392), (452, 410), (470, 470), (428, 462)], shade(c, .3))
    for i in range(4):
        t = i / 3
        x, y = 470 + t * 135, 452 + t * 38
        cv.line([(x - 14, y + 26), (x + 20, y - 20)], "#ffffff", 9)
    cv.line([(255, 575), (420, 540), (610, 555)], c2, 18 if running else 12)
    cv.rr((165, 480, 215, 565), 14, c2)
    _sole(cv, c2, 600, sole)
    if running:
        for x in range(200, 860, 60):
            cv.rr((x, 660, x + 30, 690), 8, shade(sole, -.12))


def art_formal(cv, c, c2):
    cv.shadow(500, 760, 400, 24)
    upper = [(190, 612), (195, 450), (270, 420), (400, 440), (520, 500), (700, 530), (830, 572),
             (882, 612), (882, 632), (190, 632)]
    cv.poly(upper, c)
    cv.poly([(270, 420), (400, 440), (362, 474), (285, 455)], shade(c, -.6))
    cv.line([(690, 532), (676, 628)], shade(c, -.35), 5)
    for i in range(4):
        x, y = 400 + i * 62, 462 + i * 20
        cv.line([(x, y), (x + 34, y + 16)], "#efe8dc", 7)
    cv.line([(290, 520), (520, 548)], "#ffffff55", 14)
    cv.rr((170, 626, 892, 664), 20, "#1f130b")
    cv.rr((170, 656, 340, 716), 10, "#1f130b")


def art_boot(cv, c, c2, chelsea=False):
    cv.shadow(500, 770, 400, 24)
    upper = [(250, 612), (255, 190), (450, 185), (460, 420), (610, 470), (790, 540), (860, 600),
             (865, 626), (250, 626)]
    cv.poly(upper, c)
    cv.rr((252, 175, 455, 225), 16, shade(c, -.55))
    cv.poly([(640, 505), (790, 542), (860, 602), (865, 626), (640, 626)], shade(c, .08))
    if chelsea:
        cv.poly([(255, 340), (455, 330), (452, 440), (255, 452)], "#20232a")
        cv.rr((300, 190, 334, 285), 8, shade(c, -.3))
        cv.line([(255, 452), (452, 440)], shade(c, -.4), 5)
    else:
        for i in range(6):
            y = 245 + i * 38
            cv.line([(372, y + 14), (458, y - 6)], "#efe8dc", 8)
            cv.ell((366, y + 8, 382, y + 24), c2)
    cv.rr((225, 604, 885, 706), 38, "#1d1f24")
    for x in range(255, 860, 52):
        cv.rr((x, 676, x + 28, 706), 8, c2)


# =============================================================== ACCESSORIES
def art_backpack(cv, c, c2):
    cv.shadow(500, 905, 270, 24)
    cv.arc((400, 70, 600, 250), 180, 360, shade(c, -.45), 24)
    cv.rr((190, 500, 300, 790), 40, shade(c, -.2))
    cv.rr((700, 500, 810, 790), 40, shade(c, -.2))
    cv.rr((260, 170, 740, 890), 150, c)
    cv.rr((310, 490, 690, 830), 84, shade(c, -.14))
    cv.line([(335, 520), (665, 520)], shade(c, -.5), 8)
    cv.rr((488, 505, 512, 585), 10, c2)
    cv.line([(300, 330), (700, 330)], shade(c, -.45), 8)
    cv.rr((488, 318, 512, 395), 10, c2)
    cv.rr((450, 660, 550, 712), 10, c2)
    cv.line([(300, 250), (700, 250)], shade(c, .15), 4)


def art_wallet(cv, c, c2):
    cv.shadow(500, 770, 350, 24)
    cv.rr((270, 210, 500, 350), 14, c2)
    cv.rr((340, 180, 580, 330), 14, "#e7ebf1")
    cv.rr((160, 290, 840, 730), 54, c)
    cv.rr((160, 290, 840, 480), 54, shade(c, .1))
    cv.line([(165, 480), (835, 480)], shade(c, -.32), 8)
    for a, b in (((195, 322), (805, 322)), ((805, 322), (805, 696)), ((805, 696), (195, 696)), ((195, 696), (195, 322))):
        dashed(cv, a, b, shade(c, .35), 4, 16, 10)
    cv.rr((465, 445, 535, 535), 14, "#d9b45c")
    cv.ell((488, 478, 512, 502), "#a88430")


def art_sunglasses(cv, c, c2):
    cv.shadow(500, 700, 380, 22)
    cv.rr((60, 405, 140, 455), 10, c)
    cv.rr((860, 405, 940, 455), 10, c)
    for x0 in (100, 520):
        cv.rr((x0, 350, x0 + 380, 630), 130, c)
        cv.rr((x0 + 26, 376, x0 + 354, 604), 108, c2)
        cv.rr((x0 + 26, 490, x0 + 354, 604), 100, "#00000030")
        cv.ell((x0 + 60, 402, x0 + 190, 470), "#ffffff38")
    cv.arc((430, 350, 570, 470), 180, 360, c, 24)


def art_belt(cv, c, c2):
    cv.shadow(500, 880, 300, 20)
    cv.ell((200, 170, 800, 830), outline=c, w=112)
    cv.ell((214, 184, 786, 816), outline=shade(c, .3), w=4)
    cv.ell((296, 266, 704, 734), outline=shade(c, .3), w=4)
    for a in range(130, 231, 20):
        x, y = 500 + 245 * math.cos(math.radians(a)), 500 + 275 * math.sin(math.radians(a))
        cv.ell((x - 10, y - 10, x + 10, y + 10), shade(c, -.55))
    cv.rr((690, 390, 840, 610), 18, outline=c2, w=24)
    cv.line([(705, 500), (830, 500)], c2, 16)


def art_cap(cv, c, c2):
    cv.shadow(520, 760, 340, 26)
    cv.pie((190, 210, 720, 750), 180, 360, c)
    cv.pie((190, 210, 720, 750), 250, 360, "#0000000e")
    cv.arc((300, 210, 610, 750), 180, 360, shade(c, -.28), 6)
    cv.arc((400, 210, 520, 750), 180, 360, shade(c, -.28), 6)
    cv.rr((190, 462, 730, 500), 12, shade(c, -.14))
    cv.poly([(640, 468), (790, 452), (930, 485), (972, 530), (940, 556), (700, 526), (640, 505)], shade(c, -.12))
    cv.poly([(700, 500), (930, 520), (940, 556), (700, 526)], shade(c, -.32))
    cv.ell((440, 196, 486, 240), shade(c, -.3))
    cv.ell((520, 320, 610, 410), c2)
    cv.ell((546, 346, 584, 384), c)


def art_watch(cv, c, c2):
    cv.shadow(500, 950, 190, 20)
    cv.rr((410, 10, 590, 410), 30, c2)
    cv.rr((410, 590, 590, 990), 30, c2)
    dashed(cv, (430, 30), (430, 380), shade(c2, .35), 3, 12, 8)
    dashed(cv, (570, 30), (570, 380), shade(c2, .35), 3, 12, 8)
    dashed(cv, (430, 620), (430, 970), shade(c2, .35), 3, 12, 8)
    dashed(cv, (570, 620), (570, 970), shade(c2, .35), 3, 12, 8)
    for i in range(4):
        cv.ell((490, 720 + i * 55, 510, 740 + i * 55), shade(c2, -.45))
    cv.rr((735, 478, 765, 522), 7, "#a9adb6")
    cv.ell((260, 260, 740, 740), "#c8ccd4")
    cv.ell((282, 282, 718, 718), "#eef0f4")
    cv.ell((300, 300, 700, 700), c)
    for i in range(12):
        a = math.radians(i * 30)
        r1, r2 = (160, 195) if i % 3 == 0 else (172, 195)
        cv.line([(500 + r1 * math.sin(a), 500 - r1 * math.cos(a)), (500 + r2 * math.sin(a), 500 - r2 * math.cos(a))], "#f4f4f4", 10 if i % 3 == 0 else 5)
    cv.line([(500, 500), (500, 355)], "#ffffff", 12)
    cv.line([(500, 500), (596, 545)], "#ffffff", 10)
    cv.line([(500, 520), (430, 590)], "#e0523b", 5)
    cv.ell((484, 484, 516, 516), "#e0523b")


# =============================================================== HOME & KITCHEN
def art_coffee(cv, c, c2):
    cv.shadow(500, 885, 310, 24)
    cv.rr((200, 810, 800, 878), 18, c)
    cv.rr((580, 190, 780, 850), 36, c)
    cv.rr((210, 170, 780, 340), 44, c)
    cv.rr((250, 320, 570, 362), 12, shade(c, -.35))
    cv.rr((380, 350, 430, 382), 8, shade(c, -.5))
    cv.line([(405, 384), (405, 545)], "#6b4028", 8)
    cv.arc((170, 570, 310, 780), 90, 270, "#1b1e24", 22)
    cv.poly([(285, 545), (525, 545), (540, 805), (270, 805)], "#d6e4ec")
    cv.poly([(278, 660), (532, 660), (540, 805), (270, 805)], "#4a2c1a")
    cv.rr((280, 520, 530, 552), 10, "#1b1e24")
    cv.line([(305, 580), (312, 780)], "#ffffff80", 10)
    cv.rr((620, 235, 745, 300), 10, "#0d1f1c")
    cv.rr((640, 255, 725, 268), 5, c2)
    for x in (620, 690):
        cv.ell((x, 400, x + 56, 456), c2 if x == 620 else shade(c, .3))


def art_blender(cv, c, c2):
    cv.shadow(500, 895, 270, 24)
    cv.arc((640, 170, 790, 500), 270, 90, "#20242c", 28)
    cv.poly([(330, 110), (670, 110), (628, 615), (372, 615)], "#dbe7ee")
    cv.poly([(347, 330), (653, 330), (628, 615), (372, 615)], c2)
    cv.line([(395, 160), (415, 570)], "#ffffffaa", 14)
    cv.rr((312, 68, 688, 126), 16, "#20242c")
    cv.rr((465, 34, 535, 80), 14, "#20242c")
    cv.poly([(360, 615), (640, 615), (685, 885), (315, 885)], c)
    cv.rr((298, 598, 702, 650), 14, shade(c, -.3))
    cv.ell((445, 705, 555, 815), "#0d0f14")
    cv.ell((468, 728, 532, 792), c2)
    cv.rr((395, 835, 605, 858), 10, shade(c, -.25))


def art_cookware(cv, c, c2):
    cv.shadow(500, 870, 400, 26)
    cv.rr((150, 390, 560, 790), 44, c)
    cv.rr((190, 460, 216, 750), 12, "#ffffff34")
    cv.rr((105, 480, 160, 522), 14, "#1c1f25")
    cv.ell((138, 330, 572, 440), shade(c, .2))
    cv.rr((326, 290, 384, 336), 16, "#1c1f25")
    body = shade(c, -.16)
    cv.rr((520, 530, 790, 810), 36, body)
    cv.ell((520, 505, 790, 560), shade(c, .25))
    cv.ell((534, 512, 776, 550), "#20242b")
    cv.rr((780, 590, 970, 628), 16, "#1c1f25")
    cv.rr((550, 590, 574, 780), 12, "#ffffff30")
    cv.rr((520, 740, 790, 770), 4, c2)


def art_lamp(cv, c, c2):
    cv.shadow(500, 885, 210, 22)
    cv.poly([(350, 150), (650, 150), (770, 470), (230, 470)], c)
    cv.poly([(350, 150), (500, 150), (500, 470), (230, 470)], shade(c, .16))
    cv.ell((350, 128, 650, 176), shade(c, -.12))
    cv.ell((230, 440, 770, 500), "#f8dc8f")
    cv.rr((484, 480, 516, 770), 8, "#2b2f38")
    cv.rr((465, 590, 535, 640), 12, c2)
    cv.rr((350, 745, 650, 820), 40, "#2b2f38")
    cv.rr((375, 752, 625, 768), 8, "#ffffff22")


def art_organizer(cv, c, c2):
    cv.shadow(500, 790, 390, 24)
    cv.rr((120, 290, 880, 770), 40, c)
    cv.rr((150, 322, 340, 738), 22, shade(c, -.3))
    cv.rr((354, 322, 544, 738), 22, shade(c, -.3))
    cv.rr((558, 322, 738, 738), 22, shade(c, -.3))
    cv.rr((752, 322, 850, 738), 22, shade(c, -.3))
    cv.line([(245, 345), (245, 600)], "#2b2f38", 16)
    cv.rr((205, 540, 285, 680), 26, c2)
    cv.line([(449, 350), (449, 590)], "#d1a266", 16)
    cv.ell((404, 570, 494, 700), "#d1a266")
    for dx in (-24, 0, 24):
        cv.line([(648 + dx, 380), (648 + dx, 640)], "#d6dae2", 9)
    cv.rr((600, 620, 696, 660), 12, "#b8bdc7")
    cv.rr((770, 360, 830, 710), 26, "#c08a4d")


def art_bottle(cv, c, c2):
    cv.shadow(500, 905, 160, 24)
    cv.arc((455, 30, 545, 140), 180, 360, "#20242c", 14)
    cv.rr((380, 240, 620, 890), 84, c)
    cv.rr((410, 110, 590, 262), 30, "#20242c")
    cv.rr((392, 236, 608, 280), 18, shade(c, -.28))
    cv.rr((380, 520, 620, 566), 0, c2)
    cv.rr((410, 310, 442, 830), 16, "#ffffff40")
    cv.rr((470, 640, 540, 700), 10, shade(c, .25))


def art_dinnerset(cv, c, c2):
    cv.shadow(500, 870, 410, 26)
    for i in range(3):
        y = 630 - i * 48
        cv.ell((100, y, 590, y + 175), "#f8f8f6")
        cv.ell((100, y, 590, y + 175), outline=c2, w=8)
        cv.ell((155, y + 24, 535, y + 150), "#ebebe7")
    cv.pie((560, 420, 910, 860), 0, 180, "#f8f8f6")
    cv.ell((560, 600, 910, 690), "#e8e8e3")
    cv.ell((578, 611, 892, 679), "#d3dae2")
    cv.line([(566, 650), (904, 650)], c2, 6)
    cv.arc((372, 455, 466, 560), 270, 90, c, 16)
    cv.rr((262, 440, 404, 628), 26, c)
    cv.ell((262, 428, 404, 468), shade(c, -.32))


def art_kettle(cv, c, c2):
    cv.shadow(500, 890, 270, 24)
    cv.arc((600, 290, 830, 710), 270, 90, "#20242c", 36)
    cv.poly([(300, 450), (165, 285), (212, 262), (330, 380)], c)
    cv.rr((290, 320, 710, 840), 130, c)
    cv.rr((280, 785, 720, 880), 32, "#20242c")
    cv.rr((330, 282, 670, 350), 30, shade(c, -.16))
    cv.ell((468, 222, 532, 296), "#20242c")
    cv.rr((476, 430, 524, 750), 12, "#dbe7ee")
    cv.rr((476, 590, 524, 750), 12, "#6fb3d8")
    cv.rr((322, 380, 354, 770), 16, "#ffffff40")
    cv.ell((470, 800, 530, 860), c2)


ART = {
    "smartphone": art_smartphone, "laptop": art_laptop, "headphones": art_headphones,
    "smartwatch": art_smartwatch, "earbuds": art_earbuds, "speaker": art_speaker,
    "keyboard": art_keyboard, "mouse": art_mouse,
    "tshirt": art_tshirt, "hoodie": art_hoodie, "jacket": art_jacket, "pants": art_pants, "shirt": art_shirt,
    "sneaker": art_sneaker, "formal": art_formal, "boot": art_boot,
    "backpack": art_backpack, "wallet": art_wallet, "sunglasses": art_sunglasses, "belt": art_belt,
    "cap": art_cap, "watch": art_watch,
    "coffee": art_coffee, "blender": art_blender, "cookware": art_cookware, "lamp": art_lamp,
    "organizer": art_organizer, "bottle": art_bottle, "dinnerset": art_dinnerset, "kettle": art_kettle,
}

BACKDROPS = {  # soft studio backdrops per category (top, bottom)
    "electronics": ("#eef2fa", "#cfd9ec"),
    "clothing": ("#f4f0ec", "#ddd3ca"),
    "shoes": ("#eaf3f0", "#c9ded7"),
    "accessories": ("#f3edf5", "#d9cce0"),
    "home-kitchen": ("#f6f1e6", "#e0d6bf"),
}


def render_product_image(art, path, category_slug, colors=None, **options):
    top, bottom = BACKDROPS[category_slug]
    canvas = Canvas(top, bottom)
    colors = colors or ("#3b5bdb", "#ffd166")
    ART[art](canvas, colors[0], colors[1], **options)
    canvas.save(path)
