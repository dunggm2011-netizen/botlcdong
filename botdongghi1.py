import telebot
import requests
import hashlib
import base64
import json
import logging
import threading
import time
import socketio
import random
import math
import os
from flask import Flask

# ==========================================
# CẤU HÌNH HỆ THỐNG BOT & LOGGING
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logging.getLogger('engineio').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# 🔴 CẤU HÌNH TOKEN VÀ ADMIN - HỖ TRỢ NHIỀU ADMIN
BOT_TOKEN = '8628395248:AAGOYfIVFzcrP1AGVnRN7HcnBiQe_D-hEaA'
ADMIN_IDS = [7564889663, 7887884775]  # 📌 NHIỀU ADMIN

# Cấu hình Bot thu thập dữ liệu chạy ngầm
DATA_COLLECTOR_USER = "nuphambaocode"
DATA_COLLECTOR_PASS = "nup123@"

bot = telebot.TeleBot(BOT_TOKEN)

vip_users = set(ADMIN_IDS)  # 📌 KHỞI TẠO VỚI DANH SÁCH ADMIN
active_sockets = {}
user_states = {}

# ==========================================
# DỮ LIỆU TOÀN CẦU & 35 LÕI AI ĐỘC LẬP (V3)
# ==========================================
GLOBAL_HISTORY = []
MAX_GLOBAL_HISTORY = 2000

GLOBAL_AI_WEIGHTS = {
    "trend": 1.0, "pattern": 1.0, "frequency": 1.0, "momentum": 1.0, "symmetry": 1.0,
    "alternating": 1.0, "fibonacci": 1.0, "chaos": 1.0, "shadow": 1.0,
    "markov1": 1.0, "markov2": 1.0, "markov3": 1.0,
    "rsi_indicator": 1.0, "macd_cross": 1.0, "pivot_reversal": 1.0, "cluster_3": 1.0,
    "parity": 1.0, "golden_ratio": 1.0, "quantum": 1.0,
    "anti_bait": 2.0, "smart_breaker": 2.0,
    "ngram_4": 1.5, "ngram_5": 1.5, "elliott_wave": 1.5,
    "contrarian": 2.0, "bollinger_bands": 1.5, "mean_reversion": 1.0,
    "mirror_reflection": 1.0, "martingale_trap": 1.5, "poisson_prob": 1.0,
    "harmonic_cycle": 1.0, "breakout_hunter": 1.5, "volume_fakeout": 1.5,
    "time_decay": 1.0, "neural_bias": 1.0, "twin_peaks": 1.0
}
GLOBAL_MODEL_STREAK = {k: 0 for k in GLOBAL_AI_WEIGHTS.keys()}

def init_user_state(chat_id):
    if chat_id not in user_states:
        user_states[chat_id] = {
            "profit_loss": 0, "auto_bet_enabled": False, "x2_mode": False,
            "win_streak": 0, "base_bet_amount": 10000, "current_bet": 10000,
            "target_profit": None, "current_prediction": None,
            "waiting_for_result": False, "has_bet_this_session": False,
            "session_id": None, "balance": 0, "last_predictions": {},
            "awaiting_input": None
        }

def is_vip(chat_id):
    return chat_id in vip_users or chat_id in ADMIN_IDS

# ==========================================
# 🧠 THUẬT TOÁN AI SIÊU CẤP V3 - 35 LÕI
# ==========================================
def make_prediction_vip(chat_id):
    history = GLOBAL_HISTORY
    weights = GLOBAL_AI_WEIGHTS
    
    if len(history) < 10:
        return random.choice(["TAI", "XIU"])
    
    predictions = {"TAI": 0.0, "XIU": 0.0}
    model_preds = {}

    last_item = history[-1]
    opp_item = "XIU" if last_item == "TAI" else "TAI"
    recent_str = "".join(["T" if x == "TAI" else "X" for x in history])
    streak = len(recent_str) - len(recent_str.rstrip(recent_str[-1]))

    model_preds["trend"] = last_item if history[-5:].count(last_item) >= 3 else opp_item
    model_preds["pattern"] = opp_item if recent_str.endswith("TXTX") or recent_str.endswith("TTXX") else last_item
    
    t1 = {"TAI": {"TAI": 0, "XIU": 0}, "XIU": {"TAI": 0, "XIU": 0}}
    for i in range(len(history) - 1): t1[history[i]][history[i+1]] += 1
    model_preds["markov1"] = "TAI" if t1[last_item]["TAI"] > t1[last_item]["XIU"] else "XIU"
    model_preds["markov2"] = "TAI" if history[-2:] == ["TAI", "TAI"] else "XIU"
    model_preds["markov3"] = opp_item if history[-3:] == [last_item]*3 else model_preds["markov2"]

    model_preds["frequency"] = "XIU" if history[-20:].count("TAI") > 10 else "TAI"
    model_preds["momentum"] = "TAI" if sum([i+1 if res == "TAI" else -(i+1) for i, res in enumerate(history[-5:])]) > 0 else "XIU"
    model_preds["symmetry"] = opp_item if len(recent_str) >= 6 and recent_str[-6:-3] == recent_str[-3:][::-1] else last_item
    model_preds["alternating"] = opp_item
    model_preds["fibonacci"] = opp_item if streak in [3, 5, 8, 13] else last_item
    model_preds["chaos"] = opp_item if sum(1 for i in range(len(recent_str[-10:]) - 1) if recent_str[-10:][i] != recent_str[-10:][i+1]) >= 7 else last_item
    model_preds["shadow"] = "TAI" if history[-50:].count("TAI") < 25 else "XIU"
    
    rsi_score = recent_str[-10:].count("T")
    model_preds["rsi_indicator"] = "XIU" if rsi_score >= 7 else ("TAI" if rsi_score <= 3 else last_item)
    model_preds["macd_cross"] = "TAI" if recent_str[-3:].count("T") > (recent_str[-9:].count("T") / 3) else "XIU"
    model_preds["pivot_reversal"] = history[-1] if history[-3] == history[-2] and history[-2] != history[-1] else last_item
    model_preds["cluster_3"] = "TAI" if recent_str[-3:] in ["TTT", "TXX", "XTX", "XXT"] else "XIU"
    model_preds["parity"] = opp_item if streak % 2 == 0 else last_item
    model_preds["golden_ratio"] = "TAI" if (history[-30:].count("TAI") / 30) < 0.618 else "XIU"
    model_preds["quantum"] = random.choice(["TAI", "XIU"])
    
    model_preds["anti_bait"] = opp_item if streak >= 5 or recent_str.endswith("TXTXT") else last_item
    
    max_streak = 1; cur = 1
    for i in range(1, len(history)):
        if history[i] == history[i-1]: cur += 1
        else: max_streak = max(max_streak, cur); cur = 1
    model_preds["smart_breaker"] = opp_item if streak >= max_streak - 1 and streak >= 3 else last_item

    l4 = recent_str[-4:]
    t_c4 = recent_str[:-1].count(l4 + "T")
    x_c4 = recent_str[:-1].count(l4 + "X")
    model_preds["ngram_4"] = "TAI" if t_c4 > x_c4 else ("XIU" if x_c4 > t_c4 else opp_item)

    l5 = recent_str[-5:]
    t_c5 = recent_str[:-1].count(l5 + "T")
    x_c5 = recent_str[:-1].count(l5 + "X")
    model_preds["ngram_5"] = "TAI" if t_c5 > x_c5 else ("XIU" if x_c5 > t_c5 else opp_item)

    if recent_str.endswith("TXTXT"): model_preds["elliott_wave"] = last_item
    elif recent_str.endswith("TTXXTT"): model_preds["elliott_wave"] = "XIU"
    else: model_preds["elliott_wave"] = opp_item

    if streak == 4 or streak == 6: model_preds["contrarian"] = opp_item
    elif recent_str[-6:] == "TXTXTX": model_preds["contrarian"] = "XIU"
    else: model_preds["contrarian"] = last_item

    ma10 = recent_str[-10:].count("T") / 10.0
    if ma10 >= 0.8: model_preds["bollinger_bands"] = "XIU"
    elif ma10 <= 0.2: model_preds["bollinger_bands"] = "TAI"
    else: model_preds["bollinger_bands"] = last_item

    t_total = history[-100:].count("TAI") if len(history) >= 100 else history.count("TAI")
    model_preds["mean_reversion"] = "TAI" if t_total < (len(history[-100:]) * 0.45) else "XIU"

    if len(recent_str) >= 8:
        model_preds["mirror_reflection"] = "TAI" if recent_str[-8] == "T" else "XIU"
    else: model_preds["mirror_reflection"] = opp_item

    model_preds["martingale_trap"] = opp_item if streak == 3 or streak == 7 else last_item
    model_preds["poisson_prob"] = "TAI" if (history[-5:].count("TAI") % 2 == 1) else "XIU"
    model_preds["harmonic_cycle"] = history[-4] if len(history) >= 4 else opp_item
    model_preds["breakout_hunter"] = last_item if streak == 1 and history[-2] == history[-3] else opp_item

    if len(recent_str) >= 5 and recent_str[-5:] in ["TTTXT", "XXXTX"]: model_preds["volume_fakeout"] = last_item
    else: model_preds["volume_fakeout"] = opp_item

    model_preds["time_decay"] = opp_item
    model_preds["neural_bias"] = "TAI" if history[-7:].count("TAI") > 3 else "XIU"
    model_preds["twin_peaks"] = opp_item if recent_str.endswith("TTXTT") or recent_str.endswith("XXTXX") else last_item

    if chat_id in user_states:
        user_states[chat_id]["last_predictions"] = model_preds

    for model, pred in model_preds.items():
        amplified_weight = math.pow(weights[model], 1.5)
        predictions[pred] += amplified_weight

    return "TAI" if predictions["TAI"] > predictions["XIU"] else "XIU"

def update_global_ai_weights(actual_result, chat_id=None):
    global GLOBAL_AI_WEIGHTS, GLOBAL_MODEL_STREAK
    if chat_id and chat_id in user_states and "last_predictions" in user_states[chat_id]:
        preds = user_states[chat_id]["last_predictions"]
    else: return

    for model, pred in preds.items():
        if pred == actual_result:
            GLOBAL_MODEL_STREAK[model] += 1
            bonus = 0.5 + (0.2 * GLOBAL_MODEL_STREAK[model])
            GLOBAL_AI_WEIGHTS[model] = min(20.0, GLOBAL_AI_WEIGHTS[model] + bonus)
        else:
            GLOBAL_MODEL_STREAK[model] = 0
            GLOBAL_AI_WEIGHTS[model] = max(0.1, GLOBAL_AI_WEIGHTS[model] - 2.5)

# ==========================================
# 🌐 LOGIC API & WEBSOCKET
# ==========================================
def md5_hash(text: str) -> str: return hashlib.md5(text.encode('utf-8')).hexdigest()

def login_and_get_token(username: str, password: str) -> dict:
    pw_md5 = md5_hash(password)
    url = f"https://apifo88daigia.tele68.com/api?c=3&un={username}&pw={pw_md5}&cp=R&cl=R&pf=web&at="
    try:
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        data = r.json()
        if not data.get("success"): return {"_error": f"Lỗi Game: {str(data.get('message', 'Sai thông tin'))}"}
        
        session_key = data["sessionKey"]
        session_key += "=" * ((4 - len(session_key) % 4) % 4)
        session_data = json.loads(base64.b64decode(session_key).decode('utf-8'))
        nickname = session_data.get("nickname") or session_data.get("nickName")
        
        access_token = data["accessToken"]
        r2 = requests.post("https://wlb.tele68.com/v1/lobby/auth/login?cp=R&cl=R&pf=web&at=", 
                           headers={"authority": "wlb.tele68.com", "content-type": "application/json"}, 
                           json={"nickName": nickname, "accessToken": access_token}, timeout=12)
        lobby = r2.json()
        token = lobby.get("token")
        if not token: return {"_error": "Lobby không trả về JWT token."}
        return {"token": token, "nickname": nickname, "money": lobby.get("remoteLoginResp", {}).get("money", 0)}
    except Exception as e:
        return {"_error": f"Lỗi kết nối: {e}"}

def start_websocket(chat_id, token, is_background=False):
    if chat_id in active_sockets and not is_background:
        try: active_sockets[chat_id].disconnect()
        except: pass

    sio = socketio.Client(reconnection=True, reconnection_attempts=10, logger=False, engineio_logger=False)
    if not is_background:
        active_sockets[chat_id] = sio
        init_user_state(chat_id)

    @sio.event(namespace='/txmd5')
    def connect():
        if not is_background:
            bot.send_message(chat_id, "🟢 <b>HỆ THỐNG V3: ĐÃ KẾT NỐI API</b>\n<i>Kích hoạt 35 lõi AI tính toán Lũy Thừa...</i>", parse_mode="HTML")

    @sio.on('new-session', namespace='/txmd5')
    def on_new_session(data):
        if is_background: return
        state = user_states[chat_id]
        state["session_id"] = data.get('id', 'N/A')
        state["has_bet_this_session"] = False
        
        if state["auto_bet_enabled"] and state["target_profit"] is not None:
            if state["profit_loss"] >= state["target_profit"]:
                state["auto_bet_enabled"] = False
                msg_win = (f"🏆 <b>CHÚC MỪNG! ĐÃ ĐẠT TARGET CHỐT LÃI</b> 🏆\n"
                           f"💰 Thực lãi: <code>{state['profit_loss']:,}</code> Win\n"
                           f"🎯 Mục tiêu: <code>{state['target_profit']:,}</code> Win\n"
                           f"🔴 <i>Bot đã tắt Auto Bet an toàn.</i>")
                bot.send_message(chat_id, msg_win, parse_mode="HTML")

        history_len = len(GLOBAL_HISTORY)
        prediction = make_prediction_vip(chat_id) if history_len >= 10 else None
        state["current_prediction"] = prediction

        if state["x2_mode"] and state["win_streak"] >= 1:
            state["current_bet"] = state["base_bet_amount"] * 2
        else:
            state["current_bet"] = state["base_bet_amount"]

        msg = f"🔔 <b>PHIÊN MỚI:</b> <code>#{state['session_id']}</code>\n"
        if prediction:
            pred_emoji = "🔵 TÀI" if prediction == "TAI" else "🔴 XỈU"
            msg += f"🔥 <b>AI [V3] CHỐT CẦU: {pred_emoji}</b>\n"
            if state["auto_bet_enabled"]:
                if state["x2_mode"] and state["win_streak"] >= 1:
                    msg += f"⚡ <i>Cầu Thông! X2 Nhồi tiền: <code>{state['current_bet']:,}</code> Win...</i>"
                else:
                    msg += f"⏳ <i>Vào cược gốc: <code>{state['current_bet']:,}</code> Win...</i>"
            else: msg += "⏸ <i>Auto đang tắt. Bấm nút bên dưới để bật.</i>"
        else: msg += f"⏳ <i>Đang thu thập đủ 10 tay để Deep Learning: {history_len}/10...</i>"

        bot.send_message(chat_id, msg, parse_mode="HTML")

    @sio.on('tick-update', namespace='/txmd5')
    def on_tick_update(data):
        if is_background: return
        game_state = data.get('state')
        state = user_states[chat_id]
        
        if game_state == 'BETTING' and state["auto_bet_enabled"] and state["current_prediction"]:
            if not state["has_bet_this_session"]:
                sio.emit('bet', {"type": state["current_prediction"], "amount": state["current_bet"]}, namespace='/txmd5')
                state["has_bet_this_session"] = True
                state["waiting_for_result"] = True
                bot.send_message(chat_id, f"🚀 <b>ĐÃ VÀO TIỀN:</b> <code>{state['current_bet']:,}</code> Win", parse_mode="HTML")

    @sio.on('bet-result', namespace='/txmd5')
    def on_bet_result(data):
        if is_background: return
        if "postBalance" in data: user_states[chat_id]["balance"] = data["postBalance"]
        sio.emit('get-current-my-info', None, namespace='/txmd5')

    @sio.on('session-result', namespace='/txmd5')
    def on_session_result(data):
        global GLOBAL_HISTORY
        result = data.get('resultTruyenThong', 'N/A')
        
        if result in ["TAI", "XIU"]:
            GLOBAL_HISTORY.append(result)
            if len(GLOBAL_HISTORY) > MAX_GLOBAL_HISTORY: GLOBAL_HISTORY.pop(0)
            if not is_background: update_global_ai_weights(result, chat_id)
            else: update_global_ai_weights(result, None) 

        if is_background: return

        state = user_states[chat_id]
        dices = data.get('dices', [0, 0, 0])
        result_emoji = "🔵 TÀI" if result == "TAI" else ("🔴 XỈU" if result == "XIU" else "⚪ LỖI")
        msg = f"🎲 <b>KẾT QUẢ: {result_emoji}</b> ({dices[0]}-{dices[1]}-{dices[2]})\n"

        if state["current_prediction"]:
            if state["current_prediction"] == result:
                if state["waiting_for_result"]:
                    win_amount = int(state["current_bet"] * 0.98) 
                    state["profit_loss"] += win_amount
                    state["win_streak"] += 1
                    msg += f"✅ <b>HÚP ĐẬM!</b> Thực Lãi: <code>+{win_amount:,}</code> Win\n"
            else:
                if state["waiting_for_result"]:
                    state["profit_loss"] -= state["current_bet"]
                    state["win_streak"] = 0
                    msg += f"❌ <b>GÃY CẦU!</b> Đã quay về mốc vốn gốc.\n"
            state["waiting_for_result"] = False

        status_pl = "🟢" if state["profit_loss"] >= 0 else "🔴"
        msg += f"━━━━━━━━━━━━━━━━━━\n📊 <b>Lãi/Lỗ:</b> {status_pl} <code>{state['profit_loss']:,}</code>\n💳 <b>Số Dư:</b> <code>{state['balance']:,}</code>"
        bot.send_message(chat_id, msg, parse_mode="HTML")

    try:
        sio.connect('https://wtxmd52.tele68.com', socketio_path='txmd5/', namespaces=['/txmd5'], transports=['websocket'], auth={"token": token}, headers={"User-Agent": "Mozilla/5.0"})
        sio.wait()
    except Exception as e:
        if not is_background: bot.send_message(chat_id, f"⚠️ Lỗi kết nối: <code>{e}</code>", parse_mode="HTML")

def background_data_collector():
    if DATA_COLLECTOR_USER != "acc_clone_soi_cau":
        logger.info("Khởi động AI soi cầu ngầm 24/7...")
        while True:
            try:
                res = login_and_get_token(DATA_COLLECTOR_USER, DATA_COLLECTOR_PASS)
                if "token" in res:
                    logger.info("Đã kết nối ngầm. Bắt đầu thu thập & Train 35 Lõi AI...")
                    start_websocket("BACKGROUND_WORKER", res["token"], is_background=True)
            except Exception: pass
            time.sleep(30)

# ==========================================
# 🎛️ HÀM TẠO GIAO DIỆN BẢNG ĐIỀU KHIỂN (INLINE KEYBOARD)
# ==========================================
def get_control_markup(chat_id):
    init_user_state(chat_id)
    state = user_states[chat_id]
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    
    btn_login = telebot.types.InlineKeyboardButton("🔑 Đăng Nhập Game", callback_data="ui_login")
    
    auto_text = "🟢 Tắt Auto" if state["auto_bet_enabled"] else "🔴 Bật Auto"
    btn_auto = telebot.types.InlineKeyboardButton(auto_text, callback_data="ui_toggle_auto")
    
    x2_text = "🔥 Tắt X2" if state["x2_mode"] else "💤 Bật X2"
    btn_x2 = telebot.types.InlineKeyboardButton(x2_text, callback_data="ui_toggle_x2")
    
    btn_set_bet = telebot.types.InlineKeyboardButton(f"💰 Chỉnh Tiền Cược ({state['base_bet_amount']:,})", callback_data="ui_set_bet")
    btn_target = telebot.types.InlineKeyboardButton("🎯 Đặt Target Lãi", callback_data="ui_set_target")
    
    btn_stats = telebot.types.InlineKeyboardButton("📊 Thống Kê", callback_data="ui_stats")
    btn_weights = telebot.types.InlineKeyboardButton("🧠 Top 15 Core", callback_data="ui_weights")
    
    btn_stop = telebot.types.InlineKeyboardButton("🔌 Ngắt Bot (Stop)", callback_data="ui_stop")
    
    markup.add(btn_login)
    markup.add(btn_auto, btn_x2)
    markup.add(btn_set_bet, btn_target)
    markup.add(btn_stats, btn_weights)
    markup.add(btn_stop)
    
    return markup

# ==========================================
# 🤖 XỬ LÝ LỆNH VÀ NÚT BẤM (CALLBACK QUERY)
# ==========================================
@bot.message_handler(commands=['start', 'help', 'menu'])
def send_welcome(message):
    chat_id = message.chat.id
    if not is_vip(chat_id):
        return bot.reply_to(message, f"⛔ Đọc ID này cho Admin: <code>{chat_id}</code>", parse_mode="HTML")
    
    init_user_state(chat_id)
    text = (
        "🤖 <b>AI TÀI XỈU ULTRA VIP V3 - 35 LÕI</b> 🤖\n\n"
        "👇 <i>Hệ thống bảng điều khiển đã sẵn sàng. Bấm nút bên dưới để tùy chỉnh nhanh:</i>"
    )
    bot.send_message(chat_id, text, reply_markup=get_control_markup(chat_id), parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    chat_id = call.message.chat.id
    if not is_vip(chat_id): return
    init_user_state(chat_id)
    state = user_states[chat_id]
    data = call.data

    if data == "ui_login":
        state["awaiting_input"] = "login"
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "👉 Gửi thông tin đăng nhập theo cú pháp:\n<code>tài_khoản mật_khẩu</code>", parse_mode="HTML")

    elif data == "ui_toggle_auto":
        state["auto_bet_enabled"] = not state["auto_bet_enabled"]
        status = "BẬT 🟢" if state["auto_bet_enabled"] else "TẮT 🔴"
        bot.answer_callback_query(call.id, text=f"Đã {status} Auto Bet")
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_control_markup(chat_id))

    elif data == "ui_toggle_x2":
        state["x2_mode"] = not state["x2_mode"]
        status = "BẬT 🔥" if state["x2_mode"] else "TẮT 💤"
        bot.answer_callback_query(call.id, text=f"Đã {status} chế độ X2")
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_control_markup(chat_id))

    elif data == "ui_set_bet":
        state["awaiting_input"] = "bet_amount"
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "👉 Nhập số tiền cược gốc mới muốn thay đổi (Ví dụ: <code>20000</code>):", parse_mode="HTML")

    elif data == "ui_set_target":
        state["awaiting_input"] = "target_profit"
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "👉 Nhập hạn mức target chốt lãi (Ví dụ: <code>500000</code>):", parse_mode="HTML")

    elif data == "ui_stats":
        bot.answer_callback_query(call.id)
        t_text = f"<code>{state['target_profit']:,}</code>" if state['target_profit'] else "Không"
        stat_msg = (f"📊 <b>THỐNG KÊ HIỆN TẠI</b>\n"
                    f"💳 Dư: <code>{state['balance']:,}</code>\n"
                    f"📈 Lãi/Lỗ: <code>{state['profit_loss']:,}</code>\n"
                    f"🎯 Target: {t_text}\n"
                    f"🤖 Auto: {'BẬT' if state['auto_bet_enabled'] else 'TẮT'}\n"
                    f"🔥 X2: {'BẬT' if state['x2_mode'] else 'TẮT'} (Streak: {state['win_streak']})")
        bot.send_message(chat_id, stat_msg, parse_mode="HTML")

    elif data == "ui_weights":
        bot.answer_callback_query(call.id)
        text = "🧠 <b>TOP 15 CORE BẮT CHUẨN (V3 Lũy Thừa):</b>\n"
        for k, v in sorted(GLOBAL_AI_WEIGHTS.items(), key=lambda x: x[1], reverse=True)[:15]:
            text += f"▪️ {k}: <code>{v:.2f}</code> điểm\n"
        bot.send_message(chat_id, text, parse_mode="HTML")

    elif data == "ui_stop":
        bot.answer_callback_query(call.id)
        if chat_id in active_sockets:
            active_sockets[chat_id].disconnect()
            del active_sockets[chat_id]
        state["auto_bet_enabled"] = False
        bot.send_message(chat_id, "🔌 Đã ngắt kết nối an toàn và tắt Auto.", reply_markup=get_control_markup(chat_id), parse_mode="HTML")

@bot.message_handler(func=lambda message: True)
def handle_text_inputs(message):
    chat_id = message.chat.id
    if not is_vip(chat_id): return
    init_user_state(chat_id)
    state = user_states[chat_id]
    
    awaiting = state.get("awaiting_input")
    if not awaiting: return

    if awaiting == "login":
        parts = message.text.split()
        if len(parts) != 2:
            return bot.reply_to(message, "👉 Nhập sai cú pháp! Vui lòng nhập: <code>tài_khoản mật_khẩu</code>", parse_mode="HTML")
        
        state["awaiting_input"] = None
        msg_proc = bot.reply_to(message, "🔄 Loading 35 Cores Engine...", parse_mode="HTML")
        result = login_and_get_token(parts[0], parts[1])
        if "_error" in result:
            return bot.edit_message_text(f"❌ <b>LỖI:</b> {result['_error']}", chat_id=chat_id, message_id=msg_proc.message_id, parse_mode="HTML")
        
        state["balance"] = result['money']
        bot.edit_message_text(f"🎉 <b>ĐĂNG NHẬP THÀNH CÔNG V3</b>\n👤 <code>{result['nickname']}</code>\n💰 Dư: <code>{result['money']:,}</code>\n🌍 Data: {len(GLOBAL_HISTORY)} vòng", chat_id=chat_id, message_id=msg_proc.message_id, parse_mode="HTML")
        bot.send_message(chat_id, "🎛️ Bảng điều khiển:", reply_markup=get_control_markup(chat_id), parse_mode="HTML")
        threading.Thread(target=start_websocket, args=(chat_id, result['token']), daemon=True).start()

    elif awaiting == "bet_amount":
        try:
            amount = int(message.text.strip())
            state["base_bet_amount"] = amount
            state["awaiting_input"] = None
            bot.reply_to(message, f"✅ Đã cập nhật tiền cược gốc thành: <code>{amount:,}</code> Win", reply_markup=get_control_markup(chat_id), parse_mode="HTML")
        except:
            bot.reply_to(message, "👉 Vui lòng chỉ nhập số nguyên hợp lệ!")

    elif awaiting == "target_profit":
        try:
            target = int(message.text.strip())
            state["target_profit"] = target
            state["awaiting_input"] = None
            bot.reply_to(message, f"🎯 Đã đặt target chốt lãi thành: <code>{target:,}</code> Win", reply_markup=get_control_markup(chat_id), parse_mode="HTML")
        except:
            bot.reply_to(message, "👉 Vui lòng chỉ nhập số nguyên hợp lệ!")

# ==========================================
# 🚀 FLASK - GIỮ BOT SỐNG TRÊN RENDER
# ==========================================
app = Flask(__name__)

@app.route('/')
def index():
    return f"🤖 BOT ULTRA VIP V3 ĐANG CHẠY! {int(time.time())}"

def run_flask():
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Chạy Flask thread
    threading.Thread(target=run_flask, daemon=True).start()

    print("==================================================")
    print("🤖 SYSTEM ONLINE: ULTRA VIP V3 - 35 CORES + INLINE UI")
    print(f"👑 ADMIN IDS: {ADMIN_IDS}")
    print("==================================================")
    
    t = threading.Thread(target=background_data_collector, daemon=True)
    t.start()
    bot.infinity_polling()
