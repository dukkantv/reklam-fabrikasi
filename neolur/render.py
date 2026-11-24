# Gizli Tarih "Ne Olur?" Shorts – kodla çizilen 9:16 video (şehir silüeti + zaman çizelgesi + yazılar).
# Kullanım: python render.py bolum.json zaman.json cikti_klasoru        (sahne_*.mp4 dosyalarını üretir)
#           python render.py bolum.json zaman.json cikti_klasoru kare 1.0 5.5 ...   (kontrol kareleri)
import json, math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F_BLACK = os.path.join(KOK, "arena", "fonts", "InterDisplay-Black.otf")
F_BOLD = os.path.join(KOK, "arena", "fonts", "InterDisplay-Bold.otf")
YEL, WHT, RED = (255, 206, 46), (245, 245, 245), (255, 77, 77)
_fc = {}


def font(p, s):
    if (p, s) not in _fc:
        _fc[(p, s)] = ImageFont.truetype(p, s)
    return _fc[(p, s)]


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


class Video:
    def __init__(self, bolum, zaman):
        self.b, self.z = bolum, zaman
        self.efekt = bolum.get("efekt", "normal")
        self.sahneler = []
        t = 0.0
        for i, s in enumerate(bolum["sahneler"]):
            ad = f"{i:02d}_{s['tip']}"
            zz = zaman[ad]
            self.sahneler.append(dict(s, ad=ad, bas=t, sure=zz["sure"], gorun=zz["gorun"]))
            t += zz["sure"]
        self.toplam = t
        self.an = zaman["an"]                      # olayın gerçekleştiği an (kancada)
        asamalar = [s for s in self.sahneler if s["tip"] == "asama"]
        self.asama_bas = [s["bas"] for s in asamalar] + [self.toplam]
        vur = [s for s in self.sahneler if s["tip"] in ("vurgu", "liste")]
        self.vurgu_bas = vur[0]["bas"] if vur else self.toplam
        self._sehir()

    # ------------- şehir -------------
    def _sehir(self):
        rnd = random.Random(7)
        self.bina, self.pencere = [], []
        A = self.asama_bas
        x = -20
        while x < W + 20:
            bw, top = rnd.randint(70, 170), rnd.randint(1180, 1620)
            self.bina.append((x, x + bw, top))
            for c in range(max(1, (bw - 16) // 22)):
                for yy in range(top + 18, H - 30, 30):
                    if rnd.random() < 0.72:
                        r = rnd.random()
                        if self.efekt == "karartma":
                            off = self.an + rnd.uniform(0, 0.25) if r < 0.93 else rnd.uniform(A[0], A[-2] + 3)
                        elif self.efekt == "karartma_yavas":     # ışıklar 1. aşamadan 3. aşamaya kadar söner
                            off = rnd.uniform(A[0] + 1.5, A[2] + 2)
                        else:
                            off = 1e9
                        col = rnd.choice([(255, 214, 140), (255, 232, 180), (200, 225, 255), (255, 200, 120)])
                        self.pencere.append((x + 10 + c * 22, yy, 12, 16, off, col))
            x += bw + rnd.randint(-6, 4)
        self.yildiz = [(rnd.randint(0, W), rnd.randint(0, 1350), rnd.uniform(0.3, 1.0), rnd.uniform(0, 6.28))
                       for _ in range(420)]
        self.kar = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(40, 110), rnd.uniform(2, 5)) for _ in range(160)]
        self.uydu = [(rnd.uniform(0, W), rnd.uniform(80, 900), rnd.uniform(-60, 60), rnd.uniform(10, 30)) for _ in range(9)]
        self.sil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(self.sil)
        for x0, x1, top in self.bina:
            d.rectangle([x0, top, x1, H], fill=(16, 19, 32, 255))
            d.line([x0, top, x1, top], fill=(48, 56, 86, 255), width=3)
            if rnd.random() < 0.35:
                ax = rnd.randint(x0 + 10, x1 - 10)
                d.line([ax, top, ax, top - rnd.randint(30, 80)], fill=(16, 19, 32, 255), width=4)

    def ilerleme(self, tt):
        """0 → olaydan önce, 1..5 → aşamalar boyunca sürekli artan değer."""
        A = self.asama_bas
        if tt < A[0]:
            return 0.0
        for i in range(len(A) - 1):
            if tt < A[i + 1]:
                return i + 1 + (tt - A[i]) / (A[i + 1] - A[i])
        return float(len(A))

    def gok(self, tt):
        e = self.efekt
        k = min(1.0, max(0.0, (tt - self.an) / 1.2))          # olaydan sonra geçiş
        p = self.ilerleme(tt) / 5.0                             # 0..1 aşamalar boyunca
        img = Image.new("RGB", (W, H))
        dd = ImageDraw.Draw(img)
        for y in range(0, H, 8):
            f = y / H
            gece = (int(14 + 30 * f), int(18 + 22 * f), int(40 + 20 * f))
            kara = (int(4 + 4 * f), int(5 + 5 * f), int(12 + 10 * f))
            if e in ("karartma", "karartma_yavas"):
                kk = k if e == "karartma" else min(1.0, p * 1.8)
                c = tuple(int(gece[i] * (1 - kk) + kara[i] * kk) for i in range(3))
                glow = max(0, (f - 0.45) / 0.55) * (1 - kk)
            elif e == "soguk":  # gündüz → simsiyah, sonra buz mavisi
                gun = (int(60 + 90 * f), int(130 + 70 * f), int(220 + 20 * f))
                c = tuple(int(gun[i] * (1 - k) + kara[i] * k) for i in range(3))
                buz = min(1.0, p * 1.2)
                c = (int(c[0] + 10 * buz), int(c[1] + 22 * buz), int(c[2] + 40 * buz))
                glow = 0
            elif e == "kizil":   # kuraklık: gök tozlu turuncuya döner
                toz = (int(70 + 90 * f), int(40 + 50 * f), int(20 + 15 * f))
                c = tuple(int(gece[i] * (1 - p) + toz[i] * p) for i in range(3))
                glow = max(0, (f - 0.45) / 0.55) * (1 - p)
            elif e == "solgun":  # renk solar, gri bir gök
                gri = (int(40 + 25 * f),) * 3
                c = tuple(int(gece[i] * (1 - p) + gri[i] * p) for i in range(3))
                glow = max(0, (f - 0.45) / 0.55) * (1 - p)
            else:
                c, glow = gece, max(0, (f - 0.45) / 0.55)
            c = (min(255, int(c[0] + 90 * glow)), min(255, int(c[1] + 45 * glow)), c[2])
            dd.rectangle([0, y, W, y + 8], fill=c)
        # yıldızlar
        if e == "soguk":
            vis = k
        elif e in ("karartma",):
            vis = 0.25 + 0.75 * k
        elif e == "karartma_yavas":
            vis = 0.25 + 0.75 * min(1.0, p * 1.8)
        elif e == "ay":
            vis = 0.3 + 0.7 * k
        elif e in ("kizil", "solgun"):
            vis = 0.3 * (1 - p)
        else:
            vis = 0.35
        for (sx, sy, br, ph) in self.yildiz:
            v = int(255 * br * vis * (0.75 + 0.25 * math.sin(tt * 2.2 + ph)))
            if v > 25:
                dd.point((sx, sy), fill=(v, v, v))
                if br > 0.85:
                    dd.point((sx + 1, sy), fill=(v, v, v)); dd.point((sx, sy + 1), fill=(v, v, v))
        # güneş (soguk) ya da ay
        if e == "soguk":
            if k < 1:
                g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                gd = ImageDraw.Draw(g)
                a = int(255 * (1 - k))
                gd.ellipse([760, 140, 960, 340], fill=(255, 220, 120, a))
                g = g.filter(ImageFilter.GaussianBlur(6))
                img.paste(g, (0, 0), g)
        else:
            ay = 1.0
            if e == "ay":
                ay = 1 - k
            if ay > 0.02:
                bg = img.getpixel((1000, 150))
                ac = (int(170 * ay + bg[0] * (1 - ay)), int(170 * ay + bg[1] * (1 - ay)), int(160 * ay + bg[2] * (1 - ay)))
                dd.ellipse([880, 110, 960, 190], fill=ac)
                dd.ellipse([900, 102, 980, 182], fill=bg)
        return img

    def arka(self, tt):
        img = self.gok(tt)
        e = self.efekt
        # uydular: olaydan önce gökte süzülür, sonra kırmızı söner
        if e == "uydu":
            dd = ImageDraw.Draw(img)
            for (ux, uy, vx, vy) in self.uydu:
                t0 = min(tt, self.an)
                x, y = (ux + vx * t0) % W, uy + 0.0
                if tt < self.an:
                    dd.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(230, 240, 255))
                    if int(tt * 3 + ux) % 2 == 0:
                        dd.ellipse([x - 6, y - 6, x + 6, y + 6], outline=(150, 200, 255))
                else:
                    a = max(0.0, 1 - (tt - self.an) / 3)
                    if a > 0:
                        dd.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(int(255 * a), int(60 * a), int(60 * a)))
        img.paste(self.sil, (0, 0), self.sil)
        dd = ImageDraw.Draw(img)
        blink = (self.an - 0.55 < tt < self.an) and (int(tt * 30) % 4 in (0, 1)) and e in ("karartma", "uydu", "normal")
        kis = 0.55 if e == "soguk" and tt > self.an else 1.0
        for (px, py, pw, ph, off, col) in self.pencere:
            if tt < off and not blink:
                cc = col if kis == 1 else tuple(int(v * kis) for v in col)
                dd.rectangle([px, py, px + pw, py + ph], fill=cc)
        if self.b.get("mum") and tt >= self.vurgu_bas:
            self._mum(img, tt)
        if e == "sel":
            self._su(img, tt)
        if e == "soguk" and tt > self.asama_bas[1]:
            self._kar(img, tt, min(1.0, (tt - self.asama_bas[1]) / 3))
        if e == "kizil":
            p = self.ilerleme(tt) / 5
            if p > 0:
                o = Image.new("RGBA", (W, H), (150, 90, 40, int(70 * p)))
                img.paste(o, (0, 0), o)
        return img

    def _mum(self, img, tt):
        hz = next((p for p in self.pencere if 1500 < p[1] < 1560 and 480 < p[0] < 620), None)
        if not hz:
            return
        fl = 0.8 + 0.2 * math.sin(tt * 13) * math.sin(tt * 7.3)
        px, py, pw, ph = hz[:4]
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([px - 60, py - 60, px + pw + 60, py + ph + 60], fill=(255, 150, 50, int(90 * fl)))
        g = g.filter(ImageFilter.GaussianBlur(28))
        img.paste(g, (0, 0), g)
        ImageDraw.Draw(img).rectangle([px, py, px + pw, py + ph], fill=(255, int(170 * fl + 40), 70))

    def _su(self, img, tt):
        # aşama aşama yükselen deniz: silüetin altından üstüne
        hedef = [0, 0.08, 0.2, 0.38, 0.6, 0.82]
        p = self.ilerleme(tt)
        i = int(min(5, p))
        frac = ease(min(1.0, (p - i) * 2.5)) if i < 5 else 1
        lv = hedef[i] + (hedef[min(5, i + 1)] - hedef[i]) * frac if p > 0 else 0
        if lv <= 0:
            return
        top = H - lv * (H - 1150)
        su = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(su)
        pts = [(x, top + 8 * math.sin(x / 70 + tt * 2.4)) for x in range(0, W + 20, 20)]
        sd.polygon(pts + [(W, H), (0, H)], fill=(25, 90, 160, 205))
        sd.line(pts, fill=(140, 200, 255, 230), width=4)
        img.paste(su, (0, 0), su)

    def _kar(self, img, tt, a):
        dd = ImageDraw.Draw(img)
        for (x, y, vy, r) in self.kar:
            yy = (y + vy * tt) % H
            xx = (x + 18 * math.sin(tt + y)) % W
            v = int(220 * a)
            dd.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(v, v, min(255, v + 25)))

    # ------------- yazı -------------
    @staticmethod
    def parcala(satir):
        out, vur = [], False
        for p in satir.split("*"):
            if p:
                out.append((p, vur))
            vur = not vur
        return out

    def satir_ciz(self, img, satir, y, boy, alpha, dy=0, fnt=F_BLACK, renk=WHT):
        parcalar = self.parcala(satir)
        while sum(font(fnt, boy).getlength(p) for p, _ in parcalar) > 960:
            boy -= 2
        f = font(fnt, boy)
        gen = sum(f.getlength(p) for p, _ in parcalar)
        katman = Image.new("RGBA", (W, boy + 60), (0, 0, 0, 0))
        gol = Image.new("RGBA", (W, boy + 60), (0, 0, 0, 0))
        kd, gd = ImageDraw.Draw(katman), ImageDraw.Draw(gol)
        xx = (W - gen) / 2
        for p, v in parcalar:
            gd.text((xx, 18), p, font=f, fill=(0, 0, 0, 230), stroke_width=10, stroke_fill=(0, 0, 0, 230))
            kd.text((xx, 18), p, font=f, fill=(YEL if v else renk) + (255,), stroke_width=3, stroke_fill=(0, 0, 0, 255))
            xx += f.getlength(p)
        gol = gol.filter(ImageFilter.GaussianBlur(9))
        gol.alpha_composite(katman)
        if alpha < 1:
            gol.putalpha(gol.getchannel("A").point(lambda v: int(v * alpha)))
        img.paste(gol, (0, int(y + dy - 18)), gol)

    def baslik_ciz(self, img, yazi, lt, adim):
        k = ease(lt / 0.35)
        taban = 118
        while font(F_BLACK, taban).getlength(yazi) > 860:
            taban -= 4
        boy = int(taban * (1.35 - 0.35 * k))
        f = font(F_BLACK, boy)
        gen = f.getlength(yazi)
        kat = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
        kd = ImageDraw.Draw(kat)
        kd.rounded_rectangle([(W - gen) / 2 - 34, 130 - boy * 0.62, (W + gen) / 2 + 34, 130 + boy * 0.62],
                             radius=22, fill=(200, 30, 40, 235))
        kd.text((W / 2, 130), yazi, font=f, fill=(255, 255, 255, 255), anchor="mm")
        if k < 1:
            kat.putalpha(kat.getchannel("A").point(lambda v: int(v * k)))
        img.paste(kat, (0, 330), kat)
        if adim is not None:
            self.zaman_cizgisi(img, adim, lt)

    def zaman_cizgisi(self, img, adim, lt):
        dd = ImageDraw.Draw(img)
        y, x0, x1 = 285, 120, 960
        pos = [x0 + i * (x1 - x0) / 4 for i in range(5)]
        dd.line([x0, y, x1, y], fill=(70, 70, 90), width=6)
        onceki = pos[max(0, adim - 1)]
        dd.line([x0, y, onceki + (pos[adim] - onceki) * ease(lt / 0.6), y], fill=RED, width=6)
        for i, px in enumerate(pos):
            r = 15 if i == adim else 11
            dd.ellipse([px - r, y - r, px + r, y + r], fill=RED if i <= adim else (70, 70, 90),
                       outline=(255, 255, 255) if i == adim else None, width=3)
            et = self.b["adimlar"][i]
            boy = 30
            while font(F_BOLD, boy).getlength(et) > 200:
                boy -= 2
            dd.text((px, y - 42), et, font=font(F_BOLD, boy), fill=(255, 255, 255) if i == adim else (150, 150, 165),
                    anchor="mm")

    def yazilar(self, img, s, lt):
        tip, sat, g = s["tip"], s["satir"], s["gorun"]
        gor = lambda i: ease((lt - g[i]) / 0.3)
        if tip == "kanca":
            boylar, y = [104, 122, 150, 122], 640
            for i, x in enumerate(sat):
                k = gor(i)
                if k > 0:
                    self.satir_ciz(img, x, y, boylar[i], k, dy=(1 - k) * 40)
                y += boylar[i] + 26
            return
        if tip == "son":
            k = gor(0)
            if k > 0:
                self.satir_ciz(img, sat[0], 640, 112, k, dy=(1 - k) * 40)
            k2 = gor(1)
            if k2 > 0:
                self.satir_ciz(img, sat[1], 790, int(118 * (1 + 0.04 * math.sin(lt * 6))), k2, dy=(1 - k2) * 40)
            k3 = ease((lt - g[1] - 0.6) / 0.4)
            if k3 > 0:
                self.satir_ciz(img, "Yorumlara yaz", 1000, 76, k3, fnt=F_BOLD)
                oy = 1110 + 18 * math.sin(lt * 5)
                ImageDraw.Draw(img).polygon([(W / 2 - 40, oy), (W / 2 + 40, oy), (W / 2, oy + 50)], fill=YEL)
            k4 = ease((lt - g[1] - 1.1) / 0.4)
            if k4 > 0:
                self.satir_ciz(img, self.b.get("not", "Bu bir senaryodur, kesin tahmin değildir."), 1240, 38,
                               0.8 * k4, fnt=F_BOLD, renk=(200, 200, 210))
            return
        self.baslik_ciz(img, s["baslik"], lt, s.get("adim"))
        if tip == "vurgu":
            dz, ys = [(84, F_BOLD), (84, F_BOLD), (200, F_BLACK), (66, F_BOLD)], [640, 740, 860, 1110]
        elif tip == "liste":
            dz, ys = [(70, F_BOLD), (70, F_BOLD), (92, F_BLACK), (92, F_BLACK)], [660, 750, 900, 1005]
        else:
            dz, ys = [(80, F_BLACK)] * 3, [680, 810, 940]
        for i, ((boy, fn), x, y) in enumerate(zip(dz, sat, ys)):
            k = gor(i)
            if k > 0:
                self.satir_ciz(img, x, y, boy, k, dy=(1 - k) * 36, fnt=fn)

    # ------------- fotoğraf arka planı (haber videoları: sahnede "arka" = yerel resim yolu) -------------
    _foto = {}

    def foto_hazirla(self, yol):
        """Resmi 9:16'ya kırpar (%12 pay bırakarak, yavaş yakınlaşma için), yazı okunsun diye karartır."""
        if yol in self._foto:
            return self._foto[yol]
        im = Image.open(yol).convert("RGB")
        GW, GH = int(W * 1.12), int(H * 1.12)
        o = max(GW / im.width, GH / im.height)
        im = im.resize((max(GW, round(im.width * o)), max(GH, round(im.height * o))), Image.LANCZOS)
        x0, y0 = (im.width - GW) // 2, (im.height - GH) // 3   # dikeyde biraz üstten: yüzler/nesneler genelde üstte
        im = im.crop((x0, y0, x0 + GW, y0 + GH))
        golge = Image.new("L", (GW, GH))
        gd = ImageDraw.Draw(golge)
        for y in range(0, GH, 4):
            f = y / GH
            # üstte başlık/zaman çizgisi, ortada yazılar: genel %45, üst ve alt kenarda daha koyu
            a = 135 + int(60 * max(0.0, 0.25 - f) / 0.25) + int(60 * max(0.0, f - 0.7) / 0.3)
            gd.rectangle([0, y, GW, y + 4], fill=min(235, a))
        im = Image.composite(Image.new("RGB", (GW, GH), (6, 8, 16)), im, golge)
        self._foto[yol] = im
        return im

    def foto_kare(self, s, tt):
        im = self.foto_hazirla(s["arka"])
        k = min(1.0, max(0.0, (tt - s["bas"]) / max(s["sure"], 0.1)))
        olcek = 1.12 - 0.10 * k                       # sahne boyunca yavaşça yakınlaşır
        cw, ch = int(W * olcek), int(H * olcek)
        x0, y0 = (im.width - cw) // 2, (im.height - ch) // 2
        return im.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BILINEAR)

    def kare(self, tt):
        s = next(x for x in self.sahneler if x["bas"] <= tt < x["bas"] + x["sure"] + 1e-6) if tt < self.toplam else self.sahneler[-1]
        img = (self.foto_kare(s, tt) if s.get("arka") else self.arka(tt)).convert("RGBA")
        lt = tt - s["bas"]
        yaz = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.yazilar(yaz, s, lt)
        kalan = s["sure"] - lt
        if kalan < 0.25 and s["tip"] != "son":
            yaz.putalpha(yaz.getchannel("A").point(lambda v: int(v * max(0, kalan) / 0.25)))
        img.alpha_composite(yaz)
        if self.an <= tt < self.an + 0.12:
            img = Image.blend(img, Image.new("RGBA", (W, H), (255, 255, 255, 255)), 0.35)
        return img.convert("RGB")

    def render(self, klasor):
        dosyalar = []
        for s in self.sahneler:
            yol = os.path.join(klasor, f"sahne_{s['ad']}.mp4")
            tmp = yol.replace(".mp4", ".tmp.mp4")
            n = round(s["sure"] * FPS)
            p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                  "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                                  "-pix_fmt", "yuv420p", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
            for i in range(n):
                p.stdin.write(self.kare(s["bas"] + i / FPS).tobytes())
            p.stdin.close()
            if p.wait() != 0:
                raise RuntimeError("ffmpeg hata: " + s["ad"])
            os.replace(tmp, yol)
            dosyalar.append(yol)
        return dosyalar


if __name__ == "__main__":
    b = json.load(open(sys.argv[1], encoding="utf-8"))
    z = json.load(open(sys.argv[2], encoding="utf-8"))
    v = Video(b, z)
    os.makedirs(sys.argv[3], exist_ok=True)
    if len(sys.argv) > 4 and sys.argv[4] == "kare":
        for a in sys.argv[5:]:
            v.kare(float(a)).save(os.path.join(sys.argv[3], f"kare_{float(a):05.2f}.png"))
    else:
        print("\n".join(v.render(sys.argv[3])))
