# pickmychild - בוט טלגרם לסינון תמונות 📸

בוט טלגרם חכם המאפשר זיהוי והחזרת תמונות של אנשים מתוך אלבומים גדולים ואירועים.

## ✨ תכונות עיקריות

- 👥 **ניהול רשימת אנשים אישית** - הוספה, עריכה ומחיקה של פרופילים
- 🔍 **סינון תמונות חכם** - זיהוי פנים מתקדם באמצעות AI
- 🎉 **מצב אירועים** - העלאת ZIP של תמונות אירוע וחלוקה למשתתפים
- 🚀 **ביצועים גבוהים** - חיפוש מהיר באמצעות FAISS
- 🇮🇱 **ממשק בעברית** - חווית משתמש מלאה בעברית

## 🏗️ ארכיטקטורה

### Stack טכנולוגי

- **Bot Framework**: python-telegram-bot 20.7
- **Face Recognition**: InsightFace (ArcFace)
- **Vector Search**: FAISS (Meta)
- **Database**: SQLAlchemy + SQLite/PostgreSQL
- **Image Processing**: OpenCV, Pillow

### Pipeline זיהוי פנים

1. **Detection** - זיהוי פנים בתמונה
2. **Embedding** - המרה לוקטור מספרי (512 מימדים)
3. **Similarity Search** - חיפוש דמיון במאגר הוקטורים

## 📋 דרישות מערכת

- Python 3.9+
- 4GB RAM (מינימום)
- 2GB נפח אחסון פנוי

## 🚀 התקנה

### 1. שכפול הפרויקט

```bash
git clone <repository-url>
cd pickmychild
```

### 2. יצירת סביבה וירטואלית

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# או
venv\Scripts\activate  # Windows
```

### 3. התקנת תלויות

```bash
pip install -r requirements.txt
```

### 4. הגדרת משתני סביבה

```bash
cp .env.example .env
# ערוך את .env והוסף את ה-TELEGRAM_BOT_TOKEN שלך
```

### 5. הורדת מודלי AI

```bash
python scripts/download_models.py
```

### 6. אתחול מסד הנתונים

```bash
python scripts/init_db.py
```

## ▶️ הפעלה

### Local Development

```bash
python main.py
```

### 🚀 Production Deployment (24/7)

**Recommended:** Deploy to Railway.app for free 24/7 hosting!

```bash
# Quick deploy
git push origin main  # Railway auto-deploys from GitHub

# See detailed instructions
cat RAILWAY_DEPLOY.md
```

**Other options:** Render.com, Fly.io, Google Cloud Run
- Full deployment guide: [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 📱 שימוש בבוט

### פקודות עיקריות

- `/start` - התחלת השיחה והצגת תפריט ראשי
- `/add_person` - הוספת אדם חדש לרשימה
- `/list_people` - הצגת רשימת האנשים
- `/done` - סיום הוספת תמונות לפרופיל

### תהליך Onboarding (משתמש חדש)

1. שלח `/start`
2. לחץ על "➕ הוסף אדם"
3. שלח 5-20 תמונות פנים ברורות
4. שלח `/done` לסיום
5. התפריט הראשי יופיע

### סינון תמונות

1. לחץ על "🧭 סינון לפי האנשים שלי"
2. שלח תמונות (בודדות או אלבום)
3. קבל בחזרה רק תמונות עם התאמה

### יצירת אירוע

1. לחץ על "📦 יצירת אירוע"
2. העלה ZIP של תמונות
3. קבל מספר אירוע (למשל: EVT-48231)
4. שתף את המספר עם משתתפים

### שימוש במספר אירוע

1. לחץ על "#️⃣ יש לי מספר אירוע"
2. הזן את מספר האירוע
3. קבל את כל התמונות הרלוונטיות

## 🔧 הגדרות מתקדמות

### Feature Flags

ניתן להפעיל/לכבות תכונות שונות דרך משתני סביבה:

```env
# הפעלת תכונת אירועים (ZIP uploads, event codes)
ENABLE_EVENTS_FEATURE=false
```

**הערה:** כברירת מחדל, תכונת האירועים **כבויה**. לפרטים נוספים ראה [FEATURES.md](FEATURES.md).

### סף זיהוי (Confidence Threshold)

ערך ברירת המחדל: **80%**

```env
FACE_MATCH_THRESHOLD=0.80
```

ערך גבוה יותר = פחות תוצאות אך מדויקות יותר  
ערך נמוך יותר = יותר תוצאות אך יותר False Positives

### גודל ZIP מקסימלי

```env
MAX_ZIP_SIZE_MB=500
```

### תקופת שמירת אירועים

```env
EVENT_RETENTION_DAYS=30
```

## 📊 מבנה הפרויקט

```
pickmychild/
├── main.py                 # נקודת כניסה
├── config.py               # הגדרות ומשתני סביבה
├── database.py             # חיבור למסד נתונים
├── models.py               # מודלים (User, Person, Event)
│
├── services/
│   ├── ai_service.py       # שכבת AI (InsightFace + FAISS)
│   ├── event_processor.py  # עיבוד אירועים אסינכרוני
│   └── storage_service.py  # ניהול קבצים
│
├── handlers/
│   ├── start.py            # Onboarding & תפריט ראשי
│   ├── people.py           # ניהול אנשים
│   ├── filter.py           # סינון תמונות
│   └── events.py           # יצירה ושימוש באירועים
│
├── utils/
│   ├── decorators.py       # ACK, typing, error handling
│   ├── keyboards.py        # תפריטי Inline
│   └── validators.py       # ולידציה של קלט
│
└── scripts/
    ├── download_models.py  # הורדת מודלי AI
    └── init_db.py          # אתחול DB
```

## 🎯 מדדי ביצועים (SLO)

- ⚡ **ACK Response**: ≤ 1 שניה
- 🖼️ **סינון תמונה בודדת**: ≤ 3 שניות
- 📦 **מנה ראשונה באירוע**: ≤ 2-3 שניות
- 🔄 **עדכון סטטוס**: כל 5-10 שניות

## 🔒 פרטיות ואבטחה

- 🔐 **אין שמירה של תמונות מקוריות** - רק וקטורים מספריים
- 🗑️ **מחיקה מלאה** - פקודת "שכח אותי" מוחקת את כל הנתונים
- ⏰ **ניקוי אוטומטי** - אירועים ישנים נמחקים אוטומטית
- 🔒 **עיבוד מקומי** - אין שליחת תמונות לשרתים חיצוניים

## 🐛 Troubleshooting

### הבוט לא מגיב

1. בדוק שה-TOKEN תקין
2. וודא שהבוט רץ (`python main.py`)
3. בדוק logs: `tail -f logs/bot.log`

### זיהוי לא מדויק

1. הוסף יותר תמונות דוגמה (10-15)
2. השתמש בתמונות באיכות גבוהה
3. הקפד על תאורה טובה ופנים קדמיות
4. הורד את FACE_MATCH_THRESHOLD ל-0.75

### עיבוד אירוע איטי

1. בדוק שימוש CPU/RAM
2. הקטן את BATCH_SIZE
3. שקול שדרוג חומרה או שימוש ב-GPU

## 📝 רישיון

MIT License - ראה קובץ LICENSE לפרטים

## 🤝 תרומה

Pull Requests מתקבלים בברכה! אנא פתח Issue קודם לדיון בשינויים מהותיים.

## 📞 תמיכה

לשאלות ובעיות, פתח Issue ב-GitHub.

---

**Made with ❤️ for families and event photographers**
