from flask import Flask, request, jsonify, render_template, session, send_from_directory, redirect
from flask_cors import CORS
from database import *
from model_manager import BanglaIntentClassifier
from tts_manager import BanglaTTSManager
import urllib.parse
import os
import webbrowser
import subprocess
import threading
import re
import time
import winsound
import math
from collections import Counter
from datetime import datetime, timedelta

# ==================== CREATE FLASK APP ====================
app = Flask(__name__)
app.secret_key = 'memo_mind_secret_key_2024'
CORS(app)

# ==================== INITIALIZE COMPONENTS ====================
intent_classifier = BanglaIntentClassifier()
tts_manager = BanglaTTSManager()

# ==================== INITIALIZE DATABASE ====================
init_database()

# Store last search results for this session
last_search_results = {}

# ==================== CONTEXT HANDLING ====================
user_context = {}


class ConversationContext:
    def __init__(self):
        self.last_query = ""
        self.last_response = ""
        self.last_intent = ""
        self.last_memories = []
        self.timestamp = datetime.now()

    def update(self, query, response, intent, memories=[]):
        self.last_query = query
        self.last_response = response
        self.last_intent = intent
        self.last_memories = memories
        self.timestamp = datetime.now()

    def is_recent(self):
        return (datetime.now() - self.timestamp).seconds < 300


def get_user_context(user_id):
    if user_id not in user_context:
        user_context[user_id] = ConversationContext()
    return user_context[user_id]


# ==================== LANGUAGE DETECTION ====================
def detect_language(text):
    if not text:
        return 'unknown'

    bangla_chars = 0
    total_chars = 0

    for char in text:
        if '\u0980' <= char <= '\u09FF':
            bangla_chars += 1
        total_chars += 1

    if total_chars == 0:
        return 'unknown'

    bangla_ratio = bangla_chars / total_chars
    if bangla_ratio > 0.3:
        return 'bangla'
    else:
        return 'english'


# ==================== BILINGUAL INTENT DETECTION ====================
def predict_intent_bilingual(text):
    language = detect_language(text)
    text_lower = text.lower()

    if language == 'bangla':
        if re.search(r'সকালের|সকালে|দুপুরের|দুপুরে|রাতের|রাতে|medicine|ওষুধ|মেডিসিন', text_lower):
            return 'MEDICINE'
        if re.search(r'ফাইল বের করে দাও|ফাইল খুঁজে দাও|ফাইল সার্চ করো|ডকুমেন্ট খুঁজে দাও', text_lower):
            return 'SEARCH_FILE'
        if re.search(r'ফাইল ওপেন করো', text_lower):
            return 'SEARCH_FILE'
        if re.search(r'মনে রাখো|মনে রেখো|মনে রাখ', text_lower):
            return 'SAVE_MEMORY'
        if re.search(r'মনে করে দাও|মনে করিয়ে দাও|মনে পড়াও|কি ছিল|কোথায় ছিল', text_lower):
            return 'RETRIEVE_MEMORY'
        if re.search(r'গুগল|google|সার্চ করো|খোঁজ করো', text_lower):
            return 'GOOGLE'
        if re.search(r'ইউটিউব|youtube|ভিডিও দেখাও|গান চালাও', text_lower):
            return 'YOUTUBE'
        if re.search(r'অ্যালার্ম|আলার্ম|এলার্ম|রিমাইন্ডার', text_lower):
            return 'ALARM'
        return 'GENERAL'

    else:
        if re.search(r'morning medicine|afternoon medicine|night medicine', text_lower):
            return 'MEDICINE'
        if re.search(r'file open\s+\S+|open file\s+\S+|open\s+\S+\.\w+', text_lower):
            return 'SEARCH_FILE'
        if re.search(r'search file|find file', text_lower):
            return 'SEARCH_FILE'
        if re.search(r'remember\s+|save\s+|store\s+', text_lower):
            return 'SAVE_MEMORY'
        if re.search(r'recall\s+|retrieve\s+|what is\s+|tell me\s+', text_lower):
            return 'RETRIEVE_MEMORY'
        if re.search(r'google\s+|search\s+', text_lower):
            return 'GOOGLE'
        if re.search(r'youtube\s+|video\s+', text_lower):
            return 'YOUTUBE'
        if re.search(r'alarm\s+|reminder\s+|set alarm', text_lower):
            return 'ALARM'
        return 'GENERAL'


# ==================== ENGLISH COMMAND PARSERS ====================
def extract_english_filename(text):
    patterns = [r'file open\s+(\S+)', r'open file\s+(\S+)', r'open\s+(\S+\.\w+)']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_english_memory_text(text):
    patterns = [r'remember\s+(.+)', r'save\s+(.+)', r'store\s+(.+)']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_english_search_query(text):
    patterns = [r'recall\s+(.+)', r'retrieve\s+(.+)', r'what is\s+(.+)', r'tell me\s+(.+)']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_english_google_query(text):
    patterns = [r'google\s+(.+)', r'google search\s+(.+)', r'search\s+(.+)']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return text


def extract_english_youtube_query(text):
    patterns = [r'youtube\s+(.+)', r'youtube video\s+(.+)', r'play\s+(.+)']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return text


def extract_english_alarm_time(text):
    patterns = [
        r'(\d{1,2})[:.](\d{2})\s*(am|pm)',
        r'(\d{1,2})\s*(am|pm)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) >= 2 and groups[1] and groups[1].isdigit():
                return int(groups[0]), int(groups[1]), groups[2].upper()
            elif groups[0]:
                return int(groups[0]), 0, groups[1].upper()
    return None, None, None


# ==================== BANGLA TO ENGLISH FOR FILE SEARCH ====================
def bangla_to_english_for_filename(text):
    remove_words = ['ফাইল', 'ডকুমেন্ট', 'পিডিএফ', 'বের', 'করে', 'দাও', 'খুঁজে', 'দেখাও']
    result = text
    for word in remove_words:
        result = result.replace(word, ' ')

    char_map = {
        'ক': 'k', 'খ': 'kh', 'গ': 'g', 'ঘ': 'gh', 'চ': 'ch', 'ছ': 'chh',
        'জ': 'j', 'ঝ': 'jh', 'ট': 't', 'ঠ': 'th', 'ড': 'd', 'ঢ': 'dh',
        'ত': 't', 'থ': 'th', 'দ': 'd', 'ধ': 'dh', 'ন': 'n', 'প': 'p',
        'ফ': 'ph', 'ব': 'b', 'ভ': 'bh', 'ম': 'm', 'য': 'y', 'র': 'r',
        'ল': 'l', 'শ': 'sh', 'ষ': 'sh', 'স': 's', 'হ': 'h',
        'া': 'a', 'ি': 'i', 'ী': 'ee', 'ু': 'u', 'ূ': 'oo', 'ৃ': 'ri',
        'ে': 'e', 'ৈ': 'oi', 'ো': 'o', 'ৌ': 'ou'
    }

    word_map = {
        'প্রজেক্ট': 'project', 'রিপোর্ট': 'report', 'ডকুমেন্ট': 'document',
        'ফাইল': 'file', 'ডাটা': 'data', 'টেস্ট': 'test', 'ডেমো': 'demo',
        'পিডিএফ': 'pdf', 'ডক্স': 'docx', 'ডক': 'doc', 'এক্সএলএস': 'xlsx'
    }

    for bangla, english in word_map.items():
        result = result.replace(bangla, english)
    for bangla, english in char_map.items():
        result = result.replace(bangla, english)

    result = re.sub(r'\s+', ' ', result)
    result = re.sub(r'[^a-zA-Z0-9\s\._-]', '', result)
    return result.strip().lower()


def search_files_with_bangla_voice(keyword):
    files = search_all_files_auto(keyword)
    if files:
        return files

    english_keyword = bangla_to_english_for_filename(keyword)
    if english_keyword and english_keyword != keyword:
        files = search_all_files_auto(english_keyword)
        if files:
            return files

    words = keyword.split()
    for word in words:
        if len(word) > 2:
            files = search_all_files_auto(word)
            if files:
                return files
    return None


# ==================== PURE PYTHON TF-IDF + COSINE SIMILARITY ====================
def compute_tf(text):
    words = text.lower().split()
    word_count = Counter(words)
    max_freq = max(word_count.values()) if word_count else 1
    tf = {}
    for word, count in word_count.items():
        tf[word] = count / max_freq
    return tf


def compute_idf(all_documents):
    doc_count = len(all_documents)
    word_doc_count = Counter()

    for doc in all_documents:
        unique_words = set(doc.lower().split())
        for word in unique_words:
            word_doc_count[word] += 1

    idf = {}
    for word, count in word_doc_count.items():
        idf[word] = math.log((doc_count + 1) / (count + 1)) + 1
    return idf


def compute_tfidf_vector(text, idf):
    tf = compute_tf(text)
    tfidf = {}
    for word, tf_value in tf.items():
        tfidf[word] = tf_value * idf.get(word, 1)
    return tfidf


def cosine_similarity_pure(vec1, vec2):
    common_words = set(vec1.keys()) & set(vec2.keys())
    dot_product = sum(vec1[word] * vec2[word] for word in common_words)
    mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0
    return dot_product / (mag1 * mag2)


def get_tfidf_similarity(query, memories):
    if not memories:
        return []

    all_texts = [query] + [mem['memory_text'] for mem in memories]
    idf = compute_idf(all_texts)
    vectors = [compute_tfidf_vector(text, idf) for text in all_texts]
    query_vector = vectors[0]

    scored_memories = []
    for i, mem in enumerate(memories):
        similarity = cosine_similarity_pure(query_vector, vectors[i + 1])
        scored_memories.append({
            'memory': mem,
            'score': similarity,
            'percentage': round(similarity * 100, 2),
            'created_at': mem['created_at']
        })

    scored_memories.sort(key=lambda x: x['score'], reverse=True)
    return scored_memories


def retrieve_best_memories(user_id, query, limit=10):
    all_memories = get_all_memories(user_id)
    if not all_memories:
        return []
    return get_tfidf_similarity(query, all_memories)[:limit]


# ==================== PRONOUN RESOLUTION ====================
def resolve_pronouns(text, context):
    if not context or not context.last_memories:
        return text

    pronoun_map = {
        'এটা': context.last_memories[0]['memory']['memory_text'] if context.last_memories else None,
        'ওটা': context.last_memories[0]['memory']['memory_text'] if context.last_memories else None,
        'সেটা': context.last_memories[0]['memory']['memory_text'] if context.last_memories else None,
    }

    for pronoun, replacement in pronoun_map.items():
        if replacement and pronoun in text:
            text = text.replace(pronoun, replacement)
    return text


# ==================== ANSWER FORMATTING ====================
def format_hybrid_response(query, scored_memories):
    if not scored_memories:
        return f"❌ '{query}' সম্পর্কিত কোনো স্মৃতি খুঁজে পাওয়া যায়নি।", None

    if len(scored_memories) == 1:
        return scored_memories[0]['memory']['memory_text'], scored_memories[0]['memory']['memory_text']

    best_match = scored_memories[0]
    best_match_text = best_match['memory']['memory_text']
    best_match_percentage = best_match['percentage']
    other_matches = scored_memories[1:]

    response = f"{best_match_text} (মিল: {best_match_percentage}%)\n\n"
    response += f"🔍 আরও {len(other_matches)} টি স্মৃতি পাওয়া গেছে:\n\n"

    for i, item in enumerate(other_matches[:5], 1):
        response += f"{i}. {item['memory']['memory_text']}\n"
        response += f"   📅 {item['memory']['created_at'][:16]}\n"
        response += f"   🎯 মিল: {item['percentage']}%\n\n"

    return response, best_match_text


# ==================== FILE SEARCH ====================
def search_files_by_keyword(keyword):
    try:
        search_locations = [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"),
        ]

        found_files = []

        for location in search_locations:
            if os.path.exists(location):
                try:
                    for root, dirs, files in os.walk(location):
                        depth = root.count('\\') if os.name == 'nt' else root.count('/')
                        if depth > 4:
                            dirs.clear()
                            continue

                        for file in files:
                            if keyword.lower() in file.lower():
                                full_path = os.path.join(root, file)
                                rel_path = full_path.replace(os.path.expanduser("~"), "~")
                                found_files.append({
                                    'name': file,
                                    'path': full_path,
                                    'relative_path': rel_path,
                                    'source': 'Local 💻',
                                    'modified': datetime.fromtimestamp(os.path.getmtime(full_path)).strftime(
                                        '%Y-%m-%d %H:%M')
                                })
                                if len(found_files) >= 20:
                                    break
                        if len(found_files) >= 20:
                            break
                except:
                    continue
        return found_files if found_files else None
    except:
        return None


def get_google_drive_path():
    possible_paths = [
        os.path.expanduser("~/Google Drive"),
        "G:/My Drive", "D:/Google Drive",
        f"C:/Users/{os.getlogin()}/Google Drive",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def search_google_drive_files(keyword):
    drive_path = get_google_drive_path()
    if not drive_path:
        return None

    found_files = []
    try:
        for root, dirs, files in os.walk(drive_path):
            depth = root.count('\\') if os.name == 'nt' else root.count('/')
            if depth > 4:
                dirs.clear()
                continue
            for file in files:
                if keyword.lower() in file.lower():
                    full_path = os.path.join(root, file)
                    rel_path = full_path.replace(drive_path, "Google Drive ☁️")
                    found_files.append({
                        'name': file,
                        'path': full_path,
                        'relative_path': rel_path,
                        'source': 'Google Drive ☁️',
                        'modified': datetime.fromtimestamp(os.path.getmtime(full_path)).strftime('%Y-%m-%d %H:%M')
                    })
                    if len(found_files) >= 20:
                        break
            if len(found_files) >= 20:
                break
    except:
        pass
    return found_files if found_files else None


def search_all_files_auto(keyword):
    all_files = []
    local_files = search_files_by_keyword(keyword)
    if local_files:
        all_files.extend(local_files)
    drive_files = search_google_drive_files(keyword)
    if drive_files:
        all_files.extend(drive_files)
    return all_files if all_files else None


def format_file_response_with_source(files, keyword):
    if not files:
        return f"❌ '{keyword}' সম্পর্কিত কোনো ফাইল খুঁজে পাওয়া যায়নি।", None

    local_count = sum(1 for f in files if 'Local' in f['source'])
    drive_count = sum(1 for f in files if 'Google Drive' in f['source'])

    response = f"📁 **'{keyword}' সম্পর্কিত {len(files)} টি ফাইল পাওয়া গেছে:**\n"
    if local_count > 0:
        response += f"   💻 লোকাল: {local_count} টি\n"
    if drive_count > 0:
        response += f"   ☁️ গুগল ড্রাইভ: {drive_count} টি\n"
    response += "\n"

    for i, file in enumerate(files, 1):
        ext = os.path.splitext(file['name'])[1].lower()
        icon = "📄"
        if ext == '.pdf':
            icon = "📕"
        elif ext in ['.docx', '.doc']:
            icon = "📘"
        elif ext in ['.jpg', '.png']:
            icon = "🖼️"
        elif ext in ['.mp3', '.wav']:
            icon = "🎵"
        elif ext == '.mp4':
            icon = "🎬"
        elif ext in ['.xlsx', '.xls']:
            icon = "📊"

        response += f"{i}. {icon} **{file['name']}** {file['source']}\n"
        response += f"   📂 পাথ: `{file['relative_path']}`\n"
        response += f"   📅 শেষ পরিবর্তন: {file['modified']}\n\n"

    response += f"💡 **ফাইল ওপেন করতে:** 'ফাইল ওপেন করো 1' লিখুন\n"
    return response, files[0]['path'] if files else None


def open_file_by_index(files, index):
    if 1 <= index <= len(files):
        try:
            os.startfile(files[index - 1]['path'])
            return True, files[index - 1]['name'], files[index - 1]['path']
        except:
            return False, str(e), None
    return False, "Invalid index", None


# ==================== ALARM SYSTEM ====================
active_alarms = {}
alarm_counter = 0


class Alarm:
    def __init__(self, alarm_id, hour, minute, am_pm, user_input, user_id):
        self.alarm_id = alarm_id
        self.hour = hour
        self.minute = minute
        self.am_pm = am_pm
        self.user_input = user_input
        self.user_id = user_id
        self.created_at = datetime.now()

        if am_pm.upper() == 'PM' and hour != 12:
            self.schedule_hour = hour + 12
        elif am_pm.upper() == 'AM' and hour == 12:
            self.schedule_hour = 0
        else:
            self.schedule_hour = hour

    def get_time_display(self):
        return f"{self.hour:02d}:{self.minute:02d} {self.am_pm}"

    def get_next_run_time(self):
        now = datetime.now()
        alarm_time = now.replace(hour=self.schedule_hour, minute=self.minute, second=0, microsecond=0)
        if alarm_time <= now:
            alarm_time += timedelta(days=1)
        return alarm_time


def parse_alarm_time(text):
    user_input_lower = text.lower()
    hour = None
    minute = 0
    am_pm = None

    # Bangla number to digit mapping
    bangla_number_map = {
        'এক': '1', 'দুই': '2', 'তিন': '3', 'চার': '4', 'পাঁচ': '5',
        'ছয়': '6', 'সাত': '7', 'আট': '8', 'নয়': '9', 'দশ': '10',
        'এগারো': '11', 'বারো': '12', 'ত্রিশ': '30', 'চৌত্রিশ': '34', 'পয়ত্রিশ': '35',
        'ছত্রিশ': '36', 'সাঁইত্রিশ': '37', 'আটত্রিশ': '38', 'উনচল্লিশ': '39'
    }

    converted_text = user_input_lower
    for word, digit in bangla_number_map.items():
        converted_text = converted_text.replace(word, digit)

    # Pattern: সকাল ৭টা / সকাল ৭টা ৩০ মিনিট
    match = re.search(
        r'(সকাল|সকালে|দুপুর|দুপুরে|বিকাল|বিকালে|সন্ধ্যা|সন্ধ্যায়|রাত|রাতে)\s*(\d{1,2})\s*টা\s*(?:(\d{1,2})\s*মিনিট)?',
        converted_text)
    if match:
        period = match.group(1)
        hour = int(match.group(2))
        if match.group(3):
            minute = int(match.group(3))
        am_pm = 'AM' if period in ['সকাল', 'সকালে'] else 'PM'

    # Pattern: 7:30 AM
    if hour is None:
        match = re.search(r'(\d{1,2})[:.](\d{2})\s*(am|pm)', converted_text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            am_pm = match.group(3).upper()

    # Pattern: 7 AM
    if hour is None:
        match = re.search(r'(\d{1,2})\s*(am|pm)', converted_text)
        if match:
            hour = int(match.group(1))
            minute = 0
            am_pm = match.group(2).upper()

    # Pattern: 7টা
    if hour is None:
        match = re.search(r'(\d{1,2})\s*টা', converted_text)
        if match:
            hour = int(match.group(1))
            minute = 0
            if 'রাত' in converted_text or 'সন্ধ্যা' in converted_text or 'বিকাল' in converted_text:
                am_pm = 'PM'
            elif 'সকাল' in converted_text:
                am_pm = 'AM'
            else:
                am_pm = 'AM' if hour < 12 else 'PM'

    if hour is not None:
        if hour < 1: hour = 1
        if hour > 12: hour = 12
        if minute < 0: minute = 0
        if minute > 59: minute = 59
        return hour, minute, am_pm
    return None, None, None


def play_alarm(alarm_id, alarm_time_display, user_input):
    def _play():
        try:
            for i in range(5):
                winsound.Beep(1000, 500)
                time.sleep(0.5)
            tts_manager.speak(f"⏰ অ্যালার্ম! {alarm_time_display} টা বাজে। আপনি বলেছিলেন: {user_input}")
            if alarm_id in active_alarms:
                del active_alarms[alarm_id]
        except:
            pass

    thread = threading.Thread(target=_play)
    thread.daemon = True
    thread.start()


def schedule_alarm(alarm):
    next_run = alarm.get_next_run_time()
    wait_seconds = (next_run - datetime.now()).total_seconds()
    if wait_seconds > 0:
        timer = threading.Timer(wait_seconds, play_alarm,
                                args=[alarm.alarm_id, alarm.get_time_display(), alarm.user_input])
        timer.daemon = True
        timer.start()
        active_alarms[alarm.alarm_id] = timer
        return True, next_run
    return False, None


# ==================== DASHBOARD FUNCTIONS ====================
def get_last_7_days_activity(memories):
    today = datetime.now().date()
    activity = {}
    days = ['সোম', 'মঙ্গল', 'বুধ', 'বৃহস্পতি', 'শুক্র', 'শনি', 'রবি']
    for i in range(7):
        date = today - timedelta(days=i)
        count = sum(1 for m in memories if m['created_at'].startswith(date.strftime('%Y-%m-%d')))
        activity[days[i]] = count
    return activity


def get_intent_breakdown(conversations):
    intents = [c['intent'] for c in conversations if c['intent']]
    counts = Counter(intents)
    names = {
        'SAVE_MEMORY': 'মেমরি সেভ', 'RETRIEVE_MEMORY': 'মেমরি রিকল',
        'GOOGLE': 'গুগল সার্চ', 'YOUTUBE': 'ইউটিউব', 'ALARM': 'অ্যালার্ম',
        'SEARCH_FILE': 'ফাইল সার্চ', 'GENERAL': 'সাধারণ', 'MEDICINE': 'ওষুধ রিমাইন্ডার'
    }
    return {names.get(k, k): v for k, v in counts.items()}


def get_top_keywords(memories, limit=10):
    all_text = ' '.join([m['memory_text'] for m in memories])
    words = all_text.split()
    stop = {'আমি', 'আমার', 'তুমি', 'তোমার', 'এটি', 'কি', 'কী', 'এবং', 'হল', 'ছিল'}
    filtered = [w for w in words if len(w) > 2 and w not in stop]
    return dict(Counter(filtered).most_common(limit))


def get_hourly_activity(conversations):
    hourly = [0] * 24
    for conv in conversations:
        try:
            hour = datetime.fromisoformat(conv['created_at']).hour
            hourly[hour] += 1
        except:
            pass
    return hourly


def get_weekly_activity(conversations):
    days = ['সোম', 'মঙ্গল', 'বুধ', 'বৃহস্পতি', 'শুক্র', 'শনি', 'রবি']
    weekly = [0] * 7
    for conv in conversations:
        try:
            weekly[datetime.fromisoformat(conv['created_at']).weekday()] += 1
        except:
            pass
    return {'days': days, 'counts': weekly}


def get_memory_trend(memories):
    trend = {}
    for mem in memories:
        try:
            date = mem['created_at'][:10]
            trend[date] = trend.get(date, 0) + 1
        except:
            pass
    return dict(sorted(trend.items())[-30:])


def get_current_streak(conversations):
    if not conversations:
        return 0
    dates = set()
    for conv in conversations:
        try:
            dates.add(conv['created_at'][:10])
        except:
            pass
    sorted_dates = sorted(dates, reverse=True)
    streak = 0
    for i, d in enumerate(sorted_dates):
        expected = (datetime.now().date() - timedelta(days=i)).isoformat()
        if d == expected:
            streak += 1
        else:
            break
    return streak


def get_file_type_stats(conversations):
    types = Counter()
    for conv in conversations:
        if conv['intent'] == 'SEARCH_FILE':
            inp = conv['user_input'].lower()
            if '.pdf' in inp:
                types['PDF'] += 1
            elif '.docx' in inp or '.doc' in inp:
                types['DOCX'] += 1
            elif '.jpg' in inp or '.png' in inp:
                types['IMAGE'] += 1
            else:
                types['OTHER'] += 1
    return dict(types)


# ==================== ROUTES ====================
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('dashboard.html')


@app.route('/api/dashboard_stats')
def dashboard_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Login required'})
    uid = session['user_id']
    memories = get_all_memories(uid)
    convs = get_conversation_history(uid, 500)
    return jsonify({
        'total_memories': len(memories),
        'total_conversations': len(convs),
        'last_7_days': get_last_7_days_activity(memories),
        'intent_breakdown': get_intent_breakdown(convs),
        'top_keywords': get_top_keywords(memories, 10),
        'hourly_activity': get_hourly_activity(convs),
        'weekly_activity': get_weekly_activity(convs),
        'memory_trend': get_memory_trend(memories),
        'current_streak': get_current_streak(convs),
        'file_types': get_file_type_stats(convs)
    })


@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if not username or not password:
        return jsonify({'success': False, 'message': 'ইউজারনেম এবং পাসওয়ার্ড প্রয়োজন'})
    if len(password) < 4:
        return jsonify({'success': False, 'message': 'পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে'})
    uid = create_user(username, password)
    if uid:
        return jsonify({'success': True, 'message': 'রেজিস্ট্রেশন সফল! এখন লগইন করুন।'})
    return jsonify({'success': False, 'message': 'এই ইউজারনেম ইতিমধ্যে নেওয়া হয়েছে'})


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    user = authenticate_user(username, password)
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({'success': True, 'message': f'স্বাগতম {username}!',
                        'user': {'id': user['id'], 'username': user['username']}})
    return jsonify({'success': False, 'message': 'ভুল ইউজারনেম বা পাসওয়ার্ড'})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'লগআউট সফল হয়েছে'})


@app.route('/api/check_session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'user': {'id': session['user_id'], 'username': session['username']}})
    return jsonify({'logged_in': False})


@app.route('/api/memories', methods=['GET'])
def get_memories_route():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    return jsonify({'success': True, 'memories': [dict(m) for m in get_all_memories(session['user_id'])]})


@app.route('/api/get_medicines', methods=['GET'])
def get_medicines_route():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    medicines = get_medicines(session['user_id'])
    return jsonify({'success': True, 'medicines': medicines})


@app.route('/api/save_medicines', methods=['POST'])
def save_medicines_route():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    data = request.json
    save_medicines(session['user_id'], data.get('morning', ''), data.get('afternoon', ''), data.get('night', ''))
    return jsonify({'success': True, 'message': '💊 Medicine সংরক্ষণ করা হয়েছে!'})


# ==================== MAIN PROCESS ROUTE ====================
@app.route('/api/process', methods=['POST'])
def process_input():
    global last_search_results, alarm_counter
    data = request.json
    user_input = data.get('text', '').strip()

    if not user_input:
        return jsonify({'response': 'কিছু লিখুন', 'intent': 'EMPTY'})

    user_id = session.get('user_id')
    context = get_user_context(user_id) if user_id else None
    language = detect_language(user_input)

    if context:
        user_input = resolve_pronouns(user_input, context)

    intent = predict_intent_bilingual(user_input)
    response = ""
    link = None

    if intent == 'SAVE_MEMORY':
        if user_id:
            if language == 'bangla':
                mem_text = intent_classifier.extract_memory_text(user_input)
            else:
                mem_text = extract_english_memory_text(user_input)

            if mem_text:
                save_memory(user_id, mem_text)
                log_conversation(user_id, user_input, "মনে রাখা হয়েছে", intent)
                response = "✅ মনে রাখা হয়েছে!"
                tts_manager.speak("আপনার কথাটি মনে রাখা হয়েছে")
            else:
                response = "কি মনে রাখব? দয়া করে কিছু লিখুন।"
        else:
            response = "মেমরি সেভ করতে দয়া করে লগইন করুন।"

    elif intent == 'RETRIEVE_MEMORY':
        if user_id:
            if language == 'bangla':
                query = intent_classifier.extract_search_query(user_input)
            else:
                query = extract_english_search_query(user_input)

            if query:
                scored_memories = retrieve_best_memories(user_id, query, limit=10)

                if scored_memories:
                    context.update(user_input, "", intent, scored_memories)

                    if len(scored_memories) == 1:
                        best = scored_memories[0]
                        response = f"{best['memory']['memory_text']} (মিল: {best['percentage']}%)"
                        tts_manager.speak(best['memory']['memory_text'])
                    else:
                        formatted_response, best_match = format_hybrid_response(query, scored_memories)
                        response = formatted_response
                        tts_manager.speak(best_match)

                    log_conversation(user_id, user_input, response, intent)
                else:
                    response = f"❌ '{query}' সম্পর্কিত কোনো স্মৃতি খুঁজে পাওয়া যায়নি।"
                    tts_manager.speak("দুঃখিত, কোনো স্মৃতি খুঁজে পাওয়া যায়নি")
            else:
                response = "কি মনে করিয়ে দেব? দয়া করে বলেন।"
        else:
            response = "মেমরি রিকল করতে দয়া করে লগইন করুন।"

    elif intent == 'MEDICINE':
        if user_id:
            medicines = get_medicines(user_id)
            user_input_lower = user_input.lower()

            if 'সকালের' in user_input or 'সকালে' in user_input or 'morning' in user_input_lower:
                if medicines['morning']:
                    response = f"🌅 আপনার সকালের medicine: {medicines['morning']}"
                else:
                    response = "🌅 আপনার সকালের medicine সেট করা নেই। 💊 বাটনে ক্লিক করে সেট করুন।"
            elif 'দুপুরের' in user_input or 'দুপুরে' in user_input or 'afternoon' in user_input_lower:
                if medicines['afternoon']:
                    response = f"☀️ আপনার দুপুরের medicine: {medicines['afternoon']}"
                else:
                    response = "☀️ আপনার দুপুরের medicine সেট করা নেই। 💊 বাটনে ক্লিক করে সেট করুন।"
            elif 'রাতের' in user_input or 'রাতে' in user_input or 'night' in user_input_lower:
                if medicines['night']:
                    response = f"🌙 আপনার রাতের medicine: {medicines['night']}"
                else:
                    response = "🌙 আপনার রাতের medicine সেট করা নেই। 💊 বাটনে ক্লিক করে সেট করুন।"
            else:
                response = "💊 আপনার Medicine:\n"
                if medicines['morning']:
                    response += f"🌅 সকাল: {medicines['morning']}\n"
                if medicines['afternoon']:
                    response += f"☀️ দুপুর: {medicines['afternoon']}\n"
                if medicines['night']:
                    response += f"🌙 রাত: {medicines['night']}\n"
                if not medicines['morning'] and not medicines['afternoon'] and not medicines['night']:
                    response = "💊 আপনার কোনো medicine সেট করা নেই। 💊 বাটনে ক্লিক করে সেট করুন।"

            tts_manager.speak(response)
            log_conversation(user_id, user_input, response, intent)
        else:
            response = "Medicine রিমাইন্ডার পেতে দয়া করে লগইন করুন।"

    elif intent == 'GOOGLE':
        if language == 'bangla':
            query = intent_classifier.extract_google_query(user_input)
        else:
            query = extract_english_google_query(user_input)

        if not query:
            query = user_input
        link = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        response = f"🌐 গুগল লিংক তৈরি হয়েছে: {query}"
        tts_manager.speak("গুগল লিংক তৈরি করা হয়েছে")
        webbrowser.open(link)
        if user_id:
            log_conversation(user_id, user_input, response, intent)

    elif intent == 'YOUTUBE':
        if language == 'bangla':
            query = intent_classifier.extract_youtube_query(user_input)
        else:
            query = extract_english_youtube_query(user_input)

        if not query:
            query = user_input
        link = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        response = f"🎬 ইউটিউব লিংক তৈরি হয়েছে: {query}"
        tts_manager.speak("ইউটিউব লিংক তৈরি করা হয়েছে")
        webbrowser.open(link)
        if user_id:
            log_conversation(user_id, user_input, response, intent)

    elif intent == 'ALARM':
        hour, minute, am_pm = parse_alarm_time(user_input)

        if hour is None and language == 'english':
            hour, minute, am_pm = extract_english_alarm_time(user_input)

        if hour is not None:
            alarm_counter += 1
            alarm_id = alarm_counter
            new_alarm = Alarm(alarm_id, hour, minute, am_pm, user_input, user_id)
            success, next_run = schedule_alarm(new_alarm)

            if success:
                response = f"⏰ অ্যালার্ম সেট করা হয়েছে {hour:02d}:{minute:02d} {am_pm} টার জন্য।\n📅 {next_run.strftime('%Y-%m-%d %I:%M %p')} এ বাজবে।"
                tts_manager.speak(f"অ্যালার্ম সেট করা হয়েছে {hour} টা {minute} মিনিট {am_pm} এ")
                log_conversation(user_id, user_input, response, intent)
            else:
                response = "❌ অ্যালার্ম সেট করতে ব্যর্থ।"
        else:
            response = """⏰ অ্যালার্ম সেট করার নিয়ম:
• অ্যালার্ম সেট করো সকাল ৭টা
• এলার্ম সেট করো রাত ১০টা
• alarm set for 8:30 AM"""
            tts_manager.speak("সঠিক সময় দিন")

        if user_id:
            log_conversation(user_id, user_input, response, intent)

    elif intent == 'SEARCH_FILE':
        open_match = re.search(r'ফাইল ওপেন করো\s*(\d+)', user_input, re.IGNORECASE)
        english_open_match = re.search(r'file open\s+(\S+)|open file\s+(\S+)|open\s+(\S+\.\w+)', user_input,
                                       re.IGNORECASE)

        if open_match and session.get('last_search_key'):
            file_index = int(open_match.group(1))
            files = last_search_results.get(session['last_search_key'], [])
            if files:
                success, result, file_path = open_file_by_index(files, file_index)
                if success:
                    response = f"✅ '{result}' ফাইলটি ওপেন করা হচ্ছে...\n📂 পাথ: {file_path}"
                    tts_manager.speak("ফাইল ওপেন করা হচ্ছে")
                else:
                    response = f"❌ ফাইল ওপেন করতে ব্যর্থ: {result}"
            else:
                response = "❌ আগের সার্চের ফলাফল পাওয়া যায়নি।"

        elif english_open_match:
            filename = None
            for group in english_open_match.groups():
                if group:
                    filename = group
                    break

            if filename:
                filename = filename.strip().lower()
                files = search_all_files_auto(filename)
                if not files and '.' in filename:
                    name_without_ext = filename.rsplit('.', 1)[0]
                    files = search_all_files_auto(name_without_ext)
                if not files and '.' not in filename:
                    files = search_all_files_auto(f"{filename}.pdf")

                if files:
                    session_key = f"user_{user_id if user_id else 'guest'}"
                    last_search_results[session_key] = files
                    session['last_search_key'] = session_key
                    first_file = files[0]['path']
                    try:
                        os.startfile(first_file)
                        response = f"✅ '{filename}' ফাইলটি ওপেন করা হয়েছে!\n📂 পাথ: {first_file}"
                        tts_manager.speak(f"{filename} ফাইল ওপেন করা হয়েছে")
                    except:
                        response = f"❌ ফাইল ওপেন করতে ব্যর্থ"
                else:
                    response = f"❌ '{filename}' নামে কোনো ফাইল খুঁজে পাওয়া যায়নি।"
                    tts_manager.speak("ফাইল খুঁজে পাওয়া যায়নি")
            else:
                response = "কোন ফাইল খুলতে চান? ফাইলের নাম দিন। যেমন: 'file open report.pdf'"

        else:
            filename = intent_classifier.extract_filename(user_input)
            if filename:
                files = search_files_with_bangla_voice(filename)
                if files:
                    session_key = f"user_{user_id if user_id else 'guest'}"
                    last_search_results[session_key] = files
                    session['last_search_key'] = session_key
                    response, first_file_path = format_file_response_with_source(files, filename)
                    tts_manager.speak(f"{len(files)} টি ফাইল পাওয়া গেছে")
                    if first_file_path:
                        try:
                            os.startfile(first_file_path)
                            response += f"\n\n✅ প্রথম ফাইলটি自動 ওপেন করা হয়েছে!"
                        except:
                            response += f"\n\n⚠️ ফাইল ওপেন করতে সমস্যা"
                else:
                    response = f"❌ '{filename}' সম্পর্কিত কোনো ফাইল খুঁজে পাওয়া যায়নি।"
                    tts_manager.speak("কোনো ফাইল খুঁজে পাওয়া যায়নি")
            else:
                response = "কোন ফাইল খুঁজতে চান? ফাইলের নাম দিন। যেমন: 'ফাইল বের করে দাও project'"

        if user_id:
            log_conversation(user_id, user_input, response, intent)

    else:
        response = f"""আপনি লিখেছেন: "{user_input}"

📌 কীভাবে ব্যবহার করবেন:

📝 মনে রাখো [বিষয়] / remember [topic] - মেমরি সেভ
🔍 মনে করে দাও [কী] / recall [keyword] - মেমরি রিকল
🌐 গুগল [কীওয়ার্ড] / google [keyword] - গুগল সার্চ
🎬 ইউটিউব [ভিডিও] / youtube [video] - ইউটিউব সার্চ
⏰ অ্যালার্ম [সময়] / alarm [time] - অ্যালার্ম সেট
📁 ফাইল বের করে দাও [নাম] / file open [filename] - ফাইল সার্চ
💊 মনে করে দাও সকালের medicine / morning medicine - ওষুধ রিমাইন্ডার"""
        if user_id:
            log_conversation(user_id, user_input, response, intent)

    if context:
        context.update(user_input, response, intent)

    return jsonify({'response': response, 'intent': intent, 'link': link})


@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory('audio', filename)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)