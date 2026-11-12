# Levent & Cemo kısa mizah skeçleri — elle yazılmış hazır senaryolar.
# Çalıştırınca her reklamlar/mizah-XX-*/bilgi.json dosyasına "oto.senaryo" olarak yazar (Gemini'ye gerek kalmaz).
# Kurallar: tek mekân, ~18-22 sn, 5 konuşma + 1 aksiyon, kanca ilk saniyede, son plan punchline,
# karede okunabilir yazı/rakam yok (yapay zekâ yazıları bozuyor), konuşma planında sadece konuşanın yüzü görünür.
import json
import os

KOK = os.path.dirname(os.path.abspath(__file__))


def K(kim, metin, duygu, kar, gorsel, efekt=None):
    return {"tip": "konusma", "kim": kim, "metin": metin, "duygu": duygu, "karakterler": kar, "dukkan": False,
            "gorsel": gorsel, "kasa": None, "efekt": efekt}


def A(kar, gorsel, hareket, efekt, sure=3):
    return {"tip": "aksiyon", "karakterler": kar, "dukkan": False, "gorsel": gorsel, "hareket": hareket,
            "sure": sure, "kasa": None, "efekt": efekt}


Y = "esnaf"  # meslek karakteri
SEN = {}

SEN["mizah-02-hastane"] = {
    "baslik": "Cemo Acile Koştu", "aciklama": "Cemo'nun acil durumu gerçekten çok acildi 😂 Sizce teşhis doğru mu?",
    "planlar": [
        K("cemo", "[whispers] Hemşire hanım, çok acil... kriz geldi!", "panicked",
          ["cemo", "levent"], "Inside a bright Turkish state hospital emergency room, Cemo bent over clutching his stomach "
          "at the nurse station, Levent seen from behind next to him."),
        K(Y, "Sakin olun! Ağrı nerede, ne zamandır var?", "concerned and serious",
          ["esnaf", "cemo"], "Same hospital emergency room, the nurse behind the nurse station desk, Cemo seen from behind "
          "in the foreground."),
        K("cemo", "[sighs] Sabahtan beri... midemde kocaman bir boşluk var.", "dramatic and suffering",
          ["cemo", "esnaf"], "Same hospital emergency room, Cemo leaning on the nurse station desk, the nurse seen from behind."),
        A(["esnaf", "cemo", "levent"], "Same hospital emergency room, the nurse listening to Cemo's belly with a stethoscope, "
          "Levent watching worried in the background.",
          "the nurse presses a stethoscope on Cemo's belly and jumps back startled as his belly rumbles, Levent covers his mouth",
          "very loud funny stomach growl rumble"),
        K(Y, "[laughs] Teşhis koydum: açlık. Tedavi: iki poğaça, günde üç kere.", "amused and kind",
          ["esnaf", "cemo"], "Same hospital emergency room, the nurse smiling and holding up a paper bag with two pastries, "
          "Cemo seen from behind."),
        K("cemo", "[excited] Hemşire hanım, ben bu hastanede yatmak istiyorum!", "overjoyed",
          ["cemo", "esnaf"], "Same hospital emergency room, Cemo beaming and hugging the pastry bag, the nurse seen from behind."),
    ]}

SEN["mizah-03-insaat"] = {
    "baslik": "Bu Bina Ne Zaman Biter?", "aciklama": "Türkiye'de her inşaat 'yarın' biter 😂 Sizin mahalledeki ne zaman bitiyor?",
    "planlar": [
        K("levent", "[excited] Usta, bu bina ne zaman biter?", "curious and excited",
          ["levent", "esnaf"], "A busy construction site in Bursa with scaffolding and an unfinished concrete building, "
          "Levent holding his microphone, the foreman seen from behind."),
        K(Y, "[laughs] Yarın biter evlat, yarın!", "confident and cheerful",
          ["esnaf", "levent"], "Same construction site, the foreman standing proudly in front of the unfinished building, "
          "Levent seen from behind."),
        K("levent", "Usta, geçen yıl gelmiştim, yine yarın demiştiniz!", "suspicious",
          ["levent", "esnaf"], "Same construction site, Levent raising an eyebrow, the foreman seen from behind."),
        K(Y, "Doğru... o başka yarındı, bu başka yarın.", "wise and serious, finger raised",
          ["esnaf", "levent"], "Same construction site, the foreman raising a finger like a philosopher, Levent seen from behind."),
        A(["cemo"], "Same construction site, Cemo placing a single brick on a low unfinished brick wall.",
          "Cemo places one single brick, wipes his forehead as if exhausted, then sits down on a bucket with a glass of tea",
          "a brick is placed on mortar, then a tea spoon clinks in a tea glass"),
        K("cemo", "[sighs] Usta, ben de yarın devam ederim.", "lazy and satisfied",
          ["cemo", "esnaf"], "Same construction site, Cemo sitting on an upside-down bucket sipping a tulip-shaped Turkish tea "
          "glass, the foreman seen from behind."),
    ]}

SEN["mizah-04-spor-salonu"] = {
    "baslik": "Cemo Spora Başladı", "aciklama": "Cemo'nun antrenman programı bilimsel 😂 Siz spora ne zaman başlıyorsunuz?",
    "planlar": [
        K(Y, "[excited] Hadi Cemo abi, yirmi şınav! Başla!", "super energetic",
          ["esnaf", "cemo"], "A modern gym with dumbbells and treadmills, the trainer clapping his hands, Cemo seen from "
          "behind lying flat on a yoga mat."),
        K("cemo", "[sighs] Hocam, ilk şınavı kafamda yaptım. Yoruldum.", "exhausted",
          ["cemo", "esnaf"], "Same gym, Cemo lying face up on the yoga mat, sweating, the trainer seen from behind."),
        K(Y, "Peki koşu bandı! On dakika, hafif tempo!", "motivating",
          ["esnaf", "cemo"], "Same gym, the trainer pointing at a treadmill, Cemo seen from behind."),
        A(["cemo"], "Same gym, Cemo on a treadmill walking extremely slowly while eating a grilled cheese toast.",
          "Cemo walks very slowly on the treadmill and happily takes a big bite of a toast",
          "treadmill motor humming and a crunchy toast bite"),
        K("levent", "[surprised] Cemo! Koşu bandında tost mu yiyorsun?", "shocked",
          ["levent", "cemo"], "Same gym, Levent standing next to the treadmill in disbelief, Cemo seen from behind."),
        K("cemo", "[excited] Abi, karbonhidrat yüklemesi. Profesyoneller böyle yapıyor.", "proud and serious",
          ["cemo", "levent"], "Same gym, Cemo on the treadmill holding the half-eaten toast like a trophy, Levent seen from behind."),
    ]}

SEN["mizah-05-berber"] = {
    "baslik": "Berberde Bir Saat", "aciklama": "Berbere tıraş için değil sohbet için gidilir 😂 Sizin berber de böyle mi?",
    "planlar": [
        K(Y, "[excited] Ve o gün dedim ki: Nuri, sen bu memleketin en iyi berberisin!", "storytelling with passion",
          ["esnaf", "levent"], "Inside an old-fashioned Bursa barber shop with a big mirror, the barber holding scissors "
          "and a comb and talking, Levent seen from behind sitting in the barber chair with a cape on."),
        K("levent", "Usta, harika hikâye ama... saçım ne zaman?", "polite but impatient",
          ["levent", "esnaf"], "Same barber shop, Levent in the barber chair wearing a barber cape, the barber seen from behind."),
        K(Y, "Dur evlat, daha bitmedi. Sonra askere gittim...", "nostalgic",
          ["esnaf", "levent"], "Same barber shop, the barber leaning on the chair dreamily, Levent seen from behind."),
        A(["cemo"], "Same barber shop, Cemo asleep on the waiting bench with his flat cap over his eyes.",
          "Cemo snores loudly on the waiting bench, his chest rising and falling, the wall clock hands spin fast",
          "loud snoring and a fast ticking clock"),
        K("levent", "[sighs] Usta, bir saattir oturuyorum, tek tel kesmediniz!", "desperate",
          ["levent", "esnaf"], "Same barber shop, Levent in the barber chair with his curly hair completely untouched, "
          "the barber seen from behind."),
        K(Y, "[laughs] Sohbet bedava evlat. Kesim için yarın gel!", "cheerful and friendly",
          ["esnaf", "levent"], "Same barber shop, the barber putting his scissors back in his pocket and smiling, "
          "Levent seen from behind."),
    ]}

SEN["mizah-06-manav"] = {
    "baslik": "Karpuz Uzmanı Cemo", "aciklama": "Cemo karpuzu tıklatarak seçiyor 😂 Siz karpuzu nasıl seçiyorsunuz?",
    "planlar": [
        K("cemo", "[whispers] Şşşt... bu karpuz bana beni al diyor.", "secretive and focused",
          ["cemo", "levent"], "A colorful Bursa greengrocer stall full of watermelons, Cemo pressing his ear against a big "
          "watermelon, Levent seen from behind."),
        K("levent", "Cemo, karpuzla mı konuşuyorsun?", "confused",
          ["levent", "cemo"], "Same greengrocer stall, Levent looking puzzled, Cemo seen from behind."),
        K("cemo", "Usta işi abi. Tık tık... kesin kıpkırmızı!", "expert and confident",
          ["cemo", "esnaf"], "Same greengrocer stall, Cemo knocking on the watermelon with his knuckles, the greengrocer "
          "seen from behind."),
        A(["esnaf", "cemo"], "Same greengrocer stall, a watermelon already cut in half on the wooden counter: the inside of the watermelon is "
          "completely PALE WHITE like a cucumber, with NO red or pink flesh at all. Cemo stares at it in shock, the greengrocer holds the knife.",
          "Cemo's face slowly falls in disappointment while staring at the pale white watermelon halves, the greengrocer scratches his head",
          "a knife slicing through a watermelon"),
        K(Y, "[laughs] Kırmızı değil ama bak... çok sulu!", "trying to cheer him up",
          ["esnaf", "cemo"], "Same greengrocer stall, the greengrocer holding up the pale watermelon half, Cemo seen from behind."),
        K("cemo", "[sighs] Abi, bu karpuz bana yalan söyledi.", "heartbroken",
          ["cemo", "esnaf"], "Same greengrocer stall, Cemo holding the pale watermelon half sadly, the greengrocer seen "
          "from behind."),
    ]}

SEN["mizah-07-kargo"] = {
    "baslik": "Evde Yoktunuz Abi", "aciklama": "Kargo kapıda, siz kapıda, ama 'adreste bulunamadınız' 😂 Size de oldu mu?",
    "planlar": [
        K("levent", "[surprised] Adreste bulunamadınız mı? Üç saattir kapıdayım!", "outraged",
          ["levent", "cemo"], "In front of an apartment building door in Bursa, Levent staring at his phone in shock, "
          "Cemo seen from behind."),
        K("cemo", "[sighs] Abi, belki kargo görünmezlik pelerinidir.", "deadpan",
          ["cemo", "levent"], "Same apartment building entrance, Cemo leaning on the wall, Levent seen from behind."),
        A(["esnaf", "levent"], "Same apartment building entrance, the courier walking up holding a cardboard box.",
          "the courier walks up and stops right in front of Levent while looking down at his phone",
          "footsteps and a phone notification ding"),
        K(Y, "[excited] Levent Bey siz misiniz? Sizi hiç bulamadık!", "friendly and out of breath",
          ["esnaf", "levent"], "Same apartment building entrance, the courier holding the box and smiling, Levent seen "
          "from behind standing right in front of him."),
        K("levent", "Kardeşim, burun buruna duruyoruz!", "exasperated",
          ["levent", "esnaf"], "Same apartment building entrance, Levent pointing at himself, the courier seen from behind "
          "very close to him."),
        K(Y, "Haklısın abi... ama sistem evde yok diyor.", "apologetic, shrugging",
          ["esnaf", "levent"], "Same apartment building entrance, the courier shrugging and showing his phone, Levent seen "
          "from behind."),
    ]}

SEN["mizah-08-lokanta"] = {
    "baslik": "Cemo Diyette", "aciklama": "Cemo sadece su içecekti 😂 Siz lokantada ne söylersiniz?",
    "planlar": [
        K(Y, "[excited] Kuru, pilav, türlü, karnıyarık, mantı, köfte, sarma!", "rapid fire, proud",
          ["esnaf", "levent"], "Inside a Bursa esnaf lokantası with a glass display of steaming pots, the waiter with a towel "
          "on his shoulder, Levent seen from behind at the table."),
        K("cemo", "Hepsinden birer tane. Yanına da ayran.", "calm and serious",
          ["cemo", "esnaf"], "Same restaurant, Cemo sitting at the table with a napkin tucked into his collar, the waiter "
          "seen from behind."),
        K("levent", "[surprised] Cemo, sen diyette değil miydin?", "shocked",
          ["levent", "cemo"], "Same restaurant, Levent at the table, Cemo seen from behind."),
        K("cemo", "[sighs] Diyetteyim abi. Ben sadece su içeceğim.", "innocent",
          ["cemo", "levent"], "Same restaurant, Cemo holding a glass of water innocently, Levent seen from behind."),
        A(["cemo"], "Same restaurant, the table covered with many plates of Turkish food in front of Cemo.",
          "Cemo eats very fast from plate after plate and stacks the empty plates into a tall tower",
          "cutlery clinking fast and plates stacking"),
        K(Y, "[laughs] Buyurun hesap. Suyu da ikram ettik!", "very pleased",
          ["esnaf", "cemo"], "Same restaurant, the waiter presenting a small bill tray next to a tower of empty plates, "
          "Cemo seen from behind."),
    ]}

SEN["mizah-09-oto-tamirci"] = {
    "baslik": "Arabadaki Garip Ses", "aciklama": "Tamirci arızayı buldu 😂 Sizin arabadan hangi ses geliyor?",
    "planlar": [
        K("levent", "[excited] Usta, arabadan böyle bir ses geliyor: hırrr... fışşş!", "acting out the sound",
          ["levent", "esnaf"], "A car repair garage in a Bursa industrial area, Levent next to a small red car "
          "imitating a sound with his hands, the mechanic seen from behind."),
        K(Y, "Hmm. Motor mu, şanzıman mı? Bir daha yap bakalım.", "thoughtful, rubbing his chin",
          ["esnaf", "levent"], "Same garage, the mechanic holding a wrench and thinking, Levent seen from behind."),
        K("levent", "Hırrr... fışşş... hırrr... fışşş!", "fully committed",
          ["levent", "esnaf"], "Same garage, Levent with puffed cheeks making the noise dramatically, the mechanic seen from behind."),
        K(Y, "Bu ses bana tanıdık geliyor... bagajı açalım.", "suspicious",
          ["esnaf", "levent"], "Same garage, the mechanic walking toward the back of the small red car, Levent seen from behind."),
        A(["cemo", "esnaf", "levent"], "Same garage, the trunk of the small red car open.",
          "the trunk lid swings open and reveals Cemo curled up asleep inside, hugging a sandwich and snoring",
          "car trunk opening then loud snoring"),
        K("cemo", "[sighs] Abi... vardık mı?", "sleepy, just woke up",
          ["cemo"], "Same garage, close-up of Cemo lying inside the open car trunk, rubbing his eyes, hugging a sandwich."),
    ]}

SEN["mizah-10-emlakci"] = {
    "baslik": "Deniz Manzaralı Daire", "aciklama": "İlanda deniz manzarası vardı 😂 Siz ev ararken neyle karşılaştınız?",
    "planlar": [
        K(Y, "[excited] Deniz manzaralı, metroya beş dakika, tam size göre!", "salesman charm",
          ["esnaf", "levent"], "Inside an empty rental apartment living room with closed curtains, the real estate agent "
          "spreading his arms, Levent seen from behind."),
        K("levent", "[excited] Harika! Deniz nerede?", "hopeful",
          ["levent", "esnaf"], "Same empty apartment, Levent looking around eagerly, the agent seen from behind."),
        A(["esnaf", "levent"], "Same empty apartment, the agent dramatically pulling open the curtains.",
          "the agent pulls the curtains open revealing a brick wall right outside the window with a small sea poster taped on it",
          "curtain swoosh then distant seagull sound"),
        K("levent", "[surprised] Usta... bu bir poster!", "deadpan shock",
          ["levent", "esnaf"], "Same empty apartment, Levent pointing at the window, the agent seen from behind."),
        K(Y, "[laughs] Ama çok gerçekçi, değil mi? Martısı bile var.", "proud",
          ["esnaf", "levent"], "Same empty apartment, the agent admiring the window like a painting, Levent seen from behind."),
        K("cemo", "[sighs] Abi, metroya beş dakika da... uçakla herhalde.", "sarcastic",
          ["cemo", "levent"], "Same empty apartment, Cemo leaning on the door frame with his camera, Levent seen from behind."),
    ]}

SEN["mizah-11-disci"] = {
    "baslik": "Levent Dişçide", "aciklama": "Daha başlamadan acıdı 😂 Dişçi koltuğunda siz nasılsınız?",
    "planlar": [
        K("levent", "[whispers] Hocam, acıtmayacak değil mi? Söz mü?", "terrified",
          ["levent", "esnaf"], "Inside a clean dental clinic, Levent lying in the dental chair gripping the armrests, "
          "the dentist seen from behind."),
        K(Y, "Merak etmeyin, hiçbir şey hissetmeyeceksiniz.", "calm and reassuring",
          ["esnaf", "levent"], "Same dental clinic, the dentist with a dental mirror smiling kindly, Levent seen from behind."),
        A(["levent", "esnaf"], "Same dental clinic, the dentist reaching for the dental lamp.",
          "the dentist only switches on the dental lamp and Levent jumps in the chair with huge eyes",
          "a click and a short high dental drill whirr"),
        K("levent", "[surprised] Ahh! Hocam, acıdı!", "dramatic",
          ["levent", "esnaf"], "Same dental clinic, Levent holding his cheek dramatically, the dentist seen from behind."),
        K(Y, "[laughs] Levent Bey... daha sadece ışığı açtım.", "amused",
          ["esnaf", "levent"], "Same dental clinic, the dentist pointing at the dental lamp, Levent seen from behind."),
        K("cemo", "[excited] Hocam, sırada ben varım. Bana da şeker var mı?", "hopeful",
          ["cemo"], "Same dental clinic, Cemo peeking in through the doorway holding a bag of candy."),
    ]}

SEN["mizah-12-ogretmen"] = {
    "baslik": "Veli Toplantısı", "aciklama": "Ödevleri kim yapıyormuş, ortaya çıktı 😂 Sizin karneniz nasıldı?",
    "planlar": [
        K(Y, "Öğrenciniz derste uyuyor, ödev yapmıyor, hep bir şey yiyor.", "strict but kind",
          ["esnaf", "levent"], "A primary school classroom during a parent-teacher meeting, the teacher at her desk "
          "holding a folder, Levent seen from behind sitting on a small student chair."),
        K("levent", "[surprised] Hocam, siz yeğenimi değil, Cemo'yu anlatıyorsunuz!", "realizing",
          ["levent", "esnaf"], "Same classroom, Levent sitting on a tiny student chair, the teacher seen from behind."),
        A(["cemo"], "Same classroom, Cemo squeezed into a tiny student desk at the back of the class.",
          "Cemo sleeps at the tiny desk with his head on a book while still holding a bag of chips",
          "chips bag crinkling and a soft snore"),
        K(Y, "Bir de ödevlerini başkası yapıyormuş.", "suspicious, lowering her glasses",
          ["esnaf", "levent"], "Same classroom, the teacher lowering her glasses, Levent seen from behind."),
        K("levent", "[sighs] Hocam... o ödevleri ben yapıyordum.", "ashamed",
          ["levent", "esnaf"], "Same classroom, Levent scratching his curly hair sheepishly, the teacher seen from behind."),
        K(Y, "[laughs] Belli oldu evlat, hepsi sıfır!", "laughing",
          ["esnaf", "levent"], "Same classroom, the teacher laughing behind her desk, Levent seen from behind."),
    ]}

SEN["mizah-13-market-kasiyeri"] = {
    "baslik": "Poşet Pazarlığı", "aciklama": "Cemo poşet parası vermemek için her yolu denedi 😂 Siz poşet alıyor musunuz?",
    "planlar": [
        K(Y, "[excited] Poşet ister misiniz? Poşet ücretli.", "cheerful",
          ["esnaf", "cemo"], "At the checkout counter of a neighborhood supermarket, the cashier smiling, Cemo seen from "
          "behind with a pile of groceries on the belt."),
        K("cemo", "Ücretli mi? Pazarlık payı var mı abla?", "bargaining seriously",
          ["cemo", "esnaf"], "Same supermarket checkout, Cemo leaning on the counter, the cashier seen from behind."),
        K(Y, "[laughs] Abi burası pazar değil, market!", "laughing",
          ["esnaf", "cemo"], "Same supermarket checkout, the cashier laughing, Cemo seen from behind."),
        A(["cemo", "levent"], "Same supermarket checkout, Cemo stuffing groceries into his jacket.",
          "Cemo quickly stuffs bread, a bottle and packets into his jacket pockets and under his cap, Levent stares",
          "rustling plastic packets and wrappers"),
        K("levent", "[surprised] Cemo! Ceplerine kaç şey sığdırdın?", "amazed",
          ["levent", "cemo"], "Same supermarket checkout, Levent staring, Cemo seen from behind with bulging pockets."),
        K("cemo", "[sighs] Poşet parası çıkmasın diye abi... Kartım da evde kaldı.", "innocent",
          ["cemo", "levent"], "Same supermarket checkout, Cemo with bulging pockets and a loaf of bread under his arm, "
          "Levent seen from behind."),
    ]}

SEN["mizah-14-dolmus"] = {
    "baslik": "Arkaya Doğru İlerleyelim", "aciklama": "Dolmuşta arkada hep yer vardır 😂 Siz de bu cümleyi duydunuz mu?",
    "planlar": [
        K(Y, "[excited] Arkaya doğru ilerleyelim, arkada yer var!", "loud and cheerful",
          ["esnaf", "levent"], "Inside a crowded yellow Turkish dolmuş minibus, the driver turned around in his seat "
          "shouting toward the back, Levent seen from behind standing in the aisle."),
        K("levent", "Abi, arka cama yapıştık, arkada sadece cam var!", "squeezed",
          ["levent"], "Same crowded minibus, Levent squeezed against the back window, crowd seen only from behind."),
        K(Y, "İlerleyin ilerleyin, bir kişi daha alıyoruz!", "unbothered",
          ["esnaf"], "Same minibus, the driver smiling and waving at someone outside the open door."),
        A(["cemo"], "Same crowded minibus, Cemo squished between passengers seen from behind.",
          "Cemo's cheek is pressed flat against the window glass as more people squeeze in, he holds up a coin",
          "crowded bus chatter and squeaky brakes"),
        K(Y, "Ücretleri uzatalım! Kim öğrenci?", "counting coins",
          ["esnaf"], "Same minibus, the driver holding out his hand for fares while looking back."),
        K("cemo", "[excited] Ben abi! Hayat okulunda kırk yıldır öğrenciyim.", "proud",
          ["cemo"], "Same crowded minibus, Cemo squished but smiling proudly, other passengers seen only from behind."),
    ]}

SEN["mizah-15-banka"] = {
    "baslik": "Bankada Sıra Bekleme", "aciklama": "Sıra tam bize gelmişti ki... 😂 Bankada en uzun ne kadar beklediniz?",
    "planlar": [
        K("levent", "[surprised] Numaram üç yüz kırk sekiz, ekranda yüz on iki!", "shocked",
          ["levent", "cemo"], "A Turkish bank branch waiting area with rows of chairs and a queue display screen without "
          "readable numbers, Levent holding a small paper ticket, Cemo seen from behind."),
        K("cemo", "[sighs] Abi, ben bir uyuyayım. Sıra gelince kaldır.", "sleepy",
          ["cemo", "levent"], "Same bank waiting area, Cemo lying across three chairs, Levent seen from behind."),
        A(["cemo", "levent"], "Same bank waiting area, Cemo asleep across three chairs, Levent tapping his foot.",
          "Cemo snores across the chairs while Levent taps his foot and the wall clock hands spin fast",
          "fast ticking clock then a queue ding-dong chime"),
        K("levent", "[excited] Sonunda! Üç yüz kırk sekiz benim!", "overjoyed",
          ["levent", "esnaf"], "Same bank, Levent rushing to the teller counter, the bank teller seen from behind the glass."),
        K(Y, "Çok üzgünüm efendim. Öğle arası başladı.", "polite and calm",
          ["esnaf", "levent"], "Same bank, the bank teller behind the glass counter smiling politely, Levent seen from behind."),
        K("cemo", "[excited] Öğle arası mı? Abi o zaman biz de yemeğe!", "suddenly wide awake",
          ["cemo", "levent"], "Same bank waiting area, Cemo sitting up instantly on the chairs, Levent seen from behind."),
    ]}

SEN["mizah-16-mahalle-maci"] = {
    "baslik": "Cemo Penaltı İstiyor", "aciklama": "Kamera her şeyi gördü 😂 Sizce penaltı mı?",
    "planlar": [
        K("cemo", "[surprised] Penaltıııı! Hakem bey, beni düşürdüler!", "dramatic",
          ["cemo"], "A neighborhood artificial-turf football pitch in the evening under floodlights, Cemo lying on the "
          "grass holding his leg dramatically."),
        K(Y, "Kim düşürdü? Top yüz metre ötede!", "unimpressed",
          ["esnaf", "cemo"], "Same football pitch, the referee standing with a whistle, Cemo seen from behind on the ground."),
        K("cemo", "Rüzgâr hocam. Rakibin rüzgârı!", "insisting",
          ["cemo", "esnaf"], "Same football pitch, Cemo sitting on the grass pointing at the air, the referee seen from behind."),
        K("levent", "[laughs] Hakem bey, Cemo'nun kamerasında her şey var!", "amused",
          ["levent", "esnaf"], "Same football pitch, Levent holding up Cemo's video camera, the "
          "referee seen from behind."),
        A(["esnaf"], "Same football pitch, the referee looking closely at the small screen of the video camera.",
          "the referee watches the camera screen, nods slowly, and blows his whistle", "a sharp referee whistle"),
        K(Y, "Kayıt net: kendi bağcığına basmış. Sarı kart, Cemo!", "strict, holding up a yellow card",
          ["esnaf", "cemo"], "Same football pitch, the referee holding up a yellow card, Cemo seen from behind."),
    ]}

SEN["mizah-17-bakkal"] = {
    "baslik": "Veresiye Defteri", "aciklama": "Bakkalın defteri her şeyi hatırlıyor 😂 Sizin mahallede veresiye var mı?",
    "planlar": [
        K("cemo", "[excited] Rıfat Amca, bir ekmek! Deftere yaz.", "casual",
          ["cemo", "esnaf"], "Inside a small old neighborhood grocery shop with full shelves, Cemo at the counter, "
          "the old grocer seen from behind."),
        K(Y, "Yazayım evlat... Cemo, on yıl önce: bir simit, bir ayran...", "reading slowly",
          ["esnaf", "cemo"], "Same grocery shop, the old grocer behind the counter reading from a thick old notebook, "
          "Cemo seen from behind."),
        K("cemo", "[surprised] Amca, o kadar eskisini de mi yazdın?", "shocked",
          ["cemo", "esnaf"], "Same grocery shop, Cemo leaning back in shock, the old grocer seen from behind."),
        A(["esnaf", "cemo"], "Same grocery shop, the old grocer flipping through the thick notebook.",
          "the grocer flips pages and the notebook unfolds into a long paper scroll falling down to the floor",
          "pages flipping fast"),
        K("levent", "[excited] Tamam amca, Cemo'nun borcunu ben öderim!", "generous",
          ["levent", "esnaf"], "Same grocery shop, Levent stepping in with his wallet, the old grocer seen from behind."),
        K(Y, "[laughs] Sağ ol evlat. Senin babanın sayfası da burada.", "warm and teasing",
          ["esnaf", "levent"], "Same grocery shop, the old grocer smiling and opening another page of the notebook, "
          "Levent seen from behind."),
    ]}

SEN["mizah-18-kebapci"] = {
    "baslik": "Az Tereyağlı Olsun", "aciklama": "Bursa'da az tereyağı istenmez 😂 Siz kebabı nasıl seversiniz?",
    "planlar": [
        K("cemo", "Usta, az tereyağlı olsun. Diyetteyim.", "serious",
          ["cemo", "esnaf"], "Inside a traditional Bursa kebab restaurant with a grill, Cemo at the counter, the kebab "
          "master seen from behind."),
        K(Y, "[surprised] Az tereyağı mı? Bursa'da bu söylenmez evlat!", "deeply offended",
          ["esnaf", "cemo"], "Same kebab restaurant, the kebab master holding a pan of melted butter, shocked, Cemo seen "
          "from behind."),
        K("levent", "[laughs] Usta, kusura bakma. Cemo bugün diyete başladı.", "apologetic, amused",
          ["levent", "esnaf"], "Same kebab restaurant, Levent at a table, the kebab master seen from behind."),
        A(["esnaf"], "Same kebab restaurant, a plate of iskender kebab on the counter.",
          "the kebab master pours a huge stream of sizzling melted butter over the kebab plate with dramatic flair",
          "loud sizzling butter"),
        K("cemo", "[sighs] Usta... bu az mıydı?", "staring at the plate",
          ["cemo", "esnaf"], "Same kebab restaurant, Cemo staring at a plate swimming in butter, the kebab master seen from behind."),
        K(Y, "[laughs] Ben dökmedim evlat. Tereyağı seni seçti.", "wise and proud",
          ["esnaf", "cemo"], "Same kebab restaurant, the kebab master smiling proudly with the empty butter pan, Cemo seen "
          "from behind."),
    ]}

SEN["mizah-19-taksici"] = {
    "baslik": "En Kestirme Yol", "aciklama": "Taksicinin kestirmesi biraz uzun sürdü 😂 Sizin taksici de böyle mi?",
    "planlar": [
        K("cemo", "[surprised] Abi, taksimetre bizden hızlı gidiyor!", "panicked",
          ["cemo"], "Inside a yellow Turkish taxi, Cemo in the back seat staring at the front, the taxi meter not visible."),
        K(Y, "[laughs] Kestirmeden gidiyoruz evlat, biraz sabır.", "relaxed",
          ["esnaf"], "Same taxi, the driver at the wheel turning his head to speak, city streets of Bursa outside."),
        K("levent", "Rıza Abi, Uludağ'ı üçüncü kez geçtik ama!", "worried",
          ["levent"], "Same taxi, Levent in the front passenger seat, snowy Uludağ mountain visible through the window."),
        K(Y, "Manzaralı kestirme bu. Ekstra ücreti yok... şimdilik.", "smug",
          ["esnaf"], "Same taxi, the driver smiling at the wheel."),
        A(["cemo", "levent"], "Same taxi, stopped at the curb.",
          "the taxi stops, Cemo and Levent look out the window and slowly realize they are back where they started",
          "car brakes and a handbrake pull"),
        K("cemo", "[sighs] Abi... biz binmeden önce tam buradaydık.", "defeated",
          ["cemo"], "Same taxi, Cemo in the back seat pointing out the window at the same street corner."),
    ]}


if __name__ == "__main__":
    for kl, sen in SEN.items():
        yol = os.path.join(KOK, "reklamlar", kl, "bilgi.json")
        b = json.load(open(yol, encoding="utf-8"))
        b["oto"]["senaryo"] = sen
        json.dump(b, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        kelime = sum(len(p["metin"].split()) for p in sen["planlar"] if p["tip"] == "konusma")
        print(f"{kl}: {len(sen['planlar'])} plan, {kelime} kelime — {sen['baslik']}")
