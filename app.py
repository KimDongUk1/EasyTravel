from flask import Flask, render_template, request, jsonify
import os, requests
from dotenv import load_dotenv
from openai import OpenAI  # 최신 방식으로 불러오기

load_dotenv()
app = Flask(__name__)

# API 키 가져오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")
TRAWEL_API_KEY = os.getenv("TRAWEL_API_KEY")

# OpenAI 클라이언트 생성 (한 번만)
client = OpenAI(api_key=OPENAI_API_KEY)

@app.route("/")
def index():
  return render_template("index.html")

@app.route("/chat")
def chat_ui():
  return render_template("chat.html")

@app.route("/api/chat", methods=["POST"])
def chat():
  user_message = request.json["message"]
  try:
    chat_response = client.chat.completions.create(
      model="gpt-3.5-turbo",  # gpt-4o도 가능하나 비용 ↑
      messages=[{"role": "user", "content": user_message}]
    )
    reply = chat_response.choices[0].message.content
  except Exception as e:
    reply = f"[GPT 오류] {str(e)}"
  return jsonify({"reply": reply})

@app.route("/api/recommend", methods=["POST"])
def recommend():
  data = request.json
  destination = data["destination"]
  duration = data["duration"]
  budget = data["budget"]

  prompt = f"""
다음 조건에 맞춰 여행지를 추천하고 요일별 일정 및 항공/호텔 안내를 제공해줘:

여행지: {destination}
여행 기간: {duration}
예산: {budget}

개인 맞춤형으로 응답해줘.
    """

  # GPT 응답
  try:
    chat_response = client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=[{"role": "user", "content": prompt}]
    )
    gpt_text = chat_response.choices[0].message.content
  except Exception as e:
    gpt_text = f"[ChatGPT 오류] {str(e)}"

  # Kakao 장소 검색
  try:
    kakao_res = requests.get(
      "https://dapi.kakao.com/v2/local/search/keyword.json",
      headers={"Authorization": f"KakaoAK {KAKAO_API_KEY}"},
      params={"query": destination}
    )
    kakao_data = kakao_res.json()

    if "documents" in kakao_data and kakao_data["documents"]:
      kakao_text = "\n📍 Kakao 검색 결과 Top 3:\n"
      for place in kakao_data["documents"][:3]:
        kakao_text += f"- {place['place_name']} ({place['address_name']})\n"
    else:
      kakao_text = "[Kakao 결과 없음 또는 키 오류]"
  except Exception as e:
    kakao_text = f"[Kakao 오류] {str(e)}"

  # Trawel.io 여행지 요약
  try:
    trawel_res = requests.get(
      "https://trawel.p.rapidapi.com/location",
      headers={
        "X-RapidAPI-Key": TRAWEL_API_KEY,
        "X-RapidAPI-Host": "trawel.p.rapidapi.com"
      },
      params={"name": destination}
    )
    trawel_text = f"\n🧭 Trawel.io 여행 요약:\n{trawel_res.json().get('summary', '정보 없음')}"
  except Exception as e:
    trawel_text = f"[Trawel 오류] {str(e)}"

  # 결과 통합
  result = f"{gpt_text}\n{kakao_text}\n{trawel_text}"
  return jsonify({"result": result})



if __name__ == "__main__":
  app.run(debug=True)

