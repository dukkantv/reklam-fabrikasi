# Gizli Tarih "Ne Olur?" Shorts – kodla çizilen 9:16 video (şehir silüeti + zaman çizelgesi + yazılar).
# Kullanım: python render.py bolum.json zaman.json cikti_klasoru        (sahne_*.mp4 dosyalarını üretir)
#           python render.py bolum.json zaman.json cikti_klasoru kare 1.0 5.5 ...   (kontrol kareleri)
import json, math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F_BLACK = os.path.join(KOK, "arena", "fonts", "InterDisplay-Black.otf")
F_BOLD = os.path.join(KOK, "arena", "fonts", "InterDisplay-Bold.otf")
YEL, WHT, RED = (255, 214, 60), (245, 245, 250), (255, 60, 110)
# 27 Kas 2026 (Levent: "sade kalan, boş gibi her gün yayınlanan kısa videolar neon tarzı yazılar, şablonlar olsun"):
# Dükkan TV neon diliyle aynı aile: koyu gece, parlayan yazılar, neon çerçeveli kutular, ilerleme çubuğu.
CYAN, PINK = (0, 229, 255), (255, 60, 170)
_fc = {}
_katman = {}   # aynı yazı katmanı her karede yeniden çizilmesin (hız)


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
                        col = rnd.choice([(255, 214, 140), (255, 232, 180), (120, 230, 255), (255, 120, 200), (255, 200, 120)])
                        self.pencere.append((x + 10 + c * 22, yy, 12, 16, off, col))
            x += bw + rnd.randint(-6, 4)
        self.yildiz = [(rnd.randint(0, W), rnd.randint(0, 1350), rnd.uniform(0.3, 1.0), rnd.uniform(0, 6.28))
                       for _ in range(420)]
        self.kar = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(40, 110), rnd.uniform(2, 5)) for _ in range(160)]
        self.uydu = [(rnd.uniform(0, W), rnd.uniform(80, 900), rnd.uniform(-60, 60), rnd.uniform(10, 30)) for _ in range(9)]
        self.sil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(self.sil)
        cati = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cd = ImageDraw.Draw(cati)
        for n, (x0, x1, top) in enumerate(self.bina):
            d.rectangle([x0, top, x1, H], fill=(10, 9, 20, 255))
            renk = CYAN if n % 3 else PINK
            cd.line([x0, top, x1, top], fill=renk + (255,), width=4)
            cd.line([x0, top, x0, top + 60], fill=renk + (150,), width=3)
            if rnd.random() < 0.35:
                ax = rnd.randint(x0 + 10, x1 - 10)
                d.line([ax, top, ax, top - rnd.randint(30, 80)], fill=(10, 9, 20, 255), width=4)
        isik = cati.filter(ImageFilter.GaussianBlur(10))
        isik.putalpha(isik.getchannel("A").point(lambda v: min(255, v * 3)))
        self.sil = Image.alpha_composite(self.sil, isik)
        self.sil = Image.alpha_composite(self.sil, cati)
        # yüzen neon parçacıklar
        self.parca = [(rnd.uniform(0, W), rnd.uniform(0, 1250), rnd.uniform(-12, 12), rnd.uniform(-30, -8),
                       rnd.choice([CYAN, PINK, YEL]), rnd.uniform(2, 5), rnd.uniform(0, 6.28)) for _ in range(24)]
        # ekranın ortasında yumuşak neon ışık havuzu (yazıların arkası)
        import numpy as _np
        yy, xx = _np.mgrid[0:H:4, 0:W:4]
        g = _np.exp(-(((xx - W / 2) / 520) ** 2 + ((yy - 860) / 520) ** 2))
        arr = _np.zeros((H // 4, W // 4, 4), _np.uint8)
        arr[..., 0], arr[..., 1], arr[..., 2] = 120, 30, 160
        arr[..., 3] = (g * 70).astype(_np.uint8)
        self.havuz = Image.fromarray(arr, "RGBA").resize((W, H), Image.BILINEAR)

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
            gece = (int(10 + 22 * f), int(8 + 10 * f), int(24 + 22 * f))
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
            c = (min(255, int(c[0] + 120 * glow)), min(255, int(c[1] + 14 * glow)), min(255, int(c[2] + 80 * glow)))
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
        img = img.convert("RGBA")
        img.alpha_composite(self.havuz)
        self._parcaciklar(img, tt)
        img.alpha_composite(self.sil)
        img = img.convert("RGB")
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

    def _parcaciklar(self, img, tt):
        dd = ImageDraw.Draw(img)
        for (x, y, vx, vy, c, r, ph) in self.parca:
            px, py = (x + vx * tt) % W, (y + vy * tt) % 1300
            a = 0.45 + 0.35 * math.sin(tt * 2 + ph)
            dd.ellipse([px - r * 2.6, py - r * 2.6, px + r * 2.6, py + r * 2.6], fill=c + (int(40 * a),))
            dd.ellipse([px - r, py - r, px + r, py + r], fill=c + (int(150 * a),))

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

    @staticmethod
    def _isilt(katman, yaricap, guc):
        b = katman.filter(ImageFilter.GaussianBlur(yaricap))
        b.putalpha(b.getchannel("A").point(lambda v: min(255, int(v * guc))))
        return b

    def satir_katman(self, satir, boy, fnt=F_BLACK, renk=WHT, neon=None):
        """Neon satır: koyu gölge + renkli ışıma + beyaz/neon sarı yazı. Aynı satır bir kez çizilir."""
        anahtar = ("s", satir, boy, fnt, renk, neon)
        if anahtar in _katman:
            return _katman[anahtar]
        parcalar = self.parcala(satir)
        while sum(font(fnt, boy).getlength(p) for p, _ in parcalar) > 860:
            boy -= 2
        f = font(fnt, boy)
        gen = sum(f.getlength(p) for p, _ in parcalar)
        Hk = boy + 90
        yazi, isik, gol = (Image.new("RGBA", (W, Hk), (0, 0, 0, 0)) for _ in range(3))
        kd, idr, gd = ImageDraw.Draw(yazi), ImageDraw.Draw(isik), ImageDraw.Draw(gol)
        xx = (W - gen) / 2
        for p, v in parcalar:
            gd.text((xx, 30), p, font=f, fill=(0, 0, 0, 200), stroke_width=8, stroke_fill=(0, 0, 0, 200))
            ic = YEL if v else (neon or (150, 205, 255))
            idr.text((xx, 30), p, font=f, fill=ic + (255,), stroke_width=max(3, boy // 18), stroke_fill=ic + (255,))
            kd.text((xx, 30), p, font=f, fill=(YEL if v else renk) + (255,), stroke_width=2, stroke_fill=(20, 10, 30, 255))
            xx += f.getlength(p)
        out = gol.filter(ImageFilter.GaussianBlur(10))
        out.alpha_composite(self._isilt(isik, max(6, boy * 0.22), 1.5 if neon is None else 2.4))
        out.alpha_composite(self._isilt(isik, max(3, boy * 0.07), 1.2))
        out.alpha_composite(yazi)
        _katman[anahtar] = out
        return out

    def satir_ciz(self, img, satir, y, boy, alpha, dy=0, fnt=F_BLACK, renk=WHT, neon=None, titre=False):
        k = self.satir_katman(satir, boy, fnt, renk, neon)
        if titre:   # neon tabela yanarken titreme
            alpha *= (0.35 if int(alpha * 40) % 3 == 1 else 1.0)
        if alpha < 1:
            k = k.copy()
            k.putalpha(k.getchannel("A").point(lambda v: int(v * alpha)))
        img.alpha_composite(k, (0, int(y + dy - 30)))

    def kart_ciz(self, img, y0, y1, alpha, renk=CYAN):
        """Satırların arkasında neon kenarlı yarı saydam kart (ekran boş görünmesin)."""
        anahtar = ("k", int(y0), int(y1), renk)
        if anahtar not in _katman:
            k = Image.new("RGBA", (W, int(y1 - y0) + 80), (0, 0, 0, 0))
            kenar = Image.new("RGBA", k.size, (0, 0, 0, 0))
            ImageDraw.Draw(k).rounded_rectangle([70, 40, W - 70, k.height - 40], radius=38, fill=(14, 10, 26, 175))
            ImageDraw.Draw(kenar).rounded_rectangle([70, 40, W - 70, k.height - 40], radius=38, outline=renk + (255,), width=4)
            k.alpha_composite(self._isilt(kenar, 14, 2.6))
            k.alpha_composite(kenar)
            _katman[anahtar] = k
        k = _katman[anahtar]
        if alpha < 1:
            k = k.copy()
            k.putalpha(k.getchannel("A").point(lambda v: int(v * alpha)))
        img.alpha_composite(k, (0, int(y0 - 40)))

    def baslik_ciz(self, img, yazi, lt, adim):
        k = ease(lt / 0.35)
        taban = 112
        while font(F_BLACK, taban).getlength(yazi) > 840:
            taban -= 4
        anahtar = ("b", yazi, taban)
        if anahtar not in _katman:
            f = font(F_BLACK, taban)
            gen = f.getlength(yazi)
            kat = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
            kenar = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
            kut = [(W - gen) / 2 - 40, 150 - taban * 0.66, (W + gen) / 2 + 40, 150 + taban * 0.66]
            ImageDraw.Draw(kat).rounded_rectangle(kut, radius=26, fill=(16, 8, 26, 235))
            ImageDraw.Draw(kenar).rounded_rectangle(kut, radius=26, outline=PINK + (255,), width=6)
            yz = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
            ImageDraw.Draw(yz).text((W / 2, 150), yazi, font=f, fill=WHT + (255,), anchor="mm")
            isik = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
            ImageDraw.Draw(isik).text((W / 2, 150), yazi, font=f, fill=PINK + (255,), anchor="mm", stroke_width=4, stroke_fill=PINK + (255,))
            kat.alpha_composite(self._isilt(kenar, 18, 3.0))
            kat.alpha_composite(kenar)
            kat.alpha_composite(self._isilt(isik, 16, 1.4))
            kat.alpha_composite(yz)
            _katman[anahtar] = kat
        kat = _katman[anahtar]
        if k < 1:
            kat = kat.copy()
            kat.putalpha(kat.getchannel("A").point(lambda v: int(v * k)))
        img.alpha_composite(kat, (0, 310 - int((1 - k) * 30)))
        if adim is not None:
            self.zaman_cizgisi(img, adim, lt)

    def zaman_cizgisi(self, img, adim, lt):
        y, x0, x1 = 285, 120, 960
        pos = [x0 + i * (x1 - x0) / 4 for i in range(5)]
        isik = Image.new("RGBA", (W, 120), (0, 0, 0, 0))
        dd = ImageDraw.Draw(isik)
        yy = 70
        onceki = pos[max(0, adim - 1)]
        dd.line([x0, yy, onceki + (pos[adim] - onceki) * ease(lt / 0.6), yy], fill=CYAN + (255,), width=7)
        for i, px in enumerate(pos):
            r = 16 if i == adim else 11
            if i <= adim:
                dd.ellipse([px - r, yy - r, px + r, yy + r], fill=CYAN + (255,))
        katman = Image.new("RGBA", (W, 120), (0, 0, 0, 0))
        kd = ImageDraw.Draw(katman)
        kd.line([x0, yy, x1, yy], fill=(60, 55, 90, 255), width=5)
        for i, px in enumerate(pos):
            r = 11
            if i > adim:
                kd.ellipse([px - r, yy - r, px + r, yy + r], fill=(60, 55, 90, 255))
        katman.alpha_composite(self._isilt(isik, 12, 2.6))
        katman.alpha_composite(isik)
        cd = ImageDraw.Draw(katman)
        for i, px in enumerate(pos):
            if i == adim:
                cd.ellipse([px - 7, yy - 7, px + 7, yy + 7], fill=(255, 255, 255, 255))
            et = self.b["adimlar"][i]
            boy = 30
            while font(F_BOLD, boy).getlength(et) > 200:
                boy -= 2
            cd.text((px, yy - 42), et, font=font(F_BOLD, boy),
                    fill=(255, 255, 255, 255) if i == adim else (150, 150, 175, 255), anchor="mm")
        img.alpha_composite(katman, (0, y - 70))

    def ust_bant(self, img, tt):
        """Sol üstte seri etiketi, altta ilerleme çubuğu (Dükkan TV neon şablonu)."""
        if "ust" not in _katman:
            et = self.b.get("ust_yazi")
            if not et:
                bas = self.b.get("baslik", "")
                et = "NE OLUR?" if "ne olur" in bas.lower() else " ".join(
                    w for w in bas.replace("#shorts", "").split() if w[:1].isalnum())[:30]
            et = et.replace("i", "İ").replace("ı", "I").upper()
            k = Image.new("RGBA", (W, 120), (0, 0, 0, 0))
            d = ImageDraw.Draw(k)
            d.rounded_rectangle([60, 72, 84, 96], radius=6, fill=PINK + (255,))
            d.text((100, 84), et, font=font(F_BLACK, 40), fill=(235, 235, 245, 255), anchor="lm")
            _katman["ust"] = k
        img.alpha_composite(_katman["ust"], (0, 60))
        p = min(1.0, tt / max(self.toplam, 0.1))
        bar = Image.new("RGBA", (W, 40), (0, 0, 0, 0))
        ImageDraw.Draw(bar).rectangle([0, 26, int(W * p), 36], fill=PINK + (255,))
        img.alpha_composite(self._isilt(bar, 8, 2.2), (0, H - 40))
        img.alpha_composite(bar, (0, H - 40))

    def yazilar(self, img, s, lt):
        tip, sat, g = s["tip"], s["satir"], s["gorun"]
        gor = lambda i: ease((lt - g[i]) / 0.3)
        if tip == "kanca":
            boylar, y = [104, 122, 150, 122], 640
            self.kart_ciz(img, 590, 640 + sum(b + 26 for b in boylar[:len(sat)]) + 50, gor(0), PINK)
            for i, x in enumerate(sat):
                k = gor(i)
                if k > 0:
                    self.satir_ciz(img, x, y, boylar[i], k, dy=(1 - k) * 40, titre=k < 1 and "*" in x)
                y += boylar[i] + 26
            return
        if tip == "son":
            self.kart_ciz(img, 595, 970, gor(0), PINK)
            k = gor(0)
            if k > 0:
                self.satir_ciz(img, sat[0], 640, 112, k, dy=(1 - k) * 40)
            k2 = gor(1)
            if k2 > 0:
                self.satir_ciz(img, sat[1], 790, 118, k2, dy=(1 - k2) * 40, neon=YEL)
            k3 = ease((lt - g[1] - 0.6) / 0.4)
            if k3 > 0:
                nab = 0.75 + 0.25 * math.sin(lt * 6)
                if ("dugme",) not in _katman:
                    f = font(F_BLACK, 64)
                    gen = f.getlength("YORUMLARA YAZ 👇".replace(" 👇", ""))
                    kat = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
                    kenar = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
                    kut = [(W - gen) / 2 - 60, 50, (W + gen) / 2 + 60, 150]
                    ImageDraw.Draw(kat).rounded_rectangle(kut, radius=50, fill=(20, 8, 30, 230))
                    ImageDraw.Draw(kenar).rounded_rectangle(kut, radius=50, outline=YEL + (255,), width=6)
                    kat.alpha_composite(self._isilt(kenar, 16, 3.0))
                    kat.alpha_composite(kenar)
                    ImageDraw.Draw(kat).text((W / 2, 100), "YORUMLARA YAZ", font=f, fill=YEL + (255,), anchor="mm")
                    _katman[("dugme",)] = kat
                dg = _katman[("dugme",)].copy()
                dg.putalpha(dg.getchannel("A").point(lambda v: int(v * k3 * nab)))
                img.alpha_composite(dg, (0, 980))
                oy = 1190 + 18 * math.sin(lt * 5)
                ImageDraw.Draw(img).polygon([(W / 2 - 40, oy), (W / 2 + 40, oy), (W / 2, oy + 50)], fill=YEL + (int(255 * k3),))
            k4 = ease((lt - g[1] - 1.1) / 0.4)
            if k4 > 0:
                notu = self.b.get("not", "Bu bir senaryodur, kesin tahmin değildir.")
                gen = font(F_BOLD, 38).getlength(notu)
                ImageDraw.Draw(img).rounded_rectangle([(W - gen) / 2 - 28, 1286, (W + gen) / 2 + 28, 1352], radius=30,
                                                      fill=(10, 8, 20, int(215 * k4)))   # binaların önünde okunsun
                self.satir_ciz(img, notu, 1300, 38, 0.9 * k4, fnt=F_BOLD, renk=(215, 215, 228))
            return
        self.baslik_ciz(img, s["baslik"], lt, s.get("adim"))
        if tip == "vurgu":
            dz, ys = [(84, F_BOLD), (84, F_BOLD), (200, F_BLACK), (66, F_BOLD)], [640, 740, 860, 1110]
        elif tip == "liste":
            dz, ys = [(70, F_BOLD), (70, F_BOLD), (92, F_BLACK), (92, F_BLACK)], [660, 750, 900, 1005]
        else:
            dz, ys = [(80, F_BLACK)] * 3, [680, 810, 940]
        n = min(len(sat), len(ys))
        if n:
            self.kart_ciz(img, ys[0] - 45, ys[n - 1] + dz[n - 1][0] * 1.25 + 45, gor(0), CYAN)
        for i, ((boy, fn), x, y) in enumerate(zip(dz, sat, ys)):
            k = gor(i)
            if k > 0:
                buyuk = tip == "vurgu" and i == 2
                self.satir_ciz(img, x, y, boy, k, dy=(1 - k) * 36, fnt=fn, neon=YEL if buyuk else None, titre=buyuk and k < 1)

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
        self.ust_bant(img, tt)
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
