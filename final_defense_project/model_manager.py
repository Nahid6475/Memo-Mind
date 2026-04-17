import re
import os
import math
from collections import Counter


class BanglaIntentClassifier:
    def __init__(self, model_path='models/intent_model'):
        self.labels = ['SAVE_MEMORY', 'RETRIEVE_MEMORY', 'GOOGLE', 'YOUTUBE', 'ALARM', 'GENERAL', 'SEARCH_FILE',
                       'MEDICINE']
        print("✅ Running - Pure Python Pattern Matching (No PyTorch, No NumPy)")

    def predict_intent(self, text):
        return self._pattern_match(text)

    def _pattern_match(self, text):
        text_lower = text.lower()

        # Medicine patterns
        if re.search(r'সকালের|সকালে|দুপুরের|দুপুরে|রাতের|রাতে|medicine|ওষুধ|মেডিসিন|morning|afternoon|night',
                     text_lower):
            return 'MEDICINE'

        # File search patterns
        if re.search(r'ফাইল বের করে দাও|ফাইল খুঁজে দাও|ফাইল সার্চ করো|ডকুমেন্ট খুঁজে দাও|পিডিএফ বের করে দাও',
                     text_lower):
            return 'SEARCH_FILE'

        # Memory save patterns
        if re.search(r'মনে রাখো|মনে রেখো|মনে রাখ', text_lower):
            return 'SAVE_MEMORY'

        # Memory retrieve patterns
        if re.search(r'মনে করে দাও|মনে করিয়ে দাও|মনে পড়াও|কি ছিল|কোথায় ছিল', text_lower):
            return 'RETRIEVE_MEMORY'

        # Google search patterns
        if re.search(r'গুগল|google|সার্চ করো|খোঁজ করো', text_lower):
            return 'GOOGLE'

        # YouTube search patterns
        if re.search(r'ইউটিউব|youtube|ভিডিও দেখাও|গান চালাও', text_lower):
            return 'YOUTUBE'

        # Alarm patterns
        if re.search(r'অ্যালার্ম|আলার্ম|রিমাইন্ডার|স্মরণ করিয়ে দেবে|এলার্ম', text_lower):
            return 'ALARM'

        return 'GENERAL'

    def extract_filename(self, text):
        """Extract filename from search command - supports both Bangla and English"""
        patterns = [
            r'ফাইল বের করে দাও\s*',
            r'ফাইল খুঁজে দাও\s*',
            r'ফাইল সার্চ করো\s*',
            r'ডকুমেন্ট খুঁজে দাও\s*',
            r'পিডিএফ বের করে দাও\s*',
            r'file search\s*',
            r'find file\s*',
        ]
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Remove common Bangla words from filename
        remove_words = [
            'একটা', 'একটি', 'টা', 'টি', 'দিয়ে', 'করে', 'করো',
            'প্লিজ', 'please', 'দয়া', 'করুন', 'আমার', 'তোমার'
        ]
        for word in remove_words:
            text = text.replace(word, ' ')

        # Convert Bangla digits to English digits
        bangla_digits = {'০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
                         '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'}
        for bangla, english in bangla_digits.items():
            text = text.replace(bangla, english)

        return text.strip()

    def extract_memory_text(self, text):
        patterns = [r'মনে রাখো\s*', r'মনে রেখো\s*', r'মনে রাখ\s*']
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text.strip()

    def extract_search_query(self, text):
        patterns = [r'মনে করে দাও\s*', r'মনে করিয়ে দাও\s*', r'মনে পড়াও\s*']
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text.strip()

    def extract_google_query(self, text):
        patterns = [r'গুগল\s*', r'গুগল সার্চ করো\s*', r'সার্চ করো\s*']
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text.strip()

    def extract_youtube_query(self, text):
        patterns = [r'ইউটিউব\s*', r'ইউটিউবে\s*', r'ভিডিও দেখাও\s*']
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text.strip()

    def extract_alarm_time(self, text):
        time_patterns = [
            r'(\d{1,2})[:.](\d{2})\s*(am|pm|সকাল|রাত|বিকাল)?',
            r'সকাল\s*(\d{1,2})\s*টা',
            r'রাত\s*(\d{1,2})\s*টা',
            r'(\d{1,2})\s*টা'
        ]
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2 and groups[1] and groups[1].isdigit():
                    return f"{groups[0]}:{groups[1]}"
                elif groups[0]:
                    return f"{groups[0]}:00"
        return None


# ==================== PURE PYTHON TF-IDF + COSINE SIMILARITY ====================
def compute_tf(text):
    """Term Frequency - Pure Python"""
    words = text.lower().split()
    word_count = Counter(words)
    max_freq = max(word_count.values()) if word_count else 1
    tf = {}
    for word, count in word_count.items():
        tf[word] = count / max_freq
    return tf


def compute_idf(all_documents):
    """Inverse Document Frequency - Pure Python"""
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
    """Compute TF-IDF vector for a single document"""
    tf = compute_tf(text)
    tfidf = {}
    for word, tf_value in tf.items():
        tfidf[word] = tf_value * idf.get(word, 1)
    return tfidf


def cosine_similarity_pure(vec1, vec2):
    """Compute cosine similarity between two vectors - Pure Python"""
    common_words = set(vec1.keys()) & set(vec2.keys())

    dot_product = sum(vec1[word] * vec2[word] for word in common_words)

    mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0

    return dot_product / (mag1 * mag2)


def get_tfidf_similarity(query, memories):
    """Pure Python TF-IDF + Cosine Similarity with percentage scores"""
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
    """Retrieve best matching memories using TF-IDF + Cosine Similarity"""
    from database import get_all_memories
    all_memories = get_all_memories(user_id)

    if not all_memories:
        return []

    return get_tfidf_similarity(query, all_memories)[:limit]


# ==================== SIMPLE KEYWORD MATCHING (FALLBACK) ====================
def simple_keyword_match(query, memories):
    """Simple keyword matching as fallback"""
    if not memories:
        return []

    query_words = query.lower().split()
    scored = []

    for mem in memories:
        mem_text = mem['memory_text'].lower()
        score = sum(1 for word in query_words if word in mem_text)
        scored.append({
            'memory': mem,
            'score': score / max(len(query_words), 1),
            'created_at': mem['created_at']
        })

    scored.sort(key=lambda x: (x['score'], x['created_at']), reverse=True)
    return scored