"""MiMo TTS 拟人化语音配置"""

# 情绪 prompt 模板
VOICE_PROFILES = {
    'default': '用自然亲切的语气说，像跟朋友聊天一样，语速适中，带点微笑的感觉',
    'happy': '用轻快上扬的语调说，带着兴奋和开心的感觉，语速稍快，声音明亮有活力',
    'sad': '用低沉缓慢的语气说，带点失落和难过，语速偏慢，声音轻柔',
    'angry': '用严肃紧张的语气说，语速加快，咬字用力，带着不满的情绪',
    'comfort': '用温柔安慰的语气说，带点心疼的感觉，语速放慢，声音轻柔温暖',
    'excited': '用激动惊喜的语气说，语速快，声音高亢，带着难以置信的感觉',
    'serious': '用认真严肃的语气说，语速适中，咬字清晰，不带多余情绪',
    'playful': '用俏皮调皮的语气说，带着恶作剧得逞的得意，语速轻快',
    'tired': '用疲惫无力的语气说，语速很慢，有气无力，带点叹气',
    'whisper': '用低声耳语的方式说，声音很轻，像在说悄悄话',
}

# 行内标签
INLINE_TAGS = {
    'laugh': '（笑）',
    'sigh': '（叹气）',
    'breath': '（深呼吸）',
    'cry': '（抽泣）',
    'cough': '（咳嗽）',
    'pause': '（沉默片刻）',
    'fast': '（语速加快）',
    'slow': '（语速放慢）',
}

def get_voice_profile(emotion='default'):
    return VOICE_PROFILES.get(emotion, VOICE_PROFILES['default'])

def add_inline_tags(text, tags=None):
    if not tags:
        return text
    for tag in tags:
        if tag in INLINE_TAGS:
            text = INLINE_TAGS[tag] + text
    return text
